# !/usr/bin/python
# coding=utf-8
from PySide2 import QtWidgets, QtCore

from attributes import Attributes
from text import RichText
from menu import MenuInstance


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


class CheckBox(QtWidgets.QCheckBox, MenuInstance, Attributes, RichText):
	'''
	'''
	def __init__(self, parent=None, **kwargs):
		QtWidgets.QCheckBox.__init__(self, parent)

		self.setStyleSheet(parent.styleSheet()) if parent else None

		self.setCheckBoxRichTextStyle(self.isChecked()) #set the initial style for rich text depending on the current state.
		self.stateChanged.connect(lambda state: self.setCheckBoxRichTextStyle(state)) #set the style on future state changes.

		#override built-ins
		self.text = self.richText
		self.setText = self.setRichText
		self.sizeHint = self.richTextSizeHint

		self.setAttributes(**kwargs)


	def setCheckBoxRichTextStyle(self, state):
		'''
		'''
		if self.hasRichText:
			self.setRichTextStyle(textColor='black' if state>0 else 'white')


	def checkState_(self):
		'''Get the state of a checkbox as an integer value.
		Simplifies working with tri-state checkboxes.
		'''
		if self.isTristate():		
			state = {QtCore.Qt.CheckState.Unchecked:0, QtCore.Qt.CheckState.PartiallyChecked:1, QtCore.Qt.CheckState.Checked:2}
			return state[self.checkState()]

		else:
			return 1 if self.isChecked() else 0


	def mousePressEvent(self, event):
		'''
		:Parameters:
			event (QEvent)

		:Return:
			(QEvent)
		'''
		if event.button()==QtCore.Qt.RightButton:
			if self.ctxMenu:
				self.ctxMenu.show()

		QtWidgets.QCheckBox.mousePressEvent(self, event)









if __name__ == "__main__":
	import sys
	from PySide2.QtCore import QSize
	app = QtWidgets.QApplication(sys.argv)

	w = CheckBox(
		parent=None,
		setObjectName='chk000',
		setText='QCheckBox <b>Rich Text</b>',
		resize=QSize(125, 45),
		setWhatsThis='',
		setChecked=False,
		setVisible=True,
	)

	# w.show()
	sys.exit(app.exec_())



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

# Deprecated:

