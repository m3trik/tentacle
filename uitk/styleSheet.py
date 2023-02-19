# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore

from pythontk.Iter import makeList


class StyleSheet(QtCore.QObject):
	'''# css commenting:
		/* multi-line */

	# setting a property:
		app.setStyleSheet("QLineEdit#name[prop=true] {background-color:transparent;}") #does't effect the lineEdit with objectName 'name' if that buttons property 'styleSheet' is false (c++ lowercase). 
		widget.setProperty('prop', True)

	# gradients:
		background-color: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1, stop: 0 #E0E0E0, stop: 1 #FFFFFF);

	# Set multiple widgets:
		QComboBox:!editable, QComboBox::drop-down:editable { ... }

	# Set the style for a specific widget:
		QWidget#mainWindow ('#' syntax, followed by the widget's objectName)
	'''
	_colorValues = {
			'standard': {
				'BACKGROUND'		: 'rgb(100,100,100)',
				'BACKGROUND_ALPHA'	: 'rgba(100,100,100,{ALPHA})',
				'PRESSED'			: 'rgb(127,127,127)',
				'HIGHLIGHT'			: 'yellow',
				'HOVER'				: 'rgb(82,133,166)',
				'TEXT'				: 'white',
				'TEXT_CHECKED'		: 'black',
				'TEXT_DISABLED'		: 'gray',
				'TEXT_HOVER'		: 'white',
				'TEXT_BACKGROUND'	: 'rgb(50,50,50)',
				'BORDER'			: 'rgb(50,50,50)',
			},

			'dark': {
				'BACKGROUND'		: 'rgb(60,60,60)',
				'BACKGROUND_ALPHA'	: 'rgba(60,60,60,{ALPHA})',
				'PRESSED'			: 'rgb(127,127,127)',
				'HIGHLIGHT'			: 'yellow',
				'HOVER'				: 'rgb(82,133,166)',
				'TEXT'				: 'rgb(185,185,185)',
				'TEXT_CHECKED'		: 'black',
				'TEXT_DISABLED'		: 'rgba(185,185,185,50)',
				'TEXT_HOVER'		: 'white',
				'TEXT_BACKGROUND'	: 'rgb(50,50,50)',
				'BORDER'			: 'rgb(40,40,40)',
			}
		}

	_styleSheets = {

		'QMainWindow': '''
			QMainWindow {
				background-color: {BACKGROUND_ALPHA};
			}
			''',

		'QWidget': '''
			QWidget {
				background-color: transparent;
			}
			QWidget#hud_widget {
				background-color: {BACKGROUND_ALPHA};
			}
			QWidget::item:selected {
				background-color: {HOVER};
			}
			''',

		'QStackedWidget': '''
			QStackedWidget {
				background-color: {BACKGROUND_COLOR};
			}
			QStackedWidget QFrame {
				background-color: {FRAME_BACKGROUND_COLOR};
			}
			QStackedWidget QFrame QLabel {
				color: {TEXT};
				font-size: 8;
			}

			QStackedWidget QPushButton {
				background-color: {BACKGROUND};
				color: {TEXT};
				font-size: 8;
				border: 1px solid {BORDER};
			}
			''',

		'QPushButton': '''
			QPushButton {
				border-style: outset;
				border-radius: 1px;
				border: 1px solid {BORDER};
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
				background-color: {BACKGROUND};
				color: {TEXT};
			}
			QPushButton::enabled {
				color: {TEXT};
			}
			QPushButton::disabled {
				color: {TEXT_DISABLED};
			}
			QPushButton::checked {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QPushButton::hover {
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QPushButton::checked::hover {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QPushButton::pressed {
				background-color: {PRESSED};
				color: {TEXT};
			}
			QPushButton:flat {
				border: none; /* no border for a flat push button */
			}
			QPushButton:default {
				border-color: navy; /* make the default button prominent */
			} 
			''',

		'QToolButton': '''
			QToolButton {
				border-style: outset;
				border-radius: 1px;
				border: 1px solid {BORDER};
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
				background-color: {BACKGROUND}; /* The background will not appear unless you set the border property. */
				color: {TEXT};
			}
			QToolButton::enabled {
				color: {TEXT};
			}
			QToolButton::disabled {
				color: {TEXT_DISABLED};
			}
			QToolButton::hover {   
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QToolButton::checked {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QToolButton::checked::hover {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QToolButton::pressed, QToolButton::menu-button:pressed {   
				background-color: {PRESSED};
				color: {TEXT};
			}
			QToolButton[popupMode="1"] { /* only for MenuButtonPopup */
				padding-right: 2px; /* make way for the popup button */
			}
			QToolButton:open { /* when the button has its menu open */
				background-color: dark gray;
			}
			/* popupMode set to DelayedPopup or InstantPopup */
			QToolButton::menu-indicator {
				image: none;
				subcontrol-origin: padding;
				subcontrol-position: bottom right;
				padding: 0px 5px 5px 0px; /* top, right, bottom, left */
			}
			QToolButton::menu-indicator:pressed, QToolButton::menu-indicator:open {
				position: relative;
				top: 2px; left: 2px; /* shift the arrow by 2 px */
			}
			/* When the Button displays arrows, the ::up-arrow, ::down-arrow, ::left-arrow and ::right-arrow subcontrols are used. */
			QToolButton::down-arrow, QToolButton::up-arrow, QToolButton::left-arrow, QToolButton::right-arrow {
				image: none;
				padding: 0px 15px 0px 0px; /* top, right, bottom, left */
			}
			QToolButton::down-arrow:hover, QToolButton::up-arrow:hover, QToolButton::left-arrow:hover, QToolButton::right-arrow:hover {
				background-color: {HOVER};
				padding: 0px 5px 0px 0px; /* top, right, bottom, left */
			}
			/* the subcontrols below are used only in the MenuButtonPopup mode */
			QToolButton::menu-button {
				border: 1px solid {TEXT};
				margin: 4px 2px 4px 0px; /* top, right, bottom, left */
			}
			QToolButton::menu-button::enabled {
				color: {TEXT};
			}
			QToolButton::menu-button::disabled {
				color: {TEXT_DISABLED};
				border: 1px solid transparent;
			}
			QToolButton::menu-button:hover{
				border: 1px solid {TEXT_HOVER};
			}
			QToolButton::menu-button:pressed {
				background-color: transparent;
				border: 1px solid transparent;
			}
			QToolButton::menu-arrow {
				image: none;
			}
			QToolButton::menu-arrow:open {

			} 
			''',

		'QAbstractButton': '''
			QAbstractButton:hover {
				background: {BACKGROUND};
			}
			QAbstractButton:pressed {
				background: {PRESSED};
			} 
			''',

		'QComboBox': '''
			QComboBox {
				background: {BACKGROUND};
				color: {TEXT};
				border: 1px solid {BORDER};
				padding: 1px 1px 1px 1px; /* top, right, bottom, left */
				border-radius: 1px;
				min-width: 0em;
			}
			QComboBox::hover {
				background: {HOVER};
				color: {TEXT_HOVER};
				border: 1px solid {BORDER};
			}
			QComboBox::open {
				background: {BACKGROUND};
				color: {TEXT};
				border: 1px solid {BORDER};
				selection-background-color: {HOVER};
				selection-color: {TEXT_CHECKED};
			}
			QComboBox:on { /* shift the text when the popup opens */
				padding-top: 3px;
				padding-left: 1px;
			}
			QComboBox::down-arrow {
				width: 0px;
				height: 0px;
				background: {BACKGROUND};
				border: 0px solid {BORDER};
				image: url(path/to/down_arrow.png);
			}
			QComboBox::drop-down {
				border: 0px solid {BORDER};
				background: {BACKGROUND};
				subcontrol-origin: padding;
				subcontrol-position: top right;
				width: 0px;
				height: 0px;

				border-left-width: 1px;
				border-left-color: {TEXT_CHECKED};
				border-left-style: solid; /* just a single line */
				border-top-right-radius: 1px; /* same radius as the QComboBox */
				border-bottom-right-radius: 1px;
			}
			QComboBox QAbstractItemView {
				background: {BACKGROUND};
				color: {TEXT};
				border: 1px solid {BORDER};
				min-width: 150px;
			}
			QComboBox QListView {
				background: {BACKGROUND};
				color: {TEXT};
				border: 1px solid {BORDER};
			}
			QComboBox QListView::item {
				background: {BACKGROUND};
				color: {TEXT};
			}
			QComboBox QListView::item:selected {
				background: {HOVER};
				color: {TEXT_CHECKED};
			}
			QComboBox QListView::item:hover {
				background: {HOVER};
				color: {TEXT_HOVER};
			}
			''',

		'QSpinBox': '''
			QSpinBox {
			background: {BACKGROUND};
			color: {TEXT};
			border: 1px solid {BORDER};
			}
			QSpinBox::disabled {
				color: {TEXT_DISABLED};
			}
			QSpinBox::hover {
				background-color: {BACKGROUND};
				color: {TEXT_HOVER};
				border: 1px solid {BORDER};
			} 
			''',

		'QDoubleSpinBox': '''
			QDoubleSpinBox {
			background: {BACKGROUND};
			color: {TEXT};
			border: 1px solid {BORDER};
			}
			QDoubleSpinBox::disabled {
				color: {TEXT_DISABLED};
			}
			QDoubleSpinBox::hover {
				background-color: {BACKGROUND};
				color: {TEXT_HOVER};
				border: 1px solid {BORDER};
			} 
			''',

		'QAbstractSpinBox': '''
			QScrollBar:left-arrow, QScrollBar::right-arrow, QScrollBar::up-arrow, QScrollBar::down-arrow {
				border: 1px solid {PRESSED};
				width: 3px;
				height: 3px;
			}
			QAbstractSpinBox::up-arrow, QAbstractSpinBox::down-arrow {
				width: 3px;
				height: 3px;
				border: 1px solid {PRESSED};
			}
			QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {
				border: 1px solid {PRESSED};
				background: {BACKGROUND};
				subcontrol-origin: border;
			} 
			''',

		'QCheckBox': '''
			QCheckBox {
				border-style: outset;
				border-radius: 1px;
				border: 1px solid {BORDER};
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
				background-color: {BACKGROUND};
				color: {TEXT};
				spacing: 5px;
			}
			QCheckBox::hover {
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QCheckBox::hover:checked {
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QCheckBox::enabled {
				color: {TEXT};
			}
			QCheckBox::disabled {
				color: {TEXT_DISABLED};
			}
			QCheckBox::disabled:checked {
				background-color: {BACKGROUND};
				color: {TEXT_DISABLED};
			}
			QCheckBox::checked {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QCheckBox::checked:hover {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QCheckBox::indeterminate {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QCheckBox::indeterminate:hover {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QCheckBox::indicator {
				width: 0px;
				height: 0px;
				border: 0px solid transparent;
			}
			QCheckBox::indicator::unchecked {
				image: none;
			}
			QCheckBox::indicator:unchecked:hover {
				image: none;
			}
			QCheckBox::indicator:unchecked:pressed {
				image: none;
			}
			QCheckBox::indicator::checked {
				image: none;
			}
			QCheckBox::indicator:checked:hover {
				image: none;
			} 
			QCheckBox::indicator:checked:pressed {
				image: none;
			}
			QCheckBox::indicator:indeterminate:checked {
				image: none;
			}
			QCheckBox::indicator:indeterminate:hover {
				image: none;
			}
			QCheckBox::indicator:indeterminate:pressed {
				image: none;
			}
			''',

		'QRadioButton': '''
			QRadioButton {
				border-style: outset;
				border-radius: 1px;
				border: 1px solid {BORDER};
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
				background-color: {BACKGROUND};
				color: {TEXT};
			}
			QRadioButton::hover {
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QRadioButton::hover:checked {
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QRadioButton::enabled {
				color: {TEXT};
			}
			QRadioButton::disabled {
				color: {TEXT_DISABLED};
			}
			QRadioButton::checked {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QRadioButton::checked:hover {
				background-color: {HOVER};
				color: {TEXT_CHECKED};
			}
			QRadioButton::indicator {
				width: 0px;
				height: 0px;
				border: 0px solid transparent;
			}
			QRadioButton::indicator::unchecked {
				image: none;
			}
			QRadioButton::indicator:unchecked:hover {
				image: none;
			}
			QRadioButton::indicator::checked {
				image: none;
			}
			QRadioButton::indicator:checked:hover {
				image: none;
			} 
			''',

		'QAbstractItemView': '''
			QAbstractItemView {
				show-decoration-selected: 1;
				selection-background-color: {HOVER};
				selection-color: {BACKGROUND};
				alternate-background-color: {BACKGROUND};
				min-width: 200px;
			} 
			''',

		'QHeaderView': '''
			QHeaderView {
				border: 1px solid {PRESSED};
			}
			QHeaderView::section {
				background: {PRESSED};
				border: 1px solid {PRESSED};
				padding: 1px;
			}
			QHeaderView::section:selected, QHeaderView::section::checked {
				background: {BACKGROUND};
			} 
			''',

		'QTableView': '''
			QTableView {
				gridline-color: {PRESSED};
			} 
			''',

		'QLineEdit': '''
			QLineEdit {
				border: 1px solid {BORDER};
				border-radius: 1px;
				padding: 0 8px;
				background: {BACKGROUND};
				color: {TEXT};
				selection-background-color: {HOVER};
				selection-color: {TEXT};
			}
			QLineEdit::disabled {
				color: {BACKGROUND};
			}
			QLineEdit::enabled {
				color: {TEXT};
			}
			QLineEdit:read-only {
				background: {BACKGROUND};
			} 
			''',

		'QTextEdit': '''
			QTextEdit {
				border: 1px solid {BORDER};
				background-color: {BACKGROUND};
				color: {TEXT};
				selection-background-color: {HOVER};
				selection-color: {TEXT};
				background-attachment: fixed; /* fixed, scroll */
			}
			QTextEdit#hud_text {
				border: 0px solid transparent;
				background-color: transparent;
				color: white;
				selection-background-color: {TEXT_BACKGROUND};
				selection-color: white;
			}
			''',

		'QPlainTextEdit': '''
			QPlainTextEdit {
				
			} 
			''',

		'QListView': '''
			QListView {
				background-color: {BACKGROUND};
				color: {TEXT};
				alternate-background-color: {BACKGROUND};
				background-attachment: fixed; /* fixed, scroll */
			}
			QListView::item:alternate {
				background: {BACKGROUND};
			}
			QListView::item:selected {
				border: 1px solid {HOVER};
			}
			QListView::item:selected:!active {
				background: {HOVER};
				color: {TEXT};
			}
			QListView::item:selected:active {
				background: {HOVER};
				color: {TEXT};
			}
			QListView::item:hover {
				background: {HOVER};
				color: {TEXT_HOVER};
			} 
			''',

		'QListWidget': '''
			QListWidget {
				background-color: {BACKGROUND};
				color: {TEXT};
				alternate-background-color: {BACKGROUND};
				background-attachment: fixed; /* fixed, scroll */
			}
			QListWidget::item:alternate {
				background: {BACKGROUND};
			}
			QListWidget::item:selected {
				border: 1px solid {HOVER};
			}
			QListWidget::item:selected:!active {
				background: {HOVER};
				color: {TEXT};
			}
			QListWidget::item:selected:active {
				background: {HOVER};
				color: {TEXT};
			}
			QListWidget::item:hover {
				background: {HOVER};
				color: {TEXT_HOVER};
			} 
			''',

		'QTreeWidget': '''
			QTreeWidget {
				background-color: transparent;
				border:none;
			}
			QTreeWidget::item {
				height: 20px;
			}
			QTreeWidget::item:enabled {
				color: {TEXT};
			}
			QTreeWidget::item:disabled {
				color: {TEXT_DISABLED};
			}
			QTreeView::item:hover {
				background: {HOVER};
				color: {TEXT_HOVER};
			}
			QTreeView::item:selected {
				background-color: none;
			} 
			''',

		'QToolBox': '''
			QToolBox {
				background-color: {BACKGROUND};
				color: {TEXT};
				alternate-background-color: {BACKGROUND};
				background-attachment: fixed; /* fixed, scroll */
				icon-size: 0px;
			}
			QToolBox::QScrollArea:QWidget:QWidget {
				background: transparent;
			}
			QToolBox::QToolBoxButton {
				image: url(:/none);
			}
			QToolBox::QAbstractButton {
				background-image: url(:/none);
				image: url(:/none);
			}
			QToolBox::tab {
				background: {BACKGROUND};
				color: {TEXT};
				stop: 0.0 transparent, stop: 0.0 transparent,
				stop: 0.0 transparent, stop: 0.0 transparent;
				border-radius: 1px;
			}
			QToolBox::tab:selected {
				/*font: italic;*/ /* italicize selected tabs */
				color: {TEXT};
			} 
			''',

		'QAbstractSpinBox': '''
			QAbstractSpinBox {
				padding-right: 0px;
			} 
			''',

		'QSlider': '''
			QSlider {
				border: 1px solid black;
				background: {BACKGROUND};
			}
			QSlider::groove:horizontal {
				height: 18px;
				margin: 0px 0px 0px 0px;
				background: {BACKGROUND};
			}
			QSlider::groove:vertical {
				width: 0px;
				margin: 0px 0px 0px 0px;
				background: {BACKGROUND};
			}
			QSlider::handle {
				width: 10px;
				height: 15px;
				border: 1px solid black;
				background: gray;
				margin: -1px 0px -1px 0px;
				border-radius: 1px;
			}
			QSlider::handle:hover {
				background: darkgray;
			}
			QSlider::add-page:vertical, QSlider::sub-page:horizontal {
				background: {HOVER};
			}
			QSlider::sub-page:vertical, QSlider::add-page:horizontal {
				background: {BACKGROUND};
			}
			QSlider::tickmark {
				width: 5px;
				height: 5px;
				margin: 0px -3px 0px 0px;
				border-radius: 2.5px;
				background: black;
			}
			QSlider::tickmark:not(sub-page) {
				width: 10px;
				height: 10px;
				margin: 0px -5px 0px 0px;
				border-radius: 5px;
				background: black;
			}
			QSlider::tickmark:sub-page {
				width: 5px;
				height: 5px;
				margin: 0px -3px 0px 0px;
				border-radius: 2.5px;
				background: lightgray;
			}
			''',

		'QScrollBar': '''
			QScrollBar {
				border: 1px solid transparent;
				background: {BACKGROUND};
			}
			QScrollBar:horizontal {
				height: 15px;
				margin: 0px 0px 0px 32px; /* top, right, bottom, left */
			}
			QScrollBar:vertical {
				width: 15px;
				margin: 32px 0px 0px 0px; /* top, right, bottom, left */
			}
			QScrollBar::handle {
				background: {PRESSED};
				border: 1px solid transparent;
			}
			QScrollBar::handle:horizontal {
				border-width: 0px 1px 0px 1px;
			}
			QScrollBar::handle:vertical {
				border-width: 1px 0px 1px 0px;
			}
			QScrollBar::handle:horizontal {
				min-width: 20px;
			}
			QScrollBar::handle:vertical {
				min-height: 20px;
			}
			QScrollBar::add-line, QScrollBar::sub-line {
				background:{BACKGROUND};
				border: 1px solid {PRESSED};
				subcontrol-origin: margin;
			}
			QScrollBar::add-line {
				position: absolute;
			}
			QScrollBar::add-line:horizontal {
				width: 15px;
				subcontrol-position: left;
				left: 15px;
			}
			QScrollBar::add-line:vertical {
				height: 15px;
				subcontrol-position: top;
				top: 15px;
			}
			QScrollBar::sub-line:horizontal {
				width: 15px;
				subcontrol-position: top left;
			}

			QScrollBar::sub-line:vertical {
				height: 15px;
				subcontrol-position: top;
			}
			QScrollBar::add-page, QScrollBar::sub-page {
				background: none;
			} 
			''',

		'QGroupBox': '''
			QGroupBox {
				border: 2px transparent;
				border-radius: 1px;
				margin: 10px 0px 0px 0px; /* top, right, bottom, left */ /* leave space at the top for the title */
				background-color: rgba(75,75,75,125);
			}
			QGroupBox::title {
				top: -12px;
				left: 2px;

				subcontrol-position: top left; /* position at the top center */
				background-color: transparent;
				color: {TEXT};
			} 
			''',

		'QTabBar': '''
			QTabBar {
				margin: 0px 0px 0px 2px; /* top, right, bottom, left */
			}
			QTabBar::tab {
				border-radius: 1px;
				padding-top: 1px;
				margin-top: 1px;
			}
			QTabBar::tab:selected {
				background: {BACKGROUND};
			} 
			''',

		'QMenu': '''
			QMenu {
				background-color: transparent;
				border: 1px solid {BORDER};
				margin: 0px; /* spacing around the menu */
			}
			QMenu::item {
				padding: 8px 8px 8px 8px; /* top, right, bottom, left */
				border: 1px solid transparent; /* reserve space for selection border */
			}
			QMenu::item:selected {
				border-color: {HOVER};
				background: {BACKGROUND};
			}
			QMenu::icon:checked { /* appearance of a 'checked' icon */
				background: gray;
				border: 1px inset gray;
				position: absolute;
				top: 1px;
				right: 1px;
				bottom: 1px;
				left: 1px;
			}
			QMenu::separator {
				height: 2px;
				background: {BACKGROUND};
				margin: 0px 5px 0px 10px; /* top, right, bottom, left */
			}
			QMenu::indicator {
				width: 13px;
				height: 13px;
			} 
			''',

		'QMenuBar': '''
			QMenuBar {
				background-color: {BACKGROUND};
				spacing: 1px; /* spacing between menu bar items */
			}
			QMenuBar::item {
				padding: 1px 4px;
				background: transparent;
				border-radius: 1px;
			}
			QMenuBar::item:selected { /* when selected using mouse or keyboard */
				background: {HOVER};
			}
			QMenuBar::item:pressed {
				background: {TEXT_HOVER};
			}
			''',

		'QLabel': '''
			QLabel {
				background-color: {BACKGROUND};
				color: {TEXT};
				border: 1px solid {BORDER};
				border-radius: 1px;
				margin: 0px 0px 0px 0px; /* top, right, bottom, left */
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
			}
			QLabel::hover {   
				border: 1px solid {BORDER};
				background-color: {HOVER};
				color: {TEXT_HOVER};
			}
			QLabel::enabled {
				color: {TEXT};
			}
			QLabel::disabled {
				color: {TEXT_DISABLED};
			} 
			''',

		'QToolTip': '''
			QToolTip {
				background-color: {BACKGROUND};
				color: {TEXT};
				border: 0px solid transparent;
			} 
			''',

		'QProgressBar': '''
			QProgressBar {
				border: 0px solid black;
				border-radius: 5px;
				text-align: center;
				margin: 0px 0px 0px 0px; /* top, right, bottom, left */
			}
			QProgressBar::chunk {
				width: 1px;
				margin: 0px;
				background-color: {HOVER};
			} 
			''',

		'QFrame': '''
			QFrame {
				border: 0px solid black;
				border-radius: 1px;
				padding: 2px;
				background-image: none;
			} 
			''',

		'QSplitter': '''
			QSplitter::handle {
				image: url(images/splitter.png);
			}
			QSplitter::handle:horizontal {
				width: 2px;
			}
			QSplitter::handle:vertical {
				height: 2px;
			}
			QSplitter::handle:pressed {
				url(images/splitter_pressed.png);
			}
			''',

		'QSplitterHandle': '''
			QSplitter::handle:horizontal {
				border-left: 1px solid lightGray;
			}
			QSplitter::handle:vertical {
				border-bottom: 1px solid lightGray;
			}
			''',

		'QTabWidget': '''
			QTabWidget {
				
			} 
			''',

		'QRubberBand': '''
			QRubberBand {
				color: 0px solid gray;
			}
			''',

		'QVBoxLayout': '''
			'QVBoxLayout' {

			}
			''',

		'QHBoxLayout': '''
			'QHBoxLayout' {

			}
			''',

		'QGridLayout': '''
			'QGridLayout' {

			}
			''',
		}

	@classmethod
	def getColorValues(cls, style='standard', **kwargs):
		'''Return the colorValues dict with any of the bracketed placeholders 
		replaced by the value of any given kwargs of the same name.

		:Parameters:
			style (str): The color value set to use. valid values are: 'standard', 'dark'
			**kwargs () = Keyword arguments matching the string of any bracketed placeholders.
				case insensitive.  ex. alpha=255

		:Return:
			(dict) The color values with placeholder values. ex. {'BACKGROUND_ALPHA': 'rgba(100,100,100,75)', etc..
		'''
		return {k:v.format(**{k.upper():v for k, v in kwargs.items()})
				for k, v in cls._colorValues[style].items()}


	@classmethod
	def getStyleSheet(cls, widget_type=None, style='standard', alpha=255):
		'''Get the styleSheet for the given widget type.
		By default it will return all stylesheets as one multi-line css string.

		:Parameters:
			widget_type (str): The class name of the widget. ie. 'QLabel'
			style (str): The color value set to use. valid values are: 'standard', 'dark'

		:Return:
			(str) css styleSheet
		'''
		if widget_type==None:
			return ''.join(cls._styleSheets.values())

		try:
			css = cls._styleSheets[widget_type]

		except KeyError as error:
			print ('{} in getStyleSheet\n\t# KeyError: {}: {} #'.format(__file__, widget_type, error))
			return ''

		for k, v in cls.getColorValues(style=style, ALPHA=alpha).items():
			css = css.replace('{'+k.upper()+'}', v)

		return css


	@classmethod
	def setStyle(cls, widgets, ratio=6, style='standard', hideMenuButton=False, alpha=255):
		'''Set the styleSheet for the given widgets.
		Set the style for a specific widget by using the '#' syntax and the widget's objectName. ie. QWidget#mainWindow

		:Parameters:
			widgets (obj)(list): A widget or list of widgets.
			ratio (int): The ratio of widget size, text length in relation to the amount of padding applied.
			style (str): Color mode. ie. 'standard' or 'dark'
			hideMenuButton (boool) = Hide the menu button of a widget that has one.
			alpha (int): Set the background alpha transparency between 0 and 255.
		'''
		from uitk.switchboard import Switchboard

		for widget in makeList(widgets):
			widget_type = Switchboard.getDerivedType(widget, name=True)

			try:
				s = cls.getStyleSheet(widget_type, style=style, alpha=alpha)
			except KeyError as error: #given widget has no attribute 'styleSheet'.
				continue; #print (error)

			if hideMenuButton:
				s = s + cls.hideMenuButton(widget_type)

			try:
				length = len(widget.text()) if hasattr(widget, 'text') else len(str(widget.value())) #a 'NoneType' error will be thrown if the widget does not contain text.
				if widget.size().width() // length > ratio: #ratio of widget size, text length (using integer division).
					s = s + cls.adjustPadding(widget_type)
			except (AttributeError, ZeroDivisionError) as error:
				pass; # print (__name__, error, widget.text())

			if widget.styleSheet(): #if the widget has an existing style sheet, append.
				s = s+widget.styleSheet()
			widget.setStyleSheet(s)


	@staticmethod
	def adjustPadding(widget_type):
		'''Remove padding when the text length / widget width ratio is below a given amount.
		'''
		return '''
			{0} {{
				padding: 0px 0px 0px 0px;
			}}'''.format(widget_type)


	@staticmethod
	def hideMenuButton(widget_type):
		'''Set the menu button as transparent.
		'''
		return '''
			{0}::menu-button {{
				border: 1px solid transparent;
			}}

			{0}::menu-button::hover {{
				border: 1px solid transparent;
			}}'''.format(widget_type)










if __name__ == "__main__":
	pass

# else:
# 	styleSheet = StyleSheet()

#module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


'''
#qt styleSheet reference
http://doc.qt.io/qt-5/stylesheet-reference.html#qtabbar-widget



List of Pseudo-States:
:active				This state is set when the widget resides in an active window.
:adjoins-item		This state is set when the ::branch of a QTreeView is adjacent to an item.
:alternate			This state is set for every alternate row whe painting the row of a QAbstractItemView when QAbstractItemView::alternatingRowColors() is set to true.
:bottom				The item is positioned at the bottom. For example, a QTabBar that has its tabs positioned at the bottom.
:checked			The item is checked. For example, the checked state of QAbstractButton.
:closable			The items can be closed. For example, the QDockWidget has the QDockWidget::DockWidgetClosable feature turned on.
:closed				The item is in the closed state. For example, an non-expanded item in a QTreeView
:default			The item is the default. For example, a default QPushButton or a default action in a QMenu.
:disabled			The item is disabled.
:editable			The QComboBox is editable.
:edit-focus			The item has edit focus (See QStyle::State_HasEditFocus). This state is available only for Qt Extended applications.
:enabled			The item is enabled.
:exclusive			The item is part of an exclusive item group. For example, a menu item in a exclusive QActionGroup.
:first				The item is the first (in a list). For example, the first tab in a QTabBar.
:flat				The item is flat. For example, a flat QPushButton.
:floatable			The items can be floated. For example, the QDockWidget has the QDockWidget::DockWidgetFloatable feature turned on.
:focus				The item has input focus.
:has-children		The item has children. For example, an item in a QTreeView that has child items.
:has-siblings		The item has siblings. For example, an item in a QTreeView that siblings.
:horizontal			The item has horizontal orientation
:hover				The mouse is hovering over the item.
:indeterminate		The item has indeterminate state. For example, a QCheckBox or QRadioButton is partially checked.
:last				The item is the last (in a list). For example, the last tab in a QTabBar.
:left				The item is positioned at the left. For example, a QTabBar that has its tabs positioned at the left.
:maximized			The item is maximized. For example, a maximized QMdiSubWindow.
:middle				The item is in the middle (in a list). For example, a tab that is not in the beginning or the end in a QTabBar.
:minimized			The item is minimized. For example, a minimized QMdiSubWindow.
:movable			The item can be moved around. For example, the QDockWidget has the QDockWidget::DockWidgetMovable feature turned on.
:no-frame			The item has no frame. For example, a frameless QSpinBox or QLineEdit.
:non-exclusive		The item is part of a non-exclusive item group. For example, a menu item in a non-exclusive QActionGroup.
:off				For items that can be toggled, this applies to items in the "off" state.
:on					For items that can be toggled, this applies to widgets in the "on" state.
:only-one			The item is the only one (in a list). For example, a lone tab in a QTabBar.
:open				The item is in the open state. For example, an expanded item in a QTreeView, or a QComboBox or QPushButton with an open menu.
:next-selected		The next item (in a list) is selected. For example, the selected tab of a QTabBar is next to this item.
:pressed			The item is being pressed using the mouse.
:previous-selected	The previous item (in a list) is selected. For example, a tab in a QTabBar that is next to the selected tab.
:read-only			The item is marked read only or non-editable. For example, a read only QLineEdit or a non-editable QComboBox.
:right				The item is positioned at the right. For example, a QTabBar that has its tabs positioned at the right.
:selected			The item is selected. For example, the selected tab in a QTabBar or the selected item in a QMenu.
:top				The item is positioned at the top. For example, a QTabBar that has its tabs positioned at the top.
:unchecked			The item is unchecked.
:vertical			The item has vertical orientation.
:window				The widget is a window (i.e top level widget)


List of Sub-Controls:
::add-line			The button to add a line of a QScrollBar.
::add-page			The region between the handle (slider) and the add-line of a QScrollBar.
::branch			The branch indicator of a QTreeView.
::chunk				The progress chunk of a QProgressBar.
::close-button		The close button of a QDockWidget or tabs of QTabBar
::corner			The corner between two scrollbars in a QAbstractScrollArea
::down-arrow		The down arrow of a QComboBox, QHeaderView (sort indicator), QScrollBar or QSpinBox.
::down-button		The down button of a QScrollBar or a QSpinBox.
::drop-down			The drop-down button of a QComboBox.
::float-button		The float button of a QDockWidget
::groove			The groove of a QSlider.
::indicator			The indicator of a QAbstractItemView, a QCheckBox, a QRadioButton, a checkable QMenu item or a checkable QGroupBox.
::handle			The handle (slider) of a QScrollBar, a QSplitter, or a QSlider.
::icon				The icon of a QAbstractItemView or a QMenu.
::item				An item of a QAbstractItemView, a QMenuBar, a QMenu, or a QStatusBar.
::left-arrow		The left arrow of a QScrollBar.
::left-corner		The left corner of a QTabWidget. For example, this control can be used to control position the left corner widget in a QTabWidget.
::menu-arrow		The arrow of a QToolButton with a menu.
::menu-button		The menu button of a QToolButton.
::menu-indicator 	The menu indicator of a QPushButton.
::right-arrow		The right arrow of a QMenu or a QScrollBar.
::pane				The pane (frame) of a QTabWidget.
::right-corner		The right corner of a QTabWidget. For example, this control can be used to control the position the right corner widget in a QTabWidget.
::scroller			The scroller of a QMenu or QTabBar.
::section			The section of a QHeaderView.
::separator			The separator of a QMenu or in a QMainWindow.
::sub-line			The button to subtract a line of a QScrollBar.
::sub-page			The region between the handle (slider) and the sub-line of a QScrollBar.
::tab				The tab of a QTabBar or QToolBox.
::tab-bar			The tab bar of a QTabWidget. This subcontrol exists only to control the position of the QTabBar inside the QTabWidget. To style the tabs using the ::tab subcontrol.
::tear				The tear indicator of a QTabBar.
::tearoff			The tear-off indicator of a QMenu.
::text				The text of a QAbstractItemView.
::title				The title of a QGroupBox or a QDockWidget.
::up-arrow			The up arrow of a QHeaderView (sort indicator), QScrollBar or a QSpinBox.
::up-button			The up button of a QSpinBox.

List of Colors (Qt namespace (ie. Qt::red)):
white
black
red
darkRed
green
darkGreen
blue
darkBlue
cyan
darkCyan
magenta
darkMagenta
yellow
darkYellow
gray
darkGray
lightGray
color0 (zero pixel value) (transparent, i.e. background)
color1 (non-zero pixel value) (opaque, i.e. foreground)





image urls:
url(menu_indicator.png);
url(vline.png) 0;
url(handle.png);
url(close.png)
url(close-hover.png)
url(rightarrow.png);
url(leftarrow.png);
url(downarrow.png);
url(down_arrow.png);
url(up_arrow.png);
url(tear_indicator.png);
url(scrollbutton.png) 2;
url(branch-closed.png);
url(branch-open.png);
url(branch-more.png) 0;
url(branch-end.png) 0;
url(branch-open.png);
url(images/splitter.png);
url(images/splitter_pressed.png);
url(:/images/up_arrow.png);
url(:/images/up_arrow_disabled.png);
url(:/images/down_arrow.png);
url(:/images/down_arrow_disabled.png);
url(:/images/spindown.png) 1;
url(:/images/spindown_hover.png) 1;
url(:/images/spindown_pressed.png) 1;
url(:/images/sizegrip.png);
url(:/images/frame.png) 4;
url(:/images/spinup.png) 1;
url(:/images/spinup_hover.png) 1;
url(:/images/spinup_pressed.png) 1;
url(:/images/checkbox_unchecked.png);
url(:/images/checkbox_unchecked_hover.png);
url(:/images/checkbox_checked.png);
url(:/images/checkbox_checked_hover.png);
url(:/images/radiobutton_unchecked.png);
url(:/images/radiobutton_unchecked_hover.png);
url(:/images/radiobutton_checked.png);
url(:/images/radiobutton_checked_hover.png);
url(:/images/checkbox_indeterminate_hover.png);
url(:/images/checkbox_indeterminate_pressed.png);



'''

# min-width: 80px;

# QComboBox:editable {
# 	background: {BACKGROUND};
# }

# QComboBox:!editable, QComboBox::drop-down:editable {
# 	background: {BACKGROUND};
# }

# /* QComboBox gets the "on" state when the popup is open */
# QComboBox:!editable:on, QComboBox::drop-down:editable:on {
# 	background: {BACKGROUND};
# }
		
# background-color: #ABABAB; /* sets background of the menu */
# border: 1px solid black;

# /* sets background of menu item. set this to something non-transparent
# if you want menu color and menu item color to be different */
# background-color: transparent;

# QMenu::item:selected { /* when user selects item using mouse or keyboard */
#     background-color: #654321;
# For a more advanced customization, use a style sheet as follows:

# QMenu {
#     background-color: white;
#     margin: 2px; /* some spacing around the menu */

# QMenu::item {
#     padding: 2px 25px 2px 20px;
#     border: 1px solid transparent; /* reserve space for selection border */

# QMenu::item:selected {
#     border-color: darkblue;
#     background: rgba(100, 100, 100, 150);
# }

# QMenu::icon:checked { /* appearance of a 'checked' icon */
#     background: gray;
#     border: 1px inset gray;
#     position: absolute;
#     top: 1px;
#     right: 1px;
#     bottom: 1px;
#     left: 1px;

# QPushButton {
# 	background:rgba(127,127,127,2);
# 	background-color: red;
# 	color: white;
# 	border-width: 2px;
# 	border-radius: 10px;
# 	border-color: beige;
# 	border-style: outset;
# 	font: bold 14px;
# 	min-width: 10em;
# 	padding: 5px;

# QPushButton:hover {   
# 	border: 1px solid black;
# 	border-radius: 5px;   
# 	background-color:#66c0ff;

# QPushButton:pressed {
# 	background-color: rgb(224, 0, 0);
# 	border-style: inset;

# QPushButton:enabled {
# 	color: red

# QComboBox {
# 	image: url(:/none);}

# QComboBox::drop-down {
# 	border-width: 0px; 
# 	color: transparent

# QComboBox::down-arrow {
# 	border: 0px solid transparent; 
# 	border-width: 0px; left: 0px; top: 0px; width: 0px; height: 0px; 
# 	background-color: transparent; 
# 	color: transparent; 
# 	image: url(:/none);

# QTreeView {
#   alternate-background-color: rgba(35,35,35,255);
#   background: rgba(45,45,45,255);
# }

# QMenu {
# 	background-color: white; /* background-color: #ABABAB; sets background of the menu */
# 	margin: 2px; /* some spacing around the menu */
# 	border: 1px solid black;
# }

# QMenu::item {
# 	/* sets background of menu item. set this to something non-transparent
# 	if you want menu color and menu item color to be different */
# 	background-color: transparent;
# 	padding: 2px 25px 2px 20px;
# 	border: 1px solid transparent; /* reserve space for selection border */
# }

# QMenu::item:selected { 
# 	/* when user selects item using mouse or keyboard */
# 	background-color: #654321;
# 	border-color: darkblue;
# 	background: rgba(100, 100, 100, 150);
# }

# QMenu::icon:checked { /* appearance of a 'checked' icon */
# 	background: gray;
# 	border: 1px inset gray;
# 	position: absolute;
# 	top: 1px;
# 	right: 1px;
# 	bottom: 1px;
# 	left: 1px;
# }

# /* non-exclusive indicator = check box style indicator (see QActionGroup::setExclusive) */
# QMenu::indicator:non-exclusive:unchecked {
#     image: url(:/images/checkbox_unchecked.png);
# }

# QMenu::indicator:non-exclusive:unchecked:selected {
#     image: url(:/images/checkbox_unchecked_hover.png);
# }

# QMenu::indicator:non-exclusive:checked {
#     image: url(:/images/checkbox_checked.png);
# }

# QMenu::indicator:non-exclusive:checked:selected {
#     image: url(:/images/checkbox_checked_hover.png);
# }

# /* exclusive indicator = radio button style indicator (see QActionGroup::setExclusive) */
# QMenu::indicator:exclusive:unchecked {
#     image: url(:/images/radiobutton_unchecked.png);
# }

# QMenu::indicator:exclusive:unchecked:selected {
#     image: url(:/images/radiobutton_unchecked_hover.png);
# }

# QMenu::indicator:exclusive:checked {
#     image: url(:/images/radiobutton_checked.png);
# }

# QMenu::indicator:exclusive:checked:selected {
#     image: url(:/images/radiobutton_checked_hover.png);


# QToolButton:hover, QToolButton::menu-button:hover {
#     background: #787876;
# }

# QToolButton::checked{
#     background: #484846;
#     border: 1px solid #787876;
# }

# QToolButton:pressed, QToolButton::menu-button:pressed {
#     background: #787876;
# }

# QToolButton[popupMode="1"]{
# /* only for MenuButtonPopup */
#     padding-right: 30px;
#     background: red;
# }
# QToolButton[popupMode="2"]{
# /* only for OSC Server Status */
#     padding-right: 30px;
#     background: #484846;
# }
# QToolButton[popupMode="2"]:hover{
#     background: #787876;
# }
# QToolButton::down-arrow{
# } 
# /* the subcontrols below are used only in the MenuButtonPopup mode */
# QToolButton::menu-button{
# }

# QToolButton::menu-button:hover{
#     background: #787876;
# }
# QToolButton::menu-button:pressed{
# }
# QToolButton::menu-indicator{
#     bottom: 5px;
#     right: 5px;
# }