# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets



class RichText(object):
	'''Rich text support for widgets.
	Text with rich text formatting will be set as rich text, otherwise it will be handled as usual.

	:Parameters:
		parent (obj) = parent widget.
		alignment (str) = text alignment. valid values are: 'AlignLeft', 'AlignCenter', 'AlignRight'

	ex. <hl style="color:red;">Error:</hl>
	ex. '<p style="color:white;">'
	ex. '<b style="font-weight: bold;">'
	ex. '<strong style="font-weight: bold;">'
	ex. '<mark style="background-color: grey">'
	'''
	def __init__(self, parent=None, alignment='AlignLeft', **kwargs):
		'''
		'''
		self.alignment = getattr(QtCore.Qt, alignment)

		self.setText = self.setRichText
		self.text = self.richText
		self.sizeHint = self.richTextSizeHint


	@property
	def hasRichText(self):
		'''Query whether the widget contains rich text.

		:Return:
			(bool)
		'''
		try:
			return self._hasRichText

		except AttributeError as error:
			self._hasRichText = False
			return self._hasRichText


	@property
	def richTextLabel(self):
		'''Return a QLabel and inside a QHBoxLayout.
		'''
		try:
			return self._richTextLabel

		except AttributeError as error:
			self.__layout = QtWidgets.QHBoxLayout(self)
			self.__layout.setContentsMargins(0, 0, 0, 0)
			# self.__layout.setSpacing(0)

			self._richTextLabel = QtWidgets.QLabel(self)
			self._richTextLabel.setAttribute(QtCore.Qt.WA_TranslucentBackground)
			self._richTextLabel.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
			# self._richTextLabel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
			self._richTextLabel.setAlignment(self.alignment)

			self.__layout.addWidget(self._richTextLabel)

			self.setRichTextStyle()

			return self._richTextLabel


	def setRichTextStyle(self, textColor='white'):
		self._richTextLabel.setStyleSheet('''
			QLabel {{
				color: {0};
				margin: 3px 0px 0px 0px; /* top, right, bottom, left */
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
			}}
		'''.format(textColor))


	def setRichText(self, text):
		'''If the text string contains rich text formatting:
			Set the rich text label text.
			Add whitespace to the actual widget text until it matches the sizeHint of what it would containing the richTextLabel's text.

		:Parameters:
			text (str) = The desired widget's display text.
		'''
		if text and all(i in text for i in ('<','>')): #check the text string for rich text formatting.
			self.richTextLabel.setTextFormat(QtCore.Qt.RichText)
			self.richTextLabel.setText(text)
			self.updateGeometry()

			self.__class__.__base__.setText(self, text) #temporarily set the text to get the sizeHint value.
			self.__richTextSizeHint = self.__class__.__base__.sizeHint(self)

			self.__class__.__base__.setText(self, None) #clear the text, and add whitespaces until the sizeHint is the correct size.
			whiteSpace=' '
			while self.__richTextSizeHint.width()>self.__class__.__base__.sizeHint(self).width():
				self.__class__.__base__.setText(self, whiteSpace)
				whiteSpace += ' '

			self._hasRichText=True

		else:
			self.__class__.__base__.setText(self, text) #set standard widget text


	def richText(self):
		'''
		:Return:
			(str) the widget's or the richTextLabel's text.
		'''
		if self.hasRichText:
			text = self.richTextLabel.text()
			return text

		else:
			return self.__class__.__base__.text(self) #return standard widget text


	def richTextSizeHint(self):
		'''The richTextSizeHint is the sizeHint of the actual widget if it were containing the text.

		:Return:
			(str) the widget's or the richTextLabel's sizeHint.
		'''
		if self.hasRichText:
			return self.__richTextSizeHint

		else:
			return self.__class__.__base__.sizeHint(self) #return standard widget sizeHint









if __name__ == "__main__":
	import sys
	qApp = QtWidgets.QApplication(sys.argv)

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







# -----------------------------------------------
# Notes
# -----------------------------------------------