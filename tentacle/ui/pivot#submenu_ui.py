# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pivot#submenu.ui'
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
from PySide6.QtWidgets import (QApplication, QMainWindow, QPushButton, QSizePolicy,
    QTabWidget, QWidget)

from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(600, 600)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(QtUi.sizePolicy().hasHeightForWidth())
        QtUi.setSizePolicy(sizePolicy)
        QtUi.setMinimumSize(QSize(0, 0))
        QtUi.setMaximumSize(QSize(600, 600))
        QtUi.setToolButtonStyle(Qt.ToolButtonIconOnly)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.widget = QWidget(QtUi)
        self.widget.setObjectName(u"widget")
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.i061 = QPushButton(self.widget)
        self.i061.setObjectName(u"i061")
        self.i061.setGeometry(QRect(265, 290, 66, 21))
        self.i061.setMinimumSize(QSize(0, 21))
        self.i061.setMaximumSize(QSize(16777215, 21))
        self.b000 = QPushButton(self.widget)
        self.b000.setObjectName(u"b000")
        self.b000.setEnabled(True)
        self.b000.setGeometry(QRect(275, 240, 46, 19))
        self.b000.setMaximumSize(QSize(111, 19))
        self.b000.setIconSize(QSize(18, 18))
        self.b000.setAutoDefault(False)
        self.b000.setFlat(False)
        self.b004 = QPushButton(self.widget)
        self.b004.setObjectName(u"b004")
        self.b004.setEnabled(True)
        self.b004.setGeometry(QRect(170, 220, 71, 19))
        self.b004.setMaximumSize(QSize(111, 19))
        self.b004.setIconSize(QSize(18, 18))
        self.b002 = QPushButton(self.widget)
        self.b002.setObjectName(u"b002")
        self.b002.setEnabled(True)
        self.b002.setGeometry(QRect(335, 250, 46, 19))
        self.b002.setMaximumSize(QSize(111, 19))
        self.b002.setIconSize(QSize(18, 18))
        self.b001 = QPushButton(self.widget)
        self.b001.setObjectName(u"b001")
        self.b001.setEnabled(True)
        self.b001.setGeometry(QRect(215, 250, 46, 19))
        self.b001.setMaximumSize(QSize(111, 19))
        self.b001.setIconSize(QSize(18, 18))
        self.b001.setAutoDefault(False)
        self.b001.setFlat(False)
        self.tb003 = PushButton(self.widget)
        self.tb003.setObjectName(u"tb003")
        self.tb003.setEnabled(True)
        self.tb003.setGeometry(QRect(255, 200, 86, 19))
        self.tb003.setMaximumSize(QSize(111, 19))
        self.tb003.setIconSize(QSize(18, 18))
        self.tb000 = PushButton(self.widget)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setEnabled(True)
        self.tb000.setGeometry(QRect(270, 170, 56, 19))
        self.tb000.setMaximumSize(QSize(111, 19))
        self.tb000.setIconSize(QSize(18, 18))
        QtUi.setCentralWidget(self.widget)

        self.retranslateUi(QtUi)

        self.b000.setDefault(False)
        self.b001.setDefault(False)


        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
#if QT_CONFIG(accessibility)
        self.i061.setAccessibleName(QCoreApplication.translate("QtUi", u"pivot", None))
#endif // QT_CONFIG(accessibility)
        self.i061.setText(QCoreApplication.translate("QtUi", u"Pivot", None))
#if QT_CONFIG(tooltip)
        self.b000.setToolTip(QCoreApplication.translate("QtUi", u"Move the pivot point to the center of the selected object", None))
#endif // QT_CONFIG(tooltip)
        self.b000.setText(QCoreApplication.translate("QtUi", u"Obj", None))
#if QT_CONFIG(tooltip)
        self.b004.setToolTip(QCoreApplication.translate("QtUi", u"Set selected object(s) transform to the current tool's custom axis orintaion.", None))
#endif // QT_CONFIG(tooltip)
        self.b004.setText(QCoreApplication.translate("QtUi", u"Bake", None))
#if QT_CONFIG(tooltip)
        self.b002.setToolTip(QCoreApplication.translate("QtUi", u"Set selected objects pivot point to world space 0,0,0", None))
#endif // QT_CONFIG(tooltip)
        self.b002.setText(QCoreApplication.translate("QtUi", u"World", None))
#if QT_CONFIG(tooltip)
        self.b001.setToolTip(QCoreApplication.translate("QtUi", u"Move the pivot point of the object to the center of the selected components", None))
#endif // QT_CONFIG(tooltip)
        self.b001.setText(QCoreApplication.translate("QtUi", u"Cmpnt", None))
#if QT_CONFIG(tooltip)
        self.tb003.setToolTip(QCoreApplication.translate("QtUi", u"Set pivot to world-aligned orientation.", None))
#endif // QT_CONFIG(tooltip)
        self.tb003.setText(QCoreApplication.translate("QtUi", u"Align World", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"Set pivot to world-aligned orientation.", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Reset", None))
        pass
    # retranslateUi

