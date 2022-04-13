import sys
from argparse import ArgumentParser
from PyQt6 import QtWidgets
from rocksmithconvert.controllers import MainWindowController
from os import environ

def parseFilesFromArguments():
    parser = ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs="*")
    args = parser.parse_args()
    return args.files


if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    controller = MainWindowController(parseFilesFromArguments())
    app.exec()
