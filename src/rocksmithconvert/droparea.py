from rocksmithconvert.qt_wrapper import QtCore, QtWidgets
import os
import glob
from typing import List


class DropArea(QtWidgets.QFrame):
    filesDropped = QtCore.pyqtSignal(list)

    def __init__(self, parent: QtWidgets.QFrame = None) -> None:
        super(DropArea, self).__init__(parent)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, event: QtCore.QEvent):
        event.acceptProposedAction()

    def dragMoveEvent(self, event: QtCore.QEvent):
        event.acceptProposedAction()

    def dropEvent(self, event: QtCore.QEvent):
        mimeData = event.mimeData()
        if mimeData.hasUrls():
            files: List[str] = []
            for url in mimeData.urls():
                localFile = url.toLocalFile()
                if os.path.isdir(localFile):
                    files.extend(
                        glob.iglob(
                            os.path.join(localFile, "**", "*.psarc"),
                            recursive=True,
                        )
                    )
                else:
                    files.append(localFile)
            self.filesDropped.emit(files)
            event.acceptProposedAction()

    def dragLeaveEvent(self, event: QtCore.QEvent):
        event.accept()
