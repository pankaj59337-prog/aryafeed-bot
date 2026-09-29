import os
import subprocess
import sys

bot_dir = os.path.dirname(os.path.abspath(__file__))
flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP

p = subprocess.Popen(
    ["C:\\Python314\\pythonw.exe", "main.py"],
    cwd=bot_dir,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=flags,
    close_fds=True,
)

with open(os.path.join(bot_dir, "aryafeed_bot.pid"), "w", encoding="utf-8") as f:
    f.write(str(p.pid))

print(f"AryaFeed Bot successfully detached with PID: {p.pid}")
