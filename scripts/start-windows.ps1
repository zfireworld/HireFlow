# 在项目根目录：powershell -ExecutionPolicy Bypass -File .\scripts\start-windows.ps1
$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
if (!(Get-Command docker -ErrorAction SilentlyContinue)) { throw '未检测到 Docker，请先安装并启动 Docker Desktop。' }
if (!(Test-Path '.env')) {
 Copy-Item '.env.example' '.env'
 Write-Host '已创建 .env；服务器模型配置可在该文件中填写。' -ForegroundColor Yellow
}
docker compose up -d --build
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 启动失败，请检查 Docker Desktop 并查看日志。' }
Write-Host 'HireFlow AI: http://localhost:8080' -ForegroundColor Green
Write-Host 'Swagger: http://localhost:8080/docs'
