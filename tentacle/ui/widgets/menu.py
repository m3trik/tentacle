# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

from attributes import Attributes



class Menu(QtWidgets.QMenu, Attributes):
	'''
	:Parameters:
		menu_type (str) = Menu style. valid parameters are: 'standard', 'context', 'form'
		title (str) = Text displayed at the menu's header.
		padding (int) = Area surrounding the menu.
		childHeight (int) = The minimum height of any child widgets (excluding the 'Apply' button).
		preventHide (bool) = Prevent the menu from hiding.
		position (str) = Desired menu position. Valid values are: 
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
		self.setWindowFlags(QtCore.Qt.Tool|QtCore.Qt.FramelessWindowHint|QtCore.Qt.WindowStaysOnTopHint)
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


	@property
	def containsMenuItems(self):
		'''Query whether any child objects have been added to the menu.
		'''
		state = True if self.childWidgets else False

		return state


	#property
	def getChildWidgets(self, include=[], exclude=[]):
		'''Get a list of the menu's child widgets.

		:Parameters:
			include (list) = Include only widgets of the given type(s). ie. ['QCheckBox', 'QRadioButton']
			exclude (list) = Exclude widgets by type.

		:Return:
			(list) child widgets.
		'''
		if not hasattr(self, '_childWidgets'):
			self._childWidgets=[]

		if any((include, exclude)):
			try:
				self._childWidgets = [w for w in self._childWidgets if not w.__class__.__base__.__name__ in exclude 
					and (w.__class__.__base__.__name__ in include if include else w.__class__.__base__.__name__ not in include)]
			except Exception as error:
				print (__name__+':', 'getChildWidgets:', error)

		return self._childWidgets


	@property
	def draggable_header(self):
		'''Get the draggable header.
		'''
		if not hasattr(self, '_draggable_header'):
			from pushButtonDraggable import PushButtonDraggable
			self._draggable_header = PushButtonDraggable()
			wAction = QtWidgets.QWidgetAction(self)
			wAction.setDefaultWidget(self._draggable_header)
			self.addAction(wAction)

		return self._draggable_header


	@property
	def formLayout(self):
		'''Get the menu's form layout.
		'''
		if not hasattr(self, '_formLayout'):
			form = QtWidgets.QWidget(self)
			form.setStyleSheet('QWidget {background-color:rgb(50,50,50);}')
			self._formLayout = QtWidgets.QFormLayout(form)
			self._formLayout.setVerticalSpacing(0)
			wAction = QtWidgets.QWidgetAction(self)
			wAction.setDefaultWidget(form)
			self.addAction(wAction)

		return self._formLayout


	def setTitle(self, title=''):
		'''Set the menu's title to the given string.
		If no title is given, the fuction will attempt to use the menu parents text.

		:Parameters:
			title (str) = Text to apply to the menu's header.
		'''
		if not title:
			try:
				title = self.parent().text().rstrip('*')
			except AttributeError as error:
				try:
					title = self.parent().currentText().rstrip('*')
				except AttributeError as error:
					pass
		self.draggable_header.setText(title)


	def addApplyButton(self):
		'''Add a pushbutton that executes the parent object when pressed.

		:Return:
			(widget) The added pushbutton, or None if the process failed.
		'''
		try:
			return self._applyButton

		except AttributeError as error: #construct and add the button.
			try:
				self._applyButton = self.add('QPushButton', setText='Apply', setObjectName=self.parent().objectName(), setToolTip='Execute the command.')
				self._applyButton.released.connect(lambda p=self.parent(): p.released.emit()) #trigger the released signal on the parent when the apply button is released.
				self._applyButton.setMinimumSize(119, 26)

			except AttributeError as error: #parent has no signal 'released'.
				self._applyButton = None

			return self._applyButton
		


	def addUncheckAllButton(self):
		'''Add a pushbutton that unchecks any checkBoxes when pressed.

		:Return:
			(widget) The added pushbutton, or None if the process failed.
		'''
		try:
			return self._uncheckAllButton

		except AttributeError as error: #construct and add the button.
			self._uncheckAllButton = self.add('QPushButton', setText='Disable All', setObjectName='disableAll', setToolTip='Set all unchecked.')
			self._uncheckAllButton.released.connect(lambda children=self.getChildWidgets(include=['QCheckBox']): [c.setChecked(False) for c in children]) #trigger the released signal on the parent when the apply button is released.
			# self._uncheckAllButton.setMinimumSize(119, 26)

			return self._uncheckAllButton


	def add(self, widget, label='', checkableLabel=False, **kwargs):
		'''Add items to the QMenu.

		:Parameters:
			widget (str)(obj) = The widget to add. ie. 'QLabel', QtWidgets.QLabel, QtWidgets.QLabel()
			lable (str) = Add a label. (which is actually a checkbox. by default it is not checkable)
			checkableLabel (bool) = The label is checkable.

		additional kwargs:
			insertSeparator_ (bool) = insert a separator before the widget.
			setLayoutDirection_ (str) = ie. 'LeftToRight'
			setAlignment_ (str) = ie. 'AlignVCenter'
			setButtonSymbols_ (str) = ie. 'PlusMinus'
			setMinMax_ (str) = Set the min, max, and step values with a string. ie. '1-100 step.1'

		:Return:
 			(obj) the added widget instance.

		ex.call:
		menu.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
		'''
		try: #get the widget
			w = getattr(QtWidgets, widget)() #ie. QtWidgets.QAction(self) object from string.
		except:
			try: #if callable(widget):
				w = widget() #ie. QtWidgets.QAction(self) object.
			except:
				w = widget

		self.setAttributes(w, **kwargs) #set any additional given keyword args for the widget.

		type_ = w.__class__.__name__

		if type_=='QAction': #add action item.
			a = self.addAction(w)

		else:
			if self.menu_type=='form': #add widgets to the form layout.
				l = QtWidgets.QCheckBox()
				text = ''.join([(' '+i if i.isupper() else i) for i in label]).title() #format the attr name. ie. 'Subdivisions Height' from 'subdivisionsHeight'
				l.setText(text)
				l.setObjectName(label)
				if not checkableLabel:
					l.setCheckable(False)
					l.setStyleSheet('QCheckBox::hover {background-color: rgb(100,100,100); color: white;}')
				self.formLayout.addRow(l, w)
				self.childWidgets.append(l) #add the widget to the childWidgets list.

			else: #convert to action item, then add.
				wAction = QtWidgets.QWidgetAction(self)
				wAction.setDefaultWidget(w)
				self.addAction(wAction)

			#set child height
			w.setMinimumSize(125, self.childHeight)
			w.setMaximumSize(125, self.childHeight)
			try:
				l.setMinimumSize(l.sizeHint().width(), self.childHeight)
				l.setMaximumSize(9999, self.childHeight)
			except UnboundLocalError as error: #'l' does not exist. (not a form menu)
				pass

			self.childWidgets.append(w) #add the widget to the childWidgets list.

			setattr(self, w.objectName(), w) #add the widget's objectName as a QMenu attribute.

			self.addToContextMenuToolTip(w)

			#connect to 'setLastActiveChild' when signal activated.
			if hasattr(w, 'released'):
				w.released.connect(lambda w=w: self.setLastActiveChild(w))
			elif hasattr(w, 'valueChanged'):
				w.valueChanged.connect(lambda value, w=w: self.setLastActiveChild(value, w))

		return w


	def setLastActiveChild(self, widget, *args, **kwargs):
		'''Set the given widget as the last active.
		Maintains a list of the last 10 active child widgets.

		:Parameters:
			widget = Widget to set as last active. The widget can later be returned by calling the 'lastActiveChild' method.
			*args **kwargs = Any additional arguments passed in by the wiget's signal during a connect call.

		:Return:
			(obj) widget.
		'''
		# widget = args[-1]

		if not hasattr(self, '_lastActiveChild'):
			self._lastActiveChild = []

		del self._lastActiveChild[11:] #keep the list length at 10 elements.

		self._lastActiveChild.append(widget)
		# print(args, kwargs, widget.objectName() if hasattr(widget, 'objectName') else None)
		return self._lastActiveChild[-1]


	def lastActiveChild(self, name=False, as_list=False):
		'''Get the given widget set as last active.
		Contains a list of the last 10 active child widgets.

		:Parameters:
			name (bool) = Return the last active widgets name as a string.

		:Return:
			(obj) widget or (str) widget name.

		ex. slot connection to the last active child widget:
			cmb.returnPressed.connect(lambda m=cmb.contextMenu.lastActiveChild: getattr(self, m(name=1))()) #connect to the last pressed child widget's corresponding method after return pressed. ie. self.lbl000 if cmb.lbl000 was clicked last.
		'''
		if not hasattr(self, '_lastActiveChild'):
			return None

		if name:
			lastActive = str(self._lastActiveChild[-1].objectName())
		elif name and as_list:
			lastActive = [str(w.objectName()) for w in self._lastActiveChild]
		elif as_list:
			lastActive = [w for w in self._lastActiveChild]
		else:
			lastActive = self._lastActiveChild[-1]

		return lastActive


	def addToContextMenuToolTip(self, menuItem):
		'''Add an item to the context menu toolTip.

		:Parameters:
			menuItem (obj) = The item to add.
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
		:Parameters:
			event = <QEvent>
		'''
		self.hide()

		return QtWidgets.QMenu.leaveEvent(self, event)


	def hide(self, force=False):
		'''Sets the widget as invisible.
		Prevents hide event under certain circumstances.

		:Parameters:
			force (bool) = override preventHide.
		'''
		if force or not self.preventHide:

			for child in self.children():
				try:
					if child.view().isVisible():
						return
				except AttributeError:
					pass

			return super().hide()


	def show(self):
		'''Show the menu.
		'''
		if self.containsMenuItems: #prevent show if the menu is empty.
			return super().show()


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
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

			if self.getChildWidgets(include=['QCheckBox']): #if the menu contains checkboxes:
				self.addUncheckAllButton()

		return QtWidgets.QMenu.showEvent(self, event)


	#assign properties
	childWidgets = property(getChildWidgets)



class MenuInstance(object):
	'''Get a Menu and contextMenu instance.
	'''
	@property
	def menu_(self):
		'''Get the menu.
		'''
		try:
			return self._menu

		except AttributeError as error:
			self._menu = Menu(self, position='bottomLeft', menu_type='standard')
			return self._menu


	@property
	def contextMenu(self):
		'''Get the context menu.
		'''
		try:
			return self._contextMenu

		except AttributeError as error:
			self._contextMenu = Menu(self, position='cursorPos', menu_type='context')
			return self._contextMenu








if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

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
	sys.exit(qApp.exec_())



# --------------------------------
# Notes
# --------------------------------

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

# depricated ------------------------------------------------------------------------


	# def children_(self, index=None, include=[], exclude=['QAction', 'QWidgetAction', 'QHBoxLayout', 'QVBoxLayout', 'QFormLayout', 'QValidator']):
	# 	'''Get a list of the menu's child objects, excluding those types listed in 'exclude'.

	# 	:Parameters:
	# 		index (int) = return the child widget at the given index.
	# 		exclude (list) = Widget types to exclude from the returned results.
	# 		include (list) = Widget types to include in the returned results. All others will be omitted. Exclude takes dominance over include. Meaning, if a widget is both in the exclude and include lists, it will be excluded.

	# 	:Return:
	# 		(obj)(list) child widgets or child widget at given index.
	# 	'''
	# 	# children = [i for i in self.children() 
	# 	# 		if i.__class__.__name__ not in exclude 
	# 	# 		and (i.__class__.__name__ in include if include else i.__class__.__name__ not in include)]

	# 	# children=[]
	# 	# for c in self.children():
	# 	# 	for cc in c.children():
	# 	# 		for ccc in cc.children():
	# 	# 			children.append(ccc) 

	# 	# print (children)
	# 	children = [i for i in self.children()
	# 			if i.__class__.__name__ not in exclude 
	# 			and (i.__class__.__name__ in include if include else i.__class__.__name__ not in include)]

	# 	if index is not None:
	# 		try:
	# 			children = children[index]

	# 		except IndexError:
	# 			children = None

	# 	return children


# def contextMenuToolTip(self):
# 		'''
# 		Creates an html formatted toolTip while appending the toolTips of any context menu items.

# 		:Return:
# 			(str) formatted toolTip.
# 		'''
# 		if not hasattr(self, '_contextMenuToolTip'):
# 			self._contextMenuToolTip=''
# 			menuItems = self.children_()
# 			print ('menuItems:', menuItems)
# 			if menuItems:
# 				self._contextMenuToolTip = '<br><br><u>Context menu items:</u>'
# 				for menuItem in menuItems:
# 					try:
# 						self._contextMenuToolTip = '{0}<br>  <b>{1}</b> - {2}'.format(self._contextMenuToolTip, menuItem.text(), menuItem.toolTip())				
# 					except AttributeError:
# 						pass

# 		return self._contextMenuToolTip


	# def addMenus(self, menus):
	# 	'''
	# 	Add multiple menus at once.

	# 	:Parameters:
	# 		menus (list) = list of menus.

	# 	:Return:
	# 		(list) the menuAction() for each menu

	# 	ex. usage: 
	# 	m = Menu(position='cursorPos', setVisible=True)
	# 	m1 = Menu('Create', addMenu=m)
	# 	m2 = Menu('Cameras', addMenu=m)
	# 	m.addMenus([m1,m2])
	# 	'''
	# 	return [self.addMenu(m) for m in menus]


# @property
# 	def containsContextMenuItems(self):
# 		'''
# 		Query whether a menu has been constructed.
# 		'''
# 		if not self.children_(contextMenu=True):
# 			return False
# 		return True


	# def addToContext(self, w, **kwargs):
	# 	'''
	# 	Add items to the pushbutton's context menu.

	# 	:Parameters:
	# 		w (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
	# 	kw:Parameters:
	# 		show (bool) = show the menu.
	# 		insertSeparator (QAction) = insert separator in front of the given action.
	# 	:Return:
 # 			the added widget.

	# 	ex.call:
	# 	tb.menu_.add('QCheckBox', setText='Component Ring', setObjectName='chk000', setToolTip='Select component ring.')
	# 	'''
	# 	try:
	# 		w = getattr(QtWidgets, w)() #ex. QtWidgets.QAction(self) object from string.
	# 	except:
	# 		if callable(w):
	# 			w = w() #ex. QtWidgets.QAction(self) object.

	# 	w.setMinimumHeight(self.minimumSizeHint().height()+1) #set child widget height to that of the button

	# 	w = self.contextMenu.add(w, **kwargs)
	# 	setattr(self, w.objectName(), w)
	# 	return w



	# def setAttributes(self, attributes=None, action=None, order=['globalPos', 'setVisible'], **kwargs):
	# 	'''
	# 	Internal use. Works with attributes passed in as a dict or kwargs.
	# 	If attributes are passed in as a dict, kwargs are ignored.

	# 	:Parameters:
	# 		attributes (dict) = keyword attributes and their corresponding values.
	# 		action (obj) = the child action or widgetAction to set attributes for. (default=None)
	# 		#order (list) = list of string keywords. ie. ['move_', 'setVisible']. attributes in this list will be set last, by list order. an example would be setting move positions after setting resize arguments, or showing the widget only after other attributes have been set.

	# 	kw:Parameters:
	# 		set any keyword arguments.
	# 	'''
	# 	if not attributes:
	# 		attributes = kwargs

	# 	if action is None:
	# 		action = self

	# 	for k in order:
	# 		v = attributes.pop(k, None)
	# 		if v:
	# 			from collections import OrderedDict
	# 			attributes = OrderedDict(attributes)
	# 			attributes[k] = v

	# 	for attr, value in attributes.items():
	# 		try:
	# 			getattr(action, attr)(value)

	# 		except AttributeError:
	# 			self.setCustomAttribute(action, attr, value)


	# def setCustomAttribute(self, action, attr, value):
	# 	'''
	# 	Internal use. Custom attributes can be set using a trailing underscore convention to differentiate them from standard attributes.

	# 	:Parameters:
	# 		action (obj) = action (obj) = the child action or widgetAction to set attributes for.
	# 		attr (str) = custom keyword attribute.
	# 		value (str) = the value corresponding to the given attr.

	# 	attributes:
	# 		copy (obj) = widget to copy certain attributes from.
	# 		globalPos (QPoint) = move to given global location and center.
	# 		insertSeparator_ (bool) = insert a line separater before the new widget.
	# 		setLayoutDirection_ (str) = set the layout direction using a string value. ie. 'LeftToRight'
	# 		setAlignment_ (str) = set the alignment using a string value. ie. 'AlignVCenter'
	# 		setButtonSymbols_ (str) = set button symbols using a string value. ex. ie. 'PlusMinus'
	# 		setMinMax_ (str) = set the min, max, and step value using a string value. ex. '.01-10 step.1'
	# 	'''
	# 	if attr=='copy':
	# 		self.setObjectName(value.objectName())
	# 		self.resize(value.size())
	# 		self.setText(value.text())
	# 		self.setWhatsThis(value.whatsThis())

	# 	elif attr=='globalPos':
	# 		self.move(self.mapFromGlobal(value - self.rect().center())) #move and center

	# 	elif attr=='insertSeparator_':
	# 		if action.__class__.__name__=='QAction':
	# 			self.insertSeparator(action)

	# 	elif attr=='setLayoutDirection_':
	# 		self.setAttributes({'setLayoutDirection':getattr(QtCore.Qt, value)}, action)

	# 	elif attr=='setAlignment_':
	# 		self.setAttributes({'setAlignment':getattr(QtCore.Qt, value)}, action)

	# 	elif attr=='setButtonSymbols_':
	# 		self.setAttributes({'setButtonSymbols':getattr(QtWidgets.QAbstractSpinBox, value)}, action)

	# 	#presets
	# 	elif attr=='setMinMax_':
	# 		self.setMinMax(action, value)

	# 	elif attr=='setSpinBoxByValue_':
	# 		self.setByValue(action, value[0], value[1])

	# 	else:
	# 		print('Error: {} has no attribute {}'.format(action, attr))


	# def setMinMax(self, spinbox, value):
	# 	'''
	# 	Set the minimum, maximum, and step values for a spinbox using a shorthand string value.

	# 	:Parameters:
	# 		spinbox (obj) = spinbox widget.
	# 		value (str) = value as shorthand string. ie. '0.00-100 step1'
	# 	'''
	# 	minimum = float(value.split('-')[0])
	# 	maximum = float(value.split('-')[1].split()[0])
	# 	step = float(value.split()[1].strip('step'))

	# 	self.setAttributes({
	# 		'setMinimum':minimum, 
	# 		'setMaximum':maximum, 
	# 		'setSingleStep':step, 
	# 		'setButtonSymbols_':'NoButtons',
	# 	}, spinbox)


	# def setByValue(self, spinbox, attribute, value):
	# 	'''
		
	# 	:Parameters:
	# 		spinbox (obj) = spinbox widget.
	# 		attribute (str) = object attribute.
	# 		value (multi) = attribute value.
	# 	'''
	# 	prefix = attribute+': '
	# 	suffix = spinbox.suffix()
	# 	minimum = spinbox.minimum()
	# 	maximum = spinbox.maximum()
	# 	step = spinbox.singleStep()
	# 	decimals = spinbox.decimals()

	# 	if isinstance(value, float):
	# 		decimals = str(value)[::-1].find('.') #get decimal places

	# 	elif isinstance(value, int):
	# 		decimals = 0

	# 	elif isinstance(value, bool):
	# 		value = int(value)
	# 		minimum = 0
	# 		maximum = 1

	# 	self.setAttributes({
	# 		'setValue':value,
	# 		'setPrefix':prefix,
	# 		'setSuffix':suffix,
	# 		'setMinimum':minimum, 
	# 		'setMaximum':maximum, 
	# 		'setSingleStep':step, 
	# 		'setDecimals':decimals,
	# 		'setButtonSymbols_':'NoButtons',
	# 	}, spinbox)


# if not __name__=='__main__' and not hasattr(self, 'parentUiName'):
# 	p = self.parent()
# 	try:
# 		while not hasattr(p.window(), 'sb'):
# 			p = p.parent()

# 		self.sb = p.window().sb
# 		self.parentUiName = self.sb.getUiName()
# 		self.childEvents = self.sb.getClassInstance('EventFactoryFilter')

# 		self.childEvents.addWidgets(self.parentUiName, self.children()+[self])
# 	except AttributeError:
# 		pass

# 	self.setAttributes({'setMinimum':0.0, 'setMaximum':10.0, 'setSingleStep':0.001, 'setDecimals':3, 'setButtonSymbols_':'NoButtons'}, action)