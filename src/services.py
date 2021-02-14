import os
import json
import re
from PyQt5 import QtCore
from shutil import copyfile
from rocksmith import PSARC
from models import ProcessModel


class WorkerSignals(QtCore.QObject):
    finished = QtCore.pyqtSignal(str)


class _Worker(QtCore.QRunnable):
    def __init__(self, listWidetSignals, file, target, convert, rename):
        super(_Worker, self).__init__()
        self.file = file
        self.target = target
        self.convert = convert
        self.rename = rename
        self.signal = WorkerSignals()
        self.converter = Converter()
        self.listWidgetSignals = listWidetSignals

    @QtCore.pyqtSlot()
    def run(self):
        self.converter.process(self.file, self.target,
                               self.convert, self.rename)
        self.listWidgetSignals.finished.emit(self.file)


class Converter:
    def __init__(self):
        pass

    def process(self, file, target, convert, rename):
        if convert:
            self.convert(file, target, rename)
        else:
            self.rename(file, target)

    def _convert(self, data, mac2pc):
        if mac2pc:
            data = data.replace('audio/mac', 'audio/windows')
            data = data.replace('bin/macos', 'bin/generic')
        else:
            data = data.replace('audio/windows', 'audio/mac')
            data = data.replace('bin/generic', 'bin/macos')
        return data

    def rename(self, filename, output_directory):
        head, tail = os.path.split(filename)
        short_name = None

        with open(filename, 'rb') as fh:
            content = PSARC().parse_stream(fh)
        for path, data in content.items():
            if path.endswith('.hsan'):
                short_name = self.create_short_name(tail, data)
                break
        outname = output_directory + '/' + short_name
        if os.path.isfile(outname):
            print(f"{outname} already exists.\r\n\r\n")
            return outname
        copyfile(filename, outname)
        return short_name

    def convert(self, filename, output_directory, use_shortnames=False):
        if filename.endswith('_m.psarc'):
            outname = filename.replace('_m.psarc', '_p.psarc')
            mac2pc = True
        elif filename.endswith('_p.psarc'):
            outname = filename.replace('_p.psarc', '_m.psarc')
            mac2pc = False
        else:
            print('Can only convert between MAC and PC!')
            return

        with open(filename, 'rb') as fh:
            content = PSARC().parse_stream(fh)

        head, tail = os.path.split(outname)
        short_name = None

        new_content = {}
        for path, data in content.items():
            if path.endswith('aggregategraph.nt'):
                data = self._convert(data.decode(), mac2pc)
                if mac2pc:
                    data = data.replace('macos', 'dx9').encode('ascii')
                else:
                    data = data.replace('dx9', 'macos').encode('ascii')
            new_content[self._convert(path, mac2pc)] = data
            if use_shortnames and not short_name and path.endswith('.hsan'):
                short_name = self.create_short_name(tail, data)

        outname = output_directory + '/'
        if short_name:
            outname += short_name
        else:
            outname += tail
        if os.path.isfile(outname):
            print(f"{outname} already exists.\r\n\r\n")
            return outname

        with open(outname, 'wb') as fh:
            PSARC().build_stream(new_content, fh)
        return outname

    def find_by_key(self, data, target):
        for key, value in data.items():
            if isinstance(value, dict):
                yield from self.find_by_key(value, target)
            elif key == target:
                yield value

    def create_short_name(self, original, data):
        data_dict = json.loads(data)
        artist = list(self.find_by_key(data_dict, "ArtistName"))[0]
        song = list(self.find_by_key(data_dict, "SongName"))[0]
        dd = False
        if 'dd_' in original.lower():
            dd = True
        if len(artist) > 10:
            artist = re.sub("[^A-Za-z]+", '', artist)[:10]
        max_song_length = 10+(10-len(artist))
        if len(song) > max_song_length:
            song = re.sub("[^A-Za-z]+", '', song)[:max_song_length]
        if dd:
            song += "DD"
        short_name = f"{artist}-{song}" + original[-8:]
        keepcharacters = ('.', '_', '-')
        return "".join(c for c in short_name if c.isalnum() or c in keepcharacters).rstrip()


class ConvertService:
    def __init__(self):
        self.threadpool = QtCore.QThreadPool()
        self.listWidgetSignals = WorkerSignals()

    def process(self, processModel: ProcessModel):
        for file in processModel._files:
            worker = _Worker(self.listWidgetSignals, file, processModel._target,
                             processModel._convert, processModel._rename)
            self.threadpool.start(worker)
