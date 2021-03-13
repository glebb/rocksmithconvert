import sys
import argparse
from PyQt5 import QtWidgets, QtCore
from widgets import MainWindow


def parseFilesFromArguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", help=".psarc files", nargs='*')
    args = parser.parse_args()
    return args.files

def forceShowWindow(window: MainWindow):
    window.setWindowFlags(window.windowFlags() &
                          QtCore.Qt.WindowStaysOnTopHint)
    window.show()
    window.setWindowFlags(window.windowFlags() & ~
                          QtCore.Qt.WindowStaysOnTopHint)

if __name__ == "__main__":
    files = parseFilesFromArguments()

    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow(files=files)
    forceShowWindow(window)
    app.exec()
