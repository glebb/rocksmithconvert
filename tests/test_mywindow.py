from PyQt5 import QtCore, QtWidgets
import pytest
from unittest.mock import MagicMock
from unittest.mock import patch
from rocksmithconvert.models import ProcessModel
from rocksmithconvert.controllers import MainWindowController
from rocksmithconvert.settings import SettingsHandler



@pytest.fixture()
def widget(mocker):
	widget = MainWindowController([])
	widget.convertService.process = MagicMock()
	yield widget
	widget.window.close()

def test_process_is_not_called_with_empty_files_list(widget, qtbot):
	widget.processFiles([""])
	args = widget.convertService.process.call_args
	assert args == None

def test_process_is_not_called_with_unsupported_files_list(widget, qtbot):
	widget.processFiles(["test.txt"])
	args = widget.convertService.process.call_args
	assert args == None



