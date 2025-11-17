# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'duplicate#submenu.ui'
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
        self.i025 = QPushButton(self.widget)
        self.i025.setObjectName(u"i025")
        self.i025.setGeometry(QRect(270, 290, 66, 21))
        self.i025.setMinimumSize(QSize(0, 21))
        self.i025.setMaximumSize(QSize(16777215, 21))
        self.tb001 = PushButton(self.widget)
        self.tb001.setObjectName(u"tb001")
        self.tb001.setGeometry(QRect(300, 350, 111, 19))
        self.tb001.setMaximumSize(QSize(999, 19))
        self.tb001.setIconSize(QSize(18, 18))
        self.tb001.setAutoDefault(False)
        self.tb001.setFlat(False)
        self.tb001.setProperty(u"bnabled", True)
        self.b005 = QPushButton(self.widget)
        self.b005.setObjectName(u"b005")
        self.b005.setGeometry(QRect(360, 320, 126, 19))
        self.b005.setMaximumSize(QSize(999, 19))
        self.b005.setIconSize(QSize(18, 18))
        self.b005.setAutoDefault(False)
        self.b005.setFlat(False)
        self.b005.setProperty(u"bnabled", True)
        self.tb000 = PushButton(self.widget)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setGeometry(QRect(355, 290, 136, 20))
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(999, 20))
        self.tb000.setIconSize(QSize(18, 18))
        self.tb000.setAutoDefault(False)
        self.tb000.setFlat(False)
        self.tb000.setProperty(u"bnabled", True)
        self.b006 = QPushButton(self.widget)
        self.b006.setObjectName(u"b006")
        self.b006.setGeometry(QRect(360, 250, 126, 20))
        self.b006.setMinimumSize(QSize(0, 20))
        self.b006.setMaximumSize(QSize(16777215, 20))
        self.b006.setIconSize(QSize(18, 18))
        self.b006.setAutoDefault(False)
        self.b006.setFlat(False)
        self.b006.setProperty(u"bnabled", True)
        self.b008 = QPushButton(self.widget)
        self.b008.setObjectName(u"b008")
        self.b008.setGeometry(QRect(360, 190, 126, 20))
        self.b008.setMinimumSize(QSize(0, 20))
        self.b008.setMaximumSize(QSize(16777215, 20))
        self.b008.setIconSize(QSize(18, 18))
        self.b008.setAutoDefault(False)
        self.b008.setFlat(False)
        self.b008.setProperty(u"bnabled", True)
        self.b007 = QPushButton(self.widget)
        self.b007.setObjectName(u"b007")
        self.b007.setGeometry(QRect(360, 220, 126, 20))
        self.b007.setMinimumSize(QSize(0, 20))
        self.b007.setMaximumSize(QSize(16777215, 20))
        self.b007.setIconSize(QSize(18, 18))
        self.b007.setAutoDefault(False)
        self.b007.setFlat(False)
        self.b007.setProperty(u"bnabled", True)
        self.b000 = QPushButton(self.widget)
        self.b000.setObjectName(u"b000")
        self.b000.setGeometry(QRect(270, 250, 71, 20))
        self.b000.setMinimumSize(QSize(0, 20))
        self.b000.setMaximumSize(QSize(16777215, 20))
        self.b000.setIconSize(QSize(18, 18))
        self.b000.setAutoDefault(False)
        self.b000.setFlat(False)
        self.b000.setProperty(u"bnabled", True)
        QtUi.setCentralWidget(self.widget)

        self.retranslateUi(QtUi)

        self.tb001.setDefault(False)
        self.b005.setDefault(False)
        self.tb000.setDefault(False)
        self.b006.setDefault(False)
        self.b008.setDefault(False)
        self.b007.setDefault(False)
        self.b000.setDefault(False)


        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
#if QT_CONFIG(accessibility)
        self.i025.setAccessibleName(QCoreApplication.translate("QtUi", u"duplicate", None))
#endif // QT_CONFIG(accessibility)
        self.i025.setText(QCoreApplication.translate("QtUi", u"Duplicate", None))
#if QT_CONFIG(tooltip)
        self.tb001.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Select objects that are an instance of the current selection.</p><p>If no user selection exists, function will select all instanced objects in the scene.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.tb001.setText(QCoreApplication.translate("QtUi", u"Select Instances", None))
#if QT_CONFIG(tooltip)
        self.b005.setToolTip(QCoreApplication.translate("QtUi", u"Uninstance selected objects. (no selection is needed for 'all' flag)", None))
#endif // QT_CONFIG(tooltip)
        self.b005.setText(QCoreApplication.translate("QtUi", u"Un-Instance Selected", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>The first selected object will be instanced across all other selected objects.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Convert to Instances", None))
#if QT_CONFIG(tooltip)
        self.b006.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Duplicate: Create a linear array.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b006.setText(QCoreApplication.translate("QtUi", u"Duplicate Linear", None))
#if QT_CONFIG(tooltip)
        self.b008.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Duplicate: Create a grid array.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b008.setText(QCoreApplication.translate("QtUi", u"Duplicate Grid", None))
#if QT_CONFIG(tooltip)
        self.b007.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Radial Array: Create a radial array.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b007.setText(QCoreApplication.translate("QtUi", u"Duplicate Radial", None))
#if QT_CONFIG(tooltip)
        self.b000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p><br/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b000.setText(QCoreApplication.translate("QtUi", u"Mirrior", None))
        pass
    # retranslateUi

