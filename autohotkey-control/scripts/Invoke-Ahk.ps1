param(
    [Parameter(Mandatory=$true)]
    [string]$Code,

    [int]$WaitMs = 0
)

$ahkExe = "C:\Tools\AutoHotkey\AutoHotkey64.exe"
$scriptPath = Join-Path $env:TEMP "ahk_invoke_$(Get-Random).ahk"

# AHK v2 不支持分号分隔语句（分号是注释符），自动转换为换行
# 注意：若字符串字面量中包含分号，请直接写完整 .ahk 文件而非用 -Code 传参
$normalizedCode = $Code -replace ';\s*', "`n"
$fullCode = "#Requires AutoHotkey v2.0`n" + $normalizedCode
$fullCode | Out-File -FilePath $scriptPath -Encoding utf8

$proc = Start-Process -FilePath $ahkExe -ArgumentList "`"$scriptPath`"" -PassThru

if ($WaitMs -gt 0) {
    $proc | Wait-Process -Timeout ($WaitMs / 1000) -ErrorAction SilentlyContinue
}

Write-Output "AHK script executed: $scriptPath"
Write-Output "Process ID: $($proc.Id)"
