# Form implementation generated from reading ui file 'mainwindow.ui'
#
# Created by: PyQt6 UI code generator 6.3.1
#
# WARNING: Any manual changes made to this file will be lost when pyuic6 is
# run again.  Do not edit this file unless you know what you are doing.


from rocksmithconvert.qt_wrapper import QtCore, QtWidgets


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(650, 575)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(MainWindow.sizePolicy().hasHeightForWidth())
        MainWindow.setSizePolicy(sizePolicy)
        MainWindow.setMinimumSize(QtCore.QSize(640, 480))
        MainWindow.setMaximumSize(QtCore.QSize(800, 600))
        MainWindow.setBaseSize(QtCore.QSize(640, 480))
        MainWindow.setAutoFillBackground(True)
        MainWindow.setStyleSheet("")
        MainWindow.setUnifiedTitleAndToolBarOnMac(True)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setAutoFillBackground(False)
        self.centralwidget.setStyleSheet("")
        self.centralwidget.setObjectName("centralwidget")
        self.gridLayout_2 = QtWidgets.QGridLayout(self.centralwidget)
        self.gridLayout_2.setObjectName("gridLayout_2")
        self.frameDropArea = DropArea(self.centralwidget)
        self.frameDropArea.setAcceptDrops(True)
        self.frameDropArea.setAutoFillBackground(False)
        self.frameDropArea.setFrameShape(QtWidgets.QFrame.Shape.NoFrame)
        self.frameDropArea.setFrameShadow(QtWidgets.QFrame.Shadow.Plain)
        self.frameDropArea.setLineWidth(0)
        self.frameDropArea.setObjectName("frameDropArea")
        self.gridLayout_4 = QtWidgets.QGridLayout(self.frameDropArea)
        self.gridLayout_4.setObjectName("gridLayout_4")
        self.progressBar = MyProgress(self.frameDropArea)
        self.progressBar.setAutoFillBackground(False)
        self.progressBar.setStyleSheet("padding: 3px;")
        self.progressBar.setProperty("value", 0)
        self.progressBar.setTextVisible(False)
        self.progressBar.setObjectName("progressBar")
        self.gridLayout_4.addWidget(self.progressBar, 1, 0, 1, 4)
        self.verticalLayoutRight = QtWidgets.QVBoxLayout()
        self.verticalLayoutRight.setObjectName("verticalLayoutRight")
        self.plainTextEdit = QtWidgets.QPlainTextEdit(self.frameDropArea)
        self.plainTextEdit.setAutoFillBackground(True)
        self.plainTextEdit.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.plainTextEdit.setTextInteractionFlags(QtCore.Qt.TextInteractionFlag.TextSelectableByMouse)
        self.plainTextEdit.setBackgroundVisible(False)
        self.plainTextEdit.setObjectName("plainTextEdit")
        self.verticalLayoutRight.addWidget(self.plainTextEdit)
        self.gridLayout_4.addLayout(self.verticalLayoutRight, 0, 3, 1, 1)
        self.verticalLayoutLeft = QtWidgets.QVBoxLayout()
        self.verticalLayoutLeft.setObjectName("verticalLayoutLeft")
        self.textBrowser = QtWidgets.QTextBrowser(self.frameDropArea)
        self.textBrowser.setAcceptDrops(False)
        self.textBrowser.setAutoFillBackground(False)
        self.textBrowser.setStyleSheet("")
        self.textBrowser.setFrameShadow(QtWidgets.QFrame.Shadow.Sunken)
        self.textBrowser.setOpenExternalLinks(True)
        self.textBrowser.setOpenLinks(True)
        self.textBrowser.setObjectName("textBrowser")
        self.verticalLayoutLeft.addWidget(self.textBrowser)
        self.widget = QtWidgets.QWidget(self.frameDropArea)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Maximum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.widget.setMinimumSize(QtCore.QSize(0, 22))
        self.widget.setBaseSize(QtCore.QSize(0, 0))
        self.widget.setAutoFillBackground(True)
        self.widget.setStyleSheet("")
        self.widget.setObjectName("widget")
        self.gridLayout = QtWidgets.QGridLayout(self.widget)
        self.gridLayout.setObjectName("gridLayout")
        self.label = QtWidgets.QLabel(self.widget)
        self.label.setObjectName("label")
        self.gridLayout.addWidget(self.label, 0, 0, 1, 1)
        self.label_2 = QtWidgets.QLabel(self.widget)
        self.label_2.setObjectName("label_2")
        self.gridLayout.addWidget(self.label_2, 5, 0, 1, 1)
        self.label_3 = QtWidgets.QLabel(self.widget)
        self.label_3.setObjectName("label_3")
        self.gridLayout.addWidget(self.label_3, 6, 0, 1, 1)
        self.comboBoxAppId = QtWidgets.QComboBox(self.widget)
        self.comboBoxAppId.setEditable(True)
        self.comboBoxAppId.setObjectName("comboBoxAppId")
        self.comboBoxAppId.addItem("")
        self.comboBoxAppId.addItem("")
        self.gridLayout.addWidget(self.comboBoxAppId, 6, 1, 1, 1)
        self.comboBoxRename = QtWidgets.QComboBox(self.widget)
        self.comboBoxRename.setAutoFillBackground(True)
        self.comboBoxRename.setObjectName("comboBoxRename")
        self.comboBoxRename.addItem("")
        self.comboBoxRename.addItem("")
        self.comboBoxRename.addItem("")
        self.gridLayout.addWidget(self.comboBoxRename, 5, 1, 1, 1)
        self.pushButtonSelectTarget = QtWidgets.QPushButton(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.pushButtonSelectTarget.sizePolicy().hasHeightForWidth())
        self.pushButtonSelectTarget.setSizePolicy(sizePolicy)
        self.pushButtonSelectTarget.setAutoFillBackground(False)
        self.pushButtonSelectTarget.setStyleSheet("border-color: rgb(0, 0, 0);")
        self.pushButtonSelectTarget.setObjectName("pushButtonSelectTarget")
        self.gridLayout.addWidget(self.pushButtonSelectTarget, 13, 0, 1, 2)
        self.comboBoxPlatform = QtWidgets.QComboBox(self.widget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Preferred, QtWidgets.QSizePolicy.Policy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.comboBoxPlatform.sizePolicy().hasHeightForWidth())
        self.comboBoxPlatform.setSizePolicy(sizePolicy)
        self.comboBoxPlatform.setAutoFillBackground(True)
        self.comboBoxPlatform.setStyleSheet("")
        self.comboBoxPlatform.setObjectName("comboBoxPlatform")
        self.comboBoxPlatform.addItem("")
        self.comboBoxPlatform.addItem("")
        self.comboBoxPlatform.addItem("")
        self.gridLayout.addWidget(self.comboBoxPlatform, 0, 1, 1, 1)
        self.labelTarget = QtWidgets.QLabel(self.widget)
        self.labelTarget.setObjectName("labelTarget")
        self.gridLayout.addWidget(self.labelTarget, 12, 0, 1, 1)
        self.checkBoxOverwrite = QtWidgets.QCheckBox(self.widget)
        self.checkBoxOverwrite.setObjectName("checkBoxOverwrite")
        self.gridLayout.addWidget(self.checkBoxOverwrite, 2, 0, 1, 1)
        self.verticalLayoutLeft.addWidget(self.widget)
        self.widget_3 = QtWidgets.QWidget(self.frameDropArea)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Policy.Minimum, QtWidgets.QSizePolicy.Policy.Minimum)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.widget_3.sizePolicy().hasHeightForWidth())
        self.widget_3.setSizePolicy(sizePolicy)
        self.widget_3.setAutoFillBackground(True)
        self.widget_3.setStyleSheet("")
        self.widget_3.setObjectName("widget_3")
        self.verticalLayout_4 = QtWidgets.QVBoxLayout(self.widget_3)
        self.verticalLayout_4.setObjectName("verticalLayout_4")
        self.checkBoxAutoProcess = QtWidgets.QCheckBox(self.widget_3)
        self.checkBoxAutoProcess.setObjectName("checkBoxAutoProcess")
        self.verticalLayout_4.addWidget(self.checkBoxAutoProcess)
        self.pushButtonSelectSource = QtWidgets.QPushButton(self.widget_3)
        self.pushButtonSelectSource.setEnabled(True)
        self.pushButtonSelectSource.setObjectName("pushButtonSelectSource")
        self.verticalLayout_4.addWidget(self.pushButtonSelectSource)
        self.verticalLayoutLeft.addWidget(self.widget_3)
        self.gridLayout_4.addLayout(self.verticalLayoutLeft, 0, 0, 1, 1)
        self.gridLayout_2.addWidget(self.frameDropArea, 0, 0, 1, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.comboBoxAppId.setCurrentIndex(1)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "Rocksmith 2014 CDLC convert pc/mac"))
        self.plainTextEdit.setPlaceholderText(_translate("MainWindow", "DROP FILES HERE"))
        self.textBrowser.setHtml(_translate("MainWindow", "<!DOCTYPE HTML PUBLIC \"-//W3C//DTD HTML 4.0//EN\" \"http://www.w3.org/TR/REC-html40/strict.dtd\">\n"
"<html><head><meta name=\"qrichtext\" content=\"1\" /><style type=\"text/css\">\n"
"p, li { white-space: pre-wrap; }\n"
"</style></head><body style=\" font-family:\'.AppleSystemUIFont\'; font-size:13pt; font-weight:400; font-style:normal;\">\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Drop files to app for processing.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Original files remain as they are, new files are created to target folder. If target file exists, processing is skipped.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">Rename uses the format (artist-song) without special characters and will either shorten the filename to 10+10 characters, or use the full name.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">To change cdlc app ID, set the desired app ID. If option is disabled, app ID is untouched.</p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\">With auto-processing enabled, the app will check specified folder periodically and execute processing without further user interaction when new files are found. </p>\n"
"<p style=\"-qt-paragraph-type:empty; margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><br /></p>\n"
"<p style=\" margin-top:0px; margin-bottom:0px; margin-left:0px; margin-right:0px; -qt-block-indent:0; text-indent:0px;\"><a href=\"https://github.com/glebb/rocksmithconvert\"><span style=\" text-decoration: underline; color:#0068da;\">Github page</span></a></p></body></html>"))
        self.label.setText(_translate("MainWindow", "Convert to:"))
        self.label_2.setText(_translate("MainWindow", "Rename scheme:"))
        self.label_3.setText(_translate("MainWindow", "Change AppID:"))
        self.comboBoxAppId.setItemText(0, _translate("MainWindow", "Disabled"))
        self.comboBoxAppId.setItemText(1, _translate("MainWindow", "248750"))
        self.comboBoxRename.setCurrentText(_translate("MainWindow", "Disabled"))
        self.comboBoxRename.setItemText(0, _translate("MainWindow", "Disabled"))
        self.comboBoxRename.setItemText(1, _translate("MainWindow", "Short"))
        self.comboBoxRename.setItemText(2, _translate("MainWindow", "Full"))
        self.pushButtonSelectTarget.setText(_translate("MainWindow", "Select target folder"))
        self.comboBoxPlatform.setItemText(0, _translate("MainWindow", "Disabled"))
        self.comboBoxPlatform.setItemText(1, _translate("MainWindow", "MAC"))
        self.comboBoxPlatform.setItemText(2, _translate("MainWindow", "PC"))
        self.labelTarget.setText(_translate("MainWindow", "Target:"))
        self.checkBoxOverwrite.setText(_translate("MainWindow", "Overwrite existing"))
        self.checkBoxAutoProcess.setText(_translate("MainWindow", "Auto-process:"))
        self.pushButtonSelectSource.setText(_translate("MainWindow", "Select auto-process folder"))
from rocksmithconvert.droparea import DropArea
from rocksmithconvert.myprogress import MyProgress

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.show()
    sys.exit(app.exec())
