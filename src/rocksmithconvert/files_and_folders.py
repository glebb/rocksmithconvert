from os import path
from sys import platform
from typing import List

def shortenFolder(folder: str) -> str:
    if len(folder) > 25:
        folder = "... " + folder[-25:]
    return folder

def tryGetDefaultRocksmithPath() -> str:
    if platform == "darwin":
        default = path.join(path.expanduser("~"), "Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc")
    else:
        default = "C:\\Program Files (x86)\\Steam\\steamapps\\common\\Rocksmith2014\\dlc"
    if path.isdir(default):
        return default
    return ""

def filterAndSortPsarcFiles(files: List[str]) -> List[str]:
    filesList = [file for file in files if file.endswith('.psarc')]
    return filesList