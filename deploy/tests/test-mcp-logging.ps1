param([string]$Backend = 'D:/singuxplatform/nuwax-backend', [string]$Jdk = 'C:/Program Files/Java/jdk-20', [switch]$ProductionBaseline)
$ErrorActionPreference = 'Stop'
$frontend = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$output = "$frontend/tmp/mcp-logging-test-classes"
if ($ProductionBaseline) { $output = "$frontend/tmp/mcp-logging-production-test-classes" }
New-Item -ItemType Directory -Force $output | Out-Null
$classDirs = Get-ChildItem "$Backend/app-platform-modules","$Backend/app-platform-foundation" -Recurse -Directory -Filter classes | Where-Object { $_.Parent.Name -eq 'target' } | ForEach-Object FullName
$preferred = @('org/mockito/mockito-core/5.14.1','net/bytebuddy/byte-buddy/1.14.19','net/bytebuddy/byte-buddy-agent/1.14.19','org/objenesis/objenesis/3.4','org/projectlombok/lombok/1.18.36','org/junit/jupiter/junit-jupiter-api/5.11.2','org/slf4j/slf4j-api/2.0.16','org/springframework/spring-core/6.1.16','ch/qos/logback/logback-classic/1.5.16','ch/qos/logback/logback-core/1.5.16','org/springframework/boot/spring-boot/3.3.8') | ForEach-Object { Get-ChildItem "$HOME/.m2/repository/$_" -Filter '*.jar' | ForEach-Object FullName }
$jars = Get-ChildItem "$HOME/.m2/repository" -Recurse -Filter '*.jar' | ForEach-Object FullName
$classpath = (@($output) + $preferred + $classDirs + $jars) -join ';'
$module = "$Backend/app-platform-modules/app-platform-mcp"
$application = "$module/app-platform-mcp-application/src/main/java/com/xspaceagi/mcp/application/service"
$sources = @("$application/McpLogSanitizer.java", "$application/McpDeployTaskServiceImpl.java", "$application/SSEMcpUpdateTaskServiceImpl.java", "$module/app-platform-mcp-ui/src/main/java/com/xspaceagi/mcp/ui/api/service/McpApiServiceImpl.java", "$module/app-platform-mcp-application/src/test/java/com/xspaceagi/mcp/application/service/McpDeployTaskServiceImplTest.java", "$module/app-platform-mcp-ui/src/test/java/com/xspaceagi/mcp/ui/api/service/McpExecutionLoggingTest.java", "$PSScriptRoot/McpLoggingTestRunner.java")
if ($ProductionBaseline) {
    $release = "$frontend/outputs/mcp-logging-20261010"
    $runtimeJars = Get-ChildItem "$release/compile-libs" -Filter '*.jar' | ForEach-Object FullName
    $classpath = (@($output, "$release/classes") + $runtimeJars + $preferred + $jars) -join ';'
    $sources = $sources | Where-Object { $_ -notlike '*/src/main/*' }
}
$compileArgs = @('--release','17','-encoding','UTF-8','-cp',('"'+$classpath.Replace('\','/')+'"'),'-d',('"'+$output+'"')) + ($sources | ForEach-Object { '"'+$_+'"' })
$argsFile = "$output/javac.args"
[IO.File]::WriteAllLines($argsFile, [string[]]($compileArgs | ForEach-Object { $_.Replace('\','/') }), [Text.UTF8Encoding]::new($false))
& "$Jdk/bin/javac.exe" "@$argsFile"
if ($LASTEXITCODE -ne 0) { throw 'MCP logging compilation failed' }
$runArgs = @('-cp',('"'+$classpath.Replace('\','/')+'"'),'McpLoggingTestRunner','com.xspaceagi.mcp.application.service.McpDeployTaskServiceImplTest','com.xspaceagi.mcp.ui.api.service.McpExecutionLoggingTest')
[IO.File]::WriteAllLines("$output/java.args", $runArgs, [Text.UTF8Encoding]::new($false))
& "$Jdk/bin/java.exe" "@$output/java.args"
if ($LASTEXITCODE -ne 0) { throw 'MCP logging regression failed' }
