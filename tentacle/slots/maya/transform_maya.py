# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.transform import Transform


class Transform_maya(Transform, Slots_maya):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		'''
		super().__init__(*args, **kwargs)

		cmb000 = self.sb.transform.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb000.addItems_(items, '')

		cmb002 = self.sb.transform.cmb002
		items = ['Point to Point', '2 Points to 2 Points', '3 Points to 3 Points', 'Align Objects', 'Position Along Curve', 'Align Tool', 'Snap Together Tool', 'Orient to Vertex/Edge Tool']
		cmb002.addItems_(items, 'Align To')

		cmb001 = self.sb.transform.cmb001
		edge_constraint = True if pm.xformConstraint(query=1, type=1)=='edge' else False
		surface_constraint = True if pm.xformConstraint(query=1, type=1)=='surface' else False
		live_object = True if pm.ls(live=1) else False
		values = [('chk024', 'Contrain: Edge', edge_constraint), ('chk025', 'Constain: Surface', surface_constraint), ('chk026', 'Make Live', live_object)]
		[cmb001.menu_.add(self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state) for chk, typ, state in values]
		self.sb.syncWidgets(cmb001.menu_.chk024, self.sb.transform_submenu.chk024, attributes='setChecked')
		self.sb.syncWidgets(cmb001.menu_.chk025, self.sb.transform_submenu.chk025, attributes='setChecked')

		cmb003 = self.sb.transform.cmb003
		moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
		cmb003.menu_.s021.setValue(moveValue)
		scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
		cmb003.menu_.s022.setValue(scaleValue)
		rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)
		cmb003.menu_.s023.setValue(rotateValue)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.transform.draggable_header.ctxMenu.cmb000

		if index>0:
			if index==cmd.list.index(''):
				pass
			cmb.setCurrentIndex(0)


	def cmb002(self, index=-1):
		'''Align To
		'''
		cmb = self.sb.transform.cmb002

		if index>0:
			text = cmb.items[index]
			if text=='Point to Point':
				pm.mel.SnapPointToPointOptions() #performSnapPtToPt 1; Select any type of point object or component.
			elif text=='2 Points to 2 Points':
				pm.mel.Snap2PointsTo2PointsOptions() #performSnap2PtTo2Pt 1; Select any type of point object or component.
			elif text=='3 Points to 3 Points':
				pm.mel.Snap3PointsTo3PointsOptions() #performSnap3PtTo3Pt 1; Select any type of point object or component.
			elif text=='Align Objects':
				pm.mel.performAlignObjects(1) #Align the selected objects.
			elif text=='Position Along Curve':
				pm.mel.PositionAlongCurve() #Position selected objects along a selected curve.
				# import maya.app.general.positionAlongCurve
				# maya.app.general.positionAlongCurve.positionAlongCurve()
			elif text=='Align Tool':
				pm.mel.SetAlignTool() #setToolTo alignToolCtx; Align the selection to the last selected object.
			elif text=='Snap Together Tool':
				pm.mel.SetSnapTogetherToolOptions() #setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.
			elif text=='Orient to Vertex/Edge Tool':
				pm.mel.orientToTool() #Orient To Vertex/Edge
			cmb.setCurrentIndex(0)


	def chk024(self, state=None):
		'''Transform Constraints: Edge
		'''
		cmb = self.sb.transform.cmb001
		state = cmb.menu_.chk024.isChecked() #explicit because state not being passed from submenu checkboxes.

		if state:
			pm.xformConstraint(type='edge') #pm.manipMoveSetXformConstraint(edge=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb.setCurrentText('Constrain: OFF') if not any((state, cmb.menu_.chk025.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: ON')


	def chk025(self, state=None):
		'''Transform Contraints: Surface
		'''
		cmb = self.sb.transform.cmb001
		state = cmb.menu_.chk025.isChecked()

		if state:
			pm.xformConstraint(type='surface') #pm.manipMoveSetXformConstraint(surface=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb.setCurrentText('Constrain: OFF') if not any((state, cmb.menu_.chk024.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: ON')


	def chk026(self, state=None):
		'''Transform Contraints: Make Live
		'''
		cmb = self.sb.transform.cmb001
		state = cmb.menu_.chk026.isChecked()

		selection = pm.ls(sl=1, objectsOnly=1, type='transform')
		if state and selection:
			live_object = pm.ls(live=1)
			shape = mtk.Node.getShapeNode(selection[0])
			if not shape in str(live_object):
				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
				# mtk.viewportMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
		else:
			pm.makeLive(none=True)
			# mtk.viewportMessage('Make Live: <hl>Off</hl>')

		cmb.setCurrentText('Constrain: OFF') if not any((state, cmb.menu_.chk024.isChecked(), cmb.menu_.chk025.isChecked())) else cmb.setCurrentText('Constrain: ON')


	def s021(self, value=None):
		'''Transform Tool Snap Settings: Spinboxes
		'''
		pm.manipMoveContext('Move', edit=1, snapValue=value)
		pm.texMoveContext('texMoveContext', edit=1, snapValue=value) #uv move context


	def s022(self, value=None):
		'''Transform Tool Snap Settings: Spinboxes
		'''
		pm.manipScaleContext('Scale', edit=1, snapValue=value)
		pm.texScaleContext('texScaleContext', edit=1, snapValue=value) #uv scale context


	def s023(self, value=None):
		'''Transform Tool Snap Settings: Spinboxes
		'''
		pm.manipRotateContext('Rotate', edit=1, snapValue=value)
		pm.texRotateContext('texRotateContext', edit=1, snapValue=value) #uv rotate context


	def tb000(self, state=None):
		'''Drop To Grid
		'''
		tb = self.sb.transform.tb000

		align = tb.ctxMenu.cmb004.currentText()
		origin = tb.ctxMenu.chk014.isChecked()
		centerPivot = tb.ctxMenu.chk016.isChecked()
		freezeTransforms = tb.ctxMenu.chk017.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)
		mtk.Xform.dropToGrid(objects, align, origin, centerPivot, freezeTransforms)
		pm.select(objects) #reselect the original selection.


	def tb001(self, state=None):
		'''Align Components

		Auto Align finds the axis with the largest variance, and sets the axis checkboxes accordingly before performing a regular align.
		'''
		tb = self.sb.transform.tb001

		betweenTwoComponents = tb.ctxMenu.chk013.isChecked()
		autoAlign = tb.ctxMenu.chk010.isChecked()
		autoAlign2Axes = tb.ctxMenu.chk011.isChecked() #Auto Align: Two Axes

		selection = pm.ls(orderedSelection=1, flatten=1)

		if betweenTwoComponents:
			if len(selection)>1:
				componentsOnPath = mtk.Cmpt.getEdgePath(selection, 'edgeLoopPath')
				pm.select(componentsOnPath)

		if autoAlign: #set coordinates for auto align:
			if not len(selection)>1:
				self.sb.messageBox('Operation requires a component selection.')
				return

			point = pm.xform(selection, q=True, t=True, ws=True)
			#vertex point 1
			x1 = round(point[0], 4)
			y1 = round(point[1], 4)
			z1 = round(point[2], 4)

			#vertex point 2
			x2 = round(point[3], 4)
			y2 = round(point[4], 4)
			z2 = round(point[5], 4)

			#find the axis with the largest variance to determine direction.
			x = abs(x1-x2)
			y = abs(y1-y2)
			z = abs(z1-z2)

			maskEdge = pm.selectType (query=True, edge=True)
			if maskEdge:
				selection = pm.polyListComponentConversion(fromEdge=1, toVertexFace=1)

			vertex = selection[0] if selection else None
			if vertex is None:
				self.sb.messageBox('Unable to get component path.')
				return

			vertexTangent = pm.polyNormalPerVertex(vertex, query=True, xyz=True)

			tx = abs(round(vertexTangent[0], 4))
			ty = abs(round(vertexTangent[1], 4))
			tz = abs(round(vertexTangent[2], 4))

			axis = max(x,y,z)
			tangent = max(tx,ty,tz)

			if autoAlign2Axes:
				if axis==x: #"yz"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk030-31', setUnChecked='chk029')
				if axis==y: #"xz"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk029,chk031', setUnChecked='chk030')
				if axis==z: #"xy"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk029-30', setUnChecked='chk031')
			else:
				if any ([axis==x and tangent==ty, axis==y and tangent==tx]): #"z"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk031', setUnChecked='chk029-30')
				if any ([axis==x and tangent==tz, axis==z and tangent==tx]): #"y"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk030', setUnChecked='chk029,chk031')
				if any ([axis==y and tangent==tz, axis==z and tangent==ty]): #"x"
					self.sb.toggleWidgets(tb.ctxMenu, setChecked='chk029', setUnChecked='chk030-31')

		#align
		x = tb.ctxMenu.chk029.isChecked()
		y = tb.ctxMenu.chk030.isChecked()
		z = tb.ctxMenu.chk031.isChecked()
		avg = tb.ctxMenu.chk006.isChecked()
		loop = tb.ctxMenu.chk007.isChecked()

		if all ([x, not y, not z]): #align x
			mtk.Xform.alignVertices(mode=3,average=avg,edgeloop=loop)

		if all ([not x, y, not z]): #align y
			mtk.Xform.alignVertices(mode=4,average=avg,edgeloop=loop)

		if all ([not x, not y, z]): #align z
			mtk.Xform.alignVertices(mode=5,average=avg,edgeloop=loop)

		if all ([not x, y, z]): #align yz
			mtk.Xform.alignVertices(mode=0,average=avg,edgeloop=loop)

		if all ([x, not y, z]): #align xz
			mtk.Xform.alignVertices(mode=1,average=avg,edgeloop=loop)

		if all ([x, y, not z]): #align xy
			mtk.Xform.alignVertices(mode=2,average=avg,edgeloop=loop)

		if all ([x, y, z]): #align xyz
			mtk.Xform.alignVertices(mode=6,average=avg,edgeloop=loop)


	def tb002(self, state=None):
		'''Freeze Transformations
		'''
		tb = self.sb.transform.tb002

		translate = tb.ctxMenu.chk032.isChecked()
		rotate = tb.ctxMenu.chk033.isChecked()
		scale = tb.ctxMenu.chk034.isChecked()
		centerPivot = tb.ctxMenu.chk035.isChecked()

		if centerPivot:
			pm.xform(centerPivots=1)

		pm.makeIdentity(apply=True, translate=translate, rotate=rotate, scale=scale) #this is the same as pm.makeIdentity(apply=True)


	def cmb001(self, index=-1):
		'''Transform Constraints

		constrain along normals #checkbox option for edge amd surface constaints
		setXformConstraintAlongNormal false;
		'''
		cmb = self.sb.transform.cmb001


	def cmb003(self, index=-1):
		'''Transform Tool Snapping
		'''
		cmb = self.sb.transform.cmb003


	@Slots.hideMain
	def b000(self):
		'''Object Transform Attributes
		'''
		node = pm.ls(sl=1, objectsOnly=1)
		if not node:
			self.sb.messageBox('<b>Nothing selected.</b><br>The operation requires a single selected object.')
			return

		transform = mtk.Node.getTransformNode(node)
		self.setAttributeWindow(transform, inc=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)


	def b001(self):
		'''Match Scale
		'''
		selection = pm.ls(sl=1)
		if not selection:
			self.sb.messageBox('<b>Nothing selected.</b><br>The operation requires at least two selected objects.')
			return

		frm = selection[0]
		to = selection[1:]

		mtk.Xform.matchScale(frm, to)


	def b003(self):
		'''Center Pivot Object
		'''
		pm.mel.CenterPivot()


	def b005(self):
		'''Move To
		'''
		sel = pm.ls(sl=1, transforms=1)
		if not sel:
			self.sb.messageBox('<b>Nothing selected.</b><br>The operation requires at least two selected objects.')
			return

		objects = sel[:-1]
		target = sel[-1]

		pm.matchTransform(objects, target, position=1, rotation=1, scale=0, pivots=1) #move object to center of the last selected items bounding box
		pm.select(objects)


	def b012(self):
		'''Make Live (Toggle)
		'''
		cmb = self.sb.transform.cmb001
		selection = pm.ls(sl=1, objectsOnly=1, type='transform')

		if selection:
			live_object = pm.ls(live=1)
			shape = mtk.Node.getShapeNode(selection[0])
			if not shape in str(live_object):
				self.chk026(state=1)
				cmb.menu_.chk026.setChecked(True)
		else:
			self.chk026(state=0)
			cmb.menu_.chk026.setChecked(False)


	def b014(self):
		'''Center Pivot Component
		'''
		[pm.xform (s, centerPivot=1) for s in pm.ls (sl=1, objectsOnly=1, flatten=1)]
		# pm.mel.eval("moveObjectPivotToComponentCentre;")


	def b015(self):
		'''Center Pivot World
		'''
		pm.xform(pivots=(0, 0, 0), worldSpace=1)


	def b016(self):
		'''Set To Bounding Box
		'''
		pm.mel.eval("bt_alignPivotToBoundingBoxWin;")


	def b017(self):
		'''Bake Pivot
		'''
		pm.mel.BakeCustomPivot()


	def b032(self):
		'''Reset Pivot Transforms
		'''
		objs = pm.ls(type=['transform', 'geometryShape'], sl=1)
		if len(objs)>0:
			pm.xform(cp=1)
			
		pm.manipPivot(ro=1, rp=1)

	
	def setTransformSnap(self, ctx, state):
		'''Set the transform tool's move, rotate, and scale snap states.

		Parameters:
			ctx (str): valid: 'move', 'scale', 'rotate'
			state (int): valid: 0=off, 1=relative, 2=absolute
		'''
		if ctx=='move':
			pm.manipMoveContext('Move', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
			pm.texMoveContext('texMoveContext', edit=1, snap=False if state==0 else True) #uv move context

		elif ctx=='scale':
			pm.manipScaleContext('Scale', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
			pm.texScaleContext('texScaleContext', edit=1, snap=False if state==0 else True) #uv scale context

		elif ctx=='rotate':
			pm.manipRotateContext('Rotate', edit=1, snap=False if state==0 else True, snapRelative=True if state==1 else False) #state: 0=off, 1=relative, 2=absolute
			pm.texRotateContext('texRotateContext', edit=1, snap=False if state==0 else True) #uv rotate context

# --------------------------------------------------------------------------------------------









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# deprecated ------------------------------------



	# def cmb003(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.sb.transform.cmb003
	# 	self.sb.toggleWidgets(setUnChecked='chk021-23')
	# 	cmb.setCurrentText('Off') if not any((cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	# def cmb003(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.sb.transform.lbl000
	# 	self.sb.toggleWidgets(setUnChecked='chk024-26')
	# 	cmb.setCurrentText('Off') if not any((cmb.menu_.chk024.isChecked(), cmb.menu_.chk025.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('On')


	# def s002(self, value=None):
	# 	'''
	# 	Transform: Set Step
	# 	'''
	# 	value = self.sb.transform.s002.value()
	# 	self.sb.transform.s000.setStep(value)

	# def s000(self, value=None):
		# '''
		# Transform: Perform Transformations
		# '''
		# objects = pm.ls(sl=1, objectsOnly=1)
		# xyz = self.getTransformValues()
		# self.performTransformations(objects, xyz)

	# def chk005(self, state=None):
	# 	'''
	# 	Transform: Scale

	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk008-9', setChecked='chk000-2')
	# 	self.sb.transform.s000.setValue(2)
	# 	self.sb.transform.s000.setSingleStep(1)


	# def chk008(self, state=None):
	# 	'''
	# 	Transform: Move

	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk005,chk009,chk000-2')
	# 	self.sb.transform.s000.setValue(0.1)
	# 	self.sb.transform.s000.setSingleStep(0.1)


	# def chk009(self, state=None):
	# 	'''
	# 	Transform: Rotate

	# 	'''
	# 	self.sb.toggleWidgets(setUnChecked='chk005,chk008,chk000-2')
	# 	self.sb.transform.s000.setValue(45)
	# 	self.sb.transform.s000.setSingleStep(5)

	# def b000(self):
	# 	'''
	# 	Transform negative axis
	# 	'''
	# 	#change the textfield to neg value and call performTransformations
	# 	textfield = float(self.sb.transform.s000.value())
	# 	if textfield >=0:
	# 		newText = -textfield
	# 		self.sb.transform.s000.setValue(newText)
	# 	self.performTransformations()


	# def b001(self):
	# 	'''
	# 	Transform positive axis
	# 	'''
	# 	#change the textfield to pos value and call performTransformations
	# 	textfield = float(self.sb.transform.s000.value())
	# 	if textfield <0:
	# 		newText = abs(textfield)
	# 		self.sb.transform.s000.setValue(newText)
	# 	self.performTransformations()


	# 	def getTransformValues(self):
	# 	'''
	# 	Get the XYZ transform values from the various ui wgts.
	# 	'''
	# 	x = self.sb.transform.chk000.isChecked()
	# 	y = self.sb.transform.chk001.isChecked()
	# 	z = self.sb.transform.chk002.isChecked()
	# 	relative = self.sb.transform.chk005.isChecked()

	# 	amount = self.sb.transform.s002.value() #use the step as the transform amount
	# 	floatX=floatY=floatZ = 0

	# 	if relative: #else absolute.
	# 		currentScale = pm.xform(query=1, scale=1)
	# 		floatX = round(currentScale[0], 2)
	# 		floatY = round(currentScale[1], 2)
	# 		floatZ = round(currentScale[2], 2)

	# 	if x:
	# 		floatX = amount
	# 	if y:
	# 		floatY = amount
	# 	if z:
	# 		floatZ = amount

	# 	xyz = [floatX, floatY, floatZ]
	# 	return xyz


	# def performTransformations(self, objects, xyz): #transform
	# 	'''

	# 	'''
	# 	relative = bool(self.sb.transform.chk003.isChecked())#Move absolute/relative toggle
	# 	worldspace = bool(self.sb.transform.chk004.isChecked())#Move object/worldspace toggle
		
	# 	scale = self.sb.transform.chk005.isChecked()
	# 	move = self.sb.transform.chk008.isChecked()
	# 	rotate = self.sb.transform.chk009.isChecked()

	# 	#Scale selected.
	# 	if scale:
	# 		if xyz[0] != -1: #negative values are only valid in relative mode and cannot scale relatively by one so prevent the math below which would scale incorrectly in this case.
	# 			#convert the decimal place system xform uses for negative scale values to an standard negative value
	# 			if xyz[0] < 0:
	# 				xyz[0] = xyz[0]/10.*2.5
	# 			if xyz[1] < 0:
	# 				xyz[1] = xyz[1]/10.*2.5
	# 			if xyz[2] < 0:
	# 				xyz[2] = xyz[2]/10.*2.5
	# 			pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), scale=(xyz[0], xyz[1], xyz[2]))

	# 	#Move selected relative/absolute, object/worldspace by specified amount.
	# 	if move:
	# 		pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), translation=(xyz[0], xyz[1], xyz[2]))

	# 	#Rotate selected
	# 	if rotate:
	# 		pm.xform(objects, relative=relative, worldSpace=worldspace, objectSpace=(not worldspace), rotation=(xyz[0], xyz[1], xyz[2]))


	# def cmb002(self, index=-1):
	# 	'''
	# 	Transform Contraints

	# 	constrain along normals #checkbox option for edge amd surface constaints
	# 	setXformConstraintAlongNormal false;
	# 	'''
	# 	cmb = self.sb.transform.lbl000

	# 	if index=='setMenu':
	# 		cmb.ctxMenu.add(self.sb.Label, setObjectName='lbl000', setText='Disable All', setToolTip='Disable all constraints.')

	# 		items = ['Edge', 'Surface', 'Make Live']
	# 		cmb.addItems_(items, 'Off')
	# 		return

	# 	live_object = pm.ls(live=1)
	# 	print ("live_object:", live_object)
	# 	# if not live_object and text=='Make Live'):
	# 	# 	cmb.setCurrentIndex(0)

	# 	if index>0:
	#		text = cmb.items[index]
	# 		if text=='Edge'):
	# 			pm.xformConstraint(type='edge') #pm.manipMoveSetXformConstraint(edge=True);
			
	# 		elif text=='Surface'):
	# 			pm.xformConstraint(type='surface') #pm.manipMoveSetXformConstraint(surface=True);
			
	# 		elif text=='Make Live'):
	# 			print ('3')
	# 			selection = pm.ls(sl=1, objectsOnly=1, type='transform')
	# 			if not selection and not live_object:
	# 				print ('not selection and not live_object')
	# 				cmb.setCurrentIndex(0)
	# 				return 'Error: Nothing Selected.'

	# 			if not live_object:
	# 				print ('not live_object')
	# 				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
	# 				mtk.viewportMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
	# 	else:
	# 		print ('0')
	# 		pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);
	# 		if live_object:
	# 			print ('none')
	# 			pm.makeLive(none=True)
	# 			mtk.viewportMessage('Make Live: <hl>Off</hl>')
