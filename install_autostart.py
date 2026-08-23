import os
import subprocess
import sys
import tempfile
from pathlib import Path

import app_icon

APP_DIR = Path(__file__).resolve().parent
MAIN_PY = APP_DIR / "main.py"
ICON_PATH = APP_DIR / "icon.ico"
VBS_NAME = "MeetingNotifier.vbs"
SHORTCUT_NAME = "Meeting Notifier.lnk"


def startup_folder():
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def start_menu_folder():
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def pythonw_path():
    # sys.executable is the interpreter currently running this script
    # (resolved through the pyenv shim to the real python.exe). Swap in the
    # windowless variant that lives alongside it.
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    if candidate.exists():
        return candidate
    return exe  # fallback: still works, just shows a console window


def _install_autostart(pythonw):
    vbs_path = startup_folder() / VBS_NAME
    vbs_content = (
        'Set objShell = CreateObject("WScript.Shell")\n'
        f'objShell.Run Chr(34) & "{pythonw}" & Chr(34) & " " & Chr(34) & "{MAIN_PY}" & Chr(34), 0, False\n'
    )
    vbs_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_path.write_text(vbs_content, encoding="utf-8")
    print(f"Installed autostart launcher (runs at every login): {vbs_path}")


def _uninstall_autostart():
    vbs_path = startup_folder() / VBS_NAME
    if vbs_path.exists():
        vbs_path.unlink()
        print(f"Removed autostart launcher: {vbs_path}")
    else:
        print("No autostart launcher found.")


def _install_start_menu_shortcut(pythonw):
    """Create a real .lnk in the Start Menu so the app shows up in Windows
    search (press Windows key, type "Meeting Notifier") and can be launched
    with a click, same as any installed app."""
    app_icon.save_ico(ICON_PATH)

    shortcut_path = start_menu_folder() / SHORTCUT_NAME
    vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{pythonw}"
oLink.Arguments = Chr(34) & "{MAIN_PY}" & Chr(34)
oLink.WorkingDirectory = "{APP_DIR}"
oLink.IconLocation = "{ICON_PATH}"
oLink.Description = "Meeting Notifier"
oLink.Save
'''
    with tempfile.NamedTemporaryFile(mode="w", suffix=".vbs", delete=False, encoding="utf-8") as f:
        f.write(vbs_script)
        temp_vbs = f.name

    try:
        subprocess.run(["cscript", "//nologo", "//B", temp_vbs], check=True)
    finally:
        Path(temp_vbs).unlink(missing_ok=True)

    print(f"Installed Start Menu shortcut: {shortcut_path}")
    print('  -> search "Meeting Notifier" in the Windows Start menu to launch it')


def _uninstall_start_menu_shortcut():
    shortcut_path = start_menu_folder() / SHORTCUT_NAME
    if shortcut_path.exists():
        shortcut_path.unlink()
        print(f"Removed Start Menu shortcut: {shortcut_path}")
    else:
        print("No Start Menu shortcut found.")


def install():
    pythonw = pythonw_path()
    _install_autostart(pythonw)
    _install_start_menu_shortcut(pythonw)


def uninstall():
    _uninstall_autostart()
    _uninstall_start_menu_shortcut()


if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        uninstall()
    else:
        install()
