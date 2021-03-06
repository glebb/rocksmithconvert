from PyQt5.QtCore import QEvent, pyqtSignal
from PyQt5.QtWidgets import QFrame

class DropArea(QFrame):
    selected = pyqtSignal(str)

    def __init__(self, parent: QFrame = None) -> None:
        super(DropArea, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def dragEnterEvent(self, event: QEvent):
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QEvent):
        mimeData = event.mimeData()
        if mimeData.hasText():
            files = mimeData.text().replace('file://','').strip()
            event.acceptProposedAction()
            self.selected.emit(files)

    def dragLeaveEvent(self, event: QEvent):
        event.accept()
        