from functools import lru_cache
import sys
from pathlib import Path


@lru_cache(maxsize=1)
def assets_path():
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = Path(__file__).parent.absolute()

    return str(base_path).replace("\\", "/") + "/assets/"
