from rocksmithconvert.qt_wrapper import QtWidgets, QtCore


class SettingsHandler:
    def __init__(self, settings: QtCore.QSettings):
        try:
            self.app = QtWidgets.qApp
        except:
            self.app = QtWidgets.QApplication
        
        self.settings = settings

    def settingsValueIsValid(self, widget: QtWidgets.QWidget, val: str) -> bool:
        if isinstance(widget, QtWidgets.QCheckBox) and val == "checked":
            return True
        if isinstance(widget, QtWidgets.QLineEdit) and val == "text":
            return True
        if isinstance(widget, QtWidgets.QComboBox) and val == "currentText":
            return True
        if isinstance(widget, QtWidgets.QComboBox) and val == "currentIndex":
            return True
        if (
            isinstance(widget, QtWidgets.QPushButton)
            and widget.objectName() == "pushButtonSelectSource"
            and val == "toolTip"
        ):
            return True
        if (
            isinstance(widget, QtWidgets.QPushButton)
            and widget.objectName() == "pushButtonSelectSource"
            and val == "text"
        ):
            return True
        if (
            isinstance(widget, QtWidgets.QPushButton)
            and widget.objectName() == "pushButtonSelectTarget"
            and val == "text"
        ):
            return True
        if (
            isinstance(widget, QtWidgets.QPushButton)
            and widget.objectName() == "pushButtonSelectTarget"
            and val == "toolTip"
        ):
            return True
        return False

    def saveSettings(self) -> None:
        for w in self.app.allWidgets():
            if w.objectName():
                mo = w.metaObject()
                for i in range(mo.propertyCount()):
                    prop = mo.property(i)
                    name = prop.name()
                    key = "{}/{}".format(w.objectName(), name)
                    val = w.property(name)
                    if (
                        self.settingsValueIsValid(w, name)
                        and prop.isValid()
                        and prop.isWritable()
                    ):
                        self.settings.setValue(key, w.property(name))

    def loadSettings(self) -> None:
        finfo = QtCore.QFileInfo(self.settings.fileName())
        if finfo.exists() and finfo.isFile():
            for w in self.app.allWidgets():
                if w.objectName():
                    mo = w.metaObject()
                    for i in range(mo.propertyCount()):
                        prop = mo.property(i)
                        name = prop.name()
                        last_value = w.property(name)
                        key = "{}/{}".format(w.objectName(), name)
                        if not self.settings.contains(key):
                            continue
                        val = self.settings.value(
                            key,
                            type=type(last_value),
                        )
                        if (
                            val != last_value
                            and self.settingsValueIsValid(w, name)
                            and prop.isValid()
                            and prop.isWritable()
                        ):
                            w.setProperty(name, val)
