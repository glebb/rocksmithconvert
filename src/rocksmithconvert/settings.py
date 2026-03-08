from typing import Iterable, Tuple

from rocksmithconvert.qt_wrapper import QtWidgets, QtCore


class SettingsHandler:
    PERSISTED_PROPERTIES: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
        ("checkBoxAutoProcess", ("checked",)),
        ("checkBoxOverwrite", ("checked",)),
        ("comboBoxPlatform", ("currentIndex",)),
        ("comboBoxRename", ("currentIndex",)),
        ("comboBoxAppId", ("currentIndex", "currentText")),
        ("pushButtonSelectSource", ("text", "toolTip")),
        ("pushButtonSelectTarget", ("text", "toolTip")),
    )

    def __init__(self, settings: QtCore.QSettings):
        self.settings = settings

    def iterPersistedProperties(
        self, root: QtWidgets.QWidget
    ) -> Iterable[Tuple[QtWidgets.QWidget, str]]:
        for objectName, propertyNames in self.PERSISTED_PROPERTIES:
            widget = root.findChild(QtWidgets.QWidget, objectName)
            if widget is None:
                continue
            for propertyName in propertyNames:
                yield widget, propertyName

    def getProperty(self, widget: QtWidgets.QWidget, propertyName: str):
        metaObject = widget.metaObject()
        propertyIndex = metaObject.indexOfProperty(propertyName)
        if propertyIndex < 0:
            return None, None
        prop = metaObject.property(propertyIndex)
        if not prop.isValid() or not prop.isWritable():
            return None, None
        return prop, widget.property(propertyName)

    def saveSettings(self, root: QtWidgets.QWidget) -> None:
        for widget, propertyName in self.iterPersistedProperties(root):
            prop, value = self.getProperty(widget, propertyName)
            if prop is None:
                continue
            key = "{}/{}".format(widget.objectName(), propertyName)
            self.settings.setValue(key, value)

    def loadSettings(self, root: QtWidgets.QWidget) -> None:
        finfo = QtCore.QFileInfo(self.settings.fileName())
        if finfo.exists() and finfo.isFile():
            for widget, propertyName in self.iterPersistedProperties(root):
                prop, lastValue = self.getProperty(widget, propertyName)
                if prop is None:
                    continue
                key = "{}/{}".format(widget.objectName(), propertyName)
                if not self.settings.contains(key):
                    continue
                value = self.settings.value(
                    key,
                    type=type(lastValue),
                )
                if value == lastValue:
                    continue
                blocker = QtCore.QSignalBlocker(widget)
                widget.setProperty(propertyName, value)
                del blocker
