import os
from typing import Dict, List
from PyQt5 import QtWidgets, QtCore, QtGui
from mainwindow import Ui_MainWindow
from models import ProcessModel
from services import ConvertService
import settings
import files_and_folders
from autoprocess import AutoProcessor


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    settings = QtCore.QSettings("gui.ini", QtCore.QSettings.IniFormat)

    def __init__(self, *args, obj=None, **kwargs) -> None:
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setStyleSheet(
            "#MainWindow{background-image:  url(:/assets/assets/snow.jpg); border : 0px}")
        settings.loadSettings(self.settings)
        self.setTargetPlatformState(self.checkBoxConvert.isChecked())
        self.messageBox: QtWidgets.QMessageBox = QtWidgets.QMessageBox()
        self.processModel: ProcessModel = ProcessModel()
        self.convertService: ConvertService = ConvertService()
        self.ap: AutoProcessor = AutoProcessor()
        self.setupUiSignals()
        self.setupCustomSignals()
        self.initProcessing()

    def setupUiSignals(self) -> None:
        self.pushButtonSelectTarget.clicked.connect(
            self.openSelectTargetDialog)

        self.pushButtonSelectSource.clicked.connect(
            self.openSelectSourceDialog)

        self.checkBoxConvert.stateChanged.connect(self.processModel.setConvert)
        self.checkBoxConvert.stateChanged.connect(self.setTargetPlatformState)

        self.checkBoxRename.stateChanged.connect(self.processModel.setRename)

        self.comboBoxPlatform.currentTextChanged.connect(
            self.processModel.setPlatform)

        self.checkBoxAutoProcess.stateChanged.connect(
            self.ap.autoProcessStateChanged)

    def setupCustomSignals(self):
        self.ap.filesAdded.connect(self.setFilesList)
        self.ap.folderNotSet.connect(self.openSelectSourceDialog)
        self.processModel.targetSet.connect(self.setTargetFolder)
        self.frameDropArea.selected.connect(self.setFilesList)
        self.convertService.listWidgetSignals.finished.connect(
            self.updateProgress)
        self.convertService.listWidgetSignals.info.connect(
            self.writeInfo)

    def initProcessing(self):
        self.processModel.trySetDefaultPath(self.pushButtonSelectTarget.toolTip())
        self.processModel.setConvert(self.checkBoxConvert.isChecked())
        self.processModel.setRename(self.checkBoxRename.isChecked())
        self.processModel.setPlatform(self.comboBoxPlatform.currentText())
        self.ap.autoProcessFolder = self.pushButtonSelectSource.toolTip()
        if self.checkBoxAutoProcess.isChecked():
            self.ap.start()


    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        settings.saveSettings(self.settings)
        QtWidgets.QMainWindow.closeEvent(self, event)

    @QtCore.pyqtSlot()
    def openSelectTargetDialog(self) -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select target folder", self.processModel._target, options=options)
        if directory:
            self.processModel.setTarget(directory)

    @QtCore.pyqtSlot(str)
    def writeInfo(self, info) -> None:
        self.plainTextEdit.appendHtml(
            f"<span style='color: red'>{info}</span>")

    @QtCore.pyqtSlot()
    def openSelectSourceDialog(self) -> None:
        defDir = self.pushButtonSelectSource.toolTip() if os.path.isdir(
            self.pushButtonSelectSource.toolTip()) else None
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select source folder", defDir, options=options)
        if directory and directory != self.processModel._target:
            self.ap.autoProcessFolder = directory
            self.pushButtonSelectSource.setText(files_and_folders.shortenFolder(directory))
            self.pushButtonSelectSource.setToolTip(directory)
            self.ap.autoProcessStateChanged(int(self.checkBoxAutoProcess.isChecked()))
            return
        if directory == self.processModel._target:
            self.messageBox.setText(
                f"Target and auto-process folder need to be different.")
            self.messageBox.exec()
        self.disableAutoProcessor()

    def disableAutoProcessor(self):
        self.checkBoxAutoProcess.setCheckState(0)
        self.pushButtonSelectSource.setText('Select auto-process folder')
        self.pushButtonSelectSource.setToolTip('')
        self.ap.autoProcessFolder = ''


    @QtCore.pyqtSlot(list)
    def setFilesList(self, files: List[str]) -> None:
        filesList = [file for file in files if file.endswith('.psarc')]
        if len(filesList) == 0:
            return
        filesList.sort()
        self.processModel.setFiles(filesList)

        if not self.checkBoxAutoProcess.isChecked():
            self.plainTextEdit.clear()
        else:
            self.plainTextEdit.appendHtml('<br>')  

        self.plainTextEdit.appendHtml(
            "<p><strong>Source files:</strong></p>")
        names = [os.path.split(filename)[1] for filename in filesList]
        for name in names:
            self.plainTextEdit.appendHtml(f"{name}")

        self.process()

    @QtCore.pyqtSlot()
    def process(self) -> None:
        success, message = self.processModel.setProcessing(True)
        if not success:
            self.finishedProcessing()
            error_dialog = QtWidgets.QErrorMessage()
            error_dialog.showMessage(f"Processing failed: {message}")
            error_dialog.exec()
            return
        self.allowUserInteraction(False)
        self.plainTextEdit.appendHtml("<br><p><strong>Process log:</strong></p>")
        self.progressBar.setValue(0)
        self.convertService.process(self.processModel)

    @QtCore.pyqtSlot(str)
    def setTargetFolder(self, target: str) -> None:
        self.pushButtonSelectTarget.setToolTip(target)
        self.pushButtonSelectTarget.setText(files_and_folders.shortenFolder(target))

    @QtCore.pyqtSlot(dict)
    def updateProgress(self, file: Dict[str, str]) -> None:
        self.progressBar.setValue(
            self.progressBar.value() + round(100/self.processModel._count))
        copyOfFiles = self.processModel._files.copy()
        copyOfFiles.remove(file['original'])
        self.processModel.setFiles(copyOfFiles)
        if file['processed']:
            _, tail = os.path.split(file['processed'])
            self.plainTextEdit.appendHtml(f"{tail}")
        if len(copyOfFiles) == 0:
            finished = f"Finished processing {self.processModel._count} files."
            self.plainTextEdit.appendHtml(finished)
            self.plainTextEdit.ensureCursorVisible()
            self.finishedProcessing()
            if not self.checkBoxAutoProcess.isChecked():
                self.messageBox.setText(finished)
                self.messageBox.exec()

    @QtCore.pyqtSlot(int)
    def setTargetPlatformState(self, state: int) -> None:
        if state:
            self.comboBoxPlatform.setEnabled(True)
            self.comboBoxPlatform.setVisible(True)
        else:
            self.comboBoxPlatform.setDisabled(True)
            self.comboBoxPlatform.setVisible(False)

    def finishedProcessing(self) -> None:
        self.progressBar.setValue(100)
        self.processModel.setProcessing(False)
        self.allowUserInteraction(True)

    def allowUserInteraction(self, mode: bool) -> None:
        self.frameDropArea.setAcceptDrops(mode)
        self.pushButtonSelectTarget.setEnabled(mode)
        self.comboBoxPlatform.setEnabled(mode)
        self.checkBoxConvert.setEnabled(mode)
        self.checkBoxConvert.setEnabled(mode)
        self.checkBoxAutoProcess.setEnabled(mode)
