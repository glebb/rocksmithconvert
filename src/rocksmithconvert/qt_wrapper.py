import importlib
import importlib.util
import os


def _has_module(name):
    return importlib.util.find_spec(name) is not None


def _alias_enum(owner, alias, target):
    if not hasattr(owner, alias):
        setattr(owner, alias, target)


def _alias_exec(owner):
    if hasattr(owner, "exec_") and not hasattr(owner, "exec"):
        owner.exec = owner.exec_


def _load_pyqt6():
    from PyQt6 import QtWidgets, QtCore, QtGui # type: ignore

    return QtWidgets, QtCore, QtGui, "PyQt6"


def _load_pyqt5():
    pyqt5 = importlib.import_module("PyQt5")
    QtWidgets = pyqt5.QtWidgets
    QtCore = pyqt5.QtCore
    QtGui = pyqt5.QtGui

    _alias_enum(QtWidgets.QSizePolicy, "Policy", QtWidgets.QSizePolicy)
    _alias_enum(QtWidgets.QFrame, "Shape", QtWidgets.QFrame)
    _alias_enum(QtWidgets.QFrame, "Shadow", QtWidgets.QFrame)
    _alias_enum(QtWidgets.QPlainTextEdit, "LineWrapMode", QtWidgets.QPlainTextEdit)
    _alias_enum(QtCore.Qt, "TextInteractionFlag", QtCore.Qt)
    _alias_exec(QtWidgets.QApplication)

    return QtWidgets, QtCore, QtGui, "PyQt5"


preferred = os.environ.get("ROCKSMITHCONVERT_QT_API", "").strip().lower()

if preferred == "pyqt5":
    QtWidgets, QtCore, QtGui, QT_API = _load_pyqt5()
elif preferred == "pyqt6":
    QtWidgets, QtCore, QtGui, QT_API = _load_pyqt6()
else:
    has_pyqt6 = _has_module("PyQt6")
    has_pyqt5 = _has_module("PyQt5")
    if has_pyqt6 and not has_pyqt5:
        QtWidgets, QtCore, QtGui, QT_API = _load_pyqt6()
    elif has_pyqt5 and not has_pyqt6:
        QtWidgets, QtCore, QtGui, QT_API = _load_pyqt5()
    else:
        try:
            QtWidgets, QtCore, QtGui, QT_API = _load_pyqt6()
        except ImportError:
            QtWidgets, QtCore, QtGui, QT_API = _load_pyqt5()
