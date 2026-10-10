#Requires -Version 5.1
<#
.SYNOPSIS
    Windows 一键 Docker 镜像构建脚本
.DESCRIPTION
    为 Singular Origo 前端项目构建 Docker 镜像
.EXAMPLE
    .\docker-build.ps1
    .\docker-build.ps1 -Tag v1.1.10
    .\docker-build.ps1 -RegistryPrefix registry.cn-hangzhou.aliyuncs.com/myname -Tag v1.1.10
    .\docker-build.ps1 -UseChinaMirror -Tag v1.1.10
    .\docker-build.ps1 -PushAfterBuild -Tag v1.1.10
#>
[CmdletBinding()]
param(
    [string]$ImageName = "singular-origo-frontend",
    [string]$Tag = "latest",
    [string]$RegistryPrefix = "",
    [switch]$UseChinaMirror,
    [switch]$PushAfterBuild
)

# 颜色输出
$Red = "`e[31m"
$Green = "`e[32m"
$Yellow = "`e[33m"
$Blue = "`e[34m"
$Reset = "`e[0m"

# 默认值
$NodeImage = "node:22.10.0"
$NginxImage = "nginx:alpine"
$NpmRegistry = "https://registry.npmmirror.com"

# 国内镜像加速
if ($UseChinaMirror) {
    $NodeImage = "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/node:22.10.0"
    $NginxImage = "swr.cn-north-4.myhuaweicloud.com/ddn-k8s/docker.io/nginx:alpine"
    $NpmRegistry = "https://registry.npmmirror.com"
    Write-Host "${Blue}已启用国内镜像加速${Reset}"
}

# 组合完整镜像名
if ($RegistryPrefix) {
    $FullTag = "${RegistryPrefix}/${ImageName}:${Tag}"
} else {
    $FullTag = "${ImageName}:${Tag}"
}

# 检查 Docker 环境
Write-Host "${Blue}正在检查 Docker 环境...${Reset}"
$dockerPath = Get-Command docker -ErrorAction SilentlyContinue
if (-not $dockerPath) {
    Write-Host "${Red}错误: Docker 未安装或未加入 PATH${Reset}"
    exit 1
}

try {
    $null = docker info 2>$null
} catch {
    Write-Host "${Red}错误: Docker 守护进程未运行${Reset}"
    exit 1
}

Write-Host "${Green}Docker 环境正常${Reset}"

# 显示构建信息
Write-Host "${Blue}========================================${Reset}"
Write-Host "${Blue}  镜像名称: ${FullTag}${Reset}"
Write-Host "${Blue}  Node 镜像: ${NodeImage}${Reset}"
Write-Host "${Blue}  Nginx 镜像: ${NginxImage}${Reset}"
Write-Host "${Blue}  NPM 镜像源: ${NpmRegistry}${Reset}"
Write-Host "${Blue}========================================${Reset}"

# 构建镜像
Write-Host "${Yellow}开始构建 Docker 镜像...${Reset}"
$buildArgs = @(
    "build",
    "--build-arg", "NODE_IMAGE=$NodeImage",
    "--build-arg", "NGINX_IMAGE=$NginxImage",
    "--build-arg", "NPM_REGISTRY=$NpmRegistry",
    "-t", "$FullTag",
    "-f", "Dockerfile",
    "."
)

$process = Start-Process -FilePath "docker" -ArgumentList $buildArgs -Wait -NoNewWindow -PassThru

if ($process.ExitCode -ne 0) {
    Write-Host "${Red}========================================${Reset}"
    Write-Host "${Red}  Docker 镜像构建失败${Reset}"
    Write-Host "${Red}========================================${Reset}"
    exit 1
}

Write-Host "${Green}========================================${Reset}"
Write-Host "${Green}  Docker 镜像构建成功${Reset}"
Write-Host "${Green}  镜像: ${FullTag}${Reset}"
Write-Host "${Green}========================================${Reset}"

# 可选：推送镜像
if ($PushAfterBuild) {
    Write-Host "${Yellow}正在推送镜像到仓库...${Reset}"
    docker push "${FullTag}"
    Write-Host "${Green}镜像推送完成: ${FullTag}${Reset}"
}

# 显示运行命令示例
Write-Host ""
Write-Host "${Blue}运行示例:${Reset}"
Write-Host "  ${Yellow}docker run -d -p 80:80 --name singular-origo-frontend ${FullTag}${Reset}"
Write-Host ""
Write-Host "${Blue}查看镜像:${Reset}"
Write-Host "  ${Yellow}docker images | Select-String ${ImageName}${Reset}"
