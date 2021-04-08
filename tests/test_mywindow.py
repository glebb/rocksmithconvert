from PyQt5 import QtCore
import pytest
from rocksmithconvert.controllers import MainWindowController
from unittest.mock import MagicMock
from unittest.mock import patch

from rocksmithconvert.models import ProcessModel


@pytest.fixture()
def widget(mocker):
	widget = MainWindowController([])
	mocker.patch('rocksmithconvert.settings.SettingsHandler.saveSettings')
	mocker.patch('rocksmithconvert.settings.SettingsHandler.loadSettings')
	widget.convertService.process = MagicMock()
	return widget

def test_process_is_not_called_with_empty_files_list(widget, qtbot):
	widget.processFiles([""])
	args = widget.convertService.process.call_args
	assert args == None

def test_process_is_not_called_with_unsupported_files_list(widget, qtbot):
	widget.processFiles(["test.txt"])
	args = widget.convertService.process.call_args
	assert args == None

def test_process_is_called_with_valid_files_list_and_default_parameters(widget, qtbot):
	widget.processFiles(["test_p.psarc"])
	model: ProcessModel = widget.convertService.process.call_args.args[0]
	assert model.files == ["test_p.psarc"]
	assert model.rename == False
	assert model.convert == True
	assert model.targetPlatform == "MAC"
	assert model.count == 1

def test_invoking_rename_works(widget, qtbot):
	widget.window.checkBoxRename.setCheckState(1)
	widget.processFiles(["test_p.psarc"])
	model: ProcessModel = widget.convertService.process.call_args.args[0]
	assert model.rename == True

def test_invoking_convert_works(widget, qtbot):
	widget.window.checkBoxConvert.setCheckState(0)
	widget.processFiles(["test_p.psarc"])
	model: ProcessModel = widget.convertService.process.call_args.args[0]
	assert model.rename == False

def test_invoking_setPlatform_works(widget: MainWindowController, qtbot):
	widget.window.comboBoxPlatform.setCurrentText("PC")
	widget.processFiles(["test_p.psarc"])
	model: ProcessModel = widget.convertService.process.call_args.args[0]
	assert model.targetPlatform == "PC"

def test_autoprocess_works(widget: MainWindowController, qtbot):
	widget.ap.checkFiles = MagicMock()
	widget.window.pushButtonSelectSource.setToolTip('/tmp')
	widget.window.checkBoxAutoProcess.setCheckState(1)
	widget.ap.checkFiles.assert_called_once()


