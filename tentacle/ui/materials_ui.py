# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'materials.ui'
##
## Created by: Qt User Interface Compiler version 6.9.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QComboBox, QGridLayout, QGroupBox,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QTabWidget, QVBoxLayout, QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.header.Header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(251, 130)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(QtUi.sizePolicy().hasHeightForWidth())
        QtUi.setSizePolicy(sizePolicy)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(200, 0))
        self.verticalLayout_2 = QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 20))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.verticalLayout.addWidget(self.header)

        self.group000 = QGroupBox(self.central_widget)
        self.group000.setObjectName(u"group000")
        self.gridLayout = QGridLayout(self.group000)
        self.gridLayout.setSpacing(1)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.tb000 = PushButton(self.group000)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setEnabled(True)
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(16777215, 20))

        self.gridLayout.addWidget(self.tb000, 8, 3, 1, 2)

        self.b005 = QPushButton(self.group000)
        self.b005.setObjectName(u"b005")
        self.b005.setEnabled(True)
        self.b005.setMinimumSize(QSize(0, 20))
        self.b005.setMaximumSize(QSize(16777215, 20))

        self.gridLayout.addWidget(self.b005, 8, 2, 1, 1)

        self.cmb002 = ComboBox(self.group000)
        self.cmb002.addItem("")
        self.cmb002.setObjectName(u"cmb002")
        self.cmb002.setMinimumSize(QSize(0, 20))
        self.cmb002.setMaximumSize(QSize(16777215, 20))
        self.cmb002.setMaxVisibleItems(40)
        self.cmb002.setMaxCount(500)
        self.cmb002.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb002.setFrame(True)

        self.gridLayout.addWidget(self.cmb002, 2, 0, 1, 5)

        self.b002 = QPushButton(self.group000)
        self.b002.setObjectName(u"b002")
        self.b002.setEnabled(True)
        self.b002.setMinimumSize(QSize(0, 20))
        self.b002.setMaximumSize(QSize(16777215, 20))

        self.gridLayout.addWidget(self.b002, 8, 0, 1, 2)


        self.verticalLayout.addWidget(self.group000)

        self.groupBox = QGroupBox(self.central_widget)
        self.groupBox.setObjectName(u"groupBox")
        self.gridLayout_2 = QGridLayout(self.groupBox)
        self.gridLayout_2.setSpacing(1)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setContentsMargins(0, 0, 0, 0)
        self.b006 = PushButton(self.groupBox)
        self.b006.setObjectName(u"b006")
        self.b006.setEnabled(True)
        self.b006.setMinimumSize(QSize(0, 20))
        self.b006.setMaximumSize(QSize(16777215, 20))

        self.gridLayout_2.addWidget(self.b006, 0, 1, 1, 1)

        self.b004 = PushButton(self.groupBox)
        self.b004.setObjectName(u"b004")
        self.b004.setEnabled(True)
        self.b004.setMinimumSize(QSize(0, 20))
        self.b004.setMaximumSize(QSize(16777215, 20))

        self.gridLayout_2.addWidget(self.b004, 0, 0, 1, 1)


        self.verticalLayout.addWidget(self.groupBox)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"MATERIALS", None))
        self.group000.setTitle(QCoreApplication.translate("QtUi", u"Material", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"Select objects that are assigned the current material.", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Select", None))
#if QT_CONFIG(tooltip)
        self.b005.setToolTip(QCoreApplication.translate("QtUi", u"Assign the current material to any currently selected objects.", None))
#endif // QT_CONFIG(tooltip)
        self.b005.setText(QCoreApplication.translate("QtUi", u"Assign", None))
        self.cmb002.setItemText(0, QCoreApplication.translate("QtUi", u"None", None))

#if QT_CONFIG(tooltip)
        self.cmb002.setToolTip(QCoreApplication.translate("QtUi", u"Current material.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.b002.setToolTip(QCoreApplication.translate("QtUi", u"Set material shader ID from selection.", None))
#endif // QT_CONFIG(tooltip)
        self.b002.setText(QCoreApplication.translate("QtUi", u"Get", None))
        self.groupBox.setTitle(QCoreApplication.translate("QtUi", u"Assign", None))
#if QT_CONFIG(tooltip)
        self.b006.setToolTip(QCoreApplication.translate("QtUi", u"Assign a new material to the current selection.", None))
#endif // QT_CONFIG(tooltip)
        self.b006.setText(QCoreApplication.translate("QtUi", u"New", None))
#if QT_CONFIG(tooltip)
        self.b004.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Assign a new random material to any selected object(s).</p><p><br/><span style=\" font-style:italic;\">You can click repeatedly until a desired color is found.</span></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b004.setText(QCoreApplication.translate("QtUi", u"Assign Random", None))
        pass
    # retranslateUi

