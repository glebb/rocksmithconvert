from os import path
from json import loads
from re import sub
from traceback import format_exc
from typing import Optional
from PyQt5 import QtCore
from shutil import copyfile
from rocksmith.psarc import PSARC
from rocksmithconvert.models import ProcessModel
from pathlib import Path
from time import sleep


class _WorkerSignals(QtCore.QObject):
    update = QtCore.pyqtSignal(dict)
    info = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)
    startProcess = QtCore.pyqtSignal()


class _WorkerWaiter(QtCore.QThread):
    def __init__(self, threadSignals: _WorkerSignals, pool: QtCore.QThreadPool, processModel: ProcessModel) -> None:
        super(_WorkerWaiter, self).__init__(pool)
        self.threadPool = pool
        self.signals = threadSignals
        self.processModel = processModel

    @QtCore.pyqtSlot()
    def run(self):
        self.threadPool.waitForDone()
        self.signals.finished.emit(len(self.processModel.files))


class _Worker(QtCore.QRunnable):
    def __init__(self, threadSignals: _WorkerSignals, file: str, processModel: ProcessModel) -> None:
        super(_Worker, self).__init__()
        self.file = file
        self.processModel = processModel
        self.converter = _Converter(threadSignals)
        self.signals = threadSignals

    @QtCore.pyqtSlot()
    def run(self) -> None:
        tryCount = 0
        name = None
        if not path.isfile(self.file):
            self.signals.info.emit(f"File does not exist: {self.file}.")
        else:
            while Path(self.file).stat().st_size == 0:
                sleep(1)
                tryCount += 1
                if tryCount > 20:
                    self.signals.info.emit(
                        f"Failed processing {self.file}. File size was 0.")
            try:
                name = self.converter.process(self.file, self.processModel)
            except ValueError:
                pass
            except FileExistsError:
                pass
            except:
                self.signals.info.emit(f"Failed processing {self.file}.")
                self.signals.info.emit(f"Unexpected error: {format_exc()}")
        self.signals.update.emit({'original': self.file, 'processed': name, 'count': str(
            len(self.processModel.files))})


class _Converter:
    def __init__(self, signals: _WorkerSignals):
        self.signals = signals

    def _convert(self, data: str, mac2pc: bool) -> str:
        if mac2pc:
            data = data.replace('audio/mac', 'audio/windows')
            data = data.replace('bin/macos', 'bin/generic')
        else:
            data = data.replace('audio/windows', 'audio/mac')
            data = data.replace('bin/generic', 'bin/macos')
        return data

    def _get_content(self, filename):
        content = None
        try:
            with open(filename, 'rb') as fh:
                content = PSARC(True).parse_stream(fh)
        except:
            with open(filename, 'rb') as fh:
                content = PSARC(False).parse_stream(fh)
        return content

    def _do_rename(self, filename: str, output_directory: str) -> Optional[str]:
        _, tail = path.split(filename)
        short_name = None

        content = self._get_content(filename)
        for path, data in content.items():
            if path.endswith('.hsan'):
                short_name = self._create_short_name(tail, data)
                break
        outname = output_directory + '/' + short_name
        if path.isfile(outname):
            error = f"File exists: {short_name}"
            self.signals.info.emit(error)
            raise FileExistsError(error)
        copyfile(filename, outname)
        return short_name

    def _swap_platform(self, filename, targetPlatform):
        temp = filename.lower()
        if not temp.endswith('_m.psarc') and not temp.endswith('_p.psarc'):
            error = f"Unexpected filename: {filename}"
            self.signals.info.emit(error)
            raise ValueError(error)
        if targetPlatform == "PC":
            outname = filename.replace('_m.psarc', '_p.psarc')
            mac2pc = True
        elif targetPlatform == "MAC":
            outname = filename.replace('_p.psarc', '_m.psarc')
            mac2pc = False
        else:
            error = f"Can only convert between MAC and PC filetypes: {filename}"
            self.signals.info.emit(error)
            raise ValueError(error)
        return mac2pc, outname

    def _do_conversion(self, filename: str, output_directory: str, targetPlatform: str, use_shortnames: bool = False) -> Optional[str]:
        mac2pc, outputFilename = self._swap_platform(filename, targetPlatform)
        content = self._get_content(filename)

        _, tail = path.split(outputFilename)
        short_name = None

        new_content = {}
        for filepath, data in content.items():
            if filepath.endswith('aggregategraph.nt'):
                data = self._convert(data.decode(), mac2pc)
                if mac2pc:
                    data = data.replace('macos', 'dx9').encode('utf-8')
                else:
                    data = data.replace('dx9', 'macos').encode('utf-8')
            new_content[self._convert(filepath, mac2pc)] = data
            if use_shortnames and not short_name and filepath.endswith('.hsan'):
                short_name = self._create_short_name(tail, data)

        outputFilename = output_directory + '/'
        if short_name:
            outputFilename += short_name
        else:
            outputFilename += tail
        if path.isfile(outputFilename):
            error = f"File exists: {short_name}"
            self.signals.info.emit(error)
            raise FileExistsError(error)


        with open(outputFilename, 'wb') as fh:
            PSARC().build_stream(new_content, fh)
        return outputFilename

    def _find_by_key(self, data: str, target: str) -> str:
        for key, value in data.items():
            if isinstance(value, dict):
                yield from self._find_by_key(value, target)
            elif key == target:
                yield value

    def _create_short_name(self, original: str, data: str) -> str:
        data_dict = loads(data)
        artist = list(self._find_by_key(data_dict, "ArtistName"))[0]
        song = list(self._find_by_key(data_dict, "SongName"))[0]
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

    def process(self, file: str, processModel: ProcessModel) -> Optional[str]:
        if processModel.convert:
            return self._do_conversion(file, processModel.target, processModel.targetPlatform, processModel.rename)
        else:
            return self._do_rename(file, processModel.target)


class ConvertService:
    def __init__(self) -> None:
        self.threadpool = QtCore.QThreadPool()
        self.threadSignals = _WorkerSignals()

    def process(self, processModel: ProcessModel) -> None:
        if not path.isdir(processModel.target):
            self.threadSignals.info.emit("No target folder set.")
            self.threadSignals.info.emit("ABORTED")
            return
        waiterProcess = _WorkerWaiter(
            self.threadSignals, self.threadpool, processModel)
        self.threadSignals.startProcess.emit()
        for file in processModel.files:
            worker = _Worker(self.threadSignals, file, processModel)
            self.threadpool.start(worker)
        waiterProcess.start()
