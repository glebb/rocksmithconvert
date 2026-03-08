import json
from unittest.mock import MagicMock

import pytest

from rocksmithconvert.autoprocess import AutoProcessor
from rocksmithconvert.files_and_folders import filterAndSortPsarcFiles
from rocksmithconvert.models import ProcessModel
from rocksmithconvert.mywindow import MyWindow
from rocksmithconvert.services import _Converter, _Worker


class _SignalRecorder:
    def __init__(self):
        self.calls = []

    def emit(self, value):
        self.calls.append(value)


class _FakeWorkerSignals:
    def __init__(self):
        self.info = _SignalRecorder()
        self.update = _SignalRecorder()


def test_create_new_filename_requires_required_metadata():
    converter = _Converter(_FakeWorkerSignals())
    data = json.dumps({"Entries": [{"SongName": "Song"}]})

    with pytest.raises(ValueError, match="Missing metadata field: ArtistName"):
        converter._create_new_filename("track_p.psarc", data, "Short")


def test_do_rename_requires_hsan_metadata(tmp_path):
    signals = _FakeWorkerSignals()
    converter = _Converter(signals)
    source = tmp_path / "track_p.psarc"
    source.write_bytes(b"psarc")
    converter._get_content = MagicMock(return_value={"songs/bin/generic/file": b"x"})

    with pytest.raises(ValueError, match="missing HSAN metadata"):
        converter._do_rename(str(source), str(tmp_path), "Short")

    assert signals.info.calls == ["Could not rename track_p.psarc: missing HSAN metadata"]


def test_worker_times_out_on_zero_byte_files(tmp_path, mocker):
    source = tmp_path / "track_p.psarc"
    source.write_bytes(b"")
    signals = _FakeWorkerSignals()
    model = ProcessModel(
        [str(source)],
        str(tmp_path),
        "Disabled",
        "Disabled",
        "Disabled",
        False,
    )
    worker = _Worker(signals, str(source), model)
    worker.converter.process = MagicMock(side_effect=AssertionError("converter should not run"))
    mocker.patch("rocksmithconvert.services.sleep", return_value=None)

    worker.run()

    assert signals.info.calls == [f"Failed processing {source}. File size was 0."]
    assert signals.update.calls == [
        {"original": str(source), "processed": None, "count": "1"}
    ]


def test_swap_platform_handles_uppercase_suffixes():
    converter = _Converter(_FakeWorkerSignals())

    mac2pc, output_name = converter._swap_platform("Track_M.PSARC", "PC")

    assert mac2pc is True
    assert output_name == "Track_p.psarc"


def test_filter_and_sort_psarc_files_is_case_insensitive_and_deterministic():
    files = ["b.PSARC", "notes.txt", "A.psarc", "c.psArc"]

    assert filterAndSortPsarcFiles(files) == ["A.psarc", "b.PSARC", "c.psArc"]


def test_autoprocess_stops_when_source_folder_disappears(tmp_path, mocker):
    processor = AutoProcessor()
    processor.autoProcessFolder = str(tmp_path / "missing")
    stop = mocker.patch.object(processor, "stop", wraps=processor.stop)
    signals = []
    processor.folderNotSet.connect(lambda: signals.append("folderNotSet"))

    result = processor.checkFiles()

    assert result is False
    stop.assert_called_once()
    assert signals == ["folderNotSet"]


def test_update_progress_handles_invalid_total_count(mocker, qtbot):
    mocker.patch("rocksmithconvert.settings.SettingsHandler.loadSettings")
    mocker.patch("rocksmithconvert.settings.SettingsHandler.saveSettings")
    mocker.patch(
        "rocksmithconvert.files_and_folders.tryGetDefaultRocksmithPath",
        return_value="",
    )
    window = MyWindow()
    qtbot.addWidget(window)
    window.setFileList(["track_p.psarc"])

    window.updateProgress({"processed": "", "count": "bad"})

    assert window.progressBar.value() == 100