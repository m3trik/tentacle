# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'scene.ui'
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
from PySide6.QtWidgets import (QApplication, QComboBox, QGroupBox, QLineEdit,
    QMainWindow, QSizePolicy, QSpacerItem, QTabWidget,
    QVBoxLayout, QWidget)

from uitk.widgets.comboBox.ComboBox import ComboBox
from uitk.widgets.header.Header import Header

class Ui_QtUi(object):
    def setupUi(self, QtUi):
        if not QtUi.objectName():
            QtUi.setObjectName(u"QtUi")
        QtUi.setEnabled(True)
        QtUi.resize(200, 254)
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

        self.Project = QGroupBox(self.central_widget)
        self.Project.setObjectName(u"Project")
        self.verticalLayout_5 = QVBoxLayout(self.Project)
        self.verticalLayout_5.setSpacing(1)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.verticalLayout_5.setContentsMargins(0, 0, 0, 0)
        self.cmb001 = ComboBox(self.Project)
        self.cmb001.addItem("")
        self.cmb001.setObjectName(u"cmb001")
        self.cmb001.setMinimumSize(QSize(0, 20))
        self.cmb001.setMaximumSize(QSize(16777215, 20))
        self.cmb001.setMaxVisibleItems(30)
        self.cmb001.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb001.setFrame(False)

        self.verticalLayout_5.addWidget(self.cmb001)

        self.cmb006 = ComboBox(self.Project)
        self.cmb006.addItem("")
        self.cmb006.setObjectName(u"cmb006")
        self.cmb006.setMinimumSize(QSize(0, 20))
        self.cmb006.setMaximumSize(QSize(16777215, 20))
        self.cmb006.setMaxVisibleItems(40)
        self.cmb006.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb006.setFrame(False)

        self.verticalLayout_5.addWidget(self.cmb006)

        self.txt000 = QLineEdit(self.Project)
        self.txt000.setObjectName(u"txt000")

        self.verticalLayout_5.addWidget(self.txt000)

        self.cmb000 = ComboBox(self.Project)
        self.cmb000.addItem("")
        self.cmb000.setObjectName(u"cmb000")
        self.cmb000.setMinimumSize(QSize(0, 20))
        self.cmb000.setMaximumSize(QSize(16777215, 20))
        self.cmb000.setMaxVisibleItems(40)
        self.cmb000.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb000.setFrame(False)

        self.verticalLayout_5.addWidget(self.cmb000)


        self.verticalLayout.addWidget(self.Project)

        self.File = QGroupBox(self.central_widget)
        self.File.setObjectName(u"File")
        self.verticalLayout_3 = QVBoxLayout(self.File)
        self.verticalLayout_3.setSpacing(1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.cmb005 = ComboBox(self.File)
        self.cmb005.addItem("")
        self.cmb005.setObjectName(u"cmb005")
        self.cmb005.setMinimumSize(QSize(0, 20))
        self.cmb005.setMaximumSize(QSize(16777215, 20))
        self.cmb005.setMaxVisibleItems(30)
        self.cmb005.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.cmb005.setFrame(False)

        self.verticalLayout_3.addWidget(self.cmb005)

        self.cmb002 = ComboBox(self.File)
        self.cmb002.addItem("")
        self.cmb002.setObjectName(u"cmb002")
        self.cmb002.setMinimumSize(QSize(0, 20))
        self.cmb002.setMaximumSize(QSize(16777215, 20))
        self.cmb002.setMaxVisibleItems(30)
        self.cmb002.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        self.cmb002.setFrame(False)

        self.verticalLayout_3.addWidget(self.cmb002)


        self.verticalLayout.addWidget(self.File)

        self.Import_Export = QGroupBox(self.central_widget)
        self.Import_Export.setObjectName(u"Import_Export")
        self.verticalLayout_4 = QVBoxLayout(self.Import_Export)
        self.verticalLayout_4.setSpacing(1)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.cmb003 = ComboBox(self.Import_Export)
        self.cmb003.addItem("")
        self.cmb003.setObjectName(u"cmb003")
        self.cmb003.setMinimumSize(QSize(0, 20))
        self.cmb003.setMaximumSize(QSize(16777215, 20))
        self.cmb003.setMaxVisibleItems(30)
        self.cmb003.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        self.cmb003.setFrame(False)

        self.verticalLayout_4.addWidget(self.cmb003)

        self.cmb004 = ComboBox(self.Import_Export)
        self.cmb004.addItem("")
        self.cmb004.setObjectName(u"cmb004")
        self.cmb004.setMinimumSize(QSize(0, 20))
        self.cmb004.setMaximumSize(QSize(16777215, 20))
        self.cmb004.setMaxVisibleItems(30)
        self.cmb004.setSizeAdjustPolicy(QComboBox.AdjustToContentsOnFirstShow)
        self.cmb004.setFrame(False)

        self.verticalLayout_4.addWidget(self.cmb004)


        self.verticalLayout.addWidget(self.Import_Export)

        self.verticalSpacer = QSpacerItem(0, 10, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout.addItem(self.verticalSpacer)


        self.verticalLayout_2.addLayout(self.verticalLayout)

        QtUi.setCentralWidget(self.central_widget)

        self.retranslateUi(QtUi)

        QMetaObject.connectSlotsByName(QtUi)
    # setupUi

    def retranslateUi(self, QtUi):
        self.header.setText(QCoreApplication.translate("QtUi", u"SCENE", None))
        self.Project.setTitle(QCoreApplication.translate("QtUi", u"Project", None))
        self.cmb001.setItemText(0, QCoreApplication.translate("QtUi", u"Recent Projects:", None))

#if QT_CONFIG(tooltip)
        self.cmb001.setToolTip(QCoreApplication.translate("QtUi", u"Any recent workspaces will appear here.", None))
#endif // QT_CONFIG(tooltip)
        self.cmb006.setItemText(0, QCoreApplication.translate("QtUi", u"Project:", None))

#if QT_CONFIG(tooltip)
        self.cmb006.setToolTip(QCoreApplication.translate("QtUi", u"Open a workspace folder, or set a new workspace.", None))
#endif // QT_CONFIG(tooltip)
#if QT_CONFIG(tooltip)
        self.txt000.setToolTip(QCoreApplication.translate("QtUi", u"<html><head/><body><p><span style=\" font-weight:600;\">Filter the results of the 'Scenes' list.</span></p><p>    Each item can be a string or integer. Strings can include shell-style wildcards:</p><p>     - '*': Matches any sequence of characters (including none).</p><p>	startswith*<br/>	*endswith</p><p>	*contains*</p><p>     - '?': Matches any single character.</p><p>     - '[seq]': Matches any character in 'seq'.</p><p>     - '[!seq]': Matches any character not in 'seq'.</p></body></html>", None))
#endif // QT_CONFIG(tooltip)
        self.txt000.setPlaceholderText(QCoreApplication.translate("QtUi", u"Filter Scenes:", None))
        self.cmb000.setItemText(0, QCoreApplication.translate("QtUi", u"Scenes:", None))

#if QT_CONFIG(tooltip)
        self.cmb000.setToolTip(QCoreApplication.translate("QtUi", u"Open a scene file from the current workspace directory.", None))
#endif // QT_CONFIG(tooltip)
        self.File.setTitle(QCoreApplication.translate("QtUi", u"File", None))
        self.cmb005.setItemText(0, QCoreApplication.translate("QtUi", u"Recent Files:", None))

#if QT_CONFIG(tooltip)
        self.cmb005.setToolTip(QCoreApplication.translate("QtUi", u"Any recent scenes will appear here.", None))
#endif // QT_CONFIG(tooltip)
        self.cmb002.setItemText(0, QCoreApplication.translate("QtUi", u"Recent Autosave:", None))

#if QT_CONFIG(tooltip)
        self.cmb002.setToolTip(QCoreApplication.translate("QtUi", u"Any recent autosaves will appear here.", None))
#endif // QT_CONFIG(tooltip)
        self.Import_Export.setTitle(QCoreApplication.translate("QtUi", u"Import/Export", None))
        self.cmb003.setItemText(0, QCoreApplication.translate("QtUi", u"Import:", None))

        self.cmb004.setItemText(0, QCoreApplication.translate("QtUi", u"Export:", None))

        pass
    # retranslateUi

