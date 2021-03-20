from os import path
from typing import Dict, List
from PyQt5 import QtWidgets, QtCore, QtGui
from mainwindow import Ui_MainWindow
import settings
import files_and_folders
from datetime import datetime


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
        self.checkBoxConvert.stateChanged.connect(self.setTargetPlatformState)
        if not self.pushButtonSelectTarget.toolTip():
            defaultFolder = files_and_folders.tryGetDefaultRocksmithPath()
            if defaultFolder:
                self.pushButtonSelectTarget.setText(files_and_folders.shortenFolder(defaultFolder))
                self.pushButtonSelectTarget.setToolTip(defaultFolder)
        self.plainTextEdit.appendHtml(f'Process log {self.timestamp()}')
        self.forceShowWindow()

    def timestamp(self) -> str:
        return datetime.now().strftime("%m/%d/%y %H:%M:%S")

    def forceShowWindow(self):
        self.setWindowFlags(self.windowFlags() &
                            QtCore.Qt.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~
                            QtCore.Qt.WindowStaysOnTopHint)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        settings.saveSettings(self.settings)
        QtWidgets.QMainWindow.closeEvent(self, event)

    def openSelectTargetDialog(self, target: str = "") -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select target folder", target, options=options)
        if directory:
            self.pushButtonSelectTarget.setText(files_and_folders.shortenFolder(directory))
            self.pushButtonSelectTarget.setToolTip(directory)

    def openSelectSourceDialog(self, source: str = "") -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select source folder", source, options=options)
        if directory:
            self.pushButtonSelectSource.setText(files_and_folders.shortenFolder(directory))
            self.pushButtonSelectSource.setToolTip(directory)
        elif not directory and not self.pushButtonSelectSource.toolTip():
            self.checkBoxAutoProcess.setCheckState(0)


    def disableAutoProcessor(self):
        self.checkBoxAutoProcess.setCheckState(0)
        self.pushButtonSelectSource.setText('Select auto-process folder')
        self.pushButtonSelectSource.setToolTip('')

    def allowUserInteraction(self, mode: bool) -> None:
        self.frameDropArea.setAcceptDrops(mode)
        self.pushButtonSelectTarget.setEnabled(mode)
        self.pushButtonSelectSource.setEnabled(mode)
        self.comboBoxPlatform.setEnabled(mode)
        self.checkBoxConvert.setEnabled(mode)
        self.checkBoxRename.setEnabled(mode)
        self.checkBoxAutoProcess.setEnabled(mode)

    def setFileList(self, files: List[str]):
        self.plainTextEdit.appendHtml('<br>')  

        self.plainTextEdit.appendHtml(
            "<p><strong>Source files:</strong></p>")
        names = [path.split(filename)[1] for filename in files]
        for name in names:
            self.plainTextEdit.appendHtml(f"{name}")        

    @QtCore.pyqtSlot(str)
    def writeInfo(self, info) -> None:
        self.plainTextEdit.appendHtml(
            f"<span style='color: red'>{info}</span>")

    @QtCore.pyqtSlot()
    def process(self) -> None:
        self.allowUserInteraction(False)
        self.plainTextEdit.appendHtml("<br><p><strong>Process log:</strong></p>")
        self.progressBar.setValue(0)

    @QtCore.pyqtSlot(dict)
    def updateProgress(self, file: Dict[str, str]) -> None:
        self.progressBar.setValue(
            self.progressBar.value() + round(100/int(file['count'])))
        if file['processed']:
            _, tail = path.split(file['processed'])
            self.plainTextEdit.appendHtml(f"{tail}")

    @QtCore.pyqtSlot(int)
    def setTargetPlatformState(self, state: int) -> None:
        if state:
            self.comboBoxPlatform.setEnabled(True)
            self.comboBoxPlatform.setVisible(True)
        else:
            self.comboBoxPlatform.setDisabled(True)
            self.comboBoxPlatform.setVisible(False)

    @QtCore.pyqtSlot(int)
    def finishedProcessing(self, count) -> None:
        self.progressBar.setValue(100)
        self.plainTextEdit.appendHtml(f"Finished processing {count} files.")
        self.allowUserInteraction(True)

