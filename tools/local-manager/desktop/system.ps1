param([ValidateSet('processes','startup','services')][string]$Mode)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()
if ($Mode -eq 'processes') {
  $items = @(Get-CimInstance Win32_Process | ForEach-Object {
    [pscustomobject]@{id=$_.ProcessId; name=$_.Name; memory=[double]$_.WorkingSetSize; cpu=([double]$_.KernelModeTime+[double]$_.UserModeTime)/10000000; path=$_.ExecutablePath; command=$_.CommandLine; created=if($_.CreationDate){$_.CreationDate.ToUniversalTime().ToString('o')}else{''}}
  })
  ConvertTo-Json -InputObject $items -Depth 4 -Compress
}
if ($Mode -eq 'services') {
  $items = @(Get-CimInstance Win32_Service | Select-Object Name, DisplayName, State, StartMode, ProcessId)
  ConvertTo-Json -InputObject $items -Compress
}
if ($Mode -eq 'startup') {
  $items = [System.Collections.Generic.List[object]]::new()
  $roots=@('HKCU:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\Microsoft\Windows\CurrentVersion\Run','HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run')
  foreach($root in $roots) {
    if(Test-Path -LiteralPath $root) {
      $key=Get-Item -LiteralPath $root
      foreach($name in $key.GetValueNames()) {
        $approved=$root -replace '\\Run$','\StartupApproved\Run'
        if($root -like '*WOW6432Node*'){$approved='HKLM:\Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run32'}
        else {$approved=$root -replace '\\CurrentVersion\\Run$','\CurrentVersion\Explorer\StartupApproved\Run'}
        $bytes=if(Test-Path -LiteralPath $approved){(Get-Item -LiteralPath $approved).GetValue($name)}else{$null}
        $enabled= -not ($bytes -is [byte[]] -and $bytes.Length -gt 0 -and $bytes[0] -in @(3,7))
        $items.Add([pscustomobject]@{id="registry|$root|$name";name=$name;command=[string]$key.GetValue($name,$null,[Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames);kind='registry';source=$root;enabled=$enabled})
      }
    }
  }
  $folders=@([Environment]::GetFolderPath('Startup'),[Environment]::GetFolderPath('CommonStartup'))
  foreach($folder in $folders){
    foreach($dir in @($folder,(Join-Path $folder 'LocalManager.Disabled'))){
      if(Test-Path -LiteralPath $dir){Get-ChildItem -LiteralPath $dir -File | Where-Object Name -ne 'desktop.ini' | ForEach-Object {
        $items.Add([pscustomobject]@{id="folder|$($_.FullName)";name=$_.Name;command=$_.FullName;kind='folder';source=$folder;enabled=($dir -eq $folder)})
      }}
    }
  }
  try {
    Get-ScheduledTask | Where-Object { @($_.Triggers | Where-Object { $_.CimClass.CimClassName -in @('MSFT_TaskBootTrigger','MSFT_TaskLogonTrigger') }).Count -gt 0 } | ForEach-Object {
      $items.Add([pscustomobject]@{id="task|$($_.TaskPath)|$($_.TaskName)";name=$_.TaskName;command=($_.Actions | ForEach-Object {"$($_.Execute) $($_.Arguments)"}) -join '; ';kind='task';source=$_.TaskPath;enabled=($_.State -ne 'Disabled')})
    }
  } catch { $items.Add([pscustomobject]@{id='notice';name='计划任务读取失败';command=$_.Exception.Message;kind='notice';source='权限或系统限制';enabled=$false}) }
  ConvertTo-Json -InputObject @($items.ToArray()) -Depth 5 -Compress
}
