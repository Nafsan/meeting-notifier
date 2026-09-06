import os
import subprocess
import sys
import tempfile
from pathlib import Path

import app_icon
from config import FROZEN, USER_DATA_DIR

SOURCE_DIR = Path(__file__).resolve().parent  # only meaningful in dev mode
ICON_PATH = USER_DATA_DIR / "icon.ico"
VBS_NAME = "MeetingNotifier.vbs"
SHORTCUT_NAME = "Meeting Notifier.lnk"


def _launch_target():
    """Returns (target_path, arguments) to launch the app, whether frozen
    (the exe itself) or running from source (pythonw + main.py)."""
    if FROZEN:
        return str(Path(sys.executable).resolve()), ""

    exe = Path(sys.executable)
    pythonw = exe.with_name("pythonw.exe")
    if not pythonw.exists():
        pythonw = exe  # fallback: still works, just shows a console window
    main_py = SOURCE_DIR / "main.py"
    return str(pythonw), f'"{main_py}"'


def startup_folder():
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def start_menu_folder():
    appdata = os.environ["APPDATA"]
    return Path(appdata) / "Microsoft" / "Windows" / "Start Menu" / "Programs"


def is_autostart_enabled():
    return (startup_folder() / VBS_NAME).exists()


def _install_autostart_entry(target, args):
    vbs_path = startup_folder() / VBS_NAME
    vbs_content = (
        'Set objShell = CreateObject("WScript.Shell")\n'
        f'objShell.Run Chr(34) & "{target}" & Chr(34) & " {args}", 0, False\n'
    )
    vbs_path.parent.mkdir(parents=True, exist_ok=True)
    vbs_path.write_text(vbs_content, encoding="utf-8")


def _uninstall_autostart_entry():
    vbs_path = startup_folder() / VBS_NAME
    if vbs_path.exists():
        vbs_path.unlink()


def _install_start_menu_shortcut(target, args):
    if not ICON_PATH.exists():
        app_icon.save_ico(ICON_PATH)

    shortcut_path = start_menu_folder() / SHORTCUT_NAME
    vbs_script = f'''
Set oWS = WScript.CreateObject("WScript.Shell")
Set oLink = oWS.CreateShortcut("{shortcut_path}")
oLink.TargetPath = "{target}"
oLink.Arguments = "{args}"
oLink.WorkingDirectory = "{Path(target).resolve().parent}"
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


def _uninstall_start_menu_shortcut():
    shortcut_path = start_menu_folder() / SHORTCUT_NAME
    if shortcut_path.exists():
        shortcut_path.unlink()


def install():
    target, args = _launch_target()
    _install_autostart_entry(target, args)
    _install_start_menu_shortcut(target, args)


def uninstall():
    _uninstall_autostart_entry()
    _uninstall_start_menu_shortcut()
