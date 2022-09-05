# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.pivot import Pivot



class Pivot_maya(Pivot, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Pivot.__init__(self, *args, **kwargs)

		cmb = self.sb.pivot.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		ctx = self.sb.pivot.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Reset Pivot Position', setObjectName='chk000', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Reset Pivot Orientation', setObjectName='chk001', setChecked=True, setToolTip='')

		ctx = self.sb.pivot.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QRadioButton', setText='Component', setObjectName='chk002', setToolTip='Center the pivot on the center of the selected component\'s bounding box')
			ctx.add('QRadioButton', setText='Object', setObjectName='chk003', setChecked=True, setToolTip='Center the pivot on the center of the object\'s bounding box')
			ctx.add('QRadioButton', setText='World', setObjectName='chk004', setToolTip='Center the pivot on world origin.')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.pivot.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.hideMain
	def tb000(self, state=None):
		'''Reset Pivot
		'''
		tb = self.sb.pivot.tb000

		resetPivotPosition = tb.contextMenu.chk000.isChecked() #Reset Pivot Position
		resetPivotOrientation = tb.contextMenu.chk001.isChecked() #Reset Pivot Orientation

		pm.mel.manipPivotReset(int(resetPivotPosition), int(resetPivotOrientation))
		pm.inViewMessage(statusMessage='Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.'.format(resetPivotPosition, resetPivotOrientation), pos='topCenter', fade=True)
		# self.messageBox('Reset Pivot Position <hl>{0}</hl>.<br>Reset Pivot Orientation <hl>{1}</hl>.'.format(resetPivotPosition, resetPivotOrientation))


	def tb001(self, state=None):
		'''Center Pivot
		'''
		tb = self.sb.pivot.tb001

		component = tb.contextMenu.chk002.isChecked()
		object_ = tb.contextMenu.chk003.isChecked()
		world = tb.contextMenu.chk004.isChecked()

		pm.mel.manipPivotReset(1, 1) #reset Pivot Position and Orientation.

		if component: #Set pivot points to the center of the component's bounding box.
			pm.xform(centerPivotsOnComponents=1)
		elif object_: ##Set pivot points to the center of the object's bounding box
			pm.xform(centerPivots=1)
		elif world:
			pm.xform(worldSpace=1, pivots=[0,0,0])


	def b004(self):
		'''Bake Pivot
		'''
		sel = pm.ls(sl=1)
		self.bakeCustomPivot(sel, position=1, orientation=1) #pm.mel.BakeCustomPivot()


	@staticmethod
	def resetPivotTransforms(objects):
		'''Reset Pivot Transforms
		'''
		objs = pm.ls(type=('transform', 'geometryShape'), sl=1)

		if len(objs)>0:
			pm.xform(cp=1)
			
		pm.manipPivot(ro=1, rp=1)


	@staticmethod
	def bakeCustomPivot(objects, position=False, orientation=False):
		'''
		'''
		transforms = pm.ls(objects, transforms=1)
		shapes = pm.ls(objects, shapes=1)
		objects = transforms+pm.listRelatives(shapes, path=1, parent=1, type='transform')

		ctx = pm.currentCtx()
		pivotModeActive = 0
		customModeActive = 0
		if ctx in ('RotateSuperContext', 'manipRotateContext'): #Rotate tool
			customOri = pm.manipRotateContext('Rotate', q=1, orientAxes=1)
			pivotModeActive = pm.manipRotateContext('Rotate', q=1, editPivotMode=1)
			customModeActive = pm.manipRotateContext('Rotate', q=1, mode=1)==3
		elif ctx in ('scaleSuperContext', 'manipScaleContext'): #Scale tool
			customOri = pm.manipScaleContext('Scale', q=1, orientAxes=1)
			pivotModeActive = pm.manipScaleContext('Scale', q=1, editPivotMode=1)
			customModeActive = pm.manipScaleContext('Scale', q=1, mode=1)==6
		else: #use the move tool orientation
			customOri = pm.manipMoveContext('Move', q=1, orientAxes=1) #get custom orientation
			pivotModeActive = pm.manipMoveContext('Move', q=1, editPivotMode=1)
			customModeActive = pm.manipMoveContext('Move', q=1, mode=1)==6
			if not ctx in ('moveSuperContext', 'manipMoveContext'): #Move tool
				otherToolActive = 1 #some other tool 

		if orientation and customModeActive:
			if not position:
				pm.mel.error((pm.mel.uiRes("m_bakeCustomToolPivot.kWrongAxisOriToolError")))
				return

			from math import degrees

			cX, cY, cZ = customOri = [
				degrees(customOri[0]),
				degrees(customOri[1]),
				degrees(customOri[2]),
			]

			pm.rotate(objects, cX, cY, cZ, a=1, pcp=1, pgp=1, ws=1, fo=1) #Set object(s) rotation to the custom one (preserving child transform positions and geometry positions)

		if position:
			for obj in objects:
				#Get pivot in parent space
				m = pm.xform(obj, q=1, m=1)
				p = pm.xform(obj, q=1, os=1, sp=1)
				oldX, oldY, oldZ = old = [
					(p[0]*m[0] + p[1]*m[4]+ p[2]*m[8]  + m[12]),
					(p[0]*m[1] + p[1]*m[5]+ p[2]*m[9]  + m[13]),
					(p[0]*m[2] + p[1]*m[6]+ p[2]*m[10] + m[14]),
				]

				pm.xform(obj, zeroTransformPivots=1) #Zero out pivots

				#Translate obj(s) back to previous pivot (preserving child transform positions and geometry positions)
				newX, newY, newZ = new = pm.getAttr(obj.name() + '.translate') #obj.translate
				pm.move(obj, oldX-newX, oldY-newY, oldZ-newZ, pcp=1, pgp=1, ls=1, r=1)

		if pivotModeActive:
			pm.ctxEditMode() #exit pivot mode

		#Set the axis orientation mode back to obj
		if orientation and customModeActive:
			if ctx in ('RotateSuperContext', 'manipRotateContext'):
				pm.manipPivot(rotateToolOri=0)
			elif ctx in ('scaleSuperContext', 'manipScaleContext'):
				pm.manipPivot(scaleToolOri=0)
			else: #Some other tool #Set move tool to obj mode and clear the custom ori. (so the tool won't restore it when activated)
				pm.manipPivot(moveToolOri=0)
				if not ctx in ('moveSuperContext', 'manipMoveContext'):
					pm.manipPivot(ro=1)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------