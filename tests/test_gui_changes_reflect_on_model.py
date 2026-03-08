from typing import cast
from unittest.mock import MagicMock

import pytest

import rocksmithconvert.controllers
from rocksmithconvert.models import ProcessModel
from rocksmithconvert.qt_wrapper import QtCore


@pytest.fixture()
def widget(mocker, qtbot):
    mocker.patch("rocksmithconvert.settings.SettingsHandler.loadSettings")
    mocker.patch("rocksmithconvert.settings.SettingsHandler.saveSettings")
    mocker.patch(
        "rocksmithconvert.files_and_folders.tryGetDefaultRocksmithPath",
        return_value="",
    )
    widget = rocksmithconvert.controllers.MainWindowController([])
    qtbot.waitUntil(lambda: widget.window._startupInitialized)
    widget.convertService.process = MagicMock()
    yield widget
    widget.window.close()


def test_process_is_not_called_with_empty_files_list(widget, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.processFiles([""])
    assert process.call_args is None


def test_process_is_not_called_with_unsupported_files_list(widget, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.processFiles(["test.txt"])
    assert process.call_args is None


def test_process_is_called_with_valid_files_list_and_default_parameters(widget, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = process.call_args.args[0]
    assert model.files == ["test_p.psarc"]
    assert model.targetPlatform == "Disabled"
    assert model.renameScheme == "Disabled"
    assert model.appId == "Disabled"
    assert model.count == 1


def test_invoking_rename_works(widget, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.window.comboBoxRename.setCurrentIndex(1)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = process.call_args.args[0]
    assert model.renameScheme == "Short"
    widget.window.comboBoxRename.setCurrentIndex(2)
    widget.processFiles(["test2_p.psarc"])
    model = process.call_args.args[0]
    assert model.renameScheme == "Full"


def test_invoking_convert_works(widget, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.window.comboBoxPlatform.setCurrentIndex(1)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = process.call_args.args[0]
    assert model.targetPlatform == "MAC"


def test_invoking_setPlatform_works(
    widget: rocksmithconvert.controllers.MainWindowController, qtbot
):
    process = cast(MagicMock, widget.convertService.process)
    widget.window.comboBoxPlatform.setCurrentIndex(2)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = process.call_args.args[0]
    assert model.targetPlatform == "PC"


def test_autoprocess_works(
    widget: rocksmithconvert.controllers.MainWindowController, qtbot, mocker
):
    check_files = mocker.patch.object(widget.ap, "checkFiles", return_value=True)
    widget.window.pushButtonSelectSource.setToolTip("/tmp")
    widget.window.checkBoxAutoProcess.setCheckState(QtCore.Qt.CheckState.Checked)
    check_files.assert_called_once()


def test_overwrite(widget: rocksmithconvert.controllers.MainWindowController, qtbot):
    process = cast(MagicMock, widget.convertService.process)
    widget.window.comboBoxPlatform.setCurrentIndex(1)
    widget.window.checkBoxOverwrite.setCheckState(QtCore.Qt.CheckState.Checked)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = process.call_args.args[0]
    assert model.overwrite
    widget.window.checkBoxOverwrite.setCheckState(QtCore.Qt.CheckState.Unchecked)
    widget.processFiles(["test_p.psarc"])
    model = process.call_args.args[0]
    assert not model.overwrite


def test_saved_autoprocess_starts_after_deferred_startup(mocker, qtbot):
    def fake_load_settings(_, root):
        root.pushButtonSelectSource.setToolTip("/tmp")
        blocker = QtCore.QSignalBlocker(root.checkBoxAutoProcess)
        root.checkBoxAutoProcess.setCheckState(QtCore.Qt.CheckState.Checked)
        del blocker

    mocker.patch(
        "rocksmithconvert.settings.SettingsHandler.loadSettings",
        autospec=True,
        side_effect=fake_load_settings,
    )
    mocker.patch("rocksmithconvert.settings.SettingsHandler.saveSettings")
    start = mocker.patch("rocksmithconvert.autoprocess.AutoProcessor.start")

    widget = rocksmithconvert.controllers.MainWindowController([])
    qtbot.waitUntil(lambda: widget.window._startupInitialized)

    start.assert_called_once()
    widget.window.close()


def test_initial_files_use_deferred_restored_settings(mocker, qtbot):
    def fake_load_settings(_, root):
        blocker = QtCore.QSignalBlocker(root.comboBoxPlatform)
        root.comboBoxPlatform.setCurrentIndex(1)
        del blocker

    mocker.patch(
        "rocksmithconvert.settings.SettingsHandler.loadSettings",
        autospec=True,
        side_effect=fake_load_settings,
    )
    mocker.patch("rocksmithconvert.settings.SettingsHandler.saveSettings")
    process = mocker.patch(
        "rocksmithconvert.controllers.ConvertService.process",
        autospec=True,
    )

    widget = rocksmithconvert.controllers.MainWindowController(["test_p.psarc"])
    qtbot.waitUntil(lambda: process.called)

    model: ProcessModel = process.call_args.args[1]
    assert model.targetPlatform == "MAC"
    widget.window.close()
