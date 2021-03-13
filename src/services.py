from os import path
from json import loads
from re import sub
from traceback import format_exc
from typing import Optional
from PyQt5 import QtCore
from shutil import copyfile
from rocksmith.psarc import PSARC
from models import ProcessModel
from pathlib import Path
from time import sleep

class WorkerSignals(QtCore.QObject):
    update = QtCore.pyqtSignal(dict)
    info = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)
    startProcess = QtCore.pyqtSignal()


class _WorkerWaiter(QtCore.QThread):
    def __init__(self, threadSignals: WorkerSignals, pool: QtCore.QThreadPool, processModel: ProcessModel) -> None:
        super(_WorkerWaiter, self).__init__(pool)
        self.threadPool = pool
        self.signals = threadSignals
        self.processModel = processModel

    @QtCore.pyqtSlot()
    def run(self):
        self.threadPool.waitForDone()
        self.signals.finished.emit(len(self.processModel.files))

class _Worker(QtCore.QRunnable):
    def __init__(self, threadSignals: WorkerSignals, file: str, processModel: ProcessModel) -> None:
        super(_Worker, self).__init__()
        self.file = file
        self.processModel = processModel
        self.converter = Converter(threadSignals)
        self.signals = threadSignals

    @QtCore.pyqtSlot()
    def run(self) -> None:
        tryCount = 0
        if not path.isfile(self.file):
            name = None
            self.signals.info.emit(f"File does not exist: {self.file}.")
        else:
            while Path(self.file).stat().st_size == 0:
                sleep(1)
                print(f'Waiting for file {self.file}...')
                tryCount += 1
                if tryCount > 20:
                    self.signals.info.emit(f"Failed processing {self.file}. File size was 0.")
                    name = None
            try:
                name = self.converter.process(self.file, self.processModel)
            except:
                self.signals.info.emit(f"Failed processing {self.file}.")
                self.signals.info.emit(f"Unexpected error: {format_exc()}")
                name = None
        self.signals.update.emit({'original': self.file, 'processed': name, 'count': str(len(self.processModel.files))})


class Converter:
    def __init__(self, signals: WorkerSignals):
        self.signals = signals

    def process(self, file: str, processModel: ProcessModel) -> Optional[str]:
        if processModel.convert:
            return self.convert(file, processModel.target, processModel.targetPlatform, processModel.rename)
        else:
            return self.rename(file, processModel.target)

    def _convert(self, data: str, mac2pc: bool) -> str:
        if mac2pc:
            data = data.replace('audio/mac', 'audio/windows')
            data = data.replace('bin/macos', 'bin/generic')
        else:
            data = data.replace('audio/windows', 'audio/mac')
            data = data.replace('bin/generic', 'bin/macos')
        return data

    def rename(self, filename: str, output_directory: str) -> Optional[str]:
        _, tail = path.split(filename)
        short_name = None

        with open(filename, 'rb') as fh:
            content = PSARC().parse_stream(fh)
        for path, data in content.items():
            if path.endswith('.hsan'):
                short_name = self.create_short_name(tail, data)
                break
        outname = output_directory + '/' + short_name
        if path.isfile(outname):
            print(f"{outname} already exists.\r\n\r\n")
            self.signals.info.emit(f"{outname} already exists.")
            return None
        copyfile(filename, outname)
        return short_name

    def convert(self, filename: str, output_directory: str, targetPlatform:str, use_shortnames:bool=False) -> Optional[str]:
        temp = filename.lower()
        if not temp.endswith('_m.psarc') and not temp.endswith('_p.psarc'):
            print('Can only convert between MAC and PC!')
            self.signals.info.emit(f"Can only convert between MAC and PC: {filename}")
            return None
        if targetPlatform == "PC":
            outname = filename.replace('_m.psarc', '_p.psarc')
            mac2pc = True
        elif targetPlatform == "MAC":
            outname = filename.replace('_p.psarc', '_m.psarc')
            mac2pc = False
        else:
            print('Can only convert between MAC and PC!')
            self.signals.info.emit(f"Can only convert between MAC and PC: {filename}")
            return None

        with open(filename, 'rb') as fh:
            content = PSARC().parse_stream(fh)

        _, tail = path.split(outname)
        short_name = None

        new_content = {}
        for filepath, data in content.items():
            if filepath.endswith('aggregategraph.nt'):
                data = self._convert(data.decode(), mac2pc)
                if mac2pc:
                    data = data.replace('macos', 'dx9').encode('ascii')
                else:
                    data = data.replace('dx9', 'macos').encode('ascii')
            new_content[self._convert(filepath, mac2pc)] = data
            if use_shortnames and not short_name and filepath.endswith('.hsan'):
                short_name = self.create_short_name(tail, data)

        outname = output_directory + '/'
        if short_name:
            outname += short_name
        else:
            outname += tail
        if path.isfile(outname):
            print(f"{outname} already exists.\r\n\r\n")
            self.signals.info.emit(f"{outname} already exists.")
            return None

        with open(outname, 'wb') as fh:
            PSARC().build_stream(new_content, fh)
        return outname

    def find_by_key(self, data:str, target:str) -> str:
        for key, value in data.items():
            if isinstance(value, dict):
                yield from self.find_by_key(value, target)
            elif key == target:
                yield value

    def create_short_name(self, original:str, data:str) -> str:
        data_dict = loads(data)
        artist = list(self.find_by_key(data_dict, "ArtistName"))[0]
        song = list(self.find_by_key(data_dict, "SongName"))[0]
        dd = False
        if 'dd_' in original.lower():
            dd = True
        if len(artist) > 10:
            artist = sub("[^A-Za-z]+", '', artist)[:10]
        max_song_length = 10+(10-len(artist))
        if len(song) > max_song_length:
            song = sub("[^A-Za-z]+", '', song)[:max_song_length]
        if dd:
            song += "DD"
        short_name = f"{artist}-{song}" + original[-8:]
        keepcharacters = ('.', '_', '-')
        return "".join(c for c in short_name if c.isalnum() or c in keepcharacters).rstrip()


class ConvertService:
    def __init__(self) -> None:
        self.threadpool = QtCore.QThreadPool()
        self.threadSignals = WorkerSignals()

    def process(self, processModel: ProcessModel) -> None:
        waiterProcess = _WorkerWaiter(self.threadSignals, self.threadpool, processModel)
        self.threadSignals.startProcess.emit()
        for file in processModel.files:
            worker = _Worker(self.threadSignals, file, processModel)
            self.threadpool.start(worker)
        waiterProcess.start()
