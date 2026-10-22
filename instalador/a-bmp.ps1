# Convierte las imágenes PNG del asistente a BMP de 24 bits (lo que pide Inno Setup), sobre fondo blanco.
param([string]$Carpeta = $PSScriptRoot)
Add-Type -AssemblyName System.Drawing
foreach ($png in Get-ChildItem $Carpeta -Filter *.png) {
  $origen = [System.Drawing.Image]::FromFile($png.FullName)
  $bmp = New-Object System.Drawing.Bitmap $origen.Width, $origen.Height, ([System.Drawing.Imaging.PixelFormat]::Format24bppRgb)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::White)
  $g.DrawImage($origen, 0, 0, $origen.Width, $origen.Height)
  $g.Dispose(); $origen.Dispose()
  $bmp.Save([IO.Path]::ChangeExtension($png.FullName, '.bmp'), [System.Drawing.Imaging.ImageFormat]::Bmp)
  $bmp.Dispose()
}
