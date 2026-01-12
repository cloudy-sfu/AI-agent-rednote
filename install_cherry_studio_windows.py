import os
import sys

base_dir = os.path.abspath(".")
try:
    version = sys.getwindowsversion()
except AttributeError:
    raise Exception("Deployment script only works in Windows.")
base_dir_drive = base_dir.split(":")[0]

main_bat = rf"""{base_dir_drive}:
cd {base_dir}
call .venv\Scripts\activate.bat
python server.py
"""

with open("cherry_studio_windows.bat", "w", encoding="utf-8") as f:
    f.write(main_bat)

cherry_studio_setting = rf"""Cherry studio settings are as follows.
Name: rednote-assistant
Type: Standard Input/Output (stdio)
Command: {base_dir}\cherry_studio_windows.bat
Environment variables: 
    xiaohongshu_cookies_path=
"""

print(cherry_studio_setting)
