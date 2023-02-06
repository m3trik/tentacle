# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtWidgets

try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)

from uitk.slots import Slots
import pythontk as ptk
import mayatk as mtk


class Slots_maya(Slots):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	# ======================================================================
		'UI'
	# ======================================================================

	@classmethod
	def attr(cls, fn):
		'''A decorator for setAttributeWindow (objAttrWindow).
		'''
		def wrapper(self, *args, **kwargs):
			rtn = fn(self, *args, **kwargs)
			self.setAttributeWindow(rtn)
			return rtn
		return wrapper

	def setAttributeWindow(self, obj, inc=[], exc=[], checkableLabel=False, fn=None, fn_args=[], **attributes):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (str)(obj)(list): The object to get the attributes of, or it's name. If given as a list, only the first index will be used.
			inc (list): Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exc (list): Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']
			checkableLabel (bool): Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. setParameterValuesMEL
					The first parameter of fn is always the given object. ex. fn(obj, {'attr':<value>})
			fn_args (str)(list): Any additonal args to pass to the given fn.
			attributes (kwargs) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from mtk.Node.getAttributesMEL for the given obj.

		:Example: self.setAttributeWindow(node, attrs, fn=setParameterValuesMEL, 'transformLimits') #set attributes for the Maya command transformLimits.
		:Example: self.setAttributeWindow(transform[0], inc=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		try:
			obj = pm.ls(obj)[0]
		except Exception as error:
			return 'Error: {}.setAttributeWindow: Invalid Object: {}'.format(__name__, obj)

		fn = fn if fn else mtk.Node.setAttributesMEL

		if attributes:
			attributes = ptk.Iter.filterDict(attributes, inc, exc, keys=True)
		else:
			attributes = mtk.Node.getAttributesMEL(obj, inc=inc, exc=exc)

		menu = self.objAttrWindow(obj, checkableLabel=checkableLabel, fn=fn, fn_args=fn_args, **attributes)

		if checkableLabel:
			for c in menu.childWidgets:
				if c.__class__.__name__=='QCheckBox':
					attr = getattr(obj, c.objectName())
					c.stateChanged.connect(lambda state, obj=obj, attr=attr: pm.select(attr, deselect=not state, add=1))
					if attr in pm.ls(sl=1):
						c.setChecked(True)

	# -------------------------------------------------------------------------------------------------------------------









#module name
# print (__name__)
# ======================================================================
# Notes
# ======================================================================





#deprecated -------------------------------------

	# @staticmethod
	# def convertToWidget(name):
	# 	'''
	# 	:Parameters:
	# 		name (str): name of a Maya UI element of any type. ex. name = pm.mel.eval('$tmp=$gAttributeEditorForm') (from MEL global variable)

	# 	:Return:
	# 		(QWidget) None if the object does not exist.
	# 	'''
	# 	import shiboken2
	# 	for f in ('findControl', 'findLayout', 'findMenuItem'):
	# 		ptr = getattr(omui.MQtUtil, f)(name) #equivalent to: ex. omui.MQtUtil.findControl(name)
	# 		if ptr:
	# 			return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)