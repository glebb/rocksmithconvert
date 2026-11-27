from os import path
from json import loads
from json import JSONDecodeError
from re import sub
from traceback import format_exc
from typing import Any, Generator, Optional
from rocksmithconvert.qt_wrapper import QtCore
from shutil import copyfile
from rocksmithconvert.models import ProcessModel
from rocksmithconvert import plain_psarc
from pathlib import Path
from time import sleep
import unicodedata


def _get_psarc_class():
    from rocksmith.psarc import PSARC  # type: ignore[import-untyped]

    return PSARC


def _get_sng_crypto():
    from rocksmith import crypto  # type: ignore[import-untyped]

    return crypto


class _WorkerSignals(QtCore.QObject):
    update = QtCore.pyqtSignal(dict)
    info = QtCore.pyqtSignal(str)
    finished = QtCore.pyqtSignal(int)
    startProcess = QtCore.pyqtSignal()


class _WorkerWaiter(QtCore.QThread):
    def __init__(
        self,
        threadSignals: _WorkerSignals,
        pool: QtCore.QThreadPool,
        processModel: ProcessModel,
    ) -> None:
        super(_WorkerWaiter, self).__init__(pool)
        self.threadPool = pool
        self.signals = threadSignals
        self.processModel = processModel

    @QtCore.pyqtSlot()
    def run(self):
        self.threadPool.waitForDone()
        self.signals.finished.emit(len(self.processModel.files))


class _Worker(QtCore.QRunnable):
    def __init__(
        self, threadSignals: _WorkerSignals, file: str, processModel: ProcessModel
    ) -> None:
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
            try:
                while Path(self.file).stat().st_size == 0:
                    sleep(1)
                    tryCount += 1
                    if tryCount > 20:
                        self.signals.info.emit(
                            f"Failed processing {self.file}. File size was 0."
                        )
                        self.signals.update.emit(
                            {
                                "original": self.file,
                                "processed": name,
                                "count": str(len(self.processModel.files)),
                            }
                        )
                        return
            except OSError:
                self.signals.info.emit(
                    f"Failed processing {self.file}. File became unavailable."
                )
            try:
                name = self.converter.process(self.file, self.processModel)
            except ValueError:
                pass
            except FileExistsError:
                pass
            except Exception:
                self.signals.info.emit(f"Failed processing {self.file}.")
                self.signals.info.emit(f"Unexpected error: {format_exc()}")
        self.signals.update.emit(
            {
                "original": self.file,
                "processed": name,
                "count": str(len(self.processModel.files)),
            }
        )


class _Converter:
    def __init__(self, signals: _WorkerSignals):
        self.signals = signals

    def _convert(self, data: str, mac2pc: bool) -> str:
        if mac2pc:
            data = data.replace("audio/mac", "audio/windows")
            data = data.replace("bin/macos", "bin/generic")
        else:
            data = data.replace("audio/windows", "audio/mac")
            data = data.replace("bin/generic", "bin/macos")
        return data

    def _read_package(self, filename):
        """Returns (entries, magic): magic is set for a plain archive (an RS Extended
        Range native PSXR package, or a plain PSAR one), None for a stock one.
        SNG entries are returned as stored (not decrypted); see _convert_sng."""
        with open(filename, "rb") as fh:
            magic = plain_psarc.plain_magic(fh.read(32))
        if magic is None:
            return self._get_content(filename), None
        try:
            with open(filename, "rb") as fh:
                content, magic = plain_psarc.read(fh)
        except ValueError as error:
            raise ValueError(f"Unable to parse PSARC file: {filename}") from error
        return content, magic

    @staticmethod
    def _native_name(name: str) -> str:
        """<name>_p.psarc -> <name>_rsxr_p.psarc: native packages carry the tag in their name."""
        lower = name.lower()
        if lower.endswith(("_m.psarc", "_p.psarc")) and not lower[:-8].endswith("_rsxr"):
            return name[:-8] + "_rsxr" + name[-8:]
        return name

    def _get_content(self, filename):
        """Reads a stock archive (encrypted table of contents); SNGs stay as stored."""
        try:
            with open(filename, "rb") as fh:
                return _get_psarc_class()(False).parse_stream(fh)
        except Exception as error:
            raise ValueError(f"Unable to parse PSARC file: {filename}") from error

    @staticmethod
    def _convert_sng(filepath: str, data: bytes, mac2pc: bool) -> bytes:
        """Returns the SNG for the target platform.

        Each SNG is handled on its own, whatever the archive's table of contents:
        a plain SNG (flags 1, RS Extended Range and DotCharter) has no key and is
        kept byte for byte; an empty placeholder is kept; an encrypted one is
        decrypted with the key of its folder (or the other platform's, for a
        mislabelled package) and encrypted with the target's key."""
        if not data:
            return data
        if plain_psarc.sng_is_plain(data):
            try:
                plain_psarc.check_plain_sng(data)
            except ValueError as error:
                raise ValueError(f"{filepath}: {error}") from None
            return data
        crypto = _get_sng_crypto()
        source = crypto.MAC_KEY if "songs/bin/macos/" in filepath else crypto.WIN_KEY
        other = crypto.WIN_KEY if source is crypto.MAC_KEY else crypto.MAC_KEY
        for key in (source, other):
            try:
                body = crypto.decrypt_sng(data, key)
                break
            except Exception:
                continue
        else:
            raise ValueError(f"{filepath}: SNG cannot be decrypted with either platform key")
        return crypto.encrypt_sng(body, crypto.WIN_KEY if mac2pc else crypto.MAC_KEY)

    @staticmethod
    def _valid_app_id(app_id: str) -> bool:
        return 1 <= len(app_id) <= 10 and app_id.isascii() and app_id.isdigit()

    def _do_rename(
        self, filename: str, output_directory: str, renameScheme: str
    ) -> Optional[str]:
        _, tail = path.split(filename)
        new_name = ""

        content, magic = self._read_package(filename)
        if magic == plain_psarc.NATIVE_MAGIC:
            tail = self._native_name(tail)
        for fpath, data in content.items():
            if fpath.endswith(".hsan"):
                new_name = self._create_new_filename(tail, data, renameScheme)
                break
        if not new_name:
            error = f"Could not rename {tail}: missing HSAN metadata"
            self.signals.info.emit(error)
            raise ValueError(error)
        outname = path.join(output_directory, new_name)
        if path.isfile(outname):
            error = f"File exists: {new_name}"
            self.signals.info.emit(error)
            raise FileExistsError(error)
        copyfile(filename, outname)
        return new_name

    def _swap_platform(self, filename, targetPlatform):
        temp = filename.lower()
        if not temp.endswith("_m.psarc") and not temp.endswith("_p.psarc"):
            error = f"Unexpected filename: {filename}"
            self.signals.info.emit(error)
            raise ValueError(error)
        source_suffix = temp[-8:]
        if targetPlatform == "PC":
            outname = filename[:-8] + "_p.psarc" if source_suffix == "_m.psarc" else filename
            mac2pc = True
        elif targetPlatform == "MAC":
            outname = filename[:-8] + "_m.psarc" if source_suffix == "_p.psarc" else filename
            mac2pc = False
        else:
            error = f"Can only convert between MAC and PC filetypes: {filename}"
            self.signals.info.emit(error)
            raise ValueError(error)
        return mac2pc, outname

    def _do_conversion(
        self, filename: str, processModel: ProcessModel
    ) -> Optional[str]:
        mac2pc, outputFilename = self._swap_platform(
            filename, processModel.targetPlatform
        )
        app_id = None
        if processModel.appId != "Disabled":
            app_id = processModel.appId.strip()
            if not self._valid_app_id(app_id):
                # An empty or non-numeric ID would replace the package's App ID with junk.
                error = f"App ID must be 1-10 digits, not {processModel.appId!r}: {path.basename(filename)}"
                self.signals.info.emit(error)
                raise ValueError(error)
        content, plain_magic = self._read_package(filename)

        _, tail = path.split(outputFilename)
        if plain_magic == plain_psarc.NATIVE_MAGIC:
            tail = self._native_name(tail)
        new_name = None

        new_content = {}
        for filepath, data in content.items():
            if filepath.endswith(".sng") and ("songs/bin/macos/" in filepath or "songs/bin/generic/" in filepath):
                data = self._convert_sng(filepath, data, mac2pc)
            elif filepath.endswith("aggregategraph.nt"):
                data = self._convert(data.decode(), mac2pc)
                if mac2pc:
                    data = data.replace("macos", "dx9").encode("utf8")
                else:
                    data = data.replace("dx9", "macos").encode("utf8")
            new_content[self._convert(filepath, mac2pc)] = data
            if app_id is not None and filepath.endswith("appid"):
                new_content[self._convert(filepath, mac2pc)] = app_id.encode("utf8")
            if (
                processModel.renameScheme != "Disabled"
                and not new_name
                and filepath.endswith(".hsan")
            ):
                new_name = self._create_new_filename(
                    tail, data, processModel.renameScheme
                )

        outputFilename = processModel.target
        if new_name:
            outputFilename = path.join(outputFilename, new_name)
        else:
            new_name = filename
            outputFilename = path.join(outputFilename, tail)
        if not processModel.overwrite and path.isfile(outputFilename):
            error = f"File exists: {new_name}"
            self.signals.info.emit(error)
            raise FileExistsError(error)

        with open(outputFilename, "wb") as fh:
            if plain_magic:
                # The archive keeps its magic (PSXR for a native package) and plain table.
                plain_psarc.write(new_content, fh, plain_magic)
            else:
                # SNGs are already encrypted for the target by _convert_sng.
                _get_psarc_class()(False).build_stream(new_content, fh)

        if app_id is not None:
            self.signals.info.emit(f"App id set to {app_id} for {path.basename(outputFilename)}")
        return outputFilename

    def _find_by_key(self, data: dict, target: str) -> Generator[Any, Any, Any]:
        for key, value in data.items():
            if isinstance(value, dict):
                yield from self._find_by_key(value, target)
            elif key == target:
                yield value

    def _get_required_metadata(self, data: dict, target: str) -> str:
        value = next(self._find_by_key(data, target), None)
        if not isinstance(value, str) or not value:
            raise ValueError(f"Missing metadata field: {target}")
        return value

    def _create_new_filename(self, original: str, data: str, renameScheme: str) -> str:
        try:
            data_dict = loads(data)
        except JSONDecodeError as error:
            raise ValueError("Invalid HSAN metadata") from error
        artist = self._get_required_metadata(data_dict, "ArtistName")
        song = self._get_required_metadata(data_dict, "SongName")
        dd = False
        if "dd_" in original.lower():
            dd = True
        if len(artist) > 10:
            artist = sub("[^A-Za-z]+", "", artist)
            if renameScheme == "Short":
                artist = artist[:10]
        max_song_length = 10 + (10 - len(artist))
        if renameScheme == "Short" and len(song) > max_song_length:
            song = sub("[^A-Za-z]+", "", song)[:max_song_length]
        if dd:
            song += "DD"
        suffix = original[-8:]
        if original.lower()[:-8].endswith("_rsxr"):
            suffix = original[-13:]  # keep the RS Extended Range native tag
        short_name = f"{artist}-{song}" + suffix
        keepcharacters = (".", "_", "-")
        short_name = (
            unicodedata.normalize("NFKD", short_name).encode("ASCII", "ignore").decode()
        )
        return "".join(
            c for c in short_name if c.isalnum() or c in keepcharacters
        ).rstrip()

    def process(self, file: str, processModel: ProcessModel) -> Optional[str]:
        if processModel.targetPlatform != "Disabled":
            return self._do_conversion(file, processModel)
        elif processModel.renameScheme != "Disabled":
            return self._do_rename(file, processModel.target, processModel.renameScheme)
        return None


class ConvertService:
    def __init__(self) -> None:
        self.threadpool = QtCore.QThreadPool()
        self.threadSignals = _WorkerSignals()

    def process(self, processModel: ProcessModel) -> None:
        if not path.isdir(processModel.target):
            self.threadSignals.info.emit("No target folder set.")
            self.threadSignals.info.emit("ABORTED")
            return
        waiterProcess = _WorkerWaiter(self.threadSignals, self.threadpool, processModel)
        self.threadSignals.startProcess.emit()
        for file in processModel.files:
            worker = _Worker(self.threadSignals, file, processModel)
            self.threadpool.start(worker)
        waiterProcess.start()
