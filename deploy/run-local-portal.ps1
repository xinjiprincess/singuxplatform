param(
    [string]$BackendImage = 'singux/backend:1.1.10-20260929-portal',
    [string]$FrontendImage = 'singux/frontend:1.1.10-20260929-portal',
    [int]$Port = 18093
)
$ErrorActionPreference = 'Stop'
function Docker([Parameter(ValueFromRemainingArguments=$true)][string[]]$Arguments) {
    $result = & docker.exe @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker operation failed: $($Arguments[0])" }
    return $result
}
$name = 'singux-local-backend-1'
$previous = (Docker @('inspect', $name) | ConvertFrom-Json)[0]
if ($previous.HostConfig.PortBindings.PSObject.Properties.Count -gt 0) {
    throw 'Unexpected backend host ports. Review deployment before replacing it.'
}
$backup = "$name-before-portal-$(Get-Date -Format yyyyMMddHHmmss)"
$argsList = @('create', '--name', $name, '--network', 'singux-local_default',
    '--network-alias', 'backend', '--add-host', 'host.docker.internal:host-gateway', '--restart', 'unless-stopped')
foreach ($entry in $previous.Config.Env) {
    if (!$entry.StartsWith('PLATFORM_PORTALS_ENABLED=')) { $argsList += @('-e', $entry) }
}
$argsList += @('-e', 'PLATFORM_PORTALS_ENABLED=true')
foreach ($mount in $previous.Mounts) {
    $source = if ($mount.Type -eq 'volume') { $mount.Name } else { $mount.Source }
    $spec = "type=$($mount.Type),source=$source,target=$($mount.Destination)"
    if (!$mount.RW) { $spec += ',readonly' }
    $argsList += @('--mount', $spec)
}
$argsList += $BackendImage
Docker @('image', 'inspect', $BackendImage, '--format', '{{.Id}}') | Out-Null
Docker @('image', 'inspect', $FrontendImage, '--format', '{{.Id}}') | Out-Null
Docker @('stop', $name) | Out-Null
Docker @('rename', $name, $backup) | Out-Null
try {
    Docker $argsList | Out-Null
    Docker @('start', $name) | Out-Null
    $ready = $false
    for ($i=0; $i -lt 120; $i++) {
        Start-Sleep -Seconds 5
        $status = Docker @('inspect', $name, '--format', '{{.State.Health.Status}}')
        if ($status -eq 'healthy') { $ready = $true; break }
    }
    if (!$ready) { throw 'Backend did not become healthy' }
} catch {
    & docker.exe rm -f $name 2>$null | Out-Null
    Docker @('rename', $backup, $name) | Out-Null
    Docker @('start', $name) | Out-Null
    throw
}
$previewName = "singux-portal-preview-$Port"
$existingPreview = & docker.exe ps -a --filter "name=^${previewName}$" --format '{{.Names}}'
if ($existingPreview -eq $previewName) {
    $preview = (Docker @('inspect', $previewName) | ConvertFrom-Json)[0]
    if (@($preview.Mounts).Count -gt 0) { throw 'Preview has unexpected data mounts; refusing to replace it' }
    Docker @('rm', '-f', $previewName) | Out-Null
}
Docker @('run', '-d', '--name', $previewName, '--restart', 'unless-stopped', '--network', 'singux-local_default',
    '-p', "127.0.0.1:${Port}:80", '-e', 'API_UPSTREAM=http://singux-local-backend-1:8081',
    '-e', 'MODEL_PROXY_UPSTREAM=http://singux-local-backend-1:18086', $FrontendImage) | Out-Null
Write-Host "Portal: http://127.0.0.1:$Port/zhichuangbei/login"
Write-Host "Previous backend retained: $backup"
