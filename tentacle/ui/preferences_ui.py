# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'preferences.ui'
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
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QGroupBox,
    QMainWindow, QPushButton, QSizePolicy, QSpacerItem,
    QSpinBox, QTabWidget, QVBoxLayout, QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.header.Header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(200, 307)
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

        self.parent_app = QGroupBox(self.central_widget)
        self.parent_app.setObjectName(u"parent_app")
        self.verticalLayout_3 = QVBoxLayout(self.parent_app)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.b010 = QPushButton(self.parent_app)
        self.b010.setObjectName(u"b010")
        self.b010.setMinimumSize(QSize(0, 20))
        self.b010.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_3.addWidget(self.b010)

        self.b009 = QPushButton(self.parent_app)
        self.b009.setObjectName(u"b009")
        self.b009.setMinimumSize(QSize(0, 20))
        self.b009.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_3.addWidget(self.b009)

        self.b008 = QPushButton(self.parent_app)
        self.b008.setObjectName(u"b008")
        self.b008.setMinimumSize(QSize(0, 20))
        self.b008.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_3.addWidget(self.b008)

        self.b001 = QPushButton(self.parent_app)
        self.b001.setObjectName(u"b001")
        self.b001.setMinimumSize(QSize(0, 20))
        self.b001.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_3.addWidget(self.b001)


        self.verticalLayout.addWidget(self.parent_app)

        self.units = QGroupBox(self.central_widget)
        self.units.setObjectName(u"units")
        self.verticalLayout_4 = QVBoxLayout(self.units)
        self.verticalLayout_4.setSpacing(1)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.cmb001 = ComboBox(self.units)
        self.cmb001.addItem("")
        self.cmb001.setObjectName(u"cmb001")
        self.cmb001.setMinimumSize(QSize(0, 20))
        self.cmb001.setMaximumSize(QSize(16777215, 20))
        self.cmb001.setMaxCount(999)
        self.cmb001.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb001.setFrame(False)

        self.verticalLayout_4.addWidget(self.cmb001)

        self.cmb002 = ComboBox(self.units)
        self.cmb002.addItem("")
        self.cmb002.setObjectName(u"cmb002")
        self.cmb002.setMinimumSize(QSize(0, 20))
        self.cmb002.setMaximumSize(QSize(16777215, 20))
        self.cmb002.setMaxCount(999)
        self.cmb002.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb002.setFrame(False)

        self.verticalLayout_4.addWidget(self.cmb002)

        self.autosave = QGroupBox(self.units)
        self.autosave.setObjectName(u"autosave")
        self.verticalLayout_6 = QVBoxLayout(self.autosave)
        self.verticalLayout_6.setSpacing(1)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.s000 = QSpinBox(self.autosave)
        self.s000.setObjectName(u"s000")
        self.s000.setMinimumSize(QSize(0, 20))
        self.s000.setMaximumSize(QSize(16777215, 20))
        self.s000.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.s000.setMinimum(0)
        self.s000.setMaximum(100)

        self.verticalLayout_6.addWidget(self.s000)

        self.s001 = QSpinBox(self.autosave)
        self.s001.setObjectName(u"s001")
        self.s001.setMinimumSize(QSize(0, 20))
        self.s001.setMaximumSize(QSize(16777215, 20))
        self.s001.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.s001.setMinimum(1)
        self.s001.setMaximum(60)

        self.verticalLayout_6.addWidget(self.s001)


        self.verticalLayout_4.addWidget(self.autosave)


        self.verticalLayout.addWidget(self.units)

        self.app = QGroupBox(self.central_widget)
        self.app.setObjectName(u"app")
        self.verticalLayout_5 = QVBoxLayout(self.app)
        self.verticalLayout_5.setSpacing(1)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.tb000 = PushButton(self.app)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(16777215, 20))

        self.verticalLayout_5.addWidget(self.tb000)


        self.verticalLayout.addWidget(self.app)

        self.verticalSpacer_2 = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer_2)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        QtUi.setWindowTitle("")
        self.header.setText(QCoreApplication.translate("QtUi", u"PREFERENCES", None))
        self.parent_app.setTitle(QCoreApplication.translate("QtUi", u"Parent App", None))
        self.b010.setText(QCoreApplication.translate("QtUi", u"Parent App Preferences", None))
        self.b009.setText(QCoreApplication.translate("QtUi", u"Plug-ins", None))
#if QT_CONFIG(tooltip)
        self.b008.setToolTip(QCoreApplication.translate("QtUi", u"Platonic solids", None))
#endif // QT_CONFIG(tooltip)
        self.b008.setText(QCoreApplication.translate("QtUi", u"Hotkeys", None))
#if QT_CONFIG(tooltip)
        self.b001.setToolTip(QCoreApplication.translate("QtUi", u"Open color settings editor", None))
#endif // QT_CONFIG(tooltip)
        self.b001.setText(QCoreApplication.translate("QtUi", u"Ui Color", None))
        self.units.setTitle(QCoreApplication.translate("QtUi", u"Working Units", None))
        self.cmb001.setItemText(0, QCoreApplication.translate("QtUi", u"Linear", None))

#if QT_CONFIG(tooltip)
        self.cmb001.setToolTip(QCoreApplication.translate("QtUi", u"Set working units: Linear", None))
#endif // QT_CONFIG(tooltip)
        self.cmb002.setItemText(0, QCoreApplication.translate("QtUi", u"Time", None))

#if QT_CONFIG(tooltip)
        self.cmb002.setToolTip(QCoreApplication.translate("QtUi", u"Set working units: Time", None))
#endif // QT_CONFIG(tooltip)
        self.autosave.setTitle(QCoreApplication.translate("QtUi", u"Autosave", None))
#if QT_CONFIG(tooltip)
        self.s000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>The number of autosave files to retain.</p><p>An amount of 0 will deactivate autosave.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.s000.setPrefix(QCoreApplication.translate("QtUi", u"Amount:	", None))
#if QT_CONFIG(tooltip)
        self.s001.setToolTip(QCoreApplication.translate("QtUi", u"The autosave interval in minutes.", None))
#endif // QT_CONFIG(tooltip)
        self.s001.setPrefix(QCoreApplication.translate("QtUi", u"Interval:	", None))
        self.app.setTitle(QCoreApplication.translate("QtUi", u"App", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"Updates this app to the latest version.", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Check for Update", None))
    # retranslateUi

