param(
    [ValidateSet('frontend', 'backend', 'mcp', 'file-server', 'rcoder')]
    [string[]]$Components = @('frontend', 'backend', 'mcp', 'file-server', 'rcoder'),
    [string]$ServiceRoot = 'D:\singuxplatform',
    [string]$NodeRuntime = 'master-rcoder-base:latest',
    [ValidateSet('default', 'host')]
    [string]$RustBuildNetwork = 'host',
    [switch]$ResolveCargoHosts = $true
)

$ErrorActionPreference = 'Stop'
$frontend = Split-Path -Parent $PSScriptRoot

function Invoke-DockerBuild([string[]]$Arguments) {
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Docker failed (exit $LASTEXITCODE). No containers were replaced." }
}

Invoke-DockerBuild -Arguments @('info', '--format', '{{.OSType}}')
foreach ($component in $Components) {
    Write-Host "Building $component locally..."
    switch ($component) {
        'frontend' {
            Invoke-DockerBuild -Arguments @('build', '-f', "$frontend\Dockerfile", '--build-arg', "NODE_IMAGE=$NodeRuntime", '-t', 'singux/frontend:1.1.10-20260929-local', $frontend)
        }
        'backend' {
            Invoke-DockerBuild -Arguments @('build', '-f', "$PSScriptRoot\backend-release.Dockerfile", '-t', 'singux/backend:1.1.10-20260929-r4', "$ServiceRoot\nuwax-backend")
        }
        'mcp' {
            $archive = "$PSScriptRoot\mcp\mcp-v0.2.8.tar.xz"
            $expected = '80fbada7d6fb4a2c7802fc73a0920dab19c3541459b292304c14a32044be0fb5'
            if (!(Test-Path -LiteralPath $archive)) {
                throw 'MCP release archive is missing. See deploy/mcp/sources.json and docs/runtime-recovery-and-updates.md.'
            }
            if ((Get-FileHash -LiteralPath $archive -Algorithm SHA256).Hash.ToLowerInvariant() -ne $expected) {
                throw 'MCP archive checksum mismatch.'
            }
            Invoke-DockerBuild -Arguments @('build', '-t', 'singux/mcp-proxy:0.2.8-local', "$PSScriptRoot\mcp")
        }
        'file-server' {
            Invoke-DockerBuild -Arguments @('build', '-f', "$PSScriptRoot\file-server.Dockerfile", '--build-arg', "NODE_RUNTIME=$NodeRuntime", '-t', 'singux/file-server:1.5.4-20260929-local', "$ServiceRoot\nuwax-file-server")
        }
        'rcoder' {
            $buildArgs = @('build', '--network', $RustBuildNetwork)
            if ($ResolveCargoHosts) {
                foreach ($hostName in @('index.crates.io', 'static.crates.io')) {
                    $address = Resolve-DnsName -Name $hostName -Type A |
                        Where-Object { $_.Type -eq 'A' } |
                        Select-Object -First 1 -ExpandProperty IPAddress
                    if (!$address) { throw "No IPv4 address resolved for $hostName" }
                    $buildArgs += @('--add-host', "${hostName}:$address")
                }
            }
            $buildArgs += @('-f', "$ServiceRoot\rcoder\docker\rcoder-master\Dockerfile", '--build-arg', "BASE_IMAGE=$NodeRuntime", '--build-arg', 'CARGO_USE_MIRROR=false', '--build-arg', 'CARGO_BUILD_JOBS=2', '-t', 'singux/rcoder:20260929-build', "$ServiceRoot\rcoder")
            Invoke-DockerBuild -Arguments $buildArgs
            Invoke-DockerBuild -Arguments @('build', '-f', "$PSScriptRoot\rcoder-local-runtime.Dockerfile", '-t', 'singux/rcoder:20260929-local', $PSScriptRoot)
        }
    }
}
Write-Host 'Requested image builds finished. No production deployment or container replacement was performed.'
