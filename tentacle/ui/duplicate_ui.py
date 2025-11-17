# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'duplicate.ui'
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
from PySide6.QtWidgets import (QApplication, QGroupBox, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

from uitk.widgets.header.Header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.resize(200, 144)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        QtUi.setProperty(u"bnabled", True)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(200, 0))
        palette = QPalette()
        brush = QBrush(QColor(168, 152, 250, 255))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        palette.setBrush(QPalette.ColorGroup.Active, QPalette.ColorRole.Highlight, brush)
        palette.setBrush(QPalette.ColorGroup.Inactive, QPalette.ColorRole.Highlight, brush)
        palette.setBrush(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Highlight, brush)
        self.central_widget.setPalette(palette)
        self.verticalLayout_2 = QVBoxLayout(self.central_widget)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(1, 1, 1, 1)
        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setSpacing(0)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.header = Header(self.central_widget)
        self.header.setObjectName(u"header")
        self.header.setMinimumSize(QSize(0, 20))
        self.header.setMaximumSize(QSize(16777215, 20))
        font = QFont()
        font.setBold(True)
        self.header.setFont(font)

        self.verticalLayout.addWidget(self.header)

        self.groupBox_7 = QGroupBox(self.central_widget)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.verticalLayout_3 = QVBoxLayout(self.groupBox_7)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.b000 = QPushButton(self.groupBox_7)
        self.b000.setObjectName(u"b000")
        self.b000.setMinimumSize(QSize(0, 20))
        self.b000.setMaximumSize(QSize(16777215, 20))
        self.b000.setIconSize(QSize(18, 18))
        self.b000.setAutoDefault(False)
        self.b000.setFlat(False)
        self.b000.setProperty(u"bnabled", True)

        self.verticalLayout_3.addWidget(self.b000)

        self.tb000 = PushButton(self.groupBox_7)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(16777215, 20))
        self.tb000.setIconSize(QSize(18, 18))
        self.tb000.setAutoDefault(False)
        self.tb000.setFlat(False)
        self.tb000.setProperty(u"bnabled", True)

        self.verticalLayout_3.addWidget(self.tb000)

        self.tb001 = PushButton(self.groupBox_7)
        self.tb001.setObjectName(u"tb001")
        self.tb001.setMinimumSize(QSize(0, 20))
        self.tb001.setMaximumSize(QSize(16777215, 20))
        self.tb001.setIconSize(QSize(18, 18))
        self.tb001.setAutoDefault(False)
        self.tb001.setFlat(False)
        self.tb001.setProperty(u"bnabled", True)

        self.verticalLayout_3.addWidget(self.tb001)

        self.b005 = QPushButton(self.groupBox_7)
        self.b005.setObjectName(u"b005")
        self.b005.setMinimumSize(QSize(0, 20))
        self.b005.setMaximumSize(QSize(16777215, 20))
        self.b005.setIconSize(QSize(18, 18))
        self.b005.setAutoDefault(False)
        self.b005.setFlat(False)
        self.b005.setProperty(u"bnabled", True)

        self.verticalLayout_3.addWidget(self.b005)


        self.verticalLayout.addWidget(self.groupBox_7)

        self.verticalSpacer_2 = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        self.b000.setDefault(False)
        self.tb000.setDefault(False)
        self.tb001.setDefault(False)
        self.b005.setDefault(False)


        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        QtUi.setWindowTitle(QCoreApplication.translate("QtUi", u"Toolkit", None))
        self.header.setText(QCoreApplication.translate("QtUi", u"DUPLICATE", None))
        self.groupBox_7.setTitle(QCoreApplication.translate("QtUi", u"Instance", None))
#if QT_CONFIG(tooltip)
        self.b000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Create instances of any selected objects.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.b000.setText(QCoreApplication.translate("QtUi", u"Instance Selected", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>The first selected object will be instanced across all other selected objects.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Convert to Instances", None))
#if QT_CONFIG(tooltip)
        self.tb001.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Select objects that are an instance of the current selection.</p><p>If no user selection exists, function will select all instanced objects in the scene.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.tb001.setText(QCoreApplication.translate("QtUi", u"Select Instances", None))
#if QT_CONFIG(tooltip)
        self.b005.setToolTip(QCoreApplication.translate("QtUi", u"Uninstance selected objects. (no selection is needed for 'all' flag)", None))
#endif // QT_CONFIG(tooltip)
        self.b005.setText(QCoreApplication.translate("QtUi", u"Un-Instance Selected", None))
    # retranslateUi

