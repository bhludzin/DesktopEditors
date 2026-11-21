# Exports a deck to PDF with the locally installed Microsoft PowerPoint, which
# serves as the ground truth for fidelity scoring. The deck is opened
# read-only and without a window; PowerPoint is closed again afterwards unless
# it was already running.
param([Parameter(Mandatory)][string]$Deck, [Parameter(Mandatory)][string]$Pdf)
$ErrorActionPreference = 'Stop'

$wasRunning = [bool](Get-Process POWERPNT -ErrorAction SilentlyContinue)
try {
  $app = New-Object -ComObject PowerPoint.Application
} catch {
  throw "Could not start Microsoft PowerPoint. It must be installed to export the reference PDF. $_"
}
try {
  # ReadOnly=-1 (msoTrue), Untitled=0, WithWindow=0
  $pres = $app.Presentations.Open($Deck, -1, 0, 0)
  "slides=" + $pres.Slides.Count
  $sw = [Diagnostics.Stopwatch]::StartNew()
  $pres.SaveAs($Pdf, 32)   # 32 = ppSaveAsPDF
  "export_seconds=" + [math]::Round($sw.Elapsed.TotalSeconds, 1)
  $pres.Close()
} finally {
  if (-not $wasRunning) { $app.Quit() }
  [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app)
}
