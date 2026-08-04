import os
import sys
import subprocess
import shutil

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

def get_base_pyinstaller_cmd(ico_path, app_script):
    return [
        sys.executable, "-m", "PyInstaller",
        "--noconsole",
        "--noconfirm",
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

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ico_path = os.path.join(base_dir, "Markitdown-Logo.ico")
    
    if not os.path.exists(ico_path):
        print(f"[ERROR] Icon file not found: {ico_path}")
        return

    app_script = os.path.join(base_dir, "app.py")

    # Pass 1: Build --onedir (for the Zip)
    print("=== PASS 1: Building --onedir for Zip archive ===")
    cmd_onedir = get_base_pyinstaller_cmd(ico_path, app_script) + [
        "--onedir",
        "--name=MarkItDown"
    ]
    res1 = subprocess.run(cmd_onedir, cwd=base_dir)
    if res1.returncode != 0:
        print("[ERROR] Pass 1 (--onedir) failed!")
        return

    # Clean up bloat for the onedir build
    print("\nCleaning up unused bloat DLLs from onedir build...")
    bloat_files = ["opengl32sw.dll", "Qt6Quick.dll", "Qt6Network.dll", "Qt6Qml.dll", "Qt6QmlModels.dll"]
    for bf in bloat_files:
        bf_path = os.path.join(base_dir, "dist", "MarkItDown", "_internal", "PySide6", bf)
        if os.path.exists(bf_path):
            try:
                os.remove(bf_path)
            except Exception:
                pass

    # Create the zip archive (dist/MarkItDown.zip)
    print("Creating MarkItDown.zip...")
    shutil.make_archive(
        base_name=os.path.join(base_dir, "dist", "MarkItDown"), 
        format='zip', 
        root_dir=os.path.join(base_dir, "dist"), 
        base_dir="MarkItDown"
    )

    # Pass 2: Build --onefile (for the Portable exe)
    print("\n=== PASS 2: Building --onefile for Portable Executable ===")
    cmd_onefile = get_base_pyinstaller_cmd(ico_path, app_script) + [
        "--onefile",
        "--name=MarkItDown-Portable"
    ]
    res2 = subprocess.run(cmd_onefile, cwd=base_dir)
    if res2.returncode != 0:
        print("[ERROR] Pass 2 (--onefile) failed!")
        return

    portable_exe_path = os.path.join(base_dir, "dist", "MarkItDown-Portable.exe")
    print(f"\n[SUCCESS] Dual build complete!")
    print(f"1. Zip Package: dist\\MarkItDown.zip")
    print(f"2. Portable Exe: {portable_exe_path}")

    create_desktop_shortcut(portable_exe_path, ico_path)

if __name__ == "__main__":
    main()
