import sys
from argparse import ArgumentParser
from os import environ

from rocksmithconvert import utils
from rocksmithconvert.controllers import MainWindowController
from rocksmithconvert.qt_wrapper import *


def parseFilesFromArguments():
    parser = ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs="*")
    args = parser.parse_args()
    return args.files


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(
        f"#centralwidget {{background-image:  url('{utils.assets_path()}trees.jpg'); border : 0px}}"
    )
 
    controller = MainWindowController(parseFilesFromArguments())
    app.exec()
