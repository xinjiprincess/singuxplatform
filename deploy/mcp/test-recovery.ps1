param(
    [string]$base = 'http://127.0.0.1:18021',
    [string]$Container = 'singux-mcp-recovery-test-mcp-proxy-1'
)
$ErrorActionPreference = 'Stop'
if (([uri]$base).Host -notin @('localhost', '127.0.0.1')) { throw 'Local MCP checks only' }
$config = @{ mcpServers = @{ filesystem = @{
    command = 'node'
    args = @('/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/server-filesystem/dist/index.js', '/tmp')
} } } | ConvertTo-Json -Depth 6 -Compress
$payload = @{ mcpId = 'singux-local-smoke'; mcpType = 'OneShot'; mcpJsonConfig = $config } | ConvertTo-Json -Compress
$ready = $false
for ($i = 0; $i -lt 30; $i++) {
    $response = Invoke-RestMethod "$base/mcp/sse/check_status" -Method Post -ContentType 'application/json' -Body $payload -TimeoutSec 10
    if ($response.data.status -eq 'Error') { throw "MCP fixture deployment failed: $($response.data.message)" }
    if ($response.data.status -eq 'Ready') { $ready = $true; break }
    Start-Sleep -Seconds 2
}
if (!$ready) { throw 'MCP fixture readiness timed out' }
Get-Content -Raw (Join-Path $PSScriptRoot 'smoke-call.mjs') | docker exec -i -e MCP_SDK_CLIENT=/opt/mcp-fixtures/filesystem/node_modules/@modelcontextprotocol/sdk/dist/esm/client/ $Container node --input-type=module
if ($LASTEXITCODE -ne 0) { throw 'MCP handshake/tool call failed' }
$badConfig = @{ mcpServers = @{ invalid = @{ command = '/nonexistent/singux-command'; args = @() } } } | ConvertTo-Json -Depth 6 -Compress
$badPayload = @{ mcpId = 'singux-failure-smoke'; mcpType = 'OneShot'; mcpJsonConfig = $badConfig } | ConvertTo-Json -Compress
$failed = $false
for ($i = 0; $i -lt 15; $i++) {
    $response = Invoke-RestMethod "$base/mcp/sse/check_status" -Method Post -ContentType 'application/json' -Body $badPayload -TimeoutSec 10
    if ($response.data.status -eq 'Error') { $failed = $true; break }
    Start-Sleep -Seconds 1
}
if (!$failed) { throw 'Invalid command did not produce an explicit Error state' }
Write-Output 'PASS: invalid MCP command returns Error rather than remaining Pending'
