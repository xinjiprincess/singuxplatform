param([string]$Image='singux/backend:1.1.10-20261007-knowledge-fix')
$ErrorActionPreference='Stop'
$prefix='singux-knowledge-test-'+[guid]::NewGuid().ToString('N').Substring(0,8)
$network=$prefix+'-network'; $es=$prefix+'-es'; $artifact=$prefix+'-artifact'; $runner=$prefix+'-runner'
$folder=Join-Path ([System.IO.Path]::GetTempPath()) $prefix
New-Item -ItemType Directory $folder | Out-Null
function Docker([string[]]$Arguments){ & docker.exe @Arguments; if($LASTEXITCODE -ne 0){throw "Docker failed: $($Arguments[0])"} }
try {
    Docker -Arguments @('network','create',$network) | Out-Null
    Docker -Arguments @('run','-d','--name',$es,'--network',$network,'--network-alias','elasticsearch','--memory','1g','-e','discovery.type=single-node','-e','xpack.security.enabled=false','-e','ES_JAVA_OPTS=-Xms512m -Xmx512m','bitnami/elasticsearch:8.18.0') | Out-Null
    $ready=$false
    for($i=0;$i -lt 60;$i++){
        & docker.exe exec $es curl --max-time 3 -fsS 'http://localhost:9200/_cluster/health?wait_for_status=yellow&timeout=2s' *> $null
        if($LASTEXITCODE -eq 0){$ready=$true;break};Start-Sleep -Seconds 2
    }
    if(!$ready){throw 'Isolated Elasticsearch did not become ready'}
    Docker -Arguments @('create','--name',$artifact,$Image) | Out-Null
    Docker -Arguments @('cp',"${artifact}:/app/app.jar",(Join-Path $folder 'app.jar'))
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'tests/KnowledgeDeletionSmoke.java') -Destination $folder
    $command='set -eu; mkdir /work; cd /work; jar xf /input/app.jar BOOT-INF/lib; javac -encoding UTF-8 -cp "BOOT-INF/lib/*" -d /work /input/KnowledgeDeletionSmoke.java; java -cp "/work:BOOT-INF/lib/*" KnowledgeDeletionSmoke'
    Docker -Arguments @('run','--rm','--name',$runner,'--network',$network,'--memory','1g','--mount',"type=bind,source=$folder,target=/input,readonly",'maven:3.9.9-eclipse-temurin-17','sh','-c',$command)
} finally {
    foreach($name in @($runner,$artifact,$es)){& docker.exe rm -f $name 2>$null | Out-Null}
    & docker.exe network rm $network 2>$null | Out-Null
}
