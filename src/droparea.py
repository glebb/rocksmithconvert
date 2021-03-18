from PyQt5.QtCore import QEvent, pyqtSignal
from PyQt5.QtWidgets import QFrame

class DropArea(QFrame):
    filesDropped = pyqtSignal(list)

    def __init__(self, parent: QFrame = None) -> None:
        super(DropArea, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QEvent):
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QEvent):
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            self.filesDropped.emit([url.toLocalFile() for url in mimeData.urls()])
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QEvent):
        event.accept()
        
