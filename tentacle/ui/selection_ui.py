# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'selection.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QMainWindow,
    QSizePolicy, QSpacerItem, QTabWidget, QVBoxLayout,
    QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.header.Header import Header
from widgets.pushbutton import PushButton

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(200, 263)
        QtUi.setTabShape(QTabWidget.Triangular)
        QtUi.setDockNestingEnabled(True)
        QtUi.setDockOptions(QMainWindow.AllowNestedDocks|QMainWindow.AllowTabbedDocks|QMainWindow.AnimatedDocks|QMainWindow.ForceTabbedDocks)
        self.central_widget = QWidget(QtUi)
        self.central_widget.setObjectName(u"central_widget")
        self.central_widget.setMinimumSize(QSize(200, 0))
        self.central_widget.setLayoutDirection(Qt.LeftToRight)
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

        self.groupBox_5 = QGroupBox(self.central_widget)
        self.groupBox_5.setObjectName(u"groupBox_5")
        self.verticalLayout_4 = QVBoxLayout(self.groupBox_5)
        self.verticalLayout_4.setSpacing(1)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.cmb002 = ComboBox(self.groupBox_5)
        self.cmb002.addItem("")
        self.cmb002.setObjectName(u"cmb002")
        self.cmb002.setMinimumSize(QSize(0, 20))
        self.cmb002.setMaximumSize(QSize(16777215, 20))
        self.cmb002.setEditable(False)
        self.cmb002.setMaxVisibleItems(30)
        self.cmb002.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.verticalLayout_4.addWidget(self.cmb002)

        self.tb001 = PushButton(self.groupBox_5)
        self.tb001.setObjectName(u"tb001")
        self.tb001.setEnabled(True)
        self.tb001.setMinimumSize(QSize(0, 20))
        self.tb001.setMaximumSize(QSize(16777215, 20))
        self.tb001.setIconSize(QSize(18, 18))

        self.verticalLayout_4.addWidget(self.tb001)

        self.tb002 = PushButton(self.groupBox_5)
        self.tb002.setObjectName(u"tb002")
        self.tb002.setEnabled(True)
        self.tb002.setMinimumSize(QSize(0, 20))
        self.tb002.setMaximumSize(QSize(16777215, 20))
        self.tb002.setIconSize(QSize(18, 18))

        self.verticalLayout_4.addWidget(self.tb002)

        self.tb000 = PushButton(self.groupBox_5)
        self.tb000.setObjectName(u"tb000")
        self.tb000.setEnabled(True)
        self.tb000.setMinimumSize(QSize(0, 20))
        self.tb000.setMaximumSize(QSize(16777215, 20))
        self.tb000.setIconSize(QSize(18, 18))

        self.verticalLayout_4.addWidget(self.tb000)

        self.tb003 = PushButton(self.groupBox_5)
        self.tb003.setObjectName(u"tb003")
        self.tb003.setEnabled(True)
        self.tb003.setMinimumSize(QSize(0, 20))
        self.tb003.setMaximumSize(QSize(16777215, 20))
        self.tb003.setIconSize(QSize(18, 18))

        self.verticalLayout_4.addWidget(self.tb003)

        self.tb001.raise_()
        self.tb002.raise_()
        self.cmb002.raise_()
        self.tb000.raise_()
        self.tb003.raise_()

        self.verticalLayout.addWidget(self.groupBox_5)

        self.groupBox_8 = QGroupBox(self.central_widget)
        self.groupBox_8.setObjectName(u"groupBox_8")
        self.verticalLayout_6 = QVBoxLayout(self.groupBox_8)
        self.verticalLayout_6.setSpacing(1)
        self.verticalLayout_6.setObjectName(u"verticalLayout_6")
        self.verticalLayout_6.setContentsMargins(0, 0, 0, 0)
        self.cmb005 = ComboBox(self.groupBox_8)
        self.cmb005.addItem("")
        self.cmb005.setObjectName(u"cmb005")
        self.cmb005.setMinimumSize(QSize(0, 20))
        self.cmb005.setMaximumSize(QSize(16777215, 20))
        self.cmb005.setEditable(False)
        self.cmb005.setSizeAdjustPolicy(QComboBox.AdjustToContents)

        self.verticalLayout_6.addWidget(self.cmb005)


        self.verticalLayout.addWidget(self.groupBox_8)

        self.groupBox_6 = QGroupBox(self.central_widget)
        self.groupBox_6.setObjectName(u"groupBox_6")
        self.verticalLayout_7 = QVBoxLayout(self.groupBox_6)
        self.verticalLayout_7.setSpacing(1)
        self.verticalLayout_7.setObjectName(u"verticalLayout_7")
        self.verticalLayout_7.setContentsMargins(0, 0, 0, 0)
        self.cmb003 = ComboBox(self.groupBox_6)
        self.cmb003.addItem("")
        self.cmb003.setObjectName(u"cmb003")
        self.cmb003.setMinimumSize(QSize(0, 20))
        self.cmb003.setMaximumSize(QSize(16777215, 20))
        self.cmb003.setMaxVisibleItems(30)
        self.cmb003.setMaxCount(100)
        self.cmb003.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb003.setFrame(True)

        self.verticalLayout_7.addWidget(self.cmb003)


        self.verticalLayout.addWidget(self.groupBox_6)

        self.groupBox_7 = QGroupBox(self.central_widget)
        self.groupBox_7.setObjectName(u"groupBox_7")
        self.verticalLayout_8 = QVBoxLayout(self.groupBox_7)
        self.verticalLayout_8.setSpacing(1)
        self.verticalLayout_8.setObjectName(u"verticalLayout_8")
        self.verticalLayout_8.setContentsMargins(0, 0, 0, 0)
        self.cmb001 = ComboBox(self.groupBox_7)
        self.cmb001.addItem("")
        self.cmb001.setObjectName(u"cmb001")
        self.cmb001.setMinimumSize(QSize(0, 20))
        self.cmb001.setMaximumSize(QSize(16777215, 20))
        self.cmb001.setMaxVisibleItems(30)
        self.cmb001.setMaxCount(100)
        self.cmb001.setSizeAdjustPolicy(QComboBox.AdjustToContents)
        self.cmb001.setFrame(True)

        self.verticalLayout_8.addWidget(self.cmb001)


        self.verticalLayout.addWidget(self.groupBox_7)

        self.verticalSpacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"SELECTION", None))
        self.groupBox_5.setTitle(QCoreApplication.translate("QtUi", u"Select", None))
        self.cmb002.setItemText(0, QCoreApplication.translate("QtUi", u"By Type:", None))

#if QT_CONFIG(tooltip)
        self.cmb002.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p>Select objects in the scene based on their type.&lt;br&gt;&lt;br&gt;</p><p>&lt;b&gt;Options:&lt;/b&gt;&lt;br&gt;</p><p>&lt;b&gt;Replace:&lt;/b&gt; Replace the current selection with the new selection.&lt;br&gt;</p><p>&lt;b&gt;Add:&lt;/b&gt; Add the new selection to the current selection.&lt;br&gt;</p><p>&lt;b&gt;Remove:&lt;/b&gt; Remove the new selection from the current selection.&lt;br&gt;&lt;br&gt;</p><p>When the &quot;Replace&quot; option is selected, the script uses the currently selected objects, or if none are selected, it lists all objects in the scene.&lt;br&gt;</p><p>When the &quot;Add&quot; or &quot;Remove&quot; option is selected, the script lists all objects in the scene, ignoring the current selection.</p><p><br/></p></body></html>", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.tb001.setToolTip(QCoreApplication.translate("QtUi", u"Select similar objects or components, depending on selection mode.", None))
#endif // QT_CONFIG(tooltip)
        self.tb001.setText(QCoreApplication.translate("QtUi", u"Similar", None))
#if QT_CONFIG(tooltip)
        self.tb002.setToolTip(QCoreApplication.translate("QtUi", u"Select Island: Select contiguous faces within a normal range", None))
#endif // QT_CONFIG(tooltip)
        self.tb002.setText(QCoreApplication.translate("QtUi", u"Island", None))
#if QT_CONFIG(tooltip)
        self.tb000.setToolTip(QCoreApplication.translate("QtUi", u"Select Nth: Select 2 components", None))
#endif // QT_CONFIG(tooltip)
        self.tb000.setText(QCoreApplication.translate("QtUi", u"Nth Edge", None))
#if QT_CONFIG(tooltip)
        self.tb003.setToolTip(QCoreApplication.translate("QtUi", u"Select edges having normals between the given high and low angles.", None))
#endif // QT_CONFIG(tooltip)
        self.tb003.setText(QCoreApplication.translate("QtUi", u"By Angle", None))
#if QT_CONFIG(tooltip)
        self.groupBox_8.setToolTip("")
#endif // QT_CONFIG(tooltip)
        self.groupBox_8.setTitle(QCoreApplication.translate("QtUi", u"Constraints", None))
        self.cmb005.setItemText(0, QCoreApplication.translate("QtUi", u"Off", None))

#if QT_CONFIG(tooltip)
        self.cmb005.setToolTip(QCoreApplication.translate("QtUi", u"Selection contraints.", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_6.setTitle(QCoreApplication.translate("QtUi", u"Convert", None))
        self.cmb003.setItemText(0, QCoreApplication.translate("QtUi", u"Convert To:", None))

#if QT_CONFIG(tooltip)
        self.cmb003.setToolTip(QCoreApplication.translate("QtUi", u"Convert selection to type", None))
#endif // QT_CONFIG(tooltip)
        self.groupBox_7.setTitle(QCoreApplication.translate("QtUi", u"Re-Order Selectiion", None))
        self.cmb001.setItemText(0, QCoreApplication.translate("QtUi", u"By:", None))

#if QT_CONFIG(tooltip)
        self.cmb001.setToolTip(QCoreApplication.translate("QtUi", u"Re-Order the current selection.", None))
#endif // QT_CONFIG(tooltip)
        pass
    # retranslateUi

