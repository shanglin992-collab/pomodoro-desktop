$desktop = [Environment]::GetFolderPath("Desktop")
$target = Join-Path $PSScriptRoot "启动番茄钟.bat"
$lnk = Join-Path $desktop "番茄钟.lnk"

$WshShell = New-Object -ComObject WScript.Shell
$shortcut = $WshShell.CreateShortcut($lnk)
$shortcut.TargetPath = $target
$shortcut.WorkingDirectory = $PSScriptRoot
$shortcut.Description = "番茄钟"
$shortcut.Save()

Write-Host "Done! Shortcut created on Desktop." -ForegroundColor Green
Start-Sleep -Seconds 2
