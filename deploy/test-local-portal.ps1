param(
    [string]$BaseUrl = 'http://127.0.0.1:18093',
    [string]$Slug = 'zhichuangbei',
    [string]$Username = 'admin',
    [SecureString]$Password = (Read-Host 'Local administrator password' -AsSecureString)
)
$ErrorActionPreference = 'Stop'
if (([uri]$BaseUrl).Host -notin @('127.0.0.1', 'localhost')) { throw 'Local verification only' }
function Assert($Condition, [string]$Label) {
    if (!$Condition) { throw "FAIL: $Label" }
    Write-Host "PASS: $Label"
}
function Api([string]$Path, [hashtable]$Headers, $Body = $null, [string]$Method = 'GET', $Session = $null) {
    $options = @{ Uri = "$BaseUrl$Path"; Method = $Method; Headers = $Headers; TimeoutSec = 30; SkipHttpErrorCheck = $true }
    if ($null -ne $Body) { $options.Body = $Body | ConvertTo-Json -Depth 12; $options.ContentType = 'application/json' }
    if ($null -ne $Session) { $options.WebSession = $Session }
    return Invoke-RestMethod @options
}
$plain = [System.Net.NetworkCredential]::new('', $Password).Password
try {
    $portal = Api "/api/public/portals/$Slug" @{}
    Assert ($portal.code -eq '0000' -and $portal.data.slug -eq $Slug) 'public portal configuration'
    $login = Api '/api/user/passwordLogin' @{ 'X-Singu-Portal' = $Slug } @{phoneOrEmail=$Username; password=$plain} 'POST'
    Assert ($login.code -eq '0000' -and $login.data.token -and $login.data.stage -ne 'TENANT_SELECTION_REQUIRED') 'fixed-tenant password login'
    $headers = @{ Authorization="Bearer $($login.data.token)"; 'X-Singu-Portal'=$Slug }
    $profile = Api '/api/tenant/profile' $headers
    Assert ($profile.code -eq '0000') 'portal authenticated profile'
    $null = Api '/api/user/refresh-permission' $headers
    $menus = Api '/api/user/list-menu' $headers
    Assert ($menus.code -eq '0000' -and @($menus.data).Count -gt 0) 'portal member menus initialized'
    $crossRoot = Api '/api/tenant/profile' @{Authorization=$headers.Authorization}
    Assert ($crossRoot.code -in @('4010','401','UNAUTHORIZED')) 'portal token rejected outside portal'
    $management = Api '/api/platform/portals' $headers
    Assert ($management.code -eq 'PORTAL_ROUTE_DENIED') 'portal session denied platform management'
    $switch = Api '/api/session/tenant/switch' $headers @{tenantId=1} 'POST'
    Assert ($switch.code -eq 'PORTAL_ROUTE_DENIED') 'portal session denied tenant switching'
    $unknown = Api '/api/public/portals/not-a-real-portal' @{}
    Assert ($unknown.code -eq 'PORTAL_NOT_FOUND') 'unknown portal fails closed'
    $session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
    $rootLogin = Api '/api/user/passwordLogin' @{} @{phoneOrEmail=$Username; password=$plain} 'POST' $session
    Assert ($rootLogin.code -eq '0000' -and $rootLogin.data.stage -eq 'TENANT_SELECTION_REQUIRED') 'official login retains enterprise selection'
    $selection = Api '/api/session/tenant/select' @{Origin=$BaseUrl} @{tenantId=1} 'POST' $session
    Assert ($selection.code -eq '0000' -and $selection.data.token) 'official administrator tenant selection'
    $adminHeaders = @{Authorization="Bearer $($selection.data.token)"; Origin=$BaseUrl}
    $list = Api '/api/platform/portals' $adminHeaders
    Assert ($list.code -eq '0000' -and @($list.data | Where-Object slug -eq $Slug).Count -eq 1) 'administrator portal list'
    $crossPortal = Api '/api/tenant/profile' @{Authorization=$adminHeaders.Authorization; 'X-Singu-Portal'=$Slug}
    Assert ($crossPortal.code -in @('4010','401','UNAUTHORIZED')) 'official token rejected in portal'
    $saved = Api '/api/platform/portals' $adminHeaders @{portal=$portal.data; previous=$portal.data; reason='Local portal smoke verification (unchanged configuration)'} 'PUT'
    Assert ($saved.code -eq '0000') 'administrator audited save'
    $disabled = $portal.data | ConvertTo-Json -Depth 12 | ConvertFrom-Json
    $disabled.enabled = $false
    $changed = $false
    try {
        $result = Api '/api/platform/portals' $adminHeaders @{portal=$disabled; previous=$portal.data; reason='Local disable/restore verification'} 'PUT'
        Assert ($result.code -eq '0000') 'administrator disables portal'
        $changed = $true
        $inactive = Api "/api/public/portals/$Slug" @{}
        Assert ($inactive.code -eq 'PORTAL_INACTIVE') 'disabled portal fails closed'
        $blocked = Api '/api/tenant/profile' $headers
        Assert ($blocked.code -eq 'PORTAL_INACTIVE') 'existing portal session blocked when disabled'
        $rootStillWorks = Api '/api/platform/portals' $adminHeaders
        Assert ($rootStillWorks.code -eq '0000') 'official management unaffected by portal disable'
    } finally {
        if ($changed) {
            $restored = Api '/api/platform/portals' $adminHeaders @{portal=$portal.data; previous=$disabled; reason='Restore after local verification'} 'PUT'
            Assert ($restored.code -eq '0000') 'portal configuration restored'
        }
    }
} finally {
    $plain = $null
    $login = $null
    $selection = $null
}
