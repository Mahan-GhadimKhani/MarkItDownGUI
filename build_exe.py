import os
import sys
import subprocess
from PIL import Image, ImageDraw

def create_icon_file(ico_path: str):
    """Generate a clean icon for MarkItDown if none exists."""
    print("Generating custom icon.ico...")
    size = (256, 256)
    img = Image.new("RGBA", size, color=(31, 106, 165, 255))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle([16, 16, 240, 240], radius=40, fill=(24, 80, 130, 255), outline=(255, 255, 255), width=6)
    draw.polygon([(60, 180), (60, 75), (105, 130), (150, 130), (195, 75), (195, 180), (165, 180), (165, 120), (135, 160), (120, 160), (90, 120), (90, 180)], fill=(255, 255, 255))
    draw.polygon([(115, 185), (140, 185), (127, 205)], fill=(0, 220, 130))

    img.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (32, 32), (16, 16)])
    print(f"Icon created at: {ico_path}")

def create_desktop_shortcut(target_exe: str, ico_path: str):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "MarkItDown.lnk")

    print(f"Creating Desktop shortcut at: {shortcut_path}")
    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        shortcut.TargetPath = target_exe
        shortcut.WorkingDirectory = os.path.dirname(target_exe)
        shortcut.IconLocation = ico_path
        shortcut.Description = "Microsoft MarkItDown Desktop Application"
        shortcut.save()
        print("[SUCCESS] Desktop shortcut created successfully!")
    except Exception as e:
        print("Using PowerShell fallback for shortcut creation...", e)
        ps_cmd = f'''
        $WshShell = New-Object -ComObject WScript.Shell
        $Shortcut = $WshShell.CreateShortcut("{shortcut_path}")
        $Shortcut.TargetPath = "{target_exe}"
        $Shortcut.WorkingDirectory = "{os.path.dirname(target_exe)}"
        $Shortcut.IconLocation = "{ico_path}"
        $Shortcut.Save()
        '''
        res = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
        if res.returncode == 0:
            print("[SUCCESS] Desktop shortcut created via PowerShell!")
        else:
            print("Failed to create shortcut:", res.stderr)

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "icon.ico")
    
    if not os.path.exists(ico_path):
        create_icon_file(ico_path)

    app_script = os.path.join(base_dir, "app.py")
    exe_path = os.path.join(base_dir, "dist", "MarkItDown.exe")

    # Always rebuild PyInstaller to include latest app.py changes
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        f"--name=MarkItDown",
        f"--icon={ico_path}",
        "--clean",
        "--collect-all", "customtkinter",
        "--collect-all", "markitdown",
        "--collect-all", "magika",
        app_script
    ]
    print("Rebuilding PyInstaller executable with latest app.py...")
    res = subprocess.run(pyinstaller_cmd, cwd=base_dir)
    if res.returncode != 0:
        print("[ERROR] PyInstaller build failed!")
        return

    print(f"\n[SUCCESS] Executable rebuilt at: {exe_path}")
    create_desktop_shortcut(exe_path, ico_path)

if __name__ == "__main__":
    main()
