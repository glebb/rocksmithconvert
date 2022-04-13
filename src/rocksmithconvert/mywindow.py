from os import path
from typing import Dict, List
from PyQt6 import QtWidgets, QtCore, QtGui
from rocksmithconvert.mainwindow import Ui_MainWindow
from rocksmithconvert.settings import SettingsHandler
from rocksmithconvert import files_and_folders
from datetime import datetime
from pathlib import Path
import sys


def resource_path():
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = Path(__file__).parent.absolute()

    return base_path


script_path = resource_path()


class MyWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    def __init__(self, *args, obj=None, **kwargs) -> None:
        super(MyWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.setStyleSheet(f"#centralwidget {{ background-image:url('{script_path}/assets/trees.jpg'); border: 0px; background-color: pink; }}"
        )
        self.settingsHandler = SettingsHandler(
            
            settings=QtCore.QSettings(
                QtCore.QSettings.Format.IniFormat,
                QtCore.QSettings.Scope.UserScope,
                "glebb",
                "rocksmithconvert",
            )
        )
        self.settingsHandler.loadSettings()
        self.checkBoxAutoProcess.stateChanged.connect(self.saveSettings)
        self.comboBoxPlatform.currentTextChanged.connect(self.saveSettings)
        if not self.pushButtonSelectTarget.toolTip():
            defaultFolder = files_and_folders.tryGetDefaultRocksmithPath()
            if defaultFolder:
                self.pushButtonSelectTarget.setText(
                    files_and_folders.shortenFolder(defaultFolder)
                )
                self.pushButtonSelectTarget.setToolTip(defaultFolder)
        self.forceShowWindow()
        if self.comboBoxAppId.currentIndex() == 0:
            self.comboBoxAppId.setEditable(False)
        else:
            self.comboBoxAppId.setEditable(True)
            self.comboBoxAppId.setItemText(1, self.comboBoxAppId.currentText())
        if self.comboBoxPlatform.currentIndex() == 0:
            self.comboBoxAppId.setCurrentIndex(0)

    def timestamp(self) -> str:
        return datetime.now().strftime("%m/%d/%y %H:%M:%S")

    def forceShowWindow(self):
        self.setWindowFlags(self.windowFlags() & QtCore.Qt.WindowType.WindowStaysOnTopHint)
        self.show()
        self.setWindowFlags(self.windowFlags() & ~QtCore.Qt.WindowType.WindowStaysOnTopHint)

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:
        self.settingsHandler.saveSettings()
        QtWidgets.QMainWindow.closeEvent(self, event)

    def openSelectTargetDialog(self, target: str = "") -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select target folder", target, options=options
        )
        if directory:
            self.pushButtonSelectTarget.setText(
                files_and_folders.shortenFolder(directory)
            )
            self.pushButtonSelectTarget.setToolTip(directory)
            self.settingsHandler.saveSettings()

    def openSelectSourceDialog(self, source: str = "") -> None:
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Select source folder", source, options=options
        )
        if directory:
            self.pushButtonSelectSource.setText(
                files_and_folders.shortenFolder(directory)
            )
            self.pushButtonSelectSource.setToolTip(directory)
            self.settingsHandler.saveSettings()
        elif not directory and not self.pushButtonSelectSource.toolTip():
            self.checkBoxAutoProcess.setCheckState(0)

    def disableAutoProcessor(self):
        self.checkBoxAutoProcess.setCheckState(0)
        self.pushButtonSelectSource.setText("Select auto-process folder")
        self.pushButtonSelectSource.setToolTip("")
        self.settingsHandler.saveSettings()

    def allowUserInteraction(self, mode: bool) -> None:
        self.frameDropArea.setAcceptDrops(mode)
        self.pushButtonSelectTarget.setEnabled(mode)
        self.pushButtonSelectSource.setEnabled(mode)
        self.comboBoxPlatform.setEnabled(mode)
        self.checkBoxAutoProcess.setEnabled(mode)

    def setFileList(self, files: List[str]):
        self.plainTextEdit.appendHtml(
            f"<strong>Source files {self.timestamp()}:</strong>"
        )
        names = [path.split(filename)[1] for filename in files]
        for name in names:
            self.plainTextEdit.appendHtml(f"{name}")
        self.progressBar.count = 0
        self.plainTextEdit.ensureCursorVisible()

    @QtCore.pyqtSlot(str)
    def writeInfo(self, info) -> None:
        self.plainTextEdit.appendHtml(f"<span style='color: red'>{info}</span>")
        self.plainTextEdit.ensureCursorVisible()

    @QtCore.pyqtSlot()
    def process(self) -> None:
        self.allowUserInteraction(False)
        self.plainTextEdit.appendHtml(
            f"<br><strong>Process log {self.timestamp()}:</strong>"
        )
        self.progressBar.setValue(0)

    @QtCore.pyqtSlot(dict)
    def updateProgress(self, file: Dict[str, str]) -> None:
        self.progressBar.count += 1
        self.progressBar.setValue(
            round(self.progressBar.count / int(file["count"]) * 100)
        )
        if file["processed"]:
            _, tail = path.split(file["processed"])
            self.plainTextEdit.appendHtml(f"OK: {tail}")
        self.plainTextEdit.ensureCursorVisible()

    @QtCore.pyqtSlot(int)
    def setTargetPlatformState(self, state: int) -> None:
        if state:
            self.comboBoxPlatform.setEnabled(True)
            self.comboBoxPlatform.setVisible(True)
        else:
            self.comboBoxPlatform.setDisabled(True)
            self.comboBoxPlatform.setVisible(False)
        self.settingsHandler.saveSettings()

    @QtCore.pyqtSlot()
    def saveSettings(self) -> None:
        self.settingsHandler.saveSettings()

    @QtCore.pyqtSlot(int)
    def finishedProcessing(self, count) -> None:
        self.progressBar.setValue(100)
        self.plainTextEdit.appendHtml(
            f"<strong>Finished processing {count} files</strong><br>"
        )
        self.plainTextEdit.ensureCursorVisible()
        self.allowUserInteraction(True)

    @QtCore.pyqtSlot(int)
    def appIdChange(self, index) -> None:
        if index == 0:
            self.comboBoxAppId.setEditable(False)
        else:
            self.comboBoxAppId.setEditable(True)

    @QtCore.pyqtSlot(str)
    def appIdTextChange(self, newText) -> None:
        if newText != "Disabled":
            self.comboBoxAppId.setCurrentText(newText)
            self.comboBoxAppId.setItemText(1, newText)

    @QtCore.pyqtSlot(int)
    def convertPlatformChanged(self, index) -> None:
        if index == 0:
            self.comboBoxAppId.setCurrentIndex(0)
