# !/usr/bin/python
# coding=utf-8
from PySide2 import QtCore, QtGui, QtWidgets


class RichText(object):
	'''Rich text support for widgets.
	Text with rich text formatting will be set as rich text, otherwise it will be handled as usual.

	ex. <hl style="color:red;">Error:</hl>
	ex. '<p style="color:white;">'
	ex. '<b style="font-weight: bold;">'
	ex. '<strong style="font-weight: bold;">'
	ex. '<mark style="background-color: grey">'
	'''
	hasRichText = False

	@property
	def richTextLabelDict(self):
		'''Returns a list containing any rich text labels that have been created.
		Item indices are used the keys to retrieve the label values.

		:Return:
			(list)
		'''
		try:
			return self._richTextLabelDict

		except AttributeError as error:
			self._richTextLabelDict = {}
			return self._richTextLabelDict


	@property
	def richTextSizeHintDict(self):
		'''Returns a list containing the sizeHint any rich text labels that have been created.
		Item indices are used the keys to retrieve the size values.

		:Return:
			(list)
		'''
		try:
			return self._richTextSizeHintDict

		except AttributeError as error:
			self._richTextSizeHintDict = {}
			return self._richTextSizeHintDict


	def richTextSizeHint(self, index=0):
		'''The richTextSizeHint is the sizeHint of the actual widget if it were containing the text.

		:Return:
			(str) the widget's or the label's sizeHint.
		'''
		if self.hasRichText:
			return self._richTextSizeHintDict[index]

		else:
			return self.__class__.__base__.sizeHint(self) #return standard widget sizeHint


	def _createRichTextLabel(self, index):
		'''Return a QLabel and inside a QHBoxLayout.
		'''
		layout = QtWidgets.QHBoxLayout(self)
		layout.setContentsMargins(0, 0, 0, 0)
		# layout.setSpacing(0)

		label = QtWidgets.QLabel(self)
		label.setTextFormat(QtCore.Qt.RichText)
		self.richTextLabelDict[index] = label

		label.setAttribute(QtCore.Qt.WA_TranslucentBackground)
		label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
		# label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
		layout.addWidget(label)

		self.setRichTextStyle(index)

		self.hasRichText = True

		return label


	def setRichTextStyle(self, index=0, textColor='white'):
		'''Set the stylesheet for a QLabel.

		:Parameters:

		'''
		label = self.getRichTextLabel(index)
		label.setStyleSheet('''
			QLabel {{
				color: {0};
				margin: 3px 0px 0px 0px; /* top, right, bottom, left */
				padding: 0px 5px 0px 5px; /* top, right, bottom, left */
			}}
		'''.format(textColor))


	def getRichTextLabel(self, index=0):
		'''
		'''
		try:
			label = self.richTextLabelDict[index]
		except KeyError as error:
			label = self._createRichTextLabel(index)

		return label


	def _text(self, index=None):
		'''Gets the text for the widget or widget item.

		:Parameters:
			item (str)(int) = item text or item index
		'''
		try:
			return self.__class__.__base__.text(self)

		except AttributeError as error:
			if index is not None:
				return self.__class__.__base__.itemText(self, index)
			else:
				return self.__class__.__base__.currentText(self)


	def richText(self, index=None):
		'''
		:Return:
			(str) the widget's or the label's text.
		'''
		try:
			index = index if index else 0
			label = self.richTextLabelDict[index]
			return label.text()
		except KeyError as error: #no rich text at that index. return standard text.
			pass

		return self._text(index) #return standard widget text


	def _setText(self, text, index=0):
		'''Sets the text for the widget or widget item.

		:Parameters:
			item (str)(int) = item text or item index
		'''
		try:
			self.__class__.__base__.setText(self, text)

		except AttributeError as error:
			self.__class__.__base__.setItemText(self, index, text)


	def setRichText(self, text, index=0):
		'''If the text string contains rich text formatting:
			Set the rich text label text.
			Add whitespace to the actual widget text until it matches the sizeHint of what it would containing the label's text.

		:Parameters:
			text (str) = The desired widget's display text.
			index (int) = For setting text requires an index. ie. comboBox
		'''
		if text and all(i in text for i in ('<','>')): #check the text string for rich text formatting.

			label = self.getRichTextLabel(index)

			label.setText(text)
			self.updateGeometry()

			self._setText(text, index) #temporarily set the text to get the sizeHint value.
			sizeHint = self.richTextSizeHintDict[index] = self.__class__.__base__.sizeHint(self)

			self._setText(None, index) #clear the text, and add whitespaces until the sizeHint is the correct size.
			whiteSpace=' '
			while sizeHint.width() > self.__class__.__base__.sizeHint(self).width():
				self._setText(whiteSpace, index)
				whiteSpace += ' '

		else:
			self._setText(text, index) #set standard widget text


	def setAlignment(self, alignment='AlignLeft', index=0):
		'''Override setAlignment to accept string alignment arguments as well as QtCore.Qt.AlignmentFlags.

		:Parameters:
			alignment (str)(obj) = Text alignment. valid values are: 'AlignLeft', 'AlignCenter', 'AlignRight' or QtCore.Qt.AlignLeft etc.
		'''
		if isinstance(alignment, str):
			alignment = getattr(QtCore.Qt, alignment)

		label = self.getRichTextLabel(index)
		label.setAlignment(alignment)









class TextOverlay(object):
	'''
	'''
	hasTextOverlay = False


	@property
	def textOverlayLabel(self):
		'''Return a QLabel inside a QHBoxLayout.
		'''
		try:
			return self._textOverlayLabel

		except AttributeError as error:

			layout = QtWidgets.QHBoxLayout(self)
			layout.setContentsMargins(0, 0, 0, 0)

			self._textOverlayLabel = QtWidgets.QLabel(self)
			self._textOverlayLabel.setTextFormat(QtCore.Qt.RichText)

			self._textOverlayLabel.setAttribute(QtCore.Qt.WA_TranslucentBackground)
			self._textOverlayLabel.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents)
			layout.addWidget(self._textOverlayLabel)

			self._textOverlayLabel.setStyleSheet('''
					QLabel {
						margin: 3px 0px 0px 0px; /* top, right, bottom, left */
						padding: 0px 2px 0px 2px; /* top, right, bottom, left */
					}''')

			self.hasTextOverlay = True

			return self._textOverlayLabel


	def setTextOverlay(self, text, color=None, alignment=None):
		'''If the text string contains rich text formatting:
			Set the rich text label text.
			Add whitespace to the actual widget text until it matches the sizeHint of what it would containing the label's text.

		:Parameters:
			text (str) = The desired widget's display text.
			index (int) = For setting text requires an index. ie. comboBox
			color (str) =  The desired text color.
			alignment (str)(obj) = Text alignment. valid values are: 'AlignLeft', 'AlignCenter', 'AlignRight' or QtCore.Qt.AlignLeft etc.
		'''
		self.textOverlayLabel.setText(text)

		if color is not None:
			self.setTextOverlayColor(color)

		if alignment is not None:
			self.setTextOverlayAlignment(alignment)


	def setTextOverlayAlignment(self, alignment='AlignLeft'):
		'''Override setAlignment to accept string alignment arguments as well as QtCore.Qt.AlignmentFlags.

		:Parameters:
			alignment (str)(obj) = Text alignment. valid values are: 'AlignLeft', 'AlignCenter', 'AlignRight' or QtCore.Qt.AlignLeft etc.
		'''
		if isinstance(alignment, str):
			alignment = getattr(QtCore.Qt, alignment)

		self.textOverlayLabel.setAlignment(alignment)


	def setTextOverlayColor(self, color):
		'''Set the stylesheet for a QLabel.

		:Parameters:
			color (str) =  The desired text color.

		ex. call: setTextOverlayColor('rgb(185,185,185)')
		'''
		label.setStyleSheet('''
				QLabel {{
					color: {0};
				}}
			'''.format(color))









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