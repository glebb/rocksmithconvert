import sys
import argparse
from PyQt5 import QtWidgets, QtCore
from controllers import MainController
from widgets import MainWindow


def parseFilesFromArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs='*')
    args = parser.parse_args()
    return args.files

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    controller = MainController(parseFilesFromArguments())
    app.exec()
