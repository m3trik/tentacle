# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'cameras#startmenu.ui'
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
from PySide6.QtWidgets import (QApplication, QGridLayout, QMainWindow, QPushButton,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

from widgets.region import Region

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(785, 611)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(QtUi.sizePolicy().hasHeightForWidth())
        QtUi.setSizePolicy(sizePolicy)
        QtUi.setMinimumSize(QSize(0, 0))
        QtUi.setMaximumSize(QSize(16777215, 16777215))
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.widget = QWidget(QtUi)
        self.widget.setObjectName(u"widget")
        sizePolicy.setHeightForWidth(self.widget.sizePolicy().hasHeightForWidth())
        self.widget.setSizePolicy(sizePolicy)
        self.gridLayout = QGridLayout(self.widget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.staticWindow = QWidget(self.widget)
        self.staticWindow.setObjectName(u"staticWindow")
        self.gridLayout_2 = QGridLayout(self.staticWindow)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.region_4 = Region(self.staticWindow)
        self.region_4.setObjectName(u"region_4")

        self.gridLayout_2.addWidget(self.region_4, 0, 0, 3, 1)

        self.region_3 = Region(self.staticWindow)
        self.region_3.setObjectName(u"region_3")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.MinimumExpanding)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.region_3.sizePolicy().hasHeightForWidth())
        self.region_3.setSizePolicy(sizePolicy1)
        self.verticalLayout_2 = QVBoxLayout(self.region_3)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.region_5 = QWidget(self.region_3)
        self.region_5.setObjectName(u"region_5")
        self.region_5.setMinimumSize(QSize(0, 100))
        self.i000 = QPushButton(self.region_5)
        self.i000.setObjectName(u"i000")
        self.i000.setGeometry(QRect(95, 0, 111, 21))
        self.i000.setMinimumSize(QSize(0, 21))
        self.i000.setMaximumSize(QSize(999, 21))

        self.verticalLayout_2.addWidget(self.region_5)

        self.verticalSpacer_2 = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_2.addItem(self.verticalSpacer_2)


        self.gridLayout_2.addWidget(self.region_3, 2, 1, 1, 1)

        self.region = Region(self.staticWindow)
        self.region.setObjectName(u"region")
        self.verticalLayout = QVBoxLayout(self.region)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalSpacer = QSpacerItem(20, 56, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)

        self.widget_0 = QWidget(self.region)
        self.widget_0.setObjectName(u"widget_0")
        self.widget_0.setMinimumSize(QSize(0, 100))
        self.b011 = QPushButton(self.widget_0)
        self.b011.setObjectName(u"b011")
        self.b011.setEnabled(True)
        self.b011.setGeometry(QRect(200, 80, 66, 21))
        self.b011.setMinimumSize(QSize(0, 21))
        self.b011.setMaximumSize(QSize(999, 21))
        self.b012 = QPushButton(self.widget_0)
        self.b012.setObjectName(u"b012")
        self.b012.setEnabled(True)
        self.b012.setGeometry(QRect(85, 56, 66, 21))
        self.b012.setMinimumSize(QSize(0, 21))
        self.b012.setMaximumSize(QSize(999, 21))
        self.b013 = QPushButton(self.widget_0)
        self.b013.setObjectName(u"b013")
        self.b013.setEnabled(True)
        self.b013.setGeometry(QRect(155, 56, 66, 21))
        self.b013.setMinimumSize(QSize(0, 21))
        self.b013.setMaximumSize(QSize(999, 21))
        self.b010 = QPushButton(self.widget_0)
        self.b010.setObjectName(u"b010")
        self.b010.setEnabled(True)
        self.b010.setGeometry(QRect(40, 80, 66, 21))
        self.b010.setMinimumSize(QSize(0, 21))
        self.b010.setMaximumSize(QSize(999, 21))

        self.verticalLayout.addWidget(self.widget_0)


        self.gridLayout_2.addWidget(self.region, 0, 1, 1, 1)

        self.region_2 = Region(self.staticWindow)
        self.region_2.setObjectName(u"region_2")

        self.gridLayout_2.addWidget(self.region_2, 0, 2, 3, 1)

        self.viewport = QWidget(self.staticWindow)
        self.viewport.setObjectName(u"viewport")
        self.viewport.setMinimumSize(QSize(325, 200))
        self.viewport.setMaximumSize(QSize(300, 200))
        self.b004 = QPushButton(self.viewport)
        self.b004.setObjectName(u"b004")
        self.b004.setGeometry(QRect(125, 20, 71, 21))
        self.b004.setMinimumSize(QSize(0, 21))
        self.b004.setMaximumSize(QSize(999, 21))
        self.b005 = QPushButton(self.viewport)
        self.b005.setObjectName(u"b005")
        self.b005.setGeometry(QRect(195, 50, 66, 21))
        self.b005.setMinimumSize(QSize(0, 21))
        self.b005.setMaximumSize(QSize(999, 21))
        self.b002 = QPushButton(self.viewport)
        self.b002.setObjectName(u"b002")
        self.b002.setGeometry(QRect(220, 90, 66, 21))
        self.b002.setMinimumSize(QSize(0, 21))
        self.b002.setMaximumSize(QSize(999, 21))
        self.b003 = QPushButton(self.viewport)
        self.b003.setObjectName(u"b003")
        self.b003.setGeometry(QRect(35, 90, 66, 21))
        self.b003.setMinimumSize(QSize(0, 21))
        self.b003.setMaximumSize(QSize(999, 21))
        self.b000 = QPushButton(self.viewport)
        self.b000.setObjectName(u"b000")
        self.b000.setGeometry(QRect(195, 130, 66, 21))
        self.b000.setMinimumSize(QSize(0, 21))
        self.b000.setMaximumSize(QSize(999, 21))
        self.b006 = QPushButton(self.viewport)
        self.b006.setObjectName(u"b006")
        self.b006.setGeometry(QRect(55, 130, 66, 21))
        self.b006.setMinimumSize(QSize(0, 21))
        self.b006.setMaximumSize(QSize(999, 21))
        self.b007 = QPushButton(self.viewport)
        self.b007.setObjectName(u"b007")
        self.b007.setGeometry(QRect(125, 160, 71, 21))
        self.b007.setMinimumSize(QSize(0, 21))
        self.b007.setMaximumSize(QSize(999, 21))
        self.b001 = QPushButton(self.viewport)
        self.b001.setObjectName(u"b001")
        self.b001.setGeometry(QRect(60, 50, 66, 21))
        self.b001.setMinimumSize(QSize(0, 21))
        self.b001.setMaximumSize(QSize(999, 21))

        self.gridLayout_2.addWidget(self.viewport, 1, 1, 1, 1)

        self.region.raise_()
        self.viewport.raise_()
        self.region_2.raise_()
        self.region_3.raise_()
        self.region_4.raise_()

        self.gridLayout.addWidget(self.staticWindow, 0, 0, 1, 1)

        QtUi.setCentralWidget(self.widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
#if QT_CONFIG(accessibility)
        self.i000.setAccessibleName(QCoreApplication.translate("QtUi", u"cameras#lower", None))
#endif // QT_CONFIG(accessibility)
        self.i000.setText(QCoreApplication.translate("QtUi", u"Camera Options", None))
#if QT_CONFIG(tooltip)
        self.b011.setToolTip(QCoreApplication.translate("QtUi", u"Camera: Roll", None))
#endif // QT_CONFIG(tooltip)
        self.b011.setText(QCoreApplication.translate("QtUi", u"Roll", None))
#if QT_CONFIG(tooltip)
        self.b012.setToolTip(QCoreApplication.translate("QtUi", u"Camera: Truck", None))
#endif // QT_CONFIG(tooltip)
        self.b012.setText(QCoreApplication.translate("QtUi", u"Truck", None))
#if QT_CONFIG(tooltip)
        self.b013.setToolTip(QCoreApplication.translate("QtUi", u"Camera: Pan", None))
#endif // QT_CONFIG(tooltip)
        self.b013.setText(QCoreApplication.translate("QtUi", u"Orbit", None))
#if QT_CONFIG(tooltip)
        self.b010.setToolTip(QCoreApplication.translate("QtUi", u"Camera: Dolly", None))
#endif // QT_CONFIG(tooltip)
        self.b010.setText(QCoreApplication.translate("QtUi", u"Dolly", None))
        self.b004.setText(QCoreApplication.translate("QtUi", u"Persp", None))
        self.b005.setText(QCoreApplication.translate("QtUi", u"Front   -Z", None))
        self.b002.setText(QCoreApplication.translate("QtUi", u"Right   -X", None))
        self.b003.setText(QCoreApplication.translate("QtUi", u"Left   X", None))
        self.b000.setText(QCoreApplication.translate("QtUi", u"Back   Z", None))
        self.b006.setText(QCoreApplication.translate("QtUi", u"Bottom  Y", None))
        self.b007.setText(QCoreApplication.translate("QtUi", u"Align", None))
        self.b001.setText(QCoreApplication.translate("QtUi", u"Top   -Y", None))
        pass
    # retranslateUi

