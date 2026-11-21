# Puts slide images side by side with a caption above each one.
# -Images and -Labels are '|'-separated lists of the same length.
param([Parameter(Mandatory)][string]$Out, [Parameter(Mandatory)][string]$Images, [Parameter(Mandatory)][string]$Labels)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Drawing

$paths = @($Images -split '\|')
$names = @($Labels -split '\|')
$imgs = @($paths | ForEach-Object { [System.Drawing.Image]::FromFile($_) })
try {
  $w = $imgs[0].Width; $h = $imgs[0].Height; $gap = 15; $top = 28
  $bmp = New-Object System.Drawing.Bitmap ($imgs.Count * ($w + $gap) - $gap), ($h + $top + 2)
  $g = [System.Drawing.Graphics]::FromImage($bmp)
  $g.Clear([System.Drawing.Color]::White)
  $font = New-Object System.Drawing.Font 'Arial', 14, ([System.Drawing.FontStyle]::Bold)
  for ($i = 0; $i -lt $imgs.Count; $i++) {
    $x = $i * ($w + $gap)
    $g.DrawString($names[$i], $font, [System.Drawing.Brushes]::Black, $x, 2)
    $g.DrawImage($imgs[$i], $x, $top, $w, $h)
    $g.DrawRectangle([System.Drawing.Pens]::Gray, $x, $top, $w - 1, $h - 1)
  }
  New-Item -ItemType Directory -Force (Split-Path $Out) | Out-Null
  $bmp.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
  $g.Dispose(); $bmp.Dispose()
} finally {
  $imgs | ForEach-Object { $_.Dispose() }
}
