@echo off
cd /d "D:\aryafeed bot"
wscript //nologo start_bot_silent.vbs
echo AryaFeed Bot started in background!
ping 127.0.0.1 -n 2 >nul
