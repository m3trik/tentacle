# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from max_init import *



class Pivot(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.pivot_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.pivot_ui.cmb000

		if index is 'setMenu':
			list_ = ['']
			cmb.addItems_(list_, '')
			return

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def tb000(self, state=None):
		'''Reset Pivot
		'''
		tb = self.current_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='Reset Pivot Scale', setObjectName='chk000', setChecked=True, setToolTip='')
			tb.menu_.add('QCheckBox', setText='Reset Pivot Transform', setObjectName='chk001', setChecked=True, setToolTip='')
			tb.menu_.add('QCheckBox', setText='Reset XForm', setObjectName='chk013', setToolTip='')
			return

		if tb.menu_.chk000: #Reset Pivot Scale
			rt.ResetScale(rt.selection) #Same as Hierarchy/Pivot/Reset Scale.
		
		if tb.menu_.chk001: #Reset Pivot Transform
			rt.ResetTransform(rt.selection) #Same as Hierarchy/Pivot/Reset Transform.

		if tb.menu_.chk013: #reset XForm
			rt.ResetXForm(rt.selection) #Same as the Reset XForm utility in the Utilities tab - applies XForm modifier to node, stores the current transformations in the gizmo and resets the object transformations.
			return 'Result: ResetXForm '+str([obj.name for obj in rt.selection])

		# rt.ResetPivot(rt.selection) #Same as Hierarchy/Pivot/Reset Pivot.


	def tb001(self, state=None):
		'''Center Pivot
		'''
		tb = self.pivot_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QRadioButton', setText='Component', setObjectName='chk002', setToolTip='Center the pivot on the center of the selected component\'s bounding box')
			tb.menu_.add('QRadioButton', setText='Object', setObjectName='chk003', setChecked=True, setToolTip='Center the pivot on the center of the object\'s bounding box')
			tb.menu_.add('QRadioButton', setText='World', setObjectName='chk004', setToolTip='Center the pivot on world origin.')
			tb.menu_.add('QRadioButton', setText='Object Top', setObjectName='chk005', setToolTip='Move the pivot to the top of the object.')
			tb.menu_.add('QRadioButton', setText='Object Bottom', setObjectName='chk006', setToolTip='Move the pivot to the bottom of the object.')
			tb.menu_.add('QRadioButton', setText='Object Center Left', setObjectName='chk007', setToolTip='Move the pivot to the center left of the object.')
			tb.menu_.add('QRadioButton', setText='Object Center Right', setObjectName='chk008', setToolTip='Move the pivot to the center right of the object.')
			tb.menu_.add('QRadioButton', setText='Object Bottom Left', setObjectName='chk009', setToolTip='Move the pivot to the bottom left of the object.')
			tb.menu_.add('QRadioButton', setText='Object Bottom Right', setObjectName='chk010', setToolTip='Move the pivot to the bottom right of the object.')
			tb.menu_.add('QRadioButton', setText='Object Top Left', setObjectName='chk011', setToolTip='Move the pivot to the top left of the object.')
			tb.menu_.add('QRadioButton', setText='Object Top Right', setObjectName='chk012', setToolTip='Move the pivot to the top right of the object.')
			return

		component = tb.menu_.chk002.isChecked()
		object_ = tb.menu_.chk003.isChecked()
		world = tb.menu_.chk004.isChecked()
		objectTop = tb.menu_.chk005.isChecked()
		objectBottom = tb.menu_.chk006.isChecked()
		objectCenterLeft = tb.menu_.chk007.isChecked()
		objectCenterRight = tb.menu_.chk008.isChecked()
		objectBottomLeft = tb.menu_.chk009.isChecked()
		objectBottomRight = tb.menu_.chk010.isChecked()
		objectTopLeft = tb.menu_.chk011.isChecked()
		objectTopRight = tb.menu_.chk012.isChecked()

		if component: #Set pivot points to the center of the component's bounding box.
			rt.CenterPivot(rt.selection) #Same as Hierarchy/Pivot/Affect Pivot Only - Center to Object.
		elif object_: ##Set pivot points to the center of the object's bounding box
			self.centerPivot(rt.selection)
		elif world:
			rt.selection.pivot = [0,0,0] #center pivot world 0,0,0
		elif objectTop:
			[setattr(obj, 'pivot', [obj.position.x, obj.position.y, obj.max.z]) for obj in rt.selection] #Move the pivot to the top of the object
		elif objectBottom:
			[setattr(obj, 'pivot', [obj.position.x, obj.position.y, obj.min.z]) for obj in rt.selection] #Move the pivot to the bottom of the object
		elif objectCenterLeft:
			[setattr(obj, 'pivot', [obj.min.x, obj.position.y, obj.position.z]) for obj in rt.selection] #Move the pivot to the Center left of the object
		elif objectCenterRight:
			[setattr(obj, 'pivot', [obj.max.x, obj.position.y, obj.position.z]) for obj in rt.selection] #Move the pivot to the Center right of the object
		elif objectBottomLeft:
			[setattr(obj, 'pivot', [obj.min.x, obj.position.y, obj.min.z]) for obj in rt.selection] #Move the pivot to the Bottom left of the object
		elif objectBottomRight:
			[setattr(obj, 'pivot', [obj.max.x, obj.position.y, obj.min.z]) for obj in rt.selection] #Move the pivot to the Bottom right of the object
		elif objectTopLeft:
			[setattr(obj, 'pivot', [obj.min.x, obj.position.y, obj.max.z]) for obj in rt.selection] #Move the pivot to the Top left of the object
		elif objectTopRight:
			[setattr(obj, 'pivot', [obj.max.x, obj.position.y, obj.max.z]) for obj in rt.selection] #Move the pivot to the Topright of the object


	def b000(self):
		'''Center Pivot: Object
		'''
		tb = self.pivot_ui.tb001
		tb.menu_.chk003.setChecked(True)
		self.tb001()


	def b001(self):
		'''Center Pivot: Component
		'''
		tb = self.pivot_ui.tb001
		tb.menu_.chk002.setChecked(True)
		self.tb001()


	def b002(self):
		'''Center Pivot: World
		'''
		tb = self.pivot_ui.tb001
		tb.menu_.chk004.setChecked(True)
		self.tb001()


	def b004(self):
		'''Bake Pivot
		'''
		print ('Command does not exist:', os.path.splitext(os.path.basename(__file__))[0])


	@staticmethod
	def centerPivot(objects):
		'''Center the rotation pivot on the given objects.
		'''
		for obj in objects:
			rt.toolMode.coordsys(obj) #Center Pivot Object
			obj.pivot = obj.center





	





#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------

# maxEval('max tti')

# maxEval('macros.run \"PolyTools\" \"TransformTools\")

