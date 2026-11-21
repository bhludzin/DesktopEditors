# Renders every page of a PDF to OutDir\p0001.png, p0002.png, ... using the
# PDF renderer built into Windows (Windows.Data.Pdf), so reference and
# candidate PDFs are rasterized identically.
param([Parameter(Mandatory)][string]$Pdf, [Parameter(Mandatory)][string]$OutDir, [int]$Width = 800)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime
$null = [Windows.Storage.StorageFile, Windows.Storage, ContentType = WindowsRuntime]
$null = [Windows.Data.Pdf.PdfDocument, Windows.Data.Pdf, ContentType = WindowsRuntime]
$null = [Windows.Storage.Streams.InMemoryRandomAccessStream, Windows.Storage.Streams, ContentType = WindowsRuntime]
$methods = [System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object { $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 }
$asTaskOp = $methods | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' } | Select-Object -First 1
$asTaskAction = $methods | Where-Object { $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncAction' } | Select-Object -First 1
function Await($op, [Type]$type) { $t = $asTaskOp.MakeGenericMethod($type).Invoke($null, @($op)); [void]$t.Wait(-1); $t.Result }
function AwaitAction($action) { $t = $asTaskAction.Invoke($null, @($action)); [void]$t.Wait(-1) }

New-Item -ItemType Directory -Force $OutDir | Out-Null
$file = Await ([Windows.Storage.StorageFile]::GetFileFromPathAsync($Pdf)) ([Windows.Storage.StorageFile])
$doc = Await ([Windows.Data.Pdf.PdfDocument]::LoadFromFileAsync($file)) ([Windows.Data.Pdf.PdfDocument])
$count = $doc.PageCount
for ($i = 0; $i -lt $count; $i++) {
  $page = $doc.GetPage($i)
  $opts = New-Object Windows.Data.Pdf.PdfPageRenderOptions
  $opts.DestinationWidth = $Width
  $mem = New-Object Windows.Storage.Streams.InMemoryRandomAccessStream
  AwaitAction ($page.RenderToStreamAsync($mem, $opts))
  $src = [System.IO.WindowsRuntimeStreamExtensions]::AsStreamForRead($mem.GetInputStreamAt(0))
  $dst = [IO.File]::Create((Join-Path $OutDir ('p{0:D4}.png' -f ($i + 1))))
  $src.CopyTo($dst); $dst.Close(); $src.Dispose(); $mem.Dispose(); $page.Dispose()
}
"pages=$count"
