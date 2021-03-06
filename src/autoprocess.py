from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot
from glob import glob
import os

class AutoProcessor(QObject):
    filesAdded = pyqtSignal(str)
    folderNotSet = pyqtSignal()

    def __init__(self) -> None:
        super(AutoProcessor, self).__init__()
        self.autoProcessFolder = ''
        self.timer = QTimer()
        self.fileList = []
        self.timer.timeout.connect(self.checkFiles)

    @pyqtSlot(int)
    def autoProcessStateChanged(self, state: int) -> None:
        if bool(state):
            if not os.path.isdir(self.autoProcessFolder):
                self.folderNotSet.emit()
                return
            self.start()
        else:
            self.stop()

    def checkFiles(self) -> bool:
        if not os.path.isdir(self.autoProcessFolder):
            self.folderNotSet.emit()
            return False
        freshFiles = glob(self.autoProcessFolder + "/*.psarc")
        changedFiles = list(set(freshFiles) - set(self.fileList))
        if len(changedFiles) > 0:
            self.filesAdded.emit("\n".join(changedFiles))
        self.fileList = freshFiles
        return True

    def start(self) -> None:
        if self.checkFiles():
            self.timer.start(5000)

    def stop(self) -> None:
        self.timer.stop()
        self.fileList = []
