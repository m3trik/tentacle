# !/usr/bin/python
# coding=utf-8
from maya_init import *



class Transform(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.transform_ui.draggable_header

		if state=='setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.transform_ui.draggable_header.contextMenu.cmb000

		if index=='setMenu':
			files = ['']
			cmb.addItems_(files, '')
			return

		if index>0:
			if index==cmd.list.index(''):
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Transform Constraints

		constrain along normals #checkbox option for edge amd surface constaints
		setXformConstraintAlongNormal false;
		'''
		cmb = self.transform_ui.cmb001

		if index=='setMenu':
			cmb.popupStyle = 'qmenu'
			cmb.menu_.setTitle('Constaints')

			#query and set current states:
			edge_constraint = True if pm.xformConstraint(query=1, type=1)=='edge' else False
			surface_constraint = True if pm.xformConstraint(query=1, type=1)=='surface' else False
			live_object = True if pm.ls(live=1) else False

			values = [('chk024', 'Edge', edge_constraint),
					('chk025', 'Surface', surface_constraint),
					('chk026', 'Make Live', live_object)]

			[cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName=chk, setText=typ, setChecked=state) for chk, typ, state in values]
			return


	def cmb002(self, index=-1):
		'''Align To
		'''
		cmb = self.transform_ui.cmb002

		if index=='setMenu':
			list_ = ['Point to Point', '2 Points to 2 Points', '3 Points to 3 Points', 'Align Objects', 'Position Along Curve', 'Align Tool', 'Snap Together Tool', 'Orient to Vertex/Edge Tool']
			cmb.addItems_(list_, 'Align To')
			return

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


	def cmb003(self, index=-1):
		'''Transform Tool Snapping
		'''
		cmb = self.transform_ui.cmb003

		if index=='setMenu':
			cmb.popupStyle = 'qmenu'
			cmb.menu_.setTitle('Snap')

			moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
			scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
			rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)

			values = [('chk021', 'Move: <b>Off</b>'), ('s021', 'increment:', moveValue, '1.00-1000 step2.8125'), 
					('chk022', 'Scale: <b>Off</b>'), ('s022', 'increment:', scaleValue, '1.00-1000 step2.8125'), 
					('chk023', 'Rotate: <b>Off</b>'), ('s023', 'degrees:', rotateValue, '1.00-360 step2.8125')]

			widgets = [cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName=i[0], setText=i[1], setTristate=1) if len(i)==2 
					else cmb.menu_.add('QDoubleSpinBox', setObjectName=i[0], setPrefix=i[1], setValue=i[2], setMinMax_=i[3], setDisabled=1) for i in values]
			return


	def chk014(self, state=None):
		'''Snap: Toggle Rotation
		'''
		cmb = self.transform_ui.cmb003

		cmb.menu_.chk023.setChecked(True)
		cmb.menu_.s023.setValue(11.25)
		state = 1 if self.transform_submenu_ui.chk014.isChecked() else 0
		self.chk023(state=state)


	def chk021(self, state=None):
		'''Transform Tool Snap Settings: Move
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Move: <b>Off</b>', 1:'Move: <b>Relative</b>', 2:'Move: <b>Absolute</b>'}

		cmb.menu_.chk021.setText(text[state])
		cmb.menu_.s021.setEnabled(state)
		pm.manipMoveContext('Move', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texMoveContext('texMoveContext', edit=1, snap=False if state is 0 else True) #uv move context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


	def chk022(self, state=None):
		'''Transform Tool Snap Settings: Scale
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Scale: <b>Off</b>', 1:'Scale: <b>Relative</b>', 2:'Scale: <b>Absolute</b>'}

		cmb.menu_.chk022.setText(text[state])
		cmb.menu_.s022.setEnabled(state)
		pm.manipScaleContext('Scale', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texScaleContext('texScaleContext', edit=1, snap=False if state is 0 else True) #uv scale context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


	def chk023(self, state=None):
		'''Transform Tool Snap Settings: Rotate
		'''
		cmb = self.transform_ui.cmb003
		text = {0:'Rotate: <b>Off</b>', 1:'Rotate: <b>Relative</b>', 2:'Rotate: <b>Absolute</b>'}

		cmb.menu_.chk023.setText(text[state])
		cmb.menu_.s023.setEnabled(state)
		pm.manipRotateContext('Rotate', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texRotateContext('texRotateContext', edit=1, snap=False if state is 0 else True) #uv rotate context

		cmb.setCurrentText('Snap: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked())) else cmb.setCurrentText('Snap: <hl style="color:green;">On</hl>')


	def chk024(self, state=None):
		'''Transform Constraints: Edge
		'''
		if state:
			pm.xformConstraint(type='edge') #pm.manipMoveSetXformConstraint(edge=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb = self.transform_ui.cmb001
		cmb.setCurrentText('Constrain: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk025.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: <hl style="color:green;">On</hl>')


	def chk025(self, state=None):
		'''Transform Contraints: Surface
		'''
		if state:
			pm.xformConstraint(type='surface') #pm.manipMoveSetXformConstraint(surface=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb = self.transform_ui.cmb001
		cmb.setCurrentText('Constrain: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk024.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: <hl style="color:green;">On</hl>')


	def chk026(self, state=None):
		'''Transform Contraints: Make Live
		'''
		cmb = self.transform_ui.cmb001
		chk = cmb.menu_.chk026

		selection = pm.ls(sl=1, objectsOnly=1)
		if state and selection:
			live_object = pm.ls(live=1)
			shape = self.getShapeNode(selection[0])
			if not shape in live_object:
				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
				# self.viewPortMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
		else:
			pm.makeLive(none=True)
			# self.viewPortMessage('Make Live: <hl>Off</hl>')

		cmb.setCurrentText('Constrain: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk024.isChecked(), cmb.menu_.chk025.isChecked())) else cmb.setCurrentText('Constrain: <hl style="color:green;">On</hl>')


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


	def chk010(self, state=None):
		'''Align Vertices: Auto Align
		'''
		if self.transform_ui.tb001.contextMenu.chk010.isChecked():
			self.toggleWidgets(setDisabled='chk029-31')
		else:
			self.toggleWidgets(setEnabled='chk029-31')


	def tb000(self, state=None):
		'''Drop To Grid
		'''
		tb = self.current_ui.tb000
		if state=='setMenu':
			tb.contextMenu.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
			tb.contextMenu.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
			tb.contextMenu.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=False, setToolTip='Center pivot on objects bounding box.')
			tb.contextMenu.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=True, setToolTip='Reset the selected transform and all of its children down to the shape level.')
			return

		align = tb.contextMenu.cmb004.currentText()
		origin = tb.contextMenu.chk014.isChecked()
		centerPivot = tb.contextMenu.chk016.isChecked()
		freezeTransforms = tb.contextMenu.chk017.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)
		Init.dropToGrid(objects, align, origin, centerPivot, freezeTransforms)
		pm.select(objects) #reselect the original selection.


	@Slots.message
	def tb001(self, state=None):
		'''Align Components

		Auto Align finds the axis with the largest variance, and sets the axis checkboxes accordingly before performing a regular align.
		'''
		tb = self.current_ui.tb001
		if state=='setMenu':
			tb.contextMenu.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
			tb.contextMenu.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
			tb.contextMenu.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
			tb.contextMenu.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
			tb.contextMenu.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
			tb.contextMenu.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
			tb.contextMenu.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
			tb.contextMenu.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')
			return

		betweenTwoComponents = tb.contextMenu.chk013.isChecked()
		autoAlign = tb.contextMenu.chk010.isChecked()
		autoAlign2Axes = tb.contextMenu.chk011.isChecked() #Auto Align: Two Axes

		selection = pm.ls(orderedSelection=1, flatten=1)

		if betweenTwoComponents:
			if len(selection)>1:
				componentsOnPath = Init.getPathAlongLoop([selection[0], selection[-1]])
				pm.select(componentsOnPath)

		if autoAlign: #set coordinates for auto align:
			if len(selection)>1:

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
					return 'Error: Unable to get component path.'
				vertexTangent = pm.polyNormalPerVertex(vertex, query=True, xyz=True)

				tx = abs(round(vertexTangent[0], 4))
				ty = abs(round(vertexTangent[1], 4))
				tz = abs(round(vertexTangent[2], 4))

				axis = max(x,y,z)
				tangent = max(tx,ty,tz)

				if autoAlign2Axes:
					if axis==x: #"yz"
						self.toggleWidgets(tb.contextMenu, setChecked='chk030-31', setUnChecked='chk029')
					if axis==y: #"xz"
						self.toggleWidgets(tb.contextMenu, setChecked='chk029,chk031', setUnChecked='chk030')
					if axis==z: #"xy"
						self.toggleWidgets(tb.contextMenu, setChecked='chk029-30', setUnChecked='chk031')
				else:
					if any ([axis==x and tangent==ty, axis==y and tangent==tx]): #"z"
						self.toggleWidgets(tb.contextMenu, setChecked='chk031', setUnChecked='chk029-30')
					if any ([axis==x and tangent==tz, axis==z and tangent==tx]): #"y"
						self.toggleWidgets(tb.contextMenu, setChecked='chk030', setUnChecked='chk029,chk031')
					if any ([axis==y and tangent==tz, axis==z and tangent==ty]): #"x"
						self.toggleWidgets(tb.contextMenu, setChecked='chk029', setUnChecked='chk030-31')
			else:
				return 'Error: Operation requires a component selection.'

		#align
		x = tb.contextMenu.chk029.isChecked()
		y = tb.contextMenu.chk030.isChecked()
		z = tb.contextMenu.chk031.isChecked()
		avg = tb.contextMenu.chk006.isChecked()
		loop = tb.contextMenu.chk007.isChecked()

		if all ([x, not y, not z]): #align x
			self.alignVertices(mode=3,average=avg,edgeloop=loop)

		if all ([not x, y, not z]): #align y
			self.alignVertices(mode=4,average=avg,edgeloop=loop)

		if all ([not x, not y, z]): #align z
			self.alignVertices(mode=5,average=avg,edgeloop=loop)

		if all ([not x, y, z]): #align yz
			self.alignVertices(mode=0,average=avg,edgeloop=loop)

		if all ([x, not y, z]): #align xz
			self.alignVertices(mode=1,average=avg,edgeloop=loop)

		if all ([x, y, not z]): #align xy
			self.alignVertices(mode=2,average=avg,edgeloop=loop)

		if all ([x, y, z]): #align xyz
			self.alignVertices(mode=6,average=avg,edgeloop=loop)


	def lbl000(self):
		'''Transform Constraints: Disable All
		'''
		cmb = self.transform_ui.cmb001
		cmb.setCurrentIndex(0)


	@Slots.message
	@Slots.hideMain
	def b000(self):
		'''Object Transform Attributes
		'''
		node = pm.ls(sl=1, objectsOnly=1)
		if not node:
			return 'Error: Operation requires a single selected object.'
		transform = Init.getTransformNode(node)

		self.setAttributeWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)


	@Slots.message
	@Slots.hideMain
	def b000(self):
		'''Object Transform Attributes
		'''
		node = pm.ls(sl=1, objectsOnly=1)
		if not node:
			return 'Error: Operation requires a single selected object.'
		transform = Init.getTransformNode(node)

		self.setAttributeWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)


	def b002(self):
		'''Freeze Transformations
		'''
		pm.makeIdentity(apply=True, translate=True, rotate=True, scale=True) #this is the same as pm.makeIdentity(apply=True)


	def b003(self):
		'''Center Pivot Object
		'''
		pm.mel.CenterPivot()


	def b005(self):
		'''Move To
		'''
		sel = rt.getCurrentSelection()

		source = sel[0]
		target = sel[1]
		#move object to center of the last selected items bounding box
		source.center = target.center


	def b012(self):
		'''Make Live (Toggle)
		'''
		cmb = self.transform_ui.cmb001
		selection = pm.ls(sl=1, objectsOnly=1)

		if selection:
			live_object = pm.ls(live=1)
			shape = self.getShapeNode(selection[0])
			if not shape in live_object:
				self.chk026(state=1)
				cmb.menu_.chk026.setChecked(True)
		else:
			self.chk026(state=0)
			cmb.menu_.chk026.setChecked(False)


	def b014(self):
		'''Center Pivot Component
		'''
		[pm.xform (s, centerPivot=1) for s in pm.ls (sl=1, objectsOnly=1, flatten=1)]
		# mel.eval("moveObjectPivotToComponentCentre;")


	def b015(self):
		'''Center Pivot World
		'''
		pm.xform(pivots=(0, 0, 0), worldSpace=1)


	def b016(self):
		'''Set To Bounding Box
		'''
		mel.eval("bt_alignPivotToBoundingBoxWin;")


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









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------



# deprecated ------------------------------------



	# def lbl001(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.transform_ui.cmb003
	# 	self.toggleWidgets(setUnChecked='chk021-23')
	# 	cmb.setCurrentText('Off') if not any((cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	# def lbl002(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.transform_ui.cmb001
	# 	self.toggleWidgets(setUnChecked='chk024-26')
	# 	cmb.setCurrentText('Off') if not any((cmb.menu_.chk024.isChecked(), cmb.menu_.chk025.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('On')


	# def s002(self, value=None):
	# 	'''
	# 	Transform: Set Step
	# 	'''
	# 	value = self.transform_ui.s002.value()
	# 	self.transform_ui.s000.setStep(value)

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
	# 	self.toggleWidgets(setUnChecked='chk008-9', setChecked='chk000-2')
	# 	self.transform_ui.s000.setValue(2)
	# 	self.transform_ui.s000.setSingleStep(1)


	# def chk008(self, state=None):
	# 	'''
	# 	Transform: Move

	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk005,chk009,chk000-2')
	# 	self.transform_ui.s000.setValue(0.1)
	# 	self.transform_ui.s000.setSingleStep(0.1)


	# def chk009(self, state=None):
	# 	'''
	# 	Transform: Rotate

	# 	'''
	# 	self.toggleWidgets(setUnChecked='chk005,chk008,chk000-2')
	# 	self.transform_ui.s000.setValue(45)
	# 	self.transform_ui.s000.setSingleStep(5)

	# def b000(self):
	# 	'''
	# 	Transform negative axis
	# 	'''
	# 	#change the textfield to neg value and call performTransformations
	# 	textfield = float(self.transform_ui.s000.value())
	# 	if textfield >=0:
	# 		newText = -textfield
	# 		self.transform_ui.s000.setValue(newText)
	# 	self.performTransformations()


	# def b001(self):
	# 	'''
	# 	Transform positive axis
	# 	'''
	# 	#change the textfield to pos value and call performTransformations
	# 	textfield = float(self.transform_ui.s000.value())
	# 	if textfield <0:
	# 		newText = abs(textfield)
	# 		self.transform_ui.s000.setValue(newText)
	# 	self.performTransformations()


	# 	def getTransformValues(self):
	# 	'''
	# 	Get the XYZ transform values from the various ui wgts.
	# 	'''
	# 	x = self.transform_ui.chk000.isChecked()
	# 	y = self.transform_ui.chk001.isChecked()
	# 	z = self.transform_ui.chk002.isChecked()
	# 	relative = self.transform_ui.chk005.isChecked()

	# 	amount = self.transform_ui.s002.value() #use the step as the transform amount
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
	# 	relative = bool(self.transform_ui.chk003.isChecked())#Move absolute/relative toggle
	# 	worldspace = bool(self.transform_ui.chk004.isChecked())#Move object/worldspace toggle
		
	# 	scale = self.transform_ui.chk005.isChecked()
	# 	move = self.transform_ui.chk008.isChecked()
	# 	rotate = self.transform_ui.chk009.isChecked()

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


	# @Slots.message
	# def cmb002(self, index=-1):
	# 	'''
	# 	Transform Contraints

	# 	constrain along normals #checkbox option for edge amd surface constaints
	# 	setXformConstraintAlongNormal false;
	# 	'''
	# 	cmb = self.transform_ui.cmb001

	# 	if index=='setMenu':
	# 		cmb.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Disable All', setToolTip='Disable all constraints.')

	# 		list_ = ['Edge', 'Surface', 'Make Live']
	# 		cmb.addItems_(list_, 'Off')
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
	# 			selection = pm.ls(sl=1, objectsOnly=1)
	# 			if not selection and not live_object:
	# 				print ('not selection and not live_object')
	# 				cmb.setCurrentIndex(0)
	# 				return 'Error: Nothing Selected.'

	# 			if not live_object:
	# 				print ('not live_object')
	# 				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
	# 				self.viewPortMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
	# 	else:
	# 		print ('0')
	# 		pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);
	# 		if live_object:
	# 			print ('none')
	# 			pm.makeLive(none=True)
	# 			self.viewPortMessage('Make Live: <hl>Off</hl>')
