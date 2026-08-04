import os
import sys
import subprocess

def create_desktop_shortcut(target_exe: str, ico_path: str):
    desktop = os.path.join(os.path.expanduser("~"), "Desktop")
    shortcut_path = os.path.join(desktop, "MarkItDown.lnk")

    print(f"Creating Desktop shortcut at: {shortcut_path}")
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
    ico_path = os.path.join(base_dir, "Markitdown-Logo.ico")
    
    if not os.path.exists(ico_path):
        print(f"[ERROR] Icon file not found: {ico_path}")
        return

    app_script = os.path.join(base_dir, "app.py")
    exe_path = os.path.join(base_dir, "dist", "MarkItDown.exe")

    # Rebuild PyInstaller with --onefile (single standalone executable) and excluding heavy unused Qt modules
    pyinstaller_cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--onefile",
        "--noconfirm",
        f"--name=MarkItDown",
        f"--icon={ico_path}",
        "--clean",
        "--collect-submodules", "PySide6.QtCore",
        "--collect-submodules", "PySide6.QtWidgets",
        "--collect-submodules", "PySide6.QtGui",
        "--exclude-module", "PySide6.QtWebEngineCore",
        "--exclude-module", "PySide6.QtWebEngineWidgets",
        "--exclude-module", "PySide6.QtWebEngineQuick",
        "--exclude-module", "PySide6.QtQml",
        "--exclude-module", "PySide6.QtQuick",
        "--exclude-module", "PySide6.Qt3DCore",
        "--exclude-module", "PySide6.QtBluetooth",
        "--exclude-module", "PySide6.QtSql",
        "--exclude-module", "PySide6.QtSensors",
        "--exclude-module", "PySide6.QtPositioning",
        "--exclude-module", "PySide6.QtMultimedia",
        "--exclude-module", "PySide6.QtNfc",
        "--exclude-module", "PySide6.QtPdf",
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
    
    # In --onefile mode, there is no _internal directory to clean up.
    # Exclusions are already handled by PyInstaller flags.
    create_desktop_shortcut(exe_path, ico_path)

if __name__ == "__main__":
    main()
