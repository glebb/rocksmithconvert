from typing import List
from widgets import MainWindow


class MainController:
    def __init__(self, files: List[str]):
        self.window = MainWindow(files=files)
