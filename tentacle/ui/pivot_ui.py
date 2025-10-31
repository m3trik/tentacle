# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'pivot.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QHBoxLayout, QMainWindow,
    QPushButton, QSizePolicy, QSpacerItem, QTabWidget,
    QVBoxLayout, QWidget)

from uitk.widgets.header.Header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(200, 167)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(200, 0))
        self.verticalLayout_3 = QVBoxLayout(self.central_widget)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(1, 1, 1, 1)
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

        self.Pivot = QGroupBox(self.central_widget)
        self.Pivot.setObjectName(u"Pivot")
        self.Pivot.setEnabled(True)
        self.verticalLayout_2 = QVBoxLayout(self.Pivot)
        self.verticalLayout_2.setSpacing(1)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.tb001 = PushButton(self.Pivot)
        self.tb001.setObjectName(u"tb001")
        self.tb001.setEnabled(True)
        self.tb001.setMinimumSize(QSize(0, 20))
        self.tb001.setMaximumSize(QSize(16777215, 20))
        self.tb001.setIconSize(QSize(18, 18))

        self.verticalLayout_2.addWidget(self.tb001)

        self.tb003 = PushButton(self.Pivot)
        self.tb003.setObjectName(u"tb003")
        self.tb003.setEnabled(True)
        self.tb003.setMinimumSize(QSize(0, 20))
        self.tb003.setMaximumSize(QSize(16777215, 20))
        self.tb003.setIconSize(QSize(18, 18))

        self.verticalLayout_2.addWidget(self.tb003)

        self.tb002 = PushButton(self.Pivot)
        self.tb002.setObjectName(u"tb002")
        self.tb002.setEnabled(True)
        self.tb002.setMinimumSize(QSize(0, 20))
        self.tb002.setMaximumSize(QSize(16777215, 20))
        self.tb002.setIconSize(QSize(18, 18))

        self.verticalLayout_2.addWidget(self.tb002)

        self.tb000 = PushButton(self.Pivot)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setEnabled(True)
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(16777215, 20))
        self.tb000.setIconSize(QSize(18, 18))

        self.verticalLayout_2.addWidget(self.tb000)

        self.b004 = QPushButton(self.Pivot)
        self.b004.setObjectName(u"b004")
        self.b004.setEnabled(True)
        self.b004.setMinimumSize(QSize(0, 20))
        self.b004.setMaximumSize(QSize(16777215, 20))
        self.b004.setIconSize(QSize(18, 18))

        self.verticalLayout_2.addWidget(self.b004)

        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName(u"horizontalLayout")

        self.verticalLayout_2.addLayout(self.horizontalLayout)


        self.verticalLayout.addWidget(self.Pivot)

        self.verticalSpacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.verticalLayout_3.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"PIVOT", None))
        self.Pivot.setTitle(QCoreApplication.translate("QtUi", u"Pivot", None))
#if QT_CONFIG(tooltip)
        self.tb001.setToolTip(QCoreApplication.translate("QtUi", u"Center the the selected object's pivot.", None))
#endif // QT_CONFIG(tooltip)
        self.tb001.setText(QCoreApplication.translate("QtUi", u"Center", None))
#if QT_CONFIG(tooltip)
        self.tb003.setToolTip(QCoreApplication.translate("QtUi", u"Set pivot to world-aligned orientation.", None))
#endif // QT_CONFIG(tooltip)
        self.tb003.setText(QCoreApplication.translate("QtUi", u"Align World", None))
#if QT_CONFIG(tooltip)
        self.tb002.setToolTip(QCoreApplication.translate("QtUi", u"Transfer the pivot orientation from the first given object to the remaining given objects.", None))
#endif // QT_CONFIG(tooltip)
        self.tb002.setText(QCoreApplication.translate("QtUi", u"Transfer", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"Set pivot to world-aligned orientation.", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Reset", None))
#if QT_CONFIG(tooltip)
        self.b004.setToolTip(QCoreApplication.translate("QtUi", u"Set selected object(s) transform to the current tool's custom axis orintaion.", None))
#endif // QT_CONFIG(tooltip)
        self.b004.setText(QCoreApplication.translate("QtUi", u"Bake", None))
        pass
    # retranslateUi

