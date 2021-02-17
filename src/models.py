import os
from typing import List
from PyQt5.QtCore import QObject, pyqtSignal, pyqtSlot


class ProcessModel(QObject):
    fileListChanged = pyqtSignal(str)
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
        self._targetPlatform: str = ''

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
        self.fileListChanged.emit("\n".join(self._files))
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

    @pyqtSlot(str)
    def setPlatform(self, targetPlatform):
        self._targetPlatform = targetPlatform

    def setProcessing(self, tryToProcess):
        if tryToProcess:
            if not self.sanityCheck():
                return False, f"error: check your settings"
            if os.path.isdir(self._target):
                self._processing = True
                return True, None
            else:
                errorDir = self._target
                self.setTarget('')
                self.emitCanProcess()
                return False, f"error: target folder '{errorDir}' does not exist."
        self._processing = False

    def emitCanProcess(self):
        self.canProcess.emit(self.sanityCheck()) 

    def sanityCheck(self):
        return (self._convert or self._rename) and len(
            self._files) > 0 and self._target != '' and not self._processing        
