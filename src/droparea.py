import os
from PyQt5.QtCore import pyqtSignal, pyqtSlot
from PyQt5.QtWidgets import QListWidget

class DropArea(QListWidget):
    selected = pyqtSignal(list)

    def __init__(self, parent = None):
        super(DropArea, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setAutoFillBackground(True)
        self.setAlternatingRowColors(True)

    def dragEnterEvent(self, event):
        self.setDropIndicatorShown(True)
        event.acceptProposedAction()

    def dragMoveEvent(self, event):
        event.acceptProposedAction()

    def dropEvent(self, event):
        mimeData = event.mimeData()
        if mimeData.hasText():
            files = mimeData.text().replace('file://','').strip().split('\n')
            if type(files) is not list:
                files = [files]
            event.acceptProposedAction()
            self.selected.emit(files.copy())

    def dragLeaveEvent(self, event):
        event.accept()

    @pyqtSlot(list)
    def setFilelist(self, files):
        names = [os.path.split(filename)[1] for filename in files]
        self.clear()
        self.addItems(names)
        