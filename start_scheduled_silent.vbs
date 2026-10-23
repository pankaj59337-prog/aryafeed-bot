Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "D:\instagram bot"
WshShell.Run """C:\Users\Pankaj\AppData\Local\Programs\Python\Python312\pythonw.exe"" scheduled_publisher.py --interval 49 --delay-first", 0, False
