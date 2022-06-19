import sys
from argparse import ArgumentParser
from rocksmithconvert.controllers import MainWindowController
from rocksmithconvert.qt_wrapper import *
from os import environ

environ["QT_MAC_WANTS_LAYER"] = "1"


def parseFilesFromArguments():
    parser = ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs="*")
    args = parser.parse_args()
    return args.files


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    controller = MainWindowController(parseFilesFromArguments())
    app.exec()
