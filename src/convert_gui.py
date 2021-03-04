import sys
import os
import argparse
from typing import Dict
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtGui import QCloseEvent
from mainwindow import Ui_MainWindow
from models import ProcessModel
from services import ConvertService
import settings
import folders
from autoprocess import AutoProcessor


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    settings = QtCore.QSettings("gui.ini", QtCore.QSettings.IniFormat)

    def __init__(self, *args, obj=None, **kwargs) -> None:
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.centralwidget.setObjectName("CentralWidget")
        self.setStyleSheet(
            "#CentralWidget{background-image:  url(:/assets/assets/snow.jpg); border : 0px}")
        self.messageBox = QtWidgets.QMessageBox()
        self.processModel: ProcessModel = ProcessModel()
        self.convertService: ConvertService = ConvertService()
        self.filesNamesToProcess: list[str] = []
        self.ap = AutoProcessor()
        self.setupSignals()
        self.initUI()
        if self.checkBoxAutoProcess.isChecked() and self.ap.autoProcessFolder:
            self.ap.start()

    def setupSignals(self) -> None:
        self.pushButtonSelectTarget.clicked.connect(
            self.openSelectTargetDialog)
        self.pushButtonDownloadDir.clicked.connect(
            self.openSelectDownloadDirDialog)
        self.processModel.targetSet.connect(self.setTargetFolder)
        self.plainTextEdit.selected.connect(self.setFilesList)
        self.convertService.listWidgetSignals.finished.connect(
            self.updateProgress)
        self.convertService.listWidgetSignals.info.connect(
            self.writeInfo)

        self.processButton.clicked.connect(self.process)

        self.checkBoxConvert.stateChanged.connect(self.processModel.setConvert)
        self.checkBoxConvert.stateChanged.connect(self.setTargetPlatformState)
        self.checkBoxRename.stateChanged.connect(self.processModel.setRename)

        self.processModel.canProcess.connect(self.processButton.setEnabled)

        self.comboBoxPlatform.currentTextChanged.connect(
            self.processModel.setPlatform)
        self.checkBoxAutoProcess.stateChanged.connect(
            self.ap.autoProcessStateChanged)

        self.ap.filesAdded.connect(self.setFilesList)

    def initUI(self) -> None:
        settings.loadSettings(self.settings)
        self.progressBar.setValue(0)
        self.processModel.trySetDefaultPath(self.pushButtonSelectTarget.toolTip())
        self.processModel.setConvert(self.checkBoxConvert.isChecked())
        self.processModel.setRename(self.checkBoxRename.isChecked())
        self.processModel.setPlatform(self.comboBoxPlatform.currentText())
        self.setTargetPlatformState(self.checkBoxConvert.isChecked())
        if os.path.isdir(self.pushButtonDownloadDir.toolTip()):
            self.ap.autoProcessFolder = self.pushButtonDownloadDir.toolTip()
        else:
            self.pushButtonDownloadDir.setText("Set auto-process folder")
        if os.path.isdir(self.pushButtonSelectTarget.toolTip()):
            self.processModel.setTarget(self.pushButtonSelectTarget.toolTip())


    def closeEvent(self, event: QCloseEvent) -> None:
        settings.saveSettings(self.settings)
        QtWidgets.QMainWindow.closeEvent(self, event)

    @QtCore.pyqtSlot()
    def openSelectTargetDialog(self) -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "QFileDialog.getOpenFileName()", self.processModel._target, options=options)
        if directory:
            self.processModel.setTarget(directory)

    @QtCore.pyqtSlot(str)
    def writeInfo(self, info) -> None:
        self.plainTextEdit.appendHtml(
            f"<span style='color: red'>{info}</span>")

    @QtCore.pyqtSlot()
    def openSelectDownloadDirDialog(self) -> None:
        defDir = self.pushButtonDownloadDir.text() if os.path.isdir(
            self.pushButtonDownloadDir.toolTip()) else None
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "QFileDialog.getOpenFileName()", defDir, options=options)
        if directory and directory != self.processModel._target:
            self.ap.autoProcessFolder = directory
            self.pushButtonDownloadDir.setText(folders.shortenFolder(directory))
            self.pushButtonDownloadDir.setToolTip(directory)
            self.ap.autoProcessStateChanged(int(self.checkBoxAutoProcess.isChecked()))
        if directory == self.processModel._target:
            self.messageBox.setText(
                f"Target and auto-process folder need to be different.")
            self.messageBox.exec()

    @QtCore.pyqtSlot(str)
    def setFilesList(self, files: str) -> None:
        filesList = files.strip().split("\n")
        filesList.sort()
        self.processModel.setFiles(filesList)
        self.processButton.setText(f'Process {len(filesList)} files')
        if not self.checkBoxAutoProcess.isChecked():
            self.plainTextEdit.clear()
        if len(files) > 0:
            names = [os.path.split(filename)[1] for filename in filesList]
            self.plainTextEdit.appendHtml(
                "<p><strong>Source files:</strong></p>")
            for name in names:
                self.plainTextEdit.appendHtml(f"{name}")
            if self.checkBoxAutoProcess.isChecked():
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
        self.filesNamesToProcess = self.processModel._files.copy()
        self.convertService.process(self.processModel)

    @QtCore.pyqtSlot(str)
    def setTargetFolder(self, target: str) -> None:
        self.pushButtonSelectTarget.setToolTip(target)
        self.pushButtonSelectTarget.setText(folders.shortenFolder(target))

    @QtCore.pyqtSlot(dict)
    def updateProgress(self, file: Dict[str, str]) -> None:
        self.progressBar.setValue(
            self.progressBar.value() + round(100/len(self.filesNamesToProcess)))
        copyOfFiles = self.processModel._files.copy()
        copyOfFiles.remove(file['original'])
        self.processModel.setFiles(copyOfFiles)
        self.processButton.setText(f'Process {len(copyOfFiles)} files')
        if file['processed']:
            _, tail = os.path.split(file['processed'])
            self.plainTextEdit.appendHtml(f"{tail}")
        if len(copyOfFiles) == 0:
            processedCount = len(self.filesNamesToProcess)
            finished = f"Finished processing {processedCount} files."
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
        self.progressBar.setValue(0)

    def allowUserInteraction(self, mode: bool) -> None:
        self.plainTextEdit.setAcceptDrops(mode)
        self.pushButtonSelectTarget.setEnabled(mode)
        self.comboBoxPlatform.setEnabled(mode)
        self.checkBoxConvert.setEnabled(mode)
        self.checkBoxConvert.setEnabled(mode)
        self.checkBoxAutoProcess.setEnabled(mode)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs='*')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    if args.files:
        window.setFilesList("\n".join(args.files))
    window.show()
    app.exec()
