@echo off
powershell -NoProfile -Command "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*aryafeed bot*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force; Write-Host ('Stopped AryaFeed PID: ' + $_.ProcessId) }"
echo AryaFeed Bot stopped cleanly!
ping 127.0.0.1 -n 2 >nul
