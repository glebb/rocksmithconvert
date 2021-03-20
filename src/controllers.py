from os import path
from typing import List
from autoprocess import AutoProcessor
from models import ProcessModel
from services import ConvertService
from widgets import MainWindow
from PyQt5.QtCore import pyqtSlot, QObject


class MainWindowController(QObject):
    def __init__(self, files: List[str]):
        super(MainWindowController, self).__init__()
        self.window = MainWindow()
        self.convertService = ConvertService()
        self.ap = AutoProcessor()
        self.setupMainWindowSignals()
        self.setupServiceSignals()
        self.initProcessing(files)

    def setupMainWindowSignals(self):
        self.window.checkBoxAutoProcess.stateChanged.connect(
            self.autoProcessStateChanged)
        self.window.frameDropArea.filesDropped.connect(self.processFiles)
        self.window.pushButtonSelectTarget.clicked.connect(self.selectTargetFolder)
        self.window.pushButtonSelectSource.clicked.connect(
            self.openSelectSourceDialog)


    def setupServiceSignals(self):
        self.convertService.threadSignals.finished.connect(
            self.window.finishedProcessing)

        self.convertService.threadSignals.startProcess.connect(self.window.process)
        self.convertService.threadSignals.update.connect(
            self.window.updateProgress)
        self.convertService.threadSignals.info.connect(
            self.window.writeInfo)
        self.ap.folderNotSet.connect(self.openSelectSourceDialog)
        self.ap.filesAdded.connect(self.processFiles)

    def initProcessing(self, files):
        if files:
            self.processFiles(files)
        if self.window.checkBoxAutoProcess.isChecked():
            self.ap.autoProcessFolder = self.window.pushButtonSelectSource.toolTip()
            self.ap.start()

    @pyqtSlot()
    def selectTargetFolder(self) -> None:
        defDir = self.window.pushButtonSelectTarget.toolTip() if path.isdir(
            self.window.pushButtonSelectTarget.toolTip()) else None
        self.window.openSelectTargetDialog(defDir)

    @pyqtSlot()
    def openSelectSourceDialog(self) -> None:
        defDir = self.window.pushButtonSelectSource.toolTip() if path.isdir(
            self.window.pushButtonSelectSource.toolTip()) else None
        self.window.openSelectSourceDialog(defDir)
        self.autoProcessStateChanged(self.window.checkBoxAutoProcess.isChecked())


    @pyqtSlot(list)
    def processFiles(self, files: List[str]) -> None:
        filesList = [file for file in files if file.endswith('.psarc')]
        if len(filesList) == 0:
            return
        filesList.sort()
        model = ProcessModel(
            self.window.checkBoxConvert.isChecked(),
            self.window.checkBoxRename.isChecked(),
            filesList,
            self.window.pushButtonSelectTarget.toolTip(),
            self.window.comboBoxPlatform.currentText()
        )
        self.window.setFileList(filesList)
        self.convertService.process(model)

    @pyqtSlot(int)
    def autoProcessStateChanged(self, state: int) -> None:
        if bool(state):
            if path.isdir(self.window.pushButtonSelectSource.toolTip()):
                self.ap.autoProcessFolder = self.window.pushButtonSelectSource.toolTip()
                self.ap.start()
            else:
                self.ap.folderNotSet.emit()
        else:
            self.ap.stop()
