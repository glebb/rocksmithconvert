import os
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QListWidget, QPlainTextEdit

class DropArea(QPlainTextEdit):
    selected = pyqtSignal(str)

    def __init__(self, parent = None):
        super(DropArea, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)

    def dragEnterEvent(self, event):
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasText():
            files = mimeData.text().replace('file://','').strip()
            event.acceptProposedAction()
            self.selected.emit(files)

    def dragLeaveEvent(self, event):
        event.accept()
        