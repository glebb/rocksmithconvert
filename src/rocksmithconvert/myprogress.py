from rocksmithconvert.qt_wrapper import QtWidgets


class MyProgress(QtWidgets.QProgressBar):
    def __init__(self, parent: QtWidgets.QProgressBar = None) -> None:
        super(MyProgress, self).__init__(parent)
        self.count: int = 0
