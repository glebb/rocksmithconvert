from rocksmithconvert.qt_wrapper import QtCore
from glob import glob
from os import path


class AutoProcessor(QtCore.QObject):
    filesAdded = QtCore.pyqtSignal(list)
    folderNotSet = QtCore.pyqtSignal()

    def __init__(self) -> None:
        super(AutoProcessor, self).__init__()
        self.autoProcessFolder = ""
        self.timer = QtCore.QTimer()
        self.fileList = []
        self.timer.timeout.connect(self.checkFiles)

    def checkFiles(self) -> bool:
        if not path.isdir(self.autoProcessFolder):
            self.folderNotSet.emit()
            return False
        freshFiles = glob(self.autoProcessFolder + "/*.psarc")
        changedFiles = list(set(freshFiles) - set(self.fileList))
        if len(changedFiles) > 0:
            self.filesAdded.emit(changedFiles)
        self.fileList = freshFiles
        return True

    def start(self) -> None:
        if self.checkFiles():
            self.timer.start(5000)

    def stop(self) -> None:
        self.timer.stop()
        self.fileList = []
