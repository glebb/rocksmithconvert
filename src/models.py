import os
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class ProcessModel(QObject):
    fileListChanged = pyqtSignal(list)
    fileProcessed = pyqtSignal(str)
    canProcess = pyqtSignal(bool)
    targetSet = pyqtSignal(str)

    def __init__(self):
        super(ProcessModel, self).__init__()
        self._convert: bool = False
        self._rename: bool = False
        self._files = []
        self._target = ''
        self._processing: bool = False

    def trySetDefaultPath(self, directory=None):
        if directory and os.path.isdir(directory):
            self.setTarget(directory)
            return
        home = os.path.expanduser("~")
        default = home + "/" + \
            "Library/Application Support/Steam/steamapps/common/Rocksmith2014/dlc"
        if os.path.isdir(default):
            self.setTarget(default)
        elif os.path.isdir(home):
            self.setTarget(home)
        else:
            self.setTarget('')

    @pyqtSlot(list)
    def setFiles(self, files):
        self._files = files.copy()
        self.fileListChanged.emit(self._files.copy())
        self.emitCanProcess()

    @pyqtSlot(int)
    def setConvert(self, convertValue):
        self._convert = bool(convertValue)
        self.emitCanProcess()

    @pyqtSlot(int)
    def setRename(self, renameValue):
        self._rename = bool(renameValue)
        self.emitCanProcess()

    @pyqtSlot(str)
    def setTarget(self, target):
        self._target = target
        self.targetSet.emit(target)
        self.emitCanProcess()

    def setProcessing(self, value):
        self._processing = value
        self.emitCanProcess()

    def emitCanProcess(self):
        self.canProcess.emit((self._convert or self._rename) and len(
            self._files) > 0 and self._target != '' and not self._processing) 
