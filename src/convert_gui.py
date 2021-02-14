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
        self.viewModel: ProcessModel = ProcessModel()
        self.convertService: ConvertService = ConvertService()
        self.filesNamesToProcess: list[str] = []
        self.setupSignals()
        self.initUI()
        
    def setupSignals(self):
        self.pushButtonSelectTarget.clicked.connect(self.openSelectTargetDialog)
        self.processButton.clicked.connect(self.process)
        self.viewModel.targetSet.connect(self.setTargetFolder)
        self.listWidgetFiles.selected.connect(self.updateFilesList)
        self.convertService.listWidgetSignals.finished.connect(
            self.updateProgress)

        self.viewModel.fileListChanged.connect(
            self.listWidgetFiles.setFilelist)
        
        self.checkBoxConvert.stateChanged.connect(self.viewModel.setConvert)
        self.checkBoxRename.stateChanged.connect(self.viewModel.setRename)
        
        self.viewModel.canProcess.connect(self.processButton.setEnabled)

    def initUI(self):
        self.loadSettings(self.settings)
        self.progressBar.setValue(0)
        self.viewModel.trySetDefaultPath(self.lineEditTarget.text())
        self.viewModel.setConvert(self.checkBoxConvert.isChecked())
        self.viewModel.setRename(self.checkBoxRename.isChecked())


    def closeEvent(self, event):
        self.saveSettings(self.settings)
        QtWidgets.QMainWindow.closeEvent(self, event)

    def settingsValueIsValid(self, val):
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
            self, "QFileDialog.getOpenFileName()", self.viewModel._target, options=options)
        if directory:
            self.viewModel.setTarget(directory)

    @QtCore.pyqtSlot(list)
    def updateFilesList(self, files):
        output = []
        if type(files) is not list:
            output = [files]
        else:
            output = files.copy()
        self.viewModel.setFiles(output)
        self.processButton.setText(f'Process {len(output)}')

    @QtCore.pyqtSlot()
    def process(self):
        self.progressBar.setValue(0)
        self.filesNamesToProcess = self.viewModel._files.copy()
        self.convertService.process(self.viewModel)

    @QtCore.pyqtSlot(str)
    def setTargetFolder(self, target):
        self.lineEditTarget.setText(target)

    @QtCore.pyqtSlot(str)
    def updateProgress(self, file):
        self.progressBar.setValue(
            self.progressBar.value() + round(100/len(self.filesNamesToProcess)))
        copyOfFiles = self.viewModel._files.copy()
        copyOfFiles.remove(file)
        self.updateFilesList(copyOfFiles)
        self.processButton.setText(f'Process {len(copyOfFiles)}')
        if len(copyOfFiles) == 0:
            self.progressBar.setValue(100)
            self.filesNamesToProcess = []

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
