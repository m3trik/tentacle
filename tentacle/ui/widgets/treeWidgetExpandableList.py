# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets

try: import shiboken2
except: from PySide2 import shiboken2

from attributes import Attributes


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


class TreeWidgetExpandableList(QtWidgets.QTreeWidget, Attributes):
	'''Additional column lists are shown as they are triggered by their parent widgets.

	:Parameters:
		parent (obj) = Parent Object.
		stepColumns (bool) = Start child columns at row of its parent widget. Else, always at row 0.
		expandOnHover (bool) = Expand columns on mouse hover.

	ex. widgets dict
		#QWidget object			#header	#col #row #childHeader
		widgets = {
			<Custom Camera>:	['Create',	1, 0, None],
			<Cameras>:			['root', 	0, 1, 'Cameras'], 
			<Set Custom Camera>:['Create',	1, 1, None], 
			<Cam1>:				['Cameras', 2, 1, None],
			<Cam2>:				['Cameras', 2, 2, None],
			<opt2>:				['Options', 3, 4, None], 
			<Create>:			['root', 	0, 0, 'Create'], 
			<Camera From View>:	['Create', 	1, 2, None], 
			<Options>:			['Cameras', 2, 3, 'Options'], 
			<opt1>:				['Options', 3, 3, None]
		}
	'''
	enter = QtCore.QEvent(QtCore.QEvent.Enter)
	leave = QtCore.QEvent(QtCore.QEvent.Leave)
	hoverEnter = QtCore.QEvent(QtCore.QEvent.HoverEnter)
	hoverMove = QtCore.QEvent(QtCore.QEvent.HoverMove)
	hoverLeave = QtCore.QEvent(QtCore.QEvent.HoverLeave)


	def __init__(self, parent=None, stepColumns=True, expandOnHover=False, **kwargs):
		QtWidgets.QTreeWidget.__init__(self, parent)

		self.refresh = False
		self.widgets = {}
		self._gcWidgets = {}
		self._mouseGrabber = None

		self.stepColumns = stepColumns
		self.expandOnHover = expandOnHover

		self.setHeaderHidden(True)
		self.setIndentation(0)
		self.setStyleSheet('''
			QTreeWidget {
				background-color: transparent;
				border: none;
			} 

			QTreeWidget::item {
				height: 20px;
				margin-left: 0px;
			}

			QTreeView::item:hover {
				background: transparent;
				color: none;
			}

			QTreeView::item:selected {
			    background-color: none;
			}''')

		self.setAttributes(**kwargs)


	def add(self, widget, header='root', childHeader=None, refresh=False, **kwargs):
		'''Add items to the treeWidget.
		Using custom kwarg refresh=True will flag the header's column contents to be refreshed each time the widget is shown.

		:Parameters:
			widget (str)(obj) = widget. ie. 'QLabel' or QtWidgets.QLabel
			header (str)(obj) = header or parent widget.
			childHeader (str) = The child header that is shown when this widget is active.

		:Return:
 			(str ) the child header (or None, if no child header given).

		ex.call:
			create = tree.add('QPushButton', childHeader='Create', setText='Create')
			tree.add('QPushButton', create, setText='Custom Camera')
			#sublist:
			options = tree.add('QPushButton', create, childHeader='Options', setText='Options')
			tree.add('QPushButton', options, setText='Opt1')
		'''
		if not isinstance(header, (str)): #if the header is passed in as a widget:
			header = self.getChildHeaderFromWidget(header)

		#if header doesn't contain the refresh column flag: return the child header.
		if self.refresh and self.isRefreshedHeader(header)==False:
			return self.getChildHeaderFromHeader(header)

		#set widget
		try:
			widget = getattr(QtWidgets, widget)(self) #ex. QtWidgets.QAction(self) object from string. parented to self.
		except:
			if callable(widget):
				widget = widget(self) #ex. QtWidgets.QAction(self) object. parented to self.

		#set widgetItem
		header = self.getHeaderFromWidget(widget, header)
		column = self.getColumnFromHeader(header, self.refresh)
		row = self.getStartingRowFromHeader(header)
		childHeader = self.getChildHeaderFromWidget(widget, childHeader)

		wItem = self.getWItemFromRow(row) #get the top widgetItem.
		while self.itemWidget(wItem, column): #while there is a widget in this column:
			wItem = self.itemBelow(wItem) #get the wItem below
			row+=1
		if not wItem:
			wItem = QtWidgets.QTreeWidgetItem(self)

		self.widgets[widget] = [header, column, row, childHeader, refresh] #store the widget and it's column/row/header information.

		self.setItemWidget(wItem, column, widget)
		self.setColumnCount(len(self.getColumns()))

		widget.setObjectName(self._createObjectName(wItem, column)) #set an dynamically generated objectName.
		widget.installEventFilter(self)

		self.setAttributes(widget, **kwargs) #set any additional given keyword args for the widget.

		return widget


	def eventFilter(self, widget, event):
		'''
		'''
		# if not (str(event.type()).split('.')[-1]) in ['QPaintEvent', 'UpdateLater', 'PolishRequest', 'Paint']: print(str(event.type())) #debugging
		if widget not in self.widgets or not shiboken2.isValid(widget):
			return False

		if event.type()==QtCore.QEvent.HoverEnter:
			if self.expandOnHover:
				self.resizeAndShowColumns(widget)

		if event.type()==QtCore.QEvent.HoverMove:
			try:
				w = next(w for w in self.widgets.keys() if w.rect().contains(w.mapFromGlobal(QtGui.QCursor.pos())) and w.isVisible())
			except StopIteration:
				return QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverLeave)

			if not w is self._mouseGrabber:
				if self._mouseGrabber is not None:
					QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverLeave)
					QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.leave)
				if not w is self.mouseGrabber():
					w.grabMouse()
				self._mouseGrabber = w
				QtWidgets.QApplication.sendEvent(w, self.hoverEnter)
				QtWidgets.QApplication.sendEvent(w, self.enter)

		if event.type()==QtCore.QEvent.HoverLeave:
			if self.expandOnHover:
				self.resizeAndShowColumns(widget, reset=True)
			if not __name__=='__main__':
				self.window().grabMouse()

		if event.type()==QtCore.QEvent.MouseButtonRelease:
			if widget.rect().contains(widget.mapFromGlobal(QtGui.QCursor.pos())):
				if not self.expandOnHover:
					self.resizeAndShowColumns(widget)
				wItem = self.getWItemFromWidget(widget)
				row = self.getRowFromWidget(widget)
				column = self.getColumnFromWidget(widget)
				self.itemClicked.emit(wItem, column)
				# self.window().hide()

		return super(TreeWidgetExpandableList, self).eventFilter(widget, event)


	def resizeAndShowColumns(self, widget=None, reset=False):
		'''Set size, widget states, and visible columns for a given widget.

		:Parameters:
			widget (obj) = QWidget. Required when not doing a reset.
			reset (bool) = set tree to original state.
		'''
		if reset:
			self._showColumns(0)
			self._resize(0)
			self._setEnabledState(0, widget) #set widgets enabled/disabled

		elif self.isParent(widget):
			childColumns = self.getChildColumnsFromWidget(widget)
			columns = [0]+childColumns
			self._setEnabledState(childColumns, widget) #set widgets enabled/disabled
			self._showColumns(columns)
			self._resize(columns)
		else:
			column = self.getColumnFromWidget(widget)
			parentColumns = self.getParentColumnsFromWidget(widget)
			self._setEnabledState(column, widget) #set widgets enabled/disabled
			self._showColumns([column]+parentColumns)
			self._resize([column]+parentColumns)


	def _resize(self, columns, resizeFirstColumn=False, collapseOtherColumns=False):
		'''Resize the treeWidget to fit it's current visible wItems.

		:Parameters:
			columns (int)(list) = column index or list of column indices.
			resizeFirstColumn (bool) = allow resize of column 0.
			collapseOtherColumns (bool) = set all columns not given in the argument to 0 width.
		'''
		if type(columns) is int:
			columns = [columns]

		columnWidths=[]
		for column in set(columns):
			if column==0 and not resizeFirstColumn:
				try: #if not hasattr(self, '_columnWidth0'):
					columnWidth = self._columnWidth0
				except AttributeError as error:
					columnWidth = self._columnWidth0 = self.columnWidth(column)
			else:
				columnWidth = self.sizeHintForColumn(column) #else get the size hint
			self.setColumnWidth(column, columnWidth)
			columnWidths.append(columnWidth)
		totalWidth = sum(columnWidths) #totalWidth = sum([self.columnWidth(c) for c in columns])
		self.resize(totalWidth, self.sizeHint().height()) #resize main widget to fit column.

		if collapseOtherColumns:
			[self.setColumnWidth(c, 0) for c in self.getColumns() if c not in columns] #set all other column widths to 0


	def _setEnabledState(self, columns, widget=None):
		'''Disables/Enables widgets along the tree hierarchy.

		:Parameters:
			widget (obj) = QWidget. current widget
			columns (int)(list) = column indices.
		'''
		if type(columns) is int:
			columns = [columns]
		if widget:
			if self.getColumnFromWidget(widget)==(0):
				columns = [0]+columns
			parentWidgets = self.getParentWidgetsFromWidget(widget)
		else:
			parentWidgets = []

		self.setWidgets(widgets=self.getWidgets(columns=columns, inverse=True), setDisabled=True)
		self.setWidgets(widgets=self.getWidgets(columns=columns)+parentWidgets, setEnabled=True)


	def setWidgets(self, widgets, **kwargs):
		'''
		'''
		for w in widgets:
			for k, v in kwargs.items():
				if hasattr(w, k):
					getattr(w, k)(v)


	def _createObjectName(self, wItem, column):
		'''Create an objectName for an itemWidget consisting of the parent treeWidget's object name, header, column, and childHeader.

		:Parameters:
			wItem (obj) = QWidgetItem.
			column (int) = The index of the column.
		:Return:
			(str) name string.
		'''
		header = self.getHeaderFromColumn(column)
		row = self.getRow(wItem)
		return '{0}|{1}|{2}|{3}'.format(self.objectName(), header, column, row) #ie. 'tree002|Options|0|1'


	def getWItemFromRow(self, row):
		'''Get the widgetItem contained in a given row.

		:Parameters:
			row (int) = Row index.
		'''
		try:
			return next(wItem for wItem in self.getTopLevelItems() if self.indexOfTopLevelItem(wItem)==row)
		except:
			return None


	def getIndexFromWItem(self, wItem, column=None, topLevel=False):
		'''Get an item's index.

		:Parameters:
			wItem (obj) = The widget item to get the index for.
			column (int) = Column containing the widget item.
			topLevel (bool) = Specifies whether the item is a topLevel item or not. With a top level item, the column arg is not needed.
		
		:Return:
			(int) index
		'''
		try:
			if topLevel:
				index = self.indexFromItem(wItem, column)
			else:
				index = self.indexOfTopLevelItem(wItem)
			return index
		except TypeError:
			return None


	def _setHeader(self, header, column=None):
		'''Set new header and column or modify an existing.

		:Parameters:
			header (str) = header text.
			column (int) = column index.
		:Return:
			(str) header text.
		'''
		if column:
			self.headerItem().setText(column, header)
		else: #set new header and column
			self.setHeaderLabel(header)
		return header


	def getHeaderFromWidget(self, widget, __header=None):
		'''Get the header that the widget belongs to.

		:Parameters:
			widget (obj) = A widget contained in one of the tree's wItems.
			__header (str) = internal use. header assignment.
		:Return:
			(str) header
		'''
		if __header is not None:
			return __header
		try:
			return self.widgets[widget][0]
		except:
			return None


	def getChildHeaderFromWidget(self, widget, __childHeader=None):
		'''Get the header that the widget belongs to.

		:Parameters:
			widget (obj) = A widget contained in one of the tree's wItems.
			__childHeader (str) = internal use. childHeader assignment.
		:Return:
			(str) child header
		'''
		if __childHeader is not None:
			return __childHeader
		try:
			return self.widgets[widget][3]
		except:
			return None


	def getChildHeaderFromHeader(self, header):
		'''Get the childHeader from the header name.

		:Parameters:
			header (str) = header name. ie. 'Options'
		:Return:
			(str) the parent's header.
		'''
		try:
			return next(i[3] for i in self.widgets.values() if i[3]==header)
		except:
			None


	def getHeaderFromColumn(self, column):
		'''
		'''
		try:
			return next(i[0] for i in self.widgets.values() if i[1]==column)
		except:
			return None


	def getRow(self, wItem):
		'''Get the stored row index.
		
		:Parameters:
			wItem (obj) = QWidgetItem.
		'''
		return self.indexFromItem(wItem).row()


	def getRowFromWidget(self, widget):
		'''
		'''
		return next(self.getRow(i) for c in self.getColumns() for i in self.getTopLevelItems() if self.itemWidget(i, c)==widget)


	def getColumnFromWidget(self, widget):
		'''
		'''
		try:
			return next(c for c in self.getColumns() for i in self.getTopLevelItems() if self.itemWidget(i, c)==widget)
		except:
			return None


	def getChildColumnFromWidget(self, widget):
		'''Get the child column of the given widget.

		:Parameters:
			widget (obj) = QWidget
		:Return:
			(int) child column, or None.
		'''
		header = self.widgets[widget][3]
		try:
			return next(i[1] for i in self.widgets.values() if i[0]==header)
		except:
			return None


	def getParentColumnsFromWidget(self, widget):
		'''
		'''
		header = self.widgets[widget][0]
		columns=[]
		while header!='root':
			for i in self.widgets.values():
				if i[3]==header:
					columns.append(i[1])
					header = i[0]
					break
		return columns


	def getParentWidgetsFromWidget(self, widget):
		'''
		'''
		header = self.widgets[widget][0]
		widgets=[]
		while header!='root':
			for w, i in self.widgets.items():
				if i[3]==header:
					widgets.append(w)
					header = i[0]
					break
		return widgets


	def getChildColumnsFromWidget(self, widget):
		'''Get the child column of the given widget.

		:Parameters:
			widget (obj) = QWidget
		:Return:
			(list) all child columns (int), or None.
		'''
		header = self.widgets[widget][3]
		try:
			return list(set([i[1] for i in self.widgets.values() if header in i and i[0]!='root']))
		except:
			return []


	def getColumnFromHeader(self, header, refreshedColumn=False):
		'''Get the stored column index.

		:Parameters:
			header (str) = header name.
		:Return:
			(int) = the column corresponding to the given header.
		'''
		try:
			if refreshedColumn:
				return next(i[1] for i in self._gcWidgets.values() if i and i[0]==header)
			else:
				return next(i[1] for i in self.widgets.values() if i[0]==header)
		except StopIteration: #else assign a new column to the header.
			if not hasattr(self, '_c'):
				self._c = 0 #columns start at 0
				return self._c
			self._c+=1 #and each new column is incremented by 1.
			return self._c


	def getStartingRowFromHeader(self, header):
		'''Get the starting row index for a given header's column.
		When the 'stepColumns' flag is True, the starting row corresponds to the parents row index. Else, the starting row is always 0.

		:Parameters:
			header (str) = the header of the column to get the starting row of.
		:Return:
			(int) = starting row index.
		'''
		if not hasattr(self, '_r'):
			self._r = 0
			return self._r
		if self.stepColumns:
			try:
				return next(i[2] for i in self.widgets.values() if i[3]==header) #return starting row for an existing column.
			except StopIteration:
				self._r+=1
		return self._r


	def getColumnFromChildHeader(self, childHeader):
		'''Get the stored column index.

		:Parameters:
			childHeader (str) = childHeader text.
		'''
		try:
			return next(i[1] for i in self.widgets.values() if i[3]==childHeader)
		except:
			return None


	def getColumns(self, refreshedColumns=False):
		'''Get all of the columns currently used.

		:Parameters:
			refreshedColumns (bool) = get only columns flagged as refreshed. Default is False.
		:Return:
			(set) set of ints representing column indices. 
		'''
		try:
			if refreshedColumns:
				columns = set([i[1] for i in self.widgets.values() if i[4]])
				# columns = set([i[1] for i in self.widgets.values() if self.isRefreshedHeader(i[0])])
			else:
				columns = set([i[1] for i in self.widgets.values()])
				if not columns: #when not getting refreshed columns, and columns have yet to be stored in the widgets dict, try an alt method.
					raise Exception
		except Exception:
			columns = set([i for i in range(self.columnCount())])
		return columns


	def _showColumns(self, columns):
		'''Unhide the given column, while hiding all others.

		:Parameters:
			columns (list) = list of indices of the columns to show.
		'''
		if type(columns)==int:
			columns = [columns]
		for c in self.getColumns():
			if c in columns:
				self.setColumnHidden(c, False)
			else:
				self.setColumnHidden(c, True)


	def getTopLevelItems(self):
		'''Get all top level QTreeWidgetItems in the given QTreeWidget.
		
		:Return:
			(list) All Top level QTreeWidgetItems
		'''
		return [self.topLevelItem(i) for i in range(self.topLevelItemCount())]


	def getWItemFromWidget(self, widget):
		'''
		'''
		try:
			return next(i for c in self.getColumns() for i in self.getTopLevelItems() if self.itemWidget(i, c)==widget)
		except:
			return None


	def getWidgets(self, wItem=None, columns=None, removeNoneValues=False, refreshedWidgets=False, inverse=False):
		'''Get the widgets from the given widgetItem, or all widgets if no specific widgetItem is given.

		:Parameters:
			wItem (obj) = QWidgetItem.
			columns (int)(list) = column(s) where widgets are located. single column or a list of columns.
			removeNoneValues (bool) = Remove any 'None' values from the returned list.
			refreshedWidgets (bool) = Return only widgets from a column that is flagged to refresh. ie. it's column header starts with '*'. None values are removed when this argument is set.
			inverse (bool)(iter) = get the widgets not associated with the given argument. ie. not in 'columns' or not in 'wItem'. An iterative can be passed in instead of a bool value. inverse has no effect when returning all widgets.
	
		:Return:
			widgets (list)
		'''
		if wItem:  #get widgets contained in the given widgetItem.
			if columns:
				list_ = [self.itemWidget(wItem, c) for c in columns]
			else:
				list_ = [self.itemWidget(wItem, c) for c in self.getColumns()]

		elif columns is not None:  #get widgets in the given columns.
			if type(columns)==int:
				list_ = [w for w, i in self.widgets.items() if i[1]==columns]
			else:
				list_ = [w for w, i in self.widgets.items() for c in columns if i[1]==c]

		else: #get all widgets
			list_ = [self.itemWidget(i, c) for c in self.getColumns() for i in self.getTopLevelItems()]

		if refreshedWidgets:
			list_ = [w for w in list_ if w is not None and self.isRefreshedHeader(self.getHeaderFromWidget(w))]

		if inverse:
			if isinstance(inverse, (list, tuple, set)):
				list_ = inverse
			list_ = [i for i in self.getWidgets() if i not in list_]

		if removeNoneValues:
			list_ = [i for i in list_ if not i==None]

		return list_


	@property
	def newWidgets(self):
		'''Get any newly created widgets from the treeWidget.
		'''
		if self.refresh: #after first build; on each refresh:
			widgets = self.getWidgets(refreshedWidgets=1) #get only any newly created widgets.
		else: #on first build:
			widgets = self.getWidgets(removeNoneValues=1) #get all widgets.

		return widgets


	def getWidget(self, wItem, column):
		'''Get the widget from the widgetItem at the given column (if it exists).

		:Parameters:
			wItem (obj) = The widgetItem containing the widget.
			column (int) = The column location on the widget.
		:Return:
			(obj) QWidget
		'''
		try:
			return next(w for w in self.getWidgets(wItem) if self.getColumnFromWidget(w)==column)
		except:
			return None


	def getWidgetText(self, wItem, column):
		'''Get the widget text from the widgetItem at the given column (if it exists).

		:Parameters:
			wItem (obj) = The widgetItem containing the widget.
			column (int) = The column location on the widget.
		:Return:
			(str) QWidget's text
		'''
		try:
			return next(w.text() for w in self.getWidgets(wItem) if self.getColumnFromWidget(w)==column)
		except:
			return None


	def getWidgetsFromText(self, textList):
		'''Get any widget(s) with text matching those in the given list.

		:Parameters:
			textList (list) = String list of possible widget text matches.
		:Return:
			(list) matching widget(s)
		'''
		return [w for w in self.getWidgets() if w and w.text() in textList]


	def isParent(self, widget):
		'''
		'''
		if widget in self.widgets:
			if self.widgets[widget][3] is not None:
				return True
			return False
		return None


	def isRefreshedHeader(self, header):
		'''
		'''
		try:
			return next(i[4] for i in self.widgets.values() if i[0]==header)
		except StopIteration:
			return None


	def convert(self, items, w, columns=None):
		'''Convert itemWidgets to a given type.
		Can be used with Qt Designer to convert columns and their headers to widgets.

		:Parameters:
			w (str) = widget type. ie. 'QPushButton'
			items (list) = QTreeWidgetItems

		ex. call
		tree.convert(tree.getTopLevelItems(), 'QLabel')
		'''
		[self.takeTopLevelItem(self.indexOfTopLevelItem(i)) for i in items] #delete each widgetItem

		if columns is None:
			columns = self.getColumns()
		if type(columns)==int:
			columns = [columns]
		for c in columns:
			list_ = [str(i.text(c)) for i in items] #get each widgetItem's text string.

			if c==0:
				[self.add(w, childHeader=i, setText=i) for i in list_ if i]
			else:
				header = str(self.headerItem().text(c))
				[self.add(w, header=header, setText=i) for i in list_ if i]


	def clear_(self, columns):
		'''
		'''
		self._gcWidgets={}
		for column in columns:
			for wItem in self.getTopLevelItems():
				widget = self.itemWidget(wItem, column)
				self.removeItemWidget(wItem, column)
				list_ = self.widgets.pop(widget, None) #remove the widget from the widgets dict.
				self._gcWidgets[widget] = list_
				# if widget:
				# 	shiboken2.delete(widget)


	def leaveEvent(self, event):
		'''
		'''
		self.resizeAndShowColumns(reset=True)
		self._mouseGrabber = self
		
		return QtWidgets.QTreeWidget.leaveEvent(self, event)


	def showEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''

		return QtWidgets.QTreeWidget.showEvent(self, event)


	def hideEvent(self, event):
		'''
		:Parameters:
			event = <QEvent>
		'''
		self.refresh = True #init flag stays False after first hide
		refreshedColumns = self.getColumns(refreshedColumns=True)
		if refreshedColumns:
			self.clear_(refreshedColumns)

		return QtWidgets.QTreeWidget.hideEvent(self, event)









if __name__ == '__main__':
	import sys
	qApp = QtWidgets.QApplication.instance() #get the qApp instance if it exists.
	if not qApp:
		qApp = QtWidgets.QApplication(sys.argv)

	tree=TreeWidgetExpandableList(stepColumns=1, setVisible=True)

	create = tree.add('QPushButton', childHeader='Create', setText='Create')
	tree.add('QLabel', create, setText='Custom Camera')
	tree.add('QLabel', create, setText='Set Custom Camera')
	tree.add('QLabel', create, setText='Camera From View')

	cameras = tree.add('QPushButton', childHeader='Cameras', setText='Cameras')
	tree.add('QLabel', cameras, setText='Cam1')
	tree.add('QLabel', cameras, setText='Cam2')

	options = tree.add('QPushButton', cameras, childHeader='Options', setText='Options')
	tree.add('QLabel', options, setText='Opt1')
	tree.add('QLabel', options, setText='Opt2')

	tree.show()
	sys.exit(qApp.exec_())



# #alternate call example: ------------------------------
# l = ['Create', 'Cameras', 'Editors', 'Options']
# [tree.add('QLabel', childHeader=t, setText=t) for t in l]

# l = ['Custom Camera','Set Custom Camera','Camera From View']
# [tree.add('QLabel', 'Create', setText=t) for t in l]

# l = ['camera '+str(i) for i in range(6)] #debug: dummy list
# [tree.add('QLabel', '*Cameras', setText=t, refresh=True) for t in l]

# l = ['Group Cameras']
# [tree.add('QLabel', 'Options', setText=t) for t in l]



# #using Qt Designer: ----------------------------------
# tree.convert(tree.getTopLevelItems(), 'QLabel')


# #test dict --------------------------------------------
# 	#widget					#header	  #col #row #childHeader
# widgets = {
# 	'<Custom Camera>':		['Create',	1, 0, None],
# 	'<Cameras>':			['root', 	0, 1, 'Cameras'], 
# 	'<Set Custom Camera>':	['Create',	1, 1, None], 
# 	'<Cam1>':				['Cameras', 2, 1, None],
# 	'<Cam2>':				['Cameras', 2, 2, None],
# 	'<opt2>':				['Options', 3, 4, None], 
# 	'<Create>':				['root', 	0, 0, 'Create'], 
# 	'<Camera From View>':	['Create', 	1, 2, None], 
# 	'<Options>':			['Cameras', 2, 3, 'Options'], 
# 	'<opt1>':				['Options', 3, 3, None]
# }
# # -----------------------------------------------------





# depricated: ---------------------------------------------------------------------------



# def setAttributes(self, attributes=None, action=None, order=['show'], **kwargs):
	# 	'''
	# 	Internal use. Works with attributes passed in as a dict or kwargs.
	# 	If attributes are passed in as a dict, kwargs are ignored.

	# 	:Parameters:
	# 		attributes (dict) = keyword attributes and their corresponding values.
	# 		action (obj) = the child action or widgetAction to set attributes for. (default=None)
	# 		#order (list) = list of string keywords. ie. ['move', 'show']. attributes in this list will be set last, by list order. an example would be setting move positions after setting resize arguments, or showing the widget only after other attributes have been set.
	# 	kw:Parameters:
	# 		set any keyword arguments.
	# 	'''
	# 	if not attributes:
	# 		attributes = kwargs

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
	# 		insertSeparator_ (bool) = insert a line separater before the new widget.
	# 		setLayoutDirection_ (str) = set the layout direction using a string value. ie. 'LeftToRight'
	# 		setAlignment_ (str) = set the alignment using a string value. ie. 'AlignVCenter'
	# 		setButtonSymbols_ (str) = set button symbols using a string value. ex. ie. 'PlusMinus'
	# 		setMinMax_ (str) = set the min, max, and step value using a string value. ex. '.01-10 step.1'
	# 	'''
	# 	if attr=='insertSeparator_':
	# 		self.insertSeparator(action)

	# 	elif attr=='setLayoutDirection_':
	# 		self.setAttributes({'setLayoutDirection':getattr(QtCore.Qt, value)}, action)

	# 	elif attr=='setAlignment_':
	# 		self.setAttributes({'setAlignment':getattr(QtCore.Qt, value)}, action)

	# 	elif attr=='setButtonSymbols_':
	# 		self.setAttributes({'setButtonSymbols':getattr(QtWidgets.QAbstractSpinBox, value)}, action)

	# 	#presets
	# 	elif attr=='setMinMax_':
	# 		minimum = float(value.split('-')[0])
	# 		maximum = float(value.split('-')[1].split()[0])
	# 		step = float(value.split()[1].strip('step'))

	# 		self.setAttributes({'setMinimum':minimum, 'setMaximum':maximum, 'setSingleStep':step, 'setButtonSymbols_':'NoButtons'}, action)

	# 	else:
	# 		print('Error: {} has no attribute {}'.format(action, attr))


	


# try:
# 	if not __name__=='__main__':
# 		self.classMethod()

# except:
# 	p = self.parent()
# 	while not hasattr(p.window(), 'sb'):
# 		p = p.parent()

# 	self.sb = p.window().sb
# 	self.parentUiName = self.sb.getUiName()
# 	self.childEvents = self.sb.getClassInstance('EventFactoryFilter')
# 	self.classMethod = self.sb.getMethod(self.parentUiName, self)
# 	self.classMethod()

# if self.refresh:
# 	widgets = self.getWidgets(refreshedWidgets=1) #get only any newly created widgets on each refresh.
# else:
# 	widgets = self.getWidgets(removeNoneValues=1) #get all widgets on first show.
# self.childEvents.addWidgets(self.parentUiName, widgets) #removeWidgets=self._gcWidgets.keys()




	# def isExistingWidget(self, widget, column, row):
	# 	'''
	# 	'''
	# 	wItem = self.getWItemFromRow(row) #get the top widgetItem.
	# 	if self.itemWidget(wItem, column).text()==widget.text():
	# 		print (widget.text())
	# 		return True



	# def EnterEvent(self, event):
	# 	'''
	# 	'''
	# 	print ('EnterEvent')
	# 	self._setEnabledState(0) #set widgets enabled/disabled
	# 	self._resize(0)
	# 	self._showColumns(0)
	# 	QtWidgets.QApplication.sendEvent(self._mouseGrabber, self.hoverMove)
		
	# 	return QtWidgets.QTreeWidget.EnterEvent(self, event)

	# def clear_(self):
	# 	'''
	# 	'''
	# 	self.widgets.clear()
	# 	self.clear()
	# 	# for column in self.getColumns():
	# 	# 	if column is not 0:
	# 	# 		for wItem in self.getTopLevelItems():
	# 	# 			widget = self.itemWidget(wItem, column)
	# 	# 			# self.removeItemWidget(wItem, column)
	# 	# 			self.removeChild(wItem, column)
	# 	# 			self.widgets.pop(widget, None) #remove the widget from the widgets dict.
	# 	# 			if widget:
	# 	# 				shiboken2.delete(widget)

	# 	# 		if widget:
	# 	# 			print (widget)
	# 	# 			shiboken2.delete(widget)
	# 	# gc = [w for w in self.widgets if self.getColumnFromWidget(w) is not 0]
	# 	# for widget in gc:
	# 	# 	self.widgets.pop(widget, None) #remove the widget from the widgets dict.
	# 	# 	# if widget:
	# 	# 	# 	shiboken2.delete(widget)


			# className = self.window().sb.getUiName(case='pascalCase')
			# class_ = self.window().sb.getClassInstance(className)
			# self.classMethod = getattr(class_, str(self.objectName()))

	# className = self.window().sb.getUiName(case='pascalCase')
	# class_ = self.window().sb.getClassInstance(className)
	# try:
		# self.classMethod = getattr(class_, str(self.objectName()))
	# except AttributeError as error:
	# 	print('Error:', self.__class__.__name__, 'in getattr:', error, '')