param(
    [string]$BaseUrl = 'http://127.0.0.1:18093',
    [string]$Username = 'admin',
    [SecureString]$Password = (Read-Host 'Local administrator password' -AsSecureString)
)
$ErrorActionPreference = 'Stop'
if (([uri]$BaseUrl).Host -notin @('127.0.0.1', 'localhost')) { throw 'Local verification only' }
function Assert($Condition, [string]$Label) {
    if (!$Condition) { throw "FAIL: $Label" }
    Write-Host "PASS: $Label"
}
function Api([string]$Path, $Body = $null, [string]$Token = '', [string]$Method = 'POST', $Session = $null) {
    $headers = @{ Origin = $BaseUrl }
    if ($Token) { $headers.Authorization = "Bearer $Token" }
    $options = @{ Uri = "$BaseUrl$Path"; Method = $Method; Headers = $headers; TimeoutSec = 90; SkipHttpErrorCheck = $true }
    if ($null -ne $Body) { $options.Body = $Body | ConvertTo-Json -Depth 12; $options.ContentType = 'application/json' }
    if ($null -ne $Session) { $options.WebSession = $Session }
    return Invoke-RestMethod @options
}
$session = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
$plain = [System.Net.NetworkCredential]::new('', $Password).Password
try {
    $login = Api '/api/user/passwordLogin' @{phoneOrEmail=$Username; password=$plain} '' 'POST' $session
    Assert ($login.code -eq '0000') 'root administrator authentication'
    if ($login.data.stage -eq 'TENANT_SELECTION_REQUIRED') {
        $profile = Api '/api/me/onboarding' $null '' 'GET' $session
        if ($profile.data.enabled -and !$profile.data.profile) {
            $null = Api '/api/me/onboarding' @{organizationType='COMPANY';organizationName='Local acceptance environment'} '' 'PUT' $session
        }
        $selection = Api '/api/session/tenant/select' @{tenantId=1} '' 'POST' $session
        Assert ($selection.code -eq '0000') 'root enterprise selection'
        $token = $selection.data.token
    } else { $token = $login.data.token }
    $caps = Api '/api/platform/capabilities' $null $token 'GET'
    Assert ($caps.data.canCreateTenant -eq $true) 'root-only provisioning capability'
    $stamp = Get-Date -Format yyyyMMddHHmmss
    $testPassword = [guid]::NewGuid().ToString('N')
    $created = Api '/api/system/user/batch/add' @{users=@(
        @{userName="acceptance${stamp}a";nickName='Acceptance owner';email="acceptance${stamp}a@example.com";password=$testPassword},
        @{userName="acceptance${stamp}bad";email='invalid';password=$testPassword},
        @{userName="acceptance${stamp}b";nickName='Acceptance member';email="acceptance${stamp}b@example.com";password=$testPassword}
    )} $token
    if ($created.code -ne '0000' -or !$created.data[0].success -or !$created.data[2].success) { Write-Host ($created | ConvertTo-Json -Depth 8) }
    Assert ($created.code -eq '0000' -and $created.data.Count -eq 3 -and $created.data[0].success -and !$created.data[1].success -and $created.data[2].success) 'failed creation row does not stop later rows'
    $ownerId = $created.data[0].id; $memberId = $created.data[2].id
    $enterprise = Api '/api/platform/tenants' @{name="Acceptance enterprise $stamp";ownerUserId=$ownerId;reason='Local acceptance';description='Disposable local test enterprise'} $token
    Assert ($enterprise.code -eq '0000' -and $enterprise.data.policy.plan -eq 'FREE') 'new enterprise defaults to free'
    $tenantId = $enterprise.data.tenantId
    $current = Api '/api/tenant/profile' $null $token 'GET'
    Assert ($current.data.tenantId -eq 1) 'provisioning preserves root session context'
    $members = Api "/api/platform/tenants/$tenantId/members" $null $token 'GET'
    Assert (@($members.data | Where-Object { $_.userId -eq $ownerId -and $_.role -eq 'OWNER' }).Count -eq 1) 'owner membership created'
    $change = Api "/api/platform/tenants/$tenantId/members/batch" @{reason='Local protection test';members=@(
        @{userId=$ownerId;role='OWNER';status='REVOKED';version=0},
        @{userId=$memberId;role='MEMBER';status='ACTIVE';version=-1}
    )} $token
    Assert (!$change.data[0].success -and $change.data[0].code -eq 'LAST_OWNER' -and $change.data[1].success) 'last owner protected and next membership succeeds'
    $revoke = Api "/api/platform/tenants/$tenantId/members/batch" @{reason='Local revocation test';members=@(@{userId=$memberId;role='MEMBER';status='REVOKED';version=0})} $token
    Assert ($revoke.data[0].success) 'membership revocation'
    $restore = Api "/api/platform/tenants/$tenantId/members/batch" @{reason='Local restore test';members=@(@{userId=$memberId;role='MEMBER';status='ACTIVE';version=1})} $token
    Assert ($restore.data[0].success) 'membership restoration'
    $disable = Api '/api/system/user/batch/disable' @{ids=@($ownerId,$memberId)} $token
    Assert (!$disable.data[0].success -and $disable.data[0].code -eq 'PROTECTED_OWNER' -and $disable.data[1].success) 'shared owner protected while ordinary account disabled'
    $enabled = Api '/api/system/user/batch/enable' @{ids=@($memberId)} $token
    Assert ($enabled.data[0].success) 'ordinary account re-enabled'
    $ownerSession = [Microsoft.PowerShell.Commands.WebRequestSession]::new()
    $ownerLogin = Api '/api/user/passwordLogin' @{phoneOrEmail="acceptance${stamp}a";password=$testPassword} '' 'POST' $ownerSession
    Assert ($ownerLogin.code -eq '0000' -and $ownerLogin.data.stage -eq 'TENANT_SELECTION_REQUIRED') 'new owner can authenticate'
    $null = Api '/api/me/onboarding' @{organizationType='COMPANY';organizationName="Acceptance enterprise $stamp"} '' 'PUT' $ownerSession
    $ownerSelection = Api '/api/session/tenant/select' @{tenantId=$tenantId} '' 'POST' $ownerSession
    Assert ($ownerSelection.code -eq '0000' -and $ownerSelection.data.tenantId -eq $tenantId) 'new enterprise owner session issued'
    $ownerCaps = Api '/api/platform/capabilities' $null $ownerSelection.data.token 'GET'
    Assert (!$ownerCaps.data.canCreateTenant) 'enterprise owner cannot provision platform tenants'
    $denied = Api '/api/platform/tenants' @{name='Unauthorized enterprise';ownerUserId=$ownerId;reason='Local negative test'} $ownerSelection.data.token
    Assert ($denied.code -ne '0000') 'backend rejects non-platform tenant provisioning'
    Write-Host "LOCAL_ACCEPTANCE_OK tenant=$tenantId owner=$ownerId member=$memberId"
} finally { $plain = $null; $testPassword = $null; $token = $null }
