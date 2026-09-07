import ctypes

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # PROCESS_SYSTEM_DPI_AWARE
except Exception:
    pass


def get_scale_factor():
    """Windows scaling factor (1.0 = 100%, 1.5 = 150%, etc).

    Needed because being DPI-aware means Windows reports real physical
    pixels everywhere (winfo_screenwidth, geometry()) instead of silently
    stretching a 96-DPI-sized window - so fixed pixel geometry must be
    scaled by hand to keep its intended physical size on a high-DPI screen.
    """
    try:
        return ctypes.windll.user32.GetDpiForSystem() / 96.0
    except Exception:
        return 1.0
