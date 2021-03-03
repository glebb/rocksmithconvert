from PyQt5.QtCore import QTimer, QObject, pyqtSignal, pyqtSlot
from glob import glob

class AutoProcessor(QObject):
    filesAdded = pyqtSignal(str)

    def __init__(self) -> None:
        super(AutoProcessor, self).__init__()
        self.autoProcessFolder = ''
        self.timer = QTimer()
        self.fileList = []
        self.timer.timeout.connect(self.checkFiles)

    @pyqtSlot(int)
    def autoProcessStateChanged(self, state: int) -> None:
        if bool(state) and self.autoProcessFolder:
            self.start()
        else:
            self.stop()

    def checkFiles(self) -> None:
        freshFiles = glob("/Users/bodhi/Downloads/*.psarc")
        changedFiles = list(set(freshFiles) - set(self.fileList))
        if len(changedFiles) > 0:
            self.filesAdded.emit("\n".join(changedFiles))
        self.fileList = freshFiles

    def start(self) -> None:
        self.checkFiles()
        self.timer.start(5000)

    def stop(self) -> None:
        self.timer.stop()
        self.fileList = []
