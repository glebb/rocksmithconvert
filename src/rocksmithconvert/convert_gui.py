import sys
from argparse import ArgumentParser
from os import environ

from rocksmithconvert import startup
from rocksmithconvert import utils
from rocksmithconvert.controllers import MainWindowController
from rocksmithconvert.qt_wrapper import *


def parseFilesFromArguments():
    parser = ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs="*")
    args = parser.parse_args()
    return args.files


def applyStyleSheet(app) -> None:
    app.setStyleSheet(
        f"#centralwidget {{background-image:  url('{utils.assets_path()}wood.jpg'); border : 0px}}"
    )
    startup.mark("stylesheet applied")


if __name__ == "__main__":
    startup.mark("enter main")
    app = QtWidgets.QApplication(sys.argv)
    startup.mark("QApplication created")

    controller = MainWindowController(parseFilesFromArguments())
    startup.mark("controller created")
    QtCore.QTimer.singleShot(0, lambda: applyStyleSheet(app))
    app.exec()
