from PyQt5 import QtWidgets, QtCore

def settingsValueIsValid(widget: QtWidgets.QWidget, val: str) -> bool:
    if isinstance(widget, QtWidgets.QCheckBox) and val == 'checked': return True
    if isinstance(widget, QtWidgets.QLineEdit) and val == 'text': return True
    if isinstance(widget, QtWidgets.QComboBox) and val == 'currentText': return True
    if isinstance(widget, QtWidgets.QPushButton) and widget.objectName() == 'pushButtonDownloadDir' and val == 'toolTip': return True
    if isinstance(widget, QtWidgets.QPushButton) and widget.objectName() == 'pushButtonDownloadDir' and val == 'text': return True
    if isinstance(widget, QtWidgets.QPushButton) and widget.objectName() == 'pushButtonSelectTarget' and val == 'text': return True
    if isinstance(widget, QtWidgets.QPushButton) and widget.objectName() == 'pushButtonSelectTarget' and val == 'toolTip': return True
    return False

def saveSettings(settings: QtCore.QSettings) -> None:
    for w in QtWidgets.qApp.allWidgets():
        if w.objectName():
            mo = w.metaObject()
            for i in range(mo.propertyCount()):
                prop = mo.property(i)
                name = prop.name()
                key = "{}/{}".format(w.objectName(), name)
                val = w.property(name)
                if settingsValueIsValid(w, name) and prop.isValid() and prop.isWritable():
                    settings.setValue(key, w.property(name))


def loadSettings(settings: QtCore.QSettings) -> None:
    finfo = QtCore.QFileInfo(settings.fileName())
    if finfo.exists() and finfo.isFile():
        for w in QtWidgets.qApp.allWidgets():
            if w.objectName():
                mo = w.metaObject()
                for i in range(mo.propertyCount()):
                    prop = mo.property(i)
                    name = prop.name()
                    last_value = w.property(name)
                    key = "{}/{}".format(w.objectName(), name)
                    if not settings.contains(key):
                        continue
                    val = settings.value(key, type=type(last_value),)
                    if (
                        val != last_value
                        and settingsValueIsValid(w, name)
                        and prop.isValid()
                        and prop.isWritable()
                    ):
                        w.setProperty(name, val)