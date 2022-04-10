from PyQt5 import QtCore, QtWidgets
import pytest
from unittest.mock import MagicMock
import rocksmithconvert.controllers
from rocksmithconvert.models import ProcessModel


@pytest.fixture()
def widget(mocker):
    mocker.patch("rocksmithconvert.settings.SettingsHandler.loadSettings")
    mocker.patch("rocksmithconvert.settings.SettingsHandler.saveSettings")
    widget = rocksmithconvert.controllers.MainWindowController([])
    widget.convertService.process = MagicMock()
    yield widget
    widget.window.close()


def test_process_is_not_called_with_empty_files_list(widget, qtbot):
    widget.processFiles([""])
    assert widget.convertService.process.call_args == None


def test_process_is_not_called_with_unsupported_files_list(widget, qtbot):
    widget.processFiles(["test.txt"])
    assert widget.convertService.process.call_args == None


def test_process_is_called_with_valid_files_list_and_default_parameters(widget, qtbot):
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.files == ["test_p.psarc"]
    assert model.targetPlatform == "Disabled"
    assert model.renameScheme == "Disabled"
    assert model.appId == "Disabled"
    assert model.count == 1


def test_invoking_rename_works(widget, qtbot):
    widget.window.comboBoxRename.setCurrentIndex(1)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.renameScheme == "Short"
    widget.window.comboBoxRename.setCurrentIndex(2)
    widget.processFiles(["test2_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.renameScheme == "Full"


def test_invoking_convert_works(widget, qtbot):
    widget.window.comboBoxPlatform.setCurrentIndex(1)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.targetPlatform == "MAC"


def test_invoking_setPlatform_works(
    widget: rocksmithconvert.controllers.MainWindowController, qtbot
):
    widget.window.comboBoxPlatform.setCurrentIndex(2)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.targetPlatform == "PC"


def test_autoprocess_works(
    widget: rocksmithconvert.controllers.MainWindowController, qtbot
):
    widget.ap.checkFiles = MagicMock()
    widget.window.pushButtonSelectSource.setToolTip("/tmp")
    widget.window.checkBoxAutoProcess.setCheckState(1)
    widget.ap.checkFiles.assert_called_once()


def test_overwrite(widget: rocksmithconvert.controllers.MainWindowController, qtbot):
    widget.window.comboBoxPlatform.setCurrentIndex(1)
    widget.window.checkBoxOverwrite.setCheckState(1)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.overwrite == True
    widget.window.checkBoxOverwrite.setCheckState(0)
    widget.processFiles(["test_p.psarc"])
    model: ProcessModel = widget.convertService.process.call_args.args[0]
    assert model.overwrite == False
