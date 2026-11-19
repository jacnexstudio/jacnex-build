"""Copia las versiones publicadas en GitHub (jacnexstudio) a Cloudflare R2: descargas.jacnex.store.

Jacnex Studio y las apps buscan versiones y descargan desde descargas.jacnex.store, con las mismas
rutas que GitHub (el cambio de marca reemplaza github.com por esa dirección al compilar):

    api/repos/<dueño>/<repo>/releases/latest          JSON de la última versión (como la API de GitHub)
    api/repos/<dueño>/<repo>/releases                 JSON con la lista de versiones copiadas
    <dueño>/<repo>/releases/download/<tag>/<archivo>  los archivos de cada versión
    <dueño>/<repo>/releases/latest/download/<archivo> solo Jacnex Studio: enlace fijo del instalador
    <dueño>/<repo>, .../releases, .../releases/tag/<tag>  páginas que llevan a app.jacnex.store

Así los repositorios de GitHub pueden ser privados: el token de GitHub (GH_TOKEN) solo se usa
aquí, para leer las versiones, y nunca llega a los clientes.

    python espejo_r2.py sincronizar <repo> [<repo> ...] [--versiones 3]
    python espejo_r2.py probar

Claves de R2: variables R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT (y R2_BUCKET,
por defecto jacnex-descargas), o --claves <archivo> con líneas CLAVE=valor
(ACCESS_KEY_ID, SECRET_ACCESS_KEY, ENDPOINT). Solo usa la biblioteca estándar de Python.
"""

import argparse
import datetime
import hashlib
import hmac
import http.client
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

PUBLICO = "https://descargas.jacnex.store"
DUENO = "jacnexstudio"
LANZADOR = "jacnex-studio"
WEB = "https://app.jacnex.store"
AGENTE = "jacnex-espejo"

# Repositorio -> página de la web a la que llevan los enlaces "ver en la web" del launcher.
PAGINAS = {
    LANZADOR: f"{WEB}/descargar/",
    "photocraft": f"{WEB}/apps/photonex/",
    "lightcraft": f"{WEB}/apps/lightnex/",
    "vectorcraft": f"{WEB}/apps/vectornex/",
    "filmcraft": f"{WEB}/apps/filmnex/",
    "effectcraft": f"{WEB}/apps/motionex/",
    "designcraft": f"{WEB}/apps/layoutnex/",
    "pdfcraft": f"{WEB}/apps/readnex/",
}
NOMBRES = {
    LANZADOR: "Jacnex Studio",
    "photocraft": "Photonex",
    "lightcraft": "Lightnex",
    "vectorcraft": "Vectornex",
    "filmcraft": "Filmnex",
    "effectcraft": "Motionex",
    "designcraft": "Layoutnex",
    "pdfcraft": "Readnex",
}

ARCHIVO_VALIDO = re.compile(r"^[A-Za-z0-9._+-]+$")
ETIQUETA_VALIDA = re.compile(r"^[A-Za-z0-9._+-]+$")


class Error(Exception):
    pass


# ---------------------------------------------------------------- R2 (API S3, firma SigV4)

class R2:
    def __init__(self, clave_id, secreto, endpoint, bucket):
        u = urllib.parse.urlsplit(endpoint.strip().rstrip("/"))
        if u.scheme != "https" or not u.hostname:
            raise Error("ENDPOINT de R2 inválido")
        self.host = u.hostname
        self.clave_id = clave_id.strip()
        self.secreto = secreto.strip()
        self.bucket = bucket

    def _firmar(self, metodo, ruta, consulta, cabeceras, hash_cuerpo):
        ahora = datetime.datetime.now(datetime.timezone.utc)
        fecha_larga = ahora.strftime("%Y%m%dT%H%M%SZ")
        fecha = ahora.strftime("%Y%m%d")
        cabeceras = {k.lower(): str(v).strip() for k, v in cabeceras.items()}
        cabeceras["host"] = self.host
        cabeceras["x-amz-date"] = fecha_larga
        cabeceras["x-amz-content-sha256"] = hash_cuerpo
        nombres = sorted(cabeceras)
        canon_cab = "".join(f"{k}:{cabeceras[k]}\n" for k in nombres)
        firmadas = ";".join(nombres)
        canon_consulta = "&".join(
            f"{urllib.parse.quote(k, safe='-_.~')}={urllib.parse.quote(v, safe='-_.~')}" for k, v in sorted(consulta.items())
        )
        canon = "\n".join([metodo, ruta, canon_consulta, canon_cab, firmadas, hash_cuerpo])
        alcance = f"{fecha}/auto/s3/aws4_request"
        texto = "\n".join(["AWS4-HMAC-SHA256", fecha_larga, alcance, hashlib.sha256(canon.encode()).hexdigest()])

        def h(k, m):
            return hmac.new(k, m.encode(), hashlib.sha256).digest()

        k = h(h(h(h(("AWS4" + self.secreto).encode(), fecha), "auto"), "s3"), "aws4_request")
        firma = hmac.new(k, texto.encode(), hashlib.sha256).hexdigest()
        cabeceras["authorization"] = f"AWS4-HMAC-SHA256 Credential={self.clave_id}/{alcance}, SignedHeaders={firmadas}, Signature={firma}"
        return cabeceras

    def _ruta(self, clave):
        return "/" + self.bucket + ("/" + urllib.parse.quote(clave, safe="/-_.~") if clave else "")

    def pedir(self, metodo, clave="", consulta=None, cuerpo=b"", cabeceras=None, largo=None, hash_cuerpo=None):
        consulta = consulta or {}
        cab = dict(cabeceras or {})
        if hash_cuerpo is None:
            hash_cuerpo = hashlib.sha256(cuerpo if isinstance(cuerpo, bytes) else b"").hexdigest()
        ruta = self._ruta(clave)
        cab = self._firmar(metodo, ruta, consulta, cab, hash_cuerpo)
        if largo is not None:
            cab["content-length"] = str(largo)
        elif isinstance(cuerpo, bytes) and metodo in ("PUT", "POST"):
            cab["content-length"] = str(len(cuerpo))
        url = ruta + ("?" + urllib.parse.urlencode(sorted(consulta.items()), quote_via=urllib.parse.quote) if consulta else "")
        for intento in range(4):
            con = http.client.HTTPSConnection(self.host, timeout=300)
            try:
                if hasattr(cuerpo, "seek"):
                    cuerpo.seek(0)
                con.request(metodo, url, body=cuerpo if cuerpo != b"" else None, headers=cab)
                r = con.getresponse()
                datos = r.read()
                if r.status >= 500 and intento < 3:
                    time.sleep(2 * (intento + 1))
                    continue
                return r.status, dict((k.lower(), v) for k, v in r.getheaders()), datos
            except (OSError, http.client.HTTPException):
                if intento == 3:
                    raise
                time.sleep(2 * (intento + 1))
            finally:
                con.close()
        raise Error("R2 no respondió")

    def tamano(self, clave):
        s, cab, _ = self.pedir("HEAD", clave)
        if s == 404:
            return None
        if s != 200:
            raise Error(f"R2 HEAD {clave}: HTTP {s}")
        return int(cab.get("content-length", "-1"))

    def subir_bytes(self, clave, datos, tipo, cache="public, max-age=60"):
        s, _, r = self.pedir("PUT", clave, cuerpo=datos, cabeceras={"content-type": tipo, "cache-control": cache})
        if s != 200:
            raise Error(f"R2 PUT {clave}: HTTP {s} {r[:300]!r}")

    def subir_archivo(self, clave, ruta, tipo, cache="public, max-age=31536000, immutable"):
        largo = os.path.getsize(ruta)
        with open(ruta, "rb") as f:
            s, _, r = self.pedir("PUT", clave, cuerpo=f, cabeceras={"content-type": tipo, "cache-control": cache},
                                 largo=largo, hash_cuerpo="UNSIGNED-PAYLOAD")
        if s != 200:
            raise Error(f"R2 PUT {clave}: HTTP {s} {r[:300]!r}")

    def copiar(self, origen, destino, cache="public, max-age=300"):
        fuente = urllib.parse.quote(f"{self.bucket}/{origen}", safe="/-_.~")
        s, _, r = self.pedir("PUT", destino, cabeceras={
            "x-amz-copy-source": fuente, "x-amz-metadata-directive": "REPLACE",
            "content-type": "application/octet-stream", "cache-control": cache})
        if s != 200:
            raise Error(f"R2 COPY {origen} -> {destino}: HTTP {s} {r[:300]!r}")

    def listar(self, prefijo):
        claves, token = [], None
        while True:
            consulta = {"list-type": "2", "prefix": prefijo}
            if token:
                consulta["continuation-token"] = token
            s, _, r = self.pedir("GET", "", consulta=consulta)
            if s != 200:
                raise Error(f"R2 LIST {prefijo}: HTTP {s} {r[:300]!r}")
            raiz = ET.fromstring(r)
            ns = {"s": raiz.tag.split("}")[0].strip("{")} if raiz.tag.startswith("{") else {}
            p = "s:" if ns else ""
            for c in raiz.findall(f"{p}Contents", ns):
                claves.append((c.find(f"{p}Key", ns).text, int(c.find(f"{p}Size", ns).text)))
            if (raiz.findtext(f"{p}IsTruncated", default="false", namespaces=ns)) != "true":
                return claves
            token = raiz.findtext(f"{p}NextContinuationToken", namespaces=ns)

    def borrar(self, clave):
        s, _, r = self.pedir("DELETE", clave)
        if s not in (200, 204):
            raise Error(f"R2 DELETE {clave}: HTTP {s} {r[:300]!r}")


def r2_desde(args):
    datos = {}
    if args.claves:
        with open(args.claves, encoding="utf-8-sig") as f:
            for linea in f:
                if "=" in linea:
                    k, v = linea.split("=", 1)
                    datos[k.strip().upper()] = v.strip()
    clave_id = os.environ.get("R2_ACCESS_KEY_ID") or datos.get("ACCESS_KEY_ID")
    secreto = os.environ.get("R2_SECRET_ACCESS_KEY") or datos.get("SECRET_ACCESS_KEY")
    endpoint = os.environ.get("R2_ENDPOINT") or datos.get("ENDPOINT")
    bucket = os.environ.get("R2_BUCKET") or datos.get("BUCKET") or "jacnex-descargas"
    if not (clave_id and secreto and endpoint):
        raise Error("faltan las claves de R2 (R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_ENDPOINT)")
    return R2(clave_id, secreto, endpoint, bucket)


# ---------------------------------------------------------------- GitHub (solo lectura)

def github(ruta, token, aceptar="application/vnd.github+json"):
    req = urllib.request.Request("https://api.github.com" + ruta, headers={
        "Accept": aceptar, "User-Agent": AGENTE, "X-GitHub-Api-Version": "2022-11-28",
        **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def descargar_asset(repo, asset, token, destino):
    """Descarga un archivo de una versión (funciona también con repositorios privados)."""
    req = urllib.request.Request(f"https://api.github.com/repos/{DUENO}/{repo}/releases/assets/{asset['id']}", headers={
        "Accept": "application/octet-stream", "User-Agent": AGENTE,
        **({"Authorization": f"Bearer {token}"} if token else {})})
    h = hashlib.sha256()
    with urllib.request.urlopen(req, timeout=600) as r, open(destino, "wb") as f:
        while True:
            bloque = r.read(1 << 20)
            if not bloque:
                break
            h.update(bloque)
            f.write(bloque)
    if os.path.getsize(destino) != asset["size"]:
        raise Error(f"{asset['name']}: tamaño distinto al publicado")
    return h.hexdigest()


# ---------------------------------------------------------------- JSON como la API de GitHub

def notas(repo, tag):
    return f"{NOMBRES.get(repo, repo)} {tag}"


def release_espejo(repo, rel, sumas):
    base = f"{PUBLICO}/{DUENO}/{repo}/releases"
    assets = []
    for a in rel["assets"]:
        if not ARCHIVO_VALIDO.match(a["name"]):
            continue
        sha = sumas.get(a["name"])
        assets.append({
            "name": a["name"],
            "size": a["size"],
            "content_type": a.get("content_type") or "application/octet-stream",
            "browser_download_url": f"{base}/download/{rel['tag_name']}/{a['name']}",
            **({"digest": f"sha256:{sha}"} if sha else {}),
            "created_at": a.get("created_at"),
            "updated_at": a.get("updated_at"),
        })
    return {
        "tag_name": rel["tag_name"],
        "name": f"{NOMBRES.get(repo, repo)} {rel['tag_name']}",
        "html_url": f"{base}/tag/{rel['tag_name']}",
        "draft": False,
        "prerelease": bool(rel.get("prerelease")),
        "created_at": rel.get("created_at"),
        "published_at": rel.get("published_at"),
        "body": notas(repo, rel["tag_name"]),
        "assets": assets,
    }


def pagina_redireccion(destino):
    return (
        "<!doctype html><html lang=\"es\"><head><meta charset=\"utf-8\">"
        f"<meta http-equiv=\"refresh\" content=\"0; url={destino}\"><link rel=\"canonical\" href=\"{destino}\">"
        "<meta name=\"robots\" content=\"noindex\"><title>Jacnex Studio</title></head>"
        f"<body><a href=\"{destino}\">Jacnex Studio</a></body></html>"
    ).encode()


def leer_sumas(ruta):
    sumas = {}
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            m = re.match(r"^([0-9a-fA-F]{64})\s+\*?(\S+)\s*$", linea)
            if m:
                sumas[m.group(2)] = m.group(1).lower()
    return sumas


def sincronizar(r2, repo, token, versiones):
    if not re.match(r"^[a-z0-9-]+$", repo):
        raise Error(f"repositorio inválido: {repo}")
    lista = [r for r in github(f"/repos/{DUENO}/{repo}/releases?per_page=30", token) if not r.get("draft")]
    if not lista:
        print(f"{repo}: sin versiones publicadas")
        return
    try:
        ultima = github(f"/repos/{DUENO}/{repo}/releases/latest", token)["tag_name"]
    except urllib.error.HTTPError:
        ultima = None
    copiar = lista[:versiones]
    if ultima and ultima not in [r["tag_name"] for r in copiar]:
        copiar.append(next(r for r in lista if r["tag_name"] == ultima))
    prefijo = f"{DUENO}/{repo}/releases/download/"
    existentes = dict(r2.listar(prefijo))
    espejos = []
    with tempfile.TemporaryDirectory(prefix="espejo-") as tmp:
        for rel in copiar:
            tag = rel["tag_name"]
            if not ETIQUETA_VALIDA.match(tag):
                print(f"{repo} {tag}: etiqueta rara, se omite")
                continue
            sumas = {}
            calculadas = {}
            for a in sorted(rel["assets"], key=lambda a: a["name"] != "SHA256SUMS.txt"):
                if not ARCHIVO_VALIDO.match(a["name"]):
                    continue
                clave = f"{prefijo}{tag}/{a['name']}"
                ruta = os.path.join(tmp, a["name"])
                if existentes.get(clave) == a["size"] and a["name"] != "SHA256SUMS.txt":
                    print(f"  {repo} {tag} {a['name']}: ya estaba")
                    continue
                print(f"  {repo} {tag} {a['name']}: subiendo {a['size'] / 1e6:.1f} MB", flush=True)
                calculadas[a["name"]] = descargar_asset(repo, a, token, ruta)
                if a["name"] == "SHA256SUMS.txt":
                    sumas = leer_sumas(ruta)
                elif sumas.get(a["name"]) and sumas[a["name"]] != calculadas[a["name"]]:
                    raise Error(f"{repo} {tag} {a['name']}: el SHA-256 no coincide con SHA256SUMS.txt")
                tipo = "text/plain; charset=utf-8" if a["name"].endswith(".txt") else "application/octet-stream"
                r2.subir_archivo(clave, ruta, tipo)
                os.remove(ruta)
            if not sumas:
                s_asset = next((a for a in rel["assets"] if a["name"] == "SHA256SUMS.txt"), None)
                if s_asset:
                    ruta = os.path.join(tmp, "SHA256SUMS.txt")
                    descargar_asset(repo, s_asset, token, ruta)
                    sumas = leer_sumas(ruta)
            espejos.append(release_espejo(repo, rel, sumas))
            r2.subir_bytes(f"{DUENO}/{repo}/releases/tag/{tag}", pagina_redireccion(PAGINAS.get(repo, WEB)), "text/html; charset=utf-8", "public, max-age=3600")

    # Índices como la API de GitHub. La "última" es la que GitHub marca como latest.
    espejos.sort(key=lambda r: r.get("published_at") or "", reverse=True)
    ult = next((r for r in espejos if r["tag_name"] == ultima), None) or next((r for r in espejos if not r["prerelease"]), None)
    api = f"api/repos/{DUENO}/{repo}/releases"
    r2.subir_bytes(api, json.dumps(espejos, ensure_ascii=False).encode(), "application/json; charset=utf-8")
    if ult:
        r2.subir_bytes(f"{api}/latest", json.dumps(ult, ensure_ascii=False).encode(), "application/json; charset=utf-8")
        if repo == LANZADOR:
            # Enlace fijo: .../releases/latest/download/JacnexStudio-Setup.exe y el MSI.
            for a in ult["assets"]:
                r2.copiar(f"{prefijo}{ult['tag_name']}/{a['name']}", f"{DUENO}/{repo}/releases/latest/download/{a['name']}")
    # Páginas que el launcher puede abrir en el navegador.
    pagina = pagina_redireccion(PAGINAS.get(repo, WEB))
    for clave in (f"{DUENO}/{repo}", f"{DUENO}/{repo}/", f"{DUENO}/{repo}/releases", f"{DUENO}/{repo}/releases/"):
        r2.subir_bytes(clave, pagina, "text/html; charset=utf-8", "public, max-age=3600")

    # Se borran las versiones que ya no se copian (y su página).
    guardadas = {r["tag_name"] for r in espejos}
    for clave, _ in r2.listar(prefijo):
        tag = clave[len(prefijo):].split("/", 1)[0]
        if tag not in guardadas:
            r2.borrar(clave)
            print(f"  {repo}: borrado {clave}")
    for clave, _ in r2.listar(f"{DUENO}/{repo}/releases/tag/"):
        if clave.rsplit("/", 1)[-1] not in guardadas:
            r2.borrar(clave)
    print(f"{repo}: listo ({', '.join(r['tag_name'] for r in espejos)}; última {ult['tag_name'] if ult else '-'})")


def generales(r2):
    for clave in (DUENO, f"{DUENO}/"):
        r2.subir_bytes(clave, pagina_redireccion(WEB), "text/html; charset=utf-8", "public, max-age=3600")
    r2.subir_bytes("index.html", pagina_redireccion(WEB), "text/html; charset=utf-8", "public, max-age=3600")
    r2.subir_bytes("robots.txt", b"User-agent: *\nDisallow: /\n", "text/plain; charset=utf-8", "public, max-age=3600")


def probar(r2):
    clave = "prueba/espejo.txt"
    r2.subir_bytes(clave, b"hola desde el espejo\n", "text/plain; charset=utf-8", "no-store")
    print("subido:", r2.tamano(clave), "bytes")
    print("lista:", r2.listar("prueba/"))


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--claves", help="archivo con ACCESS_KEY_ID=, SECRET_ACCESS_KEY=, ENDPOINT=")
    sub = p.add_subparsers(dest="orden", required=True)
    s = sub.add_parser("sincronizar")
    s.add_argument("repos", nargs="+")
    s.add_argument("--versiones", type=int, default=3)
    sub.add_parser("probar")
    sub.add_parser("borrar-prueba")
    args = p.parse_args()
    r2 = r2_desde(args)
    if args.orden == "probar":
        probar(r2)
    elif args.orden == "borrar-prueba":
        for clave, _ in r2.listar("prueba/"):
            r2.borrar(clave)
    else:
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
        generales(r2)
        for repo in args.repos:
            sincronizar(r2, repo, token, max(1, args.versiones))


if __name__ == "__main__":
    try:
        main()
    except (Error, urllib.error.HTTPError) as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
