from os import path
from typing import List
from rocksmithconvert.autoprocess import AutoProcessor
from rocksmithconvert.files_and_folders import filterAndSortPsarcFiles
from rocksmithconvert.models import ProcessModel
from rocksmithconvert.services import ConvertService
from rocksmithconvert.mywindow import MyWindow
from PyQt5.QtCore import pyqtSlot, QObject


class MainWindowController(QObject):
    def __init__(self, files: List[str]):
        super(MainWindowController, self).__init__()
        self.window = MyWindow()
        self.window.setWindowTitle(self.window.windowTitle() + " 2.2")
        self.convertService = ConvertService()
        self.ap = AutoProcessor()
        self.setupMainWindowSignals()
        self.setupServiceSignals()
        self.initProcessing(files)

    def setupMainWindowSignals(self):
        self.window.checkBoxAutoProcess.stateChanged.connect(
            self.autoProcessStateChanged)
        self.window.checkBoxAutoProcess.stateChanged.connect(self.window.saveSettings)
        self.window.frameDropArea.filesDropped.connect(self.processFiles)
        self.window.pushButtonSelectTarget.clicked.connect(self.selectTargetFolder)
        self.window.pushButtonSelectSource.clicked.connect(
            self.openSelectSourceDialog)
        self.window.pushButtonSelectTarget.clicked.connect(self.window.saveSettings)
        self.window.pushButtonSelectSource.clicked.connect(
            self.window.saveSettings)
        self.window.comboBoxAppId.currentIndexChanged.connect(self.window.appIdChange)
        self.window.comboBoxAppId.currentTextChanged.connect(self.window.appIdTextChange)
        self.window.comboBoxPlatform.currentIndexChanged.connect(self.window.convertPlatformChanged)


    def setupServiceSignals(self):
        self.convertService.threadSignals.finished.connect(
            self.window.finishedProcessing)

        self.convertService.threadSignals.startProcess.connect(self.window.process)
        self.convertService.threadSignals.startProcess.connect(self.window.saveSettings)
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
        filesList = filterAndSortPsarcFiles(files)
        if len(filesList) == 0:
            return
        model = ProcessModel(
            filesList,
            self.window.pushButtonSelectTarget.toolTip(),
            self.window.comboBoxPlatform.currentText(),
            self.window.comboBoxRename.currentText(),
            self.window.comboBoxAppId.currentText(),
            self.window.checkBoxOverwrite.isChecked()
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
