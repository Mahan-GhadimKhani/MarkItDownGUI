import os
import shutil

base_dir = "c:/Users/mahan/Desktop/SWE Project/MarkItDownGUI"
ico_src = os.path.join(base_dir, "icon.ico")
ico_dst = os.path.join(base_dir, "dist", "MarkItDown", "icon.ico")
if os.path.exists(ico_src):
    shutil.copy2(ico_src, ico_dst)
    print("Copied icon to dist")
