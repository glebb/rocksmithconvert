from PyQt5.QtWidgets import QProgressBar


class MyProgress(QProgressBar):
    def __init__(self, parent: QProgressBar = None) -> None:
        super(MyProgress, self).__init__(parent)
        self.count: int = 0
