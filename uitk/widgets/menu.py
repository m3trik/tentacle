# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from uitk.widgets.attributes import Attributes


class Menu(QtWidgets.QMenu, Attributes):
	'''
	Parameters:
		menu_type (str): Menu style. valid parameters are: 'standard', 'context', 'form'
		title (str): Text displayed at the menu's header.
		padding (int): Area surrounding the menu.
		childHeight (int): The minimum height of any child widgets (excluding the 'Apply' button).
		preventHide (bool): Prevent the menu from hiding.
		position (str): Desired menu position. Valid values are: 
			'center', 'top', 'bottom', 'right', 'left', 'topLeft', 'topRight', 'bottomRight', 'bottomLeft' (Positions relative to parent (requires parent))
			'cursorPos' (Positions menu at the curson location)
	'''
	def __init__(self, parent=None, menu_type='standard', title='', padding=8, childHeight=16, position='cursorPos', preventHide=False, **kwargs):
		QtWidgets.QMenu.__init__(self, parent)

		self.menu_type = menu_type
		self.position = position
		self.preventHide = preventHide
		self.childHeight = childHeight

		self.setTitle(title)
		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint)
		self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		self.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)

		self.setStyleSheet('''
			QMenu {{
				background-color: rgba(50,50,50,175);
				padding: {0}px {0}px {0}px {0}px;
			}}

			QMenu::item {{
				background-color: transparent;
				spacing: 0px;
				border: 1px solid transparent;
				margin: 0px;
			}}'''.format(padding))

		self.setAttributes(**kwargs)

		self.childWidgets = set()
		self.layouts = {} #a container for any created layouts.
		self.toggleAllButton = self._addToggleAllButton()
		self.applyButton = self._addApplyButton()


	@property
	def draggable_header(self):
		'''Get the draggable header.
		'''
		try:
			return self._draggable_header

		except AttributeError as error:
			from uitk.widgets.pushButtonDraggable import PushButtonDraggable
			dh = PushButtonDraggable()

			wAction = QtWidgets.QWidgetAction(self)
			wAction.setDefaultWidget(dh)
			self.insertAction_(wAction)

			self._draggable_header = dh
			return self._draggable_header


	@property
	def containsMenuItems(self):
		'''Query whether any child objects have been added to the menu.
		'''
		return bool(self.childWidgets)


	def getChildWidgets(self, inc=[], exc=[]):
		'''Get a list of the menu's child widgets.

		:Parameters:
			inc (list): Include only widgets of the given type(s). ie. ['QCheckBox', 'QRadioButton']
			exc (list): Exclude widgets by type.
		:Return:
			(list) child widgets.
		'''
		if any((inc, exc)):
			return [w for w in self.childWidgets 
					if not w.__class__.__base__.__name__ in exc 
						and (w.__class__.__base__.__name__ in inc if inc 
					else w.__class__.__base__.__name__ not in inc)]
		else:
			return list(self.childWidgets)


	def setTitle(self, title=''):
		'''Set the menu's title to the given string.
		If no title is given, the fuction will attempt to use the menu parents text.

		Parameters:
			title (str): Text to apply to the menu's header.
		'''
		if not title:
			try:
				title = self.parent().text()
			except AttributeError as error:
				try:
					title = self.parent().currentText()
				except AttributeError as error:
					pass

		self.draggable_header.setText(title)
		super().setTitle(title)


	def getActionAtIndex(self, index):
		'''
		'''
		try:
			return self.actions()[1:][index] #slice the actions list to omit the header and any built-in hidden buttons (ie. 'apply', 'toggleAll').

		except IndexError as error:
			return None


	def insertAction_(self, wAction, index=-1):
		'''Extends insertAction to allow inserting by index.

		Parameters:
			wAction (obj): The widget action to insert.
			index (int): The desired index. (It appends the action if index is invalid)
		'''
		_wAction = self.getActionAtIndex(index)
		self.insertAction(_wAction, wAction) #insert before _wAction. It appends the action if before is nullptr or before is not a valid action for this widget


	def _addFormLayout(self, key='form', index=0):
		'''Create a two column form layout that can later be referenced using a key.

		Parameters:
			key (str)(int): The key identifier for the layout.
			index(int): The index corresponding to the vertical positioning of the layout.

		Return:
			(obj) QLayout.
		'''
		form = QtWidgets.QWidget(self)
		form.setStyleSheet('QWidget {background-color:rgb(50,50,50);}')

		layout = QtWidgets.QFormLayout(form)
		layout.setVerticalSpacing(0)

		wAction = QtWidgets.QWidgetAction(self)
		wAction.setDefaultWidget(form)
		self.insertAction_(wAction, index)

		self.layouts[key] = layout
		return self.layouts[key]


	def getFormLayout(self, key='form'):
		'''Get a two column form layout using a key.

		Parameters:
			key (str)(int): The key identifier for the layout.

		Return:
			(obj) QLayout.
		'''
		try:
			return self.layouts[key]

		except (KeyError, AttributeError) as error: #create a layout at the given key.
			self.layouts[key] = self._addFormLayout(key)
			return self.layouts[key]


	def _addVBoxLayout(self, key='vBox', index=0):
		'''Create a single column vertical layout that can later be referenced using a key.

		Parameters:
			key (str)(int): The key identifier for the layout.
			index(int): The index corresponding to the vertical positioning of the layout.

		Return:
			(obj) QLayout.
		'''
		form = QtWidgets.QWidget(self)
		form.setStyleSheet('QWidget {background-color:rgb(50,50,50);}')

		layout = QtWidgets.QVBoxLayout(form)
		layout.setContentsMargins(0,0,0,0)
		layout.setSpacing(0)

		wAction = QtWidgets.QWidgetAction(self)
		wAction.setDefaultWidget(form)
		self.insertAction_(wAction, index)

		self.layouts[key] = layout
		return self.layouts[key]


	def getVBoxLayout(self, key='vBox'):
		'''Get a vertical box layout using a key.

		Parameters:
			key (str)(int): The key identifier for the layout.

		Return:
			(obj) QLayout.
		'''
		try:
			return self.layouts[key]

		except (KeyError, AttributeError) as error: #create a layout at the given key.			
			self.layouts[key] = self._addVBoxLayout(key)
			return self.layouts[key]


	def _addApplyButton(self):
		'''Add a pushbutton that executes the parent object when pressed.
		The button is hidden by default.

		Return:
			(widget)
		'''
		if not self.parent():
			# print (f'# Error: {__file__} in _addApplyButton\n#\tOperation requires a parent widget.')
			return

		w = QtWidgets.QPushButton('Apply') #self.add('QPushButton', setText='Apply', setObjectName=self.parent().objectName(), setToolTip='Execute the command.')
		w.setObjectName('apply_button')
		w.setToolTip('Execute the command.')
		w.released.connect(lambda: self.parent().released.emit()) #trigger the released signal on the parent when the apply button is released.
		w.setMinimumSize(119, 26)

		layout = self.getVBoxLayout('menu_buttons') #get the 'menu_buttons' layout.
		layout.addWidget(w)
		w.hide()

		return w


	def _addToggleAllButton(self):
		'''Add a pushbutton that will uncheck any checkBoxes when pressed.
		The button is hidden by default.

		Return:
			(widget)
		'''
		w = QtWidgets.QPushButton('Uncheck All') #self.add('QPushButton', setText='Disable All', setObjectName='disableAll', setToolTip='Set all unchecked.')
		w.setObjectName('toggleAll')
		w.setToolTip('Toggle all checked|unchecked.')

		w.released.connect(lambda: [c.setChecked(not next(self.getChildWidgets(inc=['QCheckBox'])).checked()) for c in self.getChildWidgets(inc=['QCheckBox'])]) #trigger the released signal on the parent when the apply button is released.
		w.setMinimumSize(119, 26)

		layout = self.getVBoxLayout('menu_buttons') #get the 'menu_buttons' layout.
		layout.addWidget(w)
		w.hide()

		return w


	def add(self, widget, label='', checkableLabel=False, **kwargs):
		'''Add items to the QMenu.

		Parameters:
			widget (str)(obj): The widget to add. ie. 'QLabel', QtWidgets.QLabel, QtWidgets.QLabel()
			lable (str): Add a label. (which is actually a checkbox. by default it is not checkable)
			checkableLabel (bool): The label is checkable.

		additional kwargs:
			insertSeparator_ (bool): insert a separator before the widget.
			setLayoutDirection_ (str): ie. 'LeftToRight'
			setAlignment_ (str): ie. 'AlignVCenter'
			setButtonSymbols_ (str): ie. 'PlusMinus'
			setMinMax_ (str): Set the min, max, and step values with a string. ie. '1-100 step.1'

		Return:
			(obj) the added widget instance.

		ex.call:
		menu.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
		'''
		try: #get the widget
			w = getattr(QtWidgets, widget)() #ie. QtWidgets.QAction(self) object from string.
		except TypeError:
			w = widget() #if callable(widget) ie. QtWidgets.QAction(self) object.
		except:
			w = widget

		self.setAttributes(w, **kwargs) #set any additional given keyword args for the widget.

		type_ = w.__class__.__name__

		if type_=='QAction': #add action item.
			self.insertAction_(wAction)

		else:
			if self.menu_type=='form': #add widgets to the form layout.
				l = QtWidgets.QCheckBox()
				text = ''.join([(' '+i if i.isupper() else i) for i in label]).title() #format the attr name. ie. 'Subdivisions Height' from 'subdivisionsHeight'
				l.setText(text)
				l.setObjectName(label)
				if not checkableLabel:
					l.setCheckable(False)
					l.setStyleSheet('QCheckBox::hover {background-color: rgb(100,100,100); color: white;}')
				layout = self.getFormLayout() #get the default form layout.
				layout.addRow(l, w)
				self.childWidgets.add(l) #add the widget to the childWidgets list.

			else: #convert to action item, then add.
				layout = self.getVBoxLayout() #get the default vertical box layout.
				layout.addWidget(w)

			#set child height
			if w.sizeHint().width() > self.sizeHint().width():
				width = w.sizeHint().width() if w.sizeHint().width() >125 else 125
				w.setMinimumSize(width, w.sizeHint().height())
			try:
				l.setMinimumSize(l.sizeHint().width(), self.childHeight)
				# l.setMaximumSize(999, self.childHeight)
			except UnboundLocalError as error: #'l' does not exist. (not a form menu)
				pass

			self.childWidgets.add(w) #add the widget to the childWidgets list.

			setattr(self, w.objectName(), w) #add the widget's objectName as a QMenu attribute.

			self._addToContextMenuToolTip(w)

			if hasattr(w, 'released'): #Get the appropriate signal to connect to.
				w.released.connect(lambda w=w: self._setLastActiveChild(w)) #Connect the signal if one was found.
			elif hasattr(w, 'valueChanged'):
				w.valueChanged.connect(lambda value, w=w: self._setLastActiveChild(value, w))

		return w


	def _setLastActiveChild(self, widget, *args, **kwargs):
		'''Set the given widget as the last active.
		Maintains a list of the last 10 active child widgets.

		Parameters:
			widget = Widget to set as last active. The widget can later be returned by calling the 'lastActiveChild' method.
			*args **kwargs = Any additional arguments passed in by the wiget's signal during a connect call.

		Return:
			(obj) widget.
		'''
		# widget = args[-1]

		if not hasattr(self, '_lastActiveChild'):
			self._lastActiveChild = []

		del self._lastActiveChild[11:] #keep the list length at 10 elements.

		self._lastActiveChild.append(widget)
		# print(args, kwargs, widget.objectName() if hasattr(widget, 'objectName') else None)
		return self._lastActiveChild[-1]


	def lastActiveChild(self, name=False, asList=False):
		'''Get the given widget set as last active.
		Contains a list of the last 10 active child widgets.

		Parameters:
			name (bool): Return the last active widgets name as a string.

		Return:
			(obj)(str)(list) dependant on flags.

		ex. slot connection to the last active child widget:
			cmb.returnPressed.connect(lambda m=cmb.ctxMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
		'''
		if not hasattr(self, '_lastActiveChild'):
			return None

		if name:
			lastActive = str(self._lastActiveChild[-1].objectName())

		elif name and asList:
			lastActive = [str(w.objectName()) for w in self._lastActiveChild]

		elif asList:
			lastActive = [w for w in self._lastActiveChild]

		else:
			lastActive = self._lastActiveChild[-1]

		return lastActive


	def _addToContextMenuToolTip(self, menuItem):
		'''Add an item to the context menu toolTip.

		Parameters:
			menuItem (obj): The item to add.
		'''
		p = self.parent()
		if not all([self.menu_type=='context', p]):
			return

		if not hasattr(self, '_contextMenuToolTip'):
			self._contextMenuToolTip = '<u>Context menu items:</u>'
			p.setToolTip('{}<br><br>{}'.format(p.toolTip(), self._contextMenuToolTip)) #initialize the toolTip.

		try:
			contextMenuToolTip = '<b>{}</b> - {}'.format(menuItem.text(), menuItem.toolTip())
			p.setToolTip('{}<br>{}'.format(p.toolTip(), contextMenuToolTip))
		except AttributeError:
			pass


	def leaveEvent(self, event):
		'''
		Parameters:
			event = <QEvent>
		'''
		self.hide()

		super().leaveEvent(event)


	def hide(self, force=False):
		'''Sets the widget as invisible.
		Prevents hide event under certain circumstances.

		Parameters:
			force (bool): override preventHide.
		'''
		if force or not self.preventHide:

			for w in self.getChildWidgets():
				try:
					if w.view().isVisible(): #comboBox menu open.
						return
				except AttributeError as error:
					pass

			super().hide()


	def setVisible(self, state):
		'''Called every time the widget is shown or hidden on screen.
		'''
		if state: #visible
			if not self.containsMenuItems: #prevent show if the menu is empty.
				return

			if not self.title():
				self.setTitle()

			if hasattr(self.parent(), 'released') and not self.parent().objectName()=='draggable_header':
				# print (f'show menu | title: {self.title()} | {self.parent().objectName()} has attr released.') #debug
				self.applyButton.show()

			checkboxes = self.getChildWidgets(inc=['QCheckBox'])
			if checkboxes: #returns None if the menu doesn't contain checkboxes.
				self.toggleAllButton.show()

			self.resize(self.sizeHint().width(), self.sizeHint().height()+10) #self.setMinimumSize(width, self.sizeHint().height()+5)
			getCenter = lambda w, p: QtCore.QPoint(p.x()-(w.width()/2), p.y()-(w.height()/4)) #get widget center position.

			#set menu position
			if self.position=='cursorPos':
				pos = QtGui.QCursor.pos() #global position
				self.move(getCenter(self, pos)) #move to cursor position.

			elif not isinstance(self.position, (type(None), str)): #if a widget is passed to 'position' (move to the widget's position).
				pos = getattr(self.positionRelativeTo.rect(), self.position)
				self.move(self.positionRelativeTo.mapToGlobal(pos()))

			elif self.parent(): #if parent: map relative to parent.
				pos = getattr(self.parent().rect(), self.position if not self.position=='cursorPos' else 'bottomLeft')
				pos = self.parent().mapToGlobal(pos())
				self.move(pos) # self.move(getCenter(self, pos))

		elif self.preventHide: #invisible
			return

		super().setVisible(state)



class MenuInstance():
	'''Get a Menu and ctxMenu instance.
	'''
	@property
	def menu_(self):
		'''Get the standard menu.
		'''
		try:
			return self._menu

		except AttributeError as error:
			self._menu = Menu(self, position='bottomLeft', menu_type='standard')
			return self._menu


	@property
	def ctxMenu(self):
		'''Get the context menu.
		'''
		try:
			return self._contextMenu

		except AttributeError as error:
			self._contextMenu = Menu(self, position='cursorPos', menu_type='context')
			return self._contextMenu

# -----------------------------------------------------------------------------









# -----------------------------------------------------------------------------

if __name__ == "__main__":
	import sys
	app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv) #return the existing QApplication object, or create a new one if none exists.

	# # create parent menu containing two submenus:
	# m = Menu(position='cursorPos')
	# m1 = Menu('Create', addMenu_=m)
	# m1.add('QAction', setText='Action', insertSeparator_=True)
	# m1.add('QAction', setText='Action', insertSeparator_=True)
	# m1.add('QPushButton', setText='Button')

	# m2 = Menu('Cameras', addMenu_=m)
	# m2.add('QAction', setText='Action', insertSeparator_=True)
	# m2.add('QAction', setText='Action', insertSeparator_=True)
	# m2.add('QPushButton', setText='Button')
	# m.show()

	# # form layout example
	menu = Menu(menu_type='form', padding=6, title='Title', position='cursorPos')
	s = menu.add('QDoubleSpinBox', label='attrOne', checkable=True, setSpinBoxByValue_=1.0)
	s = menu.add('QDoubleSpinBox', label='attrTwo', checkable=False, setSpinBoxByValue_=2.0)
	menu.show()

	print (menu.childWidgets)

	# m.exec_(parent=None)
	sys.exit(app.exec_())

# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------

'''
Promoting a widget in designer to use a custom class:
>	In Qt Designer, select all the widgets you want to replace, 
		then right-click them and select 'Promote to...'. 

>	In the dialog:
		Base Class:		Class from which you inherit. ie. QWidget
		Promoted Class:	Name of the class. ie. "MyWidget"
		Header File:	Path of the file (changing the extension .py to .h)  ie. myfolder.mymodule.mywidget.h

>	Then click "Add", "Promote", 
		and you will see the class change from "QWidget" to "MyWidget" in the Object Inspector pane.
'''

# depricated:

	# def hide(self, force=False):
	# 	'''Sets the widget as invisible.
	# 	Prevents hide event under certain circumstances.

	# 	Parameters:
	# 		force (bool): override preventHide.
	# 	'''
	# 	if force or not self.preventHide:

	# 		for w in self.getChildWidgets():
	# 			try:
	# 				if w.view().isVisible(): #comboBox menu open.
	# 					return
	# 			except AttributeError as error:
	# 				pass

	# 		super().hide()


	# def show(self):
	# 	'''Show the menu.
	# 	'''
	# 	if not self.containsMenuItems: #prevent show if the menu is empty.
	# 		return

	# 	if not self.title():
	# 			self.setTitle()

	# 	if hasattr(self.parent(), 'released') and not self.parent().objectName()=='draggable_header':
	# 		# print (f'show menu | title: {self.title()} | {self.parent().objectName()} has attr released.') #debug
	# 		self.applyButton.show()

	# 	checkboxes = self.getChildWidgets(inc=['QCheckBox'])
	# 	if checkboxes: #returns None if the menu doesn't contain checkboxes.
	# 		self.toggleAllButton.show()

	# 	super().show()


	# def showEvent(self, event):
	# 	'''
	# 	Parameters:
	# 		event = <QEvent>
	# 	'''
	# 	self.resize(self.sizeHint().width(), self.sizeHint().height()+10) #self.setMinimumSize(width, self.sizeHint().height()+5)
	# 	getCenter = lambda w, p: QtCore.QPoint(p.x()-(w.width()/2), p.y()-(w.height()/4)) #get widget center position.

	# 	#set menu position
	# 	if self.position=='cursorPos':
	# 		pos = QtGui.QCursor.pos() #global position
	# 		self.move(getCenter(self, pos)) #move to cursor position.

	# 	elif not isinstance(self.position, (type(None), str)): #if a widget is passed to 'position' (move to the widget's position).
	# 		pos = getattr(self.positionRelativeTo.rect(), self.position)
	# 		self.move(self.positionRelativeTo.mapToGlobal(pos()))

	# 	elif self.parent(): #if parent: map relative to parent.
	# 		pos = getattr(self.parent().rect(), self.position if not self.position=='cursorPos' else 'bottomLeft')
	# 		pos = self.parent().mapToGlobal(pos())
	# 		self.move(pos) # self.move(getCenter(self, pos))

	# 	QtWidgets.QMenu.showEvent(self, event)