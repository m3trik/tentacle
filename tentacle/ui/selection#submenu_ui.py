# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'selection#submenu.ui'
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
from PySide6.QtWidgets import (QApplication, QCheckBox, QMainWindow, QPushButton,
    QSizePolicy, QTabWidget, QWidget)

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
        self.i009 = QPushButton(self.widget)
        self.i009.setObjectName(u"i009")
        self.i009.setGeometry(QRect(270, 290, 66, 21))
        self.i009.setMinimumSize(QSize(0, 21))
        self.i009.setMaximumSize(QSize(16777215, 21))
        self.i021 = QPushButton(self.widget)
        self.i021.setObjectName(u"i021")
        self.i021.setGeometry(QRect(220, 250, 66, 21))
        self.i021.setMinimumSize(QSize(0, 21))
        self.i021.setMaximumSize(QSize(16777215, 21))
        self.chk006 = QCheckBox(self.widget)
        self.chk006.setObjectName(u"chk006")
        self.chk006.setEnabled(True)
        self.chk006.setGeometry(QRect(485, 270, 51, 19))
        self.chk006.setMaximumSize(QSize(104, 19))
        self.chk006.setIconSize(QSize(18, 18))
        self.chk006.setCheckable(True)
        self.tb001 = PushButton(self.widget)
        self.tb001.setObjectName(u"tb001")
        self.tb001.setEnabled(True)
        self.tb001.setGeometry(QRect(370, 290, 61, 19))
        self.tb001.setMaximumSize(QSize(111, 19))
        self.tb001.setIconSize(QSize(18, 18))
        self.tb002 = PushButton(self.widget)
        self.tb002.setObjectName(u"tb002")
        self.tb002.setEnabled(True)
        self.tb002.setGeometry(QRect(370, 260, 61, 19))
        self.tb002.setMaximumSize(QSize(111, 19))
        self.tb002.setIconSize(QSize(18, 18))
        self.chk005 = QCheckBox(self.widget)
        self.chk005.setObjectName(u"chk005")
        self.chk005.setEnabled(True)
        self.chk005.setGeometry(QRect(455, 240, 76, 19))
        self.chk005.setMaximumSize(QSize(104, 19))
        self.chk005.setIconSize(QSize(18, 18))
        self.chk005.setCheckable(True)
        self.chk007 = QCheckBox(self.widget)
        self.chk007.setObjectName(u"chk007")
        self.chk007.setEnabled(True)
        self.chk007.setGeometry(QRect(485, 300, 51, 19))
        self.chk007.setMaximumSize(QSize(104, 19))
        self.chk007.setIconSize(QSize(18, 18))
        self.chk007.setCheckable(True)
        self.chk004 = QCheckBox(self.widget)
        self.chk004.setObjectName(u"chk004")
        self.chk004.setEnabled(True)
        self.chk004.setGeometry(QRect(455, 330, 126, 19))
        self.chk004.setMaximumSize(QSize(999, 19))
        self.chk004.setIconSize(QSize(18, 18))
        self.chk004.setCheckable(True)
        self.b001 = PushButton(self.widget)
        self.b001.setObjectName(u"b001")
        self.b001.setEnabled(True)
        self.b001.setGeometry(QRect(290, 330, 146, 19))
        self.b001.setMaximumSize(QSize(16777215, 19))
        self.b001.setIconSize(QSize(18, 18))
        QtUi.setCentralWidget(self.widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
#if QT_CONFIG(accessibility)
        self.i009.setAccessibleName(QCoreApplication.translate("QtUi", u"selection", None))
#endif // QT_CONFIG(accessibility)
        self.i009.setText(QCoreApplication.translate("QtUi", u"Selection", None))
#if QT_CONFIG(accessibility)
        self.i021.setAccessibleName(QCoreApplication.translate("QtUi", u"symmetry", None))
#endif // QT_CONFIG(accessibility)
        self.i021.setText(QCoreApplication.translate("QtUi", u"Symmetry", None))
#if QT_CONFIG(tooltip)
        self.chk006.setToolTip(QCoreApplication.translate("QtUi", u"Select Style: Lasso", None))
#endif // QT_CONFIG(tooltip)
        self.chk006.setText(QCoreApplication.translate("QtUi", u"Lasso \u00b1", None))
#if QT_CONFIG(tooltip)
        self.tb001.setToolTip(QCoreApplication.translate("QtUi", u"Select similar objects or components, depending on selection mode.", None))
#endif // QT_CONFIG(tooltip)
        self.tb001.setText(QCoreApplication.translate("QtUi", u"Similar", None))
#if QT_CONFIG(tooltip)
        self.tb002.setToolTip(QCoreApplication.translate("QtUi", u"Select contiguous faces within a normal range", None))
#endif // QT_CONFIG(tooltip)
        self.tb002.setText(QCoreApplication.translate("QtUi", u"Island", None))
#if QT_CONFIG(tooltip)
        self.chk005.setToolTip(QCoreApplication.translate("QtUi", u"Select Style: Marquee", None))
#endif // QT_CONFIG(tooltip)
        self.chk005.setText(QCoreApplication.translate("QtUi", u"Marquee \u00b1", None))
#if QT_CONFIG(tooltip)
        self.chk007.setToolTip(QCoreApplication.translate("QtUi", u"Select Style: Paint", None))
#endif // QT_CONFIG(tooltip)
        self.chk007.setText(QCoreApplication.translate("QtUi", u"Paint \u00b1", None))
#if QT_CONFIG(tooltip)
        self.chk004.setToolTip(QCoreApplication.translate("QtUi", u"Select Style: Marquee", None))
#endif // QT_CONFIG(tooltip)
        self.chk004.setText(QCoreApplication.translate("QtUi", u"Ignore Backfacing \u00b1", None))
#if QT_CONFIG(tooltip)
        self.b001.setToolTip(QCoreApplication.translate("QtUi", u"Expand the outliner to show the currently selected object(s).", None))
#endif // QT_CONFIG(tooltip)
        self.b001.setText(QCoreApplication.translate("QtUi", u"Toggle Non/Selectable", None))
        pass
    # retranslateUi

