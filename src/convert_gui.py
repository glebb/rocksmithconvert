import sys
import argparse
from PyQt5 import QtWidgets, QtCore
from mainwindow import Ui_MainWindow
from models import ProcessModel
from services import ConvertService


class MainWindow(QtWidgets.QMainWindow, Ui_MainWindow):
    settings = QtCore.QSettings("gui.ini", QtCore.QSettings.IniFormat)
    
    def __init__(self, *args, obj=None, **kwargs):
        super(MainWindow, self).__init__(*args, **kwargs)
        self.setupUi(self)
        self.messageBox = QtWidgets.QMessageBox()
        self.processModel: ProcessModel = ProcessModel()
        self.convertService: ConvertService = ConvertService()
        self.filesNamesToProcess: list[str] = []
        self.setupSignals()
        self.initUI()
        
    def setupSignals(self):
        self.pushButtonSelectTarget.clicked.connect(self.openSelectTargetDialog)
        self.processButton.clicked.connect(self.process)
        self.processModel.targetSet.connect(self.setTargetFolder)
        self.listWidgetFiles.selected.connect(self.updateFilesList)
        self.convertService.listWidgetSignals.finished.connect(
            self.updateProgress)

        self.processModel.fileListChanged.connect(
            self.listWidgetFiles.setFilelist)
        
        self.checkBoxConvert.stateChanged.connect(self.processModel.setConvert)
        self.checkBoxRename.stateChanged.connect(self.processModel.setRename)
        
        self.processModel.canProcess.connect(self.processButton.setEnabled)

    def initUI(self):
        self.loadSettings(self.settings)
        self.progressBar.setValue(0)
        self.processModel.trySetDefaultPath(self.lineEditTarget.text())
        self.processModel.setConvert(self.checkBoxConvert.isChecked())
        self.processModel.setRename(self.checkBoxRename.isChecked())


    def closeEvent(self, event):
        self.saveSettings(self.settings)
        QtWidgets.QMainWindow.closeEvent(self, event)

    def settingsValueIsValid(self, val: str):
        if val == 'checkBoxConvert': return True
        if val == 'checkBoxRename': return True
        if val == 'lineEditTarget': return True
        if val == 'checkBoxRename': return True
        if val == 'checked' or val == 'text': return True
        return False

    def saveSettings(self, settings):
        for w in QtWidgets.qApp.allWidgets():
            if w.objectName():
                if self.settingsValueIsValid(w.objectName()):
                    mo = w.metaObject()
                    for i in range(mo.propertyCount()):
                        prop = mo.property(i)
                        name = prop.name()
                        key = "{}/{}".format(w.objectName(), name)
                        val = w.property(name)
                        if self.settingsValueIsValid(name) and prop.isValid() and prop.isWritable():
                            settings.setValue(key, w.property(name))
    
    
    def loadSettings(self, settings):
        finfo = QtCore.QFileInfo(settings.fileName())

        if finfo.exists() and finfo.isFile():
            for w in QtWidgets.qApp.allWidgets():
                if w.objectName():
                    mo = w.metaObject()
                    for i in range(mo.propertyCount()):
                        prop = mo.property(i)
                        name = prop.name()
                        last_value = w.property(name)
                        key = "{}/{}".format(w.objectName(), name)
                        if not settings.contains(key):
                            continue
                        val = settings.value(key, type=type(last_value),)
                        if (
                            val != last_value
                            and self.settingsValueIsValid(w.objectName())
                            and prop.isValid()
                            and prop.isWritable()
                        ):
                            w.setProperty(name, val)

    @QtCore.pyqtSlot()
    def openSelectTargetDialog(self):
        options = QtWidgets.QFileDialog.Options()
        directory = QtWidgets.QFileDialog.getExistingDirectory(
            self, "QFileDialog.getOpenFileName()", self.processModel._target, options=options)
        if directory:
            self.processModel.setTarget(directory)

    @QtCore.pyqtSlot(list)
    def updateFilesList(self, files):
        output = []
        if type(files) is not list:
            output = [files]
        else:
            output = files.copy()
        self.processModel.setFiles(output)
        self.processButton.setText(f'Process {len(output)} files')

    @QtCore.pyqtSlot()
    def process(self):
        self.processModel.setProcessing(True)
        self.listWidgetFiles.setAcceptDrops(False)
        self.progressBar.setValue(0)
        self.filesNamesToProcess = self.processModel._files.copy()
        self.convertService.process(self.processModel)

    @QtCore.pyqtSlot(str)
    def setTargetFolder(self, target):
        self.lineEditTarget.setText(target)

    @QtCore.pyqtSlot(str)
    def updateProgress(self, file):
        self.progressBar.setValue(
            self.progressBar.value() + round(100/len(self.filesNamesToProcess)))
        copyOfFiles = self.processModel._files.copy()
        copyOfFiles.remove(file)
        self.updateFilesList(copyOfFiles)
        self.processButton.setText(f'Process {len(copyOfFiles)} files')
        if len(copyOfFiles) == 0:
            self.progressBar.setValue(100)
            self.messageBox.setText(f"Finished processing {len(self.filesNamesToProcess)} files.")
            self.messageBox.exec()
            self.filesNamesToProcess = []
            self.processModel.setProcessing(False)
            self.listWidgetFiles.setAcceptDrops(True)



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--files", help=".psarc files", nargs='*')
    args = parser.parse_args()
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    if args.files:
        window.updateFilesList(args.files)
    window.show()
    app.exec()
