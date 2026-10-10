param([string]$Archive = 'D:\dlxmate\exports\singux-docs-starter.zip')
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.IO.Compression.FileSystem
$destination = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../public/docs'))
if (Test-Path -LiteralPath $destination) { throw 'Documentation directory already exists; review before replacing.' }
$zip = [IO.Compression.ZipFile]::OpenRead($Archive)
try {
    $files = @()
    foreach ($entry in $zip.Entries) {
        $name = $entry.FullName
        $relative = $null
        if ($name -eq 'singux-docs-starter/static/index.html') { $relative = 'index.html' }
        elseif ($name.StartsWith('singux-docs-starter/static/assets/')) { $relative = 'ui/assets/' + $name.Substring('singux-docs-starter/static/assets/'.Length) }
        elseif ($name.StartsWith('singux-docs-starter/static/manual/')) { $relative = 'assets/' + $name.Substring('singux-docs-starter/static/manual/'.Length) }
        if (!$relative -or $name.EndsWith('/')) { continue }
        $target = [IO.Path]::GetFullPath((Join-Path $destination $relative))
        if (!$target.StartsWith($destination + [IO.Path]::DirectorySeparatorChar)) { throw 'Unsafe archive path' }
        if ($entry.Length -gt 20MB) { throw 'Unexpected documentation asset size' }
        $files += @{ Entry = $entry; Target = $target }
    }
    if (!$files.Count) { throw 'No documentation assets found' }
    foreach ($file in $files) {
        [IO.Directory]::CreateDirectory([IO.Path]::GetDirectoryName($file.Target)) | Out-Null
        [IO.Compression.ZipFileExtensions]::ExtractToFile($file.Entry, $file.Target, $false)
    }
    $pdf = Get-ChildItem -LiteralPath (Join-Path $destination 'assets') -Filter '*.pdf'
    if (@($pdf).Count -ne 1) { throw 'Expected exactly one manual PDF' }
    [IO.Directory]::CreateDirectory((Join-Path $destination 'download')) | Out-Null
    Copy-Item -LiteralPath $pdf.FullName -Destination (Join-Path $destination 'download/manual.pdf')
    Write-Output "Imported $($files.Count) documentation assets"
} finally { $zip.Dispose() }
