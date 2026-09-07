import sys

import autostart

if __name__ == "__main__":
    if "--uninstall" in sys.argv:
        autostart.uninstall()
        print("Removed autostart entry and Start Menu shortcut.")
    else:
        autostart.install()
        print("Installed autostart entry and Start Menu shortcut.")
        print('Search "Meeting Notifier" in the Windows Start menu to launch it.')
