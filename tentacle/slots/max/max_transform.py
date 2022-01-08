# !/usr/bin/python
# coding=utf-8
from slots.max import *



class Transform(Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)

		ctx = self.transform_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.transform_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		cmb = self.transform_ui.cmb001
		cmb.popupStyle = 'qmenu'
		menu = cmb.menu_
		if not menu.containsMenuItems:
			menu.setTitle('Constaints')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk017', setText='Standard', setChecked=True, setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk018', setText='Body Shapes', setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk019', setText='NURBS', setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk020', setText='Point Cloud Shapes', setToolTip='')
			cmb.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Disable All', setToolTip='Disable all constraints.')
			self.connect_('chk017-20', 'toggled', self.cmb001, cmb.contextMenu) #connect to this method on toggle
			#query and set current states:
			edge_constraint = True if pm.xformConstraint(query=1, type=1)=='edge' else False
			surface_constraint = True if pm.xformConstraint(query=1, type=1)=='surface' else False
			live_object = True if pm.ls(live=1) else False

			values = [('chk024', 'Edge', edge_constraint),
					('chk025', 'Surface', surface_constraint),
					('chk026', 'Make Live', live_object)]

			[menu.add(self.tcl.wgts.CheckBox, setObjectName=chk, setText=typ, setChecked=state) for chk, typ, state in values]

		cmb = self.transform_ui.cmb002
		items = ['Point to Point', '2 Points to 2 Points', '3 Points to 3 Points', 'Align Objects', 'Position Along Curve', 'Align Tool', 'Snap Together Tool']
		cmb.addItems_(items, 'Align To')

		cmb = self.transform_ui.cmb003
		cmb.popupStyle = 'qmenu'
		menu = cmb.menu_
		if not menu.containsMenuItems:
			menu.setTitle('Snap')

			moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
			scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
			rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)

			values = [('chk021', 'Move: <b>Off</b>'), ('s021', 'increment:', moveValue, '1.00-1000 step2.8125'), 
					('chk022', 'Scale: <b>Off</b>'), ('s022', 'increment:', scaleValue, '1.00-1000 step2.8125'), 
					('chk023', 'Rotate: <b>Off</b>'), ('s023', 'degrees:', rotateValue, '1.00-360 step2.8125')]

			widgets = [menu.add(self.tcl.wgts.CheckBox, setObjectName=i[0], setText=i[1], setTristate=1) if len(i)==2 
					else menu.add('QDoubleSpinBox', setObjectName=i[0], setPrefix=i[1], setValue=i[2], setMinMax_=i[3], setDisabled=1) for i in values]

		ctx = self.transform_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
			ctx.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
			ctx.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=False, setToolTip='Center pivot on objects bounding box.')
			# ctx.add('QCheckBox', setText='Freeze Transforms', setObjectName='chk017', setChecked=False, setToolTip='Reset the selected transform and all of its children down to the shape level.')

		ctx = self.transform_ui.tb001.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
			ctx.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
			ctx.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
			ctx.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
			ctx.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
			ctx.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
			ctx.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
			ctx.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.transform_ui.draggable_header


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.transform_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Transform Contraints

		constrain along normals #checkbox option for edge amd surface constaints
		setXformConstraintAlongNormal false;
		'''
		cmb = self.transform_ui.cmb001

		cmb.menu_.clear()
		if cmb.contextMenu.chk017.isChecked(): #Standard
			cmb.setItemText(0,'Standard') #set cetagory title in standard model/view
			list_ = ['Grid Points', 'Pivot', 'Perpendicular', 'Vertex', 'Edge/Segment', 'Face', 'Grid Lines', 'Bounding Box', 'Tangent', 'Endpoint', 'Midpoint', 'Center Face']
		if cmb.contextMenu.chk018.isChecked(): #Body Shapes
			cmb.setItemText(0,'Body Shapes') #set category title in standard model/view
			list_ = ['Vertex_', 'Edge', 'Face_', 'End Edge', 'Edge Midpoint']
		if cmb.contextMenu.chk019.isChecked(): #NURBS
			cmb.setItemText(0,'NURBS') #set category title in standard model/view
			list_ = ['CV', 'Curve Center', 'Curve Tangent', 'Curve End', 'Surface Normal', 'Point', 'Curve Normal', 'Curve Edge', 'Surface Center','Surface Edge']
		if cmb.contextMenu.chk020.isChecked(): #Point Cloud Shapes
			cmb.setItemText(0,'Point Cloud Shapes') #set category title in standard model/view
			list_ = ['Point Cloud Vertex']

		widgets = [cmb.menu_.add('QCheckBox', setText=t) for t in list_]

		for w in widgets:
			try:
				w.disconnect() #disconnect all previous connections.
			except TypeError:
				pass #if no connections are present; pass
			w.toggled.connect(lambda state, widget=w: self.chkxxx(state=state, widget=widget))


	def cmb002(self, index=-1):
		'''Align To
		'''
		cmb = self.transform_ui.cmb002

		if index>0:
			text = cmb.items[index]
			if text=='Point to Point':
				mel.eval('SnapPointToPointOptions;') #performSnapPtToPt 1; Select any type of point object or component.
			elif text=='2 Points to 2 Points':
				mel.eval('Snap2PointsTo2PointsOptions;') #performSnap2PtTo2Pt 1; Select any type of point object or component.
			elif text=='3 Points to 3 Points':
				mel.eval('Snap3PointsTo3PointsOptions;') #performSnap3PtTo3Pt 1; Select any type of point object or component.
			elif text=='Align Objects':
				mel.eval('performAlignObjects 1;') #Align the selected objects.
			elif text=='Position Along Curve':
				mel.eval('PositionAlongCurve;') #Position selected objects along a selected curve.
				# import maya.app.general.positionAlongCurve
				# maya.app.general.positionAlongCurve.positionAlongCurve()
			elif text=='Align Tool':
				mel.eval('SetAlignTool;') #setToolTo alignToolCtx; Align the selection to the last selected object.
			elif text=='Snap Together Tool':
				mel.eval('SetSnapTogetherToolOptions;') #setToolTo snapTogetherToolCtx; toolPropertyWindow;) Snap two objects together.


	def cmb003(self, index=-1):
		'''Transform Tool Snapping
		'''
		cmb = self.transform_ui.cmb003


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
		text = {0:'Move <b>Off</b>', 1:'Move <b>Relative</b>', 2:'Move <b>Absolute</b>'}
		self.transform_ui.chk021.setText(text[state])
		self.transform_ui.s021.setEnabled(state)
		pm.manipMoveContext('Move', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texMoveContext('texMoveContext', edit=1, snap=False if state is 0 else True) #uv move context

		cmb = self.transform_ui.cmb003
		cmb.setCurrentText('Off') if not any((state, cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	def chk022(self, state=None):
		'''Transform Tool Snap Settings: Scale
		'''
		text = {0:'Scale <b>Off</b>', 1:'Scale <b>Relative</b>', 2:'Scale <b>Absolute</b>'}
		self.transform_ui.chk022.setText(text[state])
		self.transform_ui.s022.setEnabled(state)
		pm.manipScaleContext('Scale', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texScaleContext('texScaleContext', edit=1, snap=False if state is 0 else True) #uv scale context

		cmb = self.transform_ui.cmb003
		cmb.setCurrentText('Off') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	def chk023(self, state=None):
		'''Transform Tool Snap Settings: Rotate
		'''
		text = {0:'Rotate <b>Off</b>', 1:'Rotate <b>Relative</b>', 2:'Rotate <b>Absolute</b>'}
		self.transform_ui.chk023.setText(text[state])
		self.transform_ui.s023.setEnabled(state)
		pm.manipRotateContext('Rotate', edit=1, snap=False if state is 0 else True, snapRelative=True if state is 1 else False) #state: 0=off, 1=relative, 2=absolute
		pm.texRotateContext('texRotateContext', edit=1, snap=False if state is 0 else True) #uv rotate context

		cmb = self.transform_ui.cmb003
		cmb.setCurrentText('Off') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked())) else cmb.setCurrentText('On')


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


	def chkxxx(self, **kwargs):
		'''Transform Constraints: Constraint CheckBoxes
		'''
		try:
			Transform.setSnapState(kwargs['widget'].text(), kwargs['state'])
		except KeyError:
			pass


	@staticmethod
	def setSnapState(fn, state):
		'''Grid and Snap Settings: Modify grid and snap states.

		:Parameters:
			fn (str) = Snap string name.
			state (bool) = Desired snap state.

		Valid fn arguments for snap name:
			Body Shapes: (1) 'Vertex_', 'Edge', 'Face_', 'End Edge', 'Edge Midpoint'
			NURBS: (2) 'CV', 'Curve Center', 'Curve Tangent', 'Curve End', 'Surface Normal', 'Point', 'Curve Normal', 'Curve Edge', 'Surface Center','Surface Edge'
			Point Cloud Shapes: (3) 'Point Cloud Vertex'
			Standard: (4,5,6,7) 'Grid Points', 'Pivot', 'Perpendicular', 'Vertex', 'Edge/Segment', 'Face', 'Grid Lines', 'Bounding Box', 'Tangent', 'Endpoint', 'Midpoint', 'Center Face'

		ex. setSnapState('Edge', True)
		'''
		snaps = {
			1:['Vertex_', 'Edge', 'Face_', 'End Edge', 'Edge Midpoint'], #Body Shapes
			2:['CV', 'Curve Center', 'Curve Tangent', 'Curve End', 'Surface Normal', 'Point', 'Curve Normal', 'Curve Edge', 'Surface Center','Surface Edge'], #NURBS
			3:['Point Cloud Vertex'], #Point Cloud Shapes
			4:['Grid Points', 'Pivot'], #Standard
			5:['Perpendicular', 'Vertex'], #Standard
			6:['Edge/Segment', 'Face'], #Standard
			7:['Grid Lines', 'Bounding Box', 'Tangent', 'Endpoint', 'Midpoint', 'Center Face'] #Standard
		}

		for category, list_ in snaps.items():
			if fn in list_:
				index = list_.index(fn)+1 #add 1 to align with max array.
				rt.snapmode.setOSnapItemActive(category, index, state) #ie. rt.snapmode.setOSnapItemActive(3, 1, False) #'Point Cloud Shapes'->'Point Cloud Vertex'->Off
				print (fn, '|', state)


	def chk010(self, state=None):
		'''Align Vertices: Auto Align
		'''
		if self.transform_ui.chk010.isChecked():
			self.toggleWidgets(setDisabled='chk029-31')
		else:
			self.toggleWidgets(setEnabled='chk029-31')


	def tb000(self, state=None):
		'''Drop To Grid
		'''
		tb = self.current_ui.tb000

		align = tb.contextMenu.cmb004.currentText()
		origin = tb.contextMenu.chk014.isChecked()
		centerPivot = tb.contextMenu.chk016.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)
		Slots_max.dropToGrid(objects, align, origin, centerPivot)
		pm.select(objects) #reselect the original selection.


	@Slots.message
	def tb001(self, state=None):
		'''Align Vertices

		Auto Align finds the axis with the largest variance, and set the axis checkboxes accordingly before performing a regular align.
		'''
		tb = self.current_ui.tb001

		betweenTwoComponents = tb.contextMenu.chk013.isChecked()
		autoAlign = tb.contextMenu.chk010.isChecked()
		autoAlign2Axes = tb.contextMenu.chk011.isChecked() #Auto Align: Two Axes

		selection = pm.ls(orderedSelection=1)

		if betweenTwoComponents:
			if len(selection)>1:
				componentsOnPath = Slots_max.getPathAlongLoop([selection[0], selection[-1]])
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


	@Slots.message
	@Slots.hideMain
	def b000(self):
		'''Object Transform Attributes
		'''
		selection = list(rt.selection)
		if not selection:
			return 'Error: <b>Nothing selected.</b><br>The operation requires a single selected object.'

		obj = selection[0]

		props = ['pos.x', 'pos.y', 'pos.z', 'rotation.x_rotation', 'rotation.y_rotation', 'rotation.z_rotation', 
				'scale.x', 'scale.y', 'scale.z', 'center', 'pivot.x', 'pivot.y', 'pivot.z']
		attrs = {p:getattr(obj, p) for p in props}

		self.setAttributeWindow(obj, attributes=attrs, checkableLabel=True)


	@Slots.message
	def b001(self):
		'''Match Scale
		'''
		selection = list(rt.selection)
		if not selection:
			return 'Error: <b>Nothing selected.</b><br>The operation requires at least two selected object.'

		frm = selection[0]
		to = selection[1:]

		Slots_maya.matchScale(to, frm)


	def lbl000(self):
		'''Transform Constraints: Disable All
		'''
		widgets = self.transform_ui.cmb001.contextMenu.children_(of_type=['QCheckBox'])
		[w.setChecked(False) for w in widgets if w.isChecked()]


	def lbl001(self):
		'''Transform Tool Snapping: Disable All
		'''
		cmb = self.transform_ui.cmb003
		self.toggleWidgets(setDisabled='chk021-23')
		cmb.setCurrentText('Off') if not any((state, cmb.menu_.chk021.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	def b002(self):
		'''Freeze Transformations
		'''
		maxEval('macros.run \"Animation Tools\" \"FreezeTransform\"')


	def b003(self):
		'''Center Pivot Object
		'''
		for obj in rt.selection:
			rt.toolMode.coordsys(obj)
			obj.pivot = obj.center

	
	def b005(self):
		'''Move To
		'''
		sel = [s for s in rt.getCurrentSelection()] #rebuild selection array in python.

		objects = sel[:-1]
		target = sel[-1]
		#move object(s) to center of the last selected items bounding box
		for obj in objects: 
			obj.center = target.center


	def b014(self):
		'''Center Pivot Component
		'''
		[pm.xform (s, centerPivot=1) for s in pm.ls (sl=1, objectsOnly=1, flatten=1)]
		# mel.eval("moveObjectPivotToComponentCentre;")


	def b015(self):
		'''Center Pivot World
		'''
		mel.eval("xform -worldSpace -pivots 0 0 0;")


	def b016(self):
		'''Set To Bounding Box
		'''
		mel.eval("bt_alignPivotToBoundingBoxWin;")


	def b017(self):
		'''Bake Pivot
		'''
		mel.eval("BakeCustomPivot;")


	def b032(self):
		'''Reset Pivot Transforms
		'''
		maxEval('''
			{ string $objs[] = `ls -sl -type transform -type geometryShape`;
			if (size($objs) > 0) { xform -cp; } manipPivot -rp -ro; };
			''')




	




#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------

# deprecated:

# maxEval('max tti')

# maxEval('macros.run \"PolyTools\" \"TransformTools\")



	# def b000(self):
	# 	'''
	# 	Transform: negative
	# 	'''
	# 	#change the textfield to neg value and call performTransformations
	# 	textfield = float(self.transform_ui.s000.value())
	# 	if textfield >=0:
	# 		newText = -textfield
	# 		self.transform_ui.s000.setValue(newText)
	# 	self.performTransformations()


	# def b001(self):
	# 	'''
	# 	Transform: positive
	# 	'''
	# 	#change the textfield to pos value and call performTransformations
	# 	textfield = float(self.transform_ui.s000.value())
	# 	if textfield <0:
	# 		newText = abs(textfield)
	# 		self.transform_ui.s000.setValue(newText)
	# 	self.performTransformations()
