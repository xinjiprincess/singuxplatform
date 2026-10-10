param([string]$OutputRoot = 'C:\Users\zhang\nuwax\outputs')
$ErrorActionPreference = 'Stop'
$version = '1.1.10-20261008-tenant-admin-r2'
$name = 'singux-tenant-admin-20261008-candidate-r2'
$root = [IO.Path]::GetFullPath($OutputRoot)
$folder = Join-Path $root $name
$archive = Join-Path $root "$name.tar.gz"
if ((Test-Path -LiteralPath $folder) -or (Test-Path -LiteralPath $archive)) { throw 'Candidate package exists; choose a different output directory' }
$images = @("singux/backend:$version", 'singux/frontend:1.1.10-20261008-tenant-admin')
$manifest = @()
foreach ($tag in $images) {
    $info = & docker image inspect $tag | ConvertFrom-Json
    if ($LASTEXITCODE -ne 0 -or $info[0].Os -ne 'linux' -or $info[0].Architecture -ne 'amd64') { throw "Expected a Linux amd64 image: $tag" }
    $manifest += @{tag=$tag;id=$info[0].Id;os=$info[0].Os;architecture=$info[0].Architecture}
}
New-Item -ItemType Directory -Path (Join-Path $folder 'migrations') | Out-Null
& docker save -o (Join-Path $folder 'images.tar') @images
if ($LASTEXITCODE -ne 0) { throw 'Image export failed' }
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'TENANT_CANDIDATE.md') -Destination (Join-Path $folder 'README.md')
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'test-local-tenant-admin.ps1') -Destination $folder
Copy-Item -Path 'D:\singuxplatform\nuwax-backend\sql\migrations\*.sql' -Destination (Join-Path $folder 'migrations')
$utf8 = [Text.UTF8Encoding]::new($false)
[IO.File]::WriteAllText((Join-Path $folder 'release.json'), (@{version=$version;productionApproved=$false;images=$manifest} | ConvertTo-Json -Depth 8), $utf8)
$checks = Get-ChildItem -LiteralPath $folder -Recurse -File | Sort-Object FullName | ForEach-Object {
    $relative = [IO.Path]::GetRelativePath($folder, $_.FullName).Replace('\','/')
    "$((Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash.ToLowerInvariant())  $relative"
}
[IO.File]::WriteAllText((Join-Path $folder 'SHA256SUMS'), ($checks -join "`n") + "`n", $utf8)
& tar -czf $archive -C $root $name
if ($LASTEXITCODE -ne 0) { throw 'Archive creation failed' }
$hash = (Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant()
[IO.File]::WriteAllText("$archive.sha256", "$hash  $name.tar.gz`n", $utf8)
Get-Item -LiteralPath $archive | Select-Object FullName, Length
Write-Host "SHA256: $hash"
Write-Host 'Candidate only; no server was connected or updated.'
