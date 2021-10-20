# !/usr/bin/python
# coding=utf-8
import os.path

from max_init import *



class Transform(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.transform_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='')
			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.transform_ui.draggable_header.contextMenu.cmb000

		if index is 'setMenu':
			files = ['']
			cmb.addItems_(files, '')
			return

		if inde>0:
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

		if index is 'setMenu':
			cmb.popupStyle = 'qmenu'
			cmb.contextMenu.add('QRadioButton', setObjectName='chk017', setText='Standard', setChecked=True, setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk018', setText='Body Shapes', setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk019', setText='NURBS', setToolTip='')
			cmb.contextMenu.add('QRadioButton', setObjectName='chk020', setText='Point Cloud Shapes', setToolTip='')
			cmb.contextMenu.add(self.tcl.wgts.Label, setObjectName='lbl000', setText='Disable All', setToolTip='Disable all constraints.')
			self.connect_('chk017-20', 'toggled', self.cmb001, cmb.contextMenu) #connect to this method on toggle
			return

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

		if index is 'setMenu':
			list_ = ['Point to Point', '2 Points to 2 Points', '3 Points to 3 Points', 'Align Objects', 'Position Along Curve', 'Align Tool', 'Snap Together Tool']
			cmb.addItems_(list_, 'Align To')
			return

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

		if index is 'setMenu':
			cmb.popupStyle = 'qmenu'
			cmb.contextMenu.add(self.tcl.wgts.Label, setText='Disable All', setObjectName='lbl001', setToolTip='Disable all transform snapping.')

			try:
				moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
				scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
				rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)

				list_ = [('chk021', 'Move <b>Off</b>'), ('s021', 'increment:', moveValue, '1.00-1000 step2.8125'), 
						('chk022', 'Scale <b>Off</b>'), ('s022', 'increment:', scaleValue, '1.00-1000 step2.8125'), 
						('chk023', 'Rotate <b>Off</b>'), ('s023', 'degrees:', rotateValue, '1.00-360 step2.8125')]

				widgets = [cmb.menu_.add(self.tcl.wgts.CheckBox, setObjectName=i[0], setText=i[1], setTristate=1) if len(i) is 2 
						else cmb.menu_.add('QDoubleSpinBox', setObjectName=i[0], setPrefix=i[1], setValue=i[2], setMinMax_=i[3], setDisabled=1) for i in list_]

			except NameError as error:
				print(error)
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
		tb = self.transform_ui.tb000
		if state is 'setMenu':
			tb.menu_.add('QComboBox', addItems=['Min','Mid','Max'], setObjectName='cmb004', setToolTip='Choose which point of the bounding box to align to.')
			tb.menu_.add('QCheckBox', setText='Move to Origin', setObjectName='chk014', setChecked=True, setToolTip='Move to origin (xyz 0,0,0).')
			tb.menu_.add('QCheckBox', setText='Center Pivot', setObjectName='chk016', setChecked=False, setToolTip='Center pivot on objects bounding box.')
			return

		align = tb.menu_.cmb004.currentText()
		origin = tb.menu_.chk014.isChecked()
		centerPivot = tb.menu_.chk016.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)
		Init.dropToGrid(objects, align, origin, centerPivot)
		pm.select(objects) #reselect the original selection.


	@Slots.message
	def tb001(self, state=None):
		'''Align Vertices

		Auto Align finds the axis with the largest variance, and set the axis checkboxes accordingly before performing a regular align.
		'''
		tb = self.transform_ui.tb001
		if state is 'setMenu':
			tb.menu_.add('QCheckBox', setText='X Axis', setObjectName='chk029', setDisabled=True, setToolTip='Align X axis')
			tb.menu_.add('QCheckBox', setText='Y Axis', setObjectName='chk030', setDisabled=True, setToolTip='Align Y axis')
			tb.menu_.add('QCheckBox', setText='Z Axis', setObjectName='chk031', setDisabled=True, setToolTip='Align Z axis')
			tb.menu_.add('QCheckBox', setText='Between Two Components', setObjectName='chk013', setToolTip='Align the path along an edge loop between two selected vertices or edges.')
			tb.menu_.add('QCheckBox', setText='Align Loop', setObjectName='chk007', setToolTip='Align entire edge loop from selected edge(s).')
			tb.menu_.add('QCheckBox', setText='Average', setObjectName='chk006', setToolTip='Align to last selected object or average.')
			tb.menu_.add('QCheckBox', setText='Auto Align', setObjectName='chk010', setChecked=True, setToolTip='')
			tb.menu_.add('QCheckBox', setText='Auto Align: Two Axes', setObjectName='chk011', setToolTip='')
			return

		betweenTwoComponents = tb.menu_.chk013.isChecked()
		autoAlign = tb.menu_.chk010.isChecked()
		autoAlign2Axes = tb.menu_.chk011.isChecked() #Auto Align: Two Axes

		selection = pm.ls(orderedSelection=1)

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
						self.toggleWidgets(tb.menu_, setChecked='chk030-31', setUnChecked='chk029')
					if axis==y: #"xz"
						self.toggleWidgets(tb.menu_, setChecked='chk029,chk031', setUnChecked='chk030')
					if axis==z: #"xy"
						self.toggleWidgets(tb.menu_, setChecked='chk029-30', setUnChecked='chk031')
				else:
					if any ([axis==x and tangent==ty, axis==y and tangent==tx]): #"z"
						self.toggleWidgets(tb.menu_, setChecked='chk031', setUnChecked='chk029-30')
					if any ([axis==x and tangent==tz, axis==z and tangent==tx]): #"y"
						self.toggleWidgets(tb.menu_, setChecked='chk030', setUnChecked='chk029,chk031')
					if any ([axis==y and tangent==tz, axis==z and tangent==ty]): #"x"
						self.toggleWidgets(tb.menu_, setChecked='chk029', setUnChecked='chk030-31')
			else:
				return 'Error: Operation requires a component selection.'

		#align
		x = tb.menu_.chk029.isChecked()
		y = tb.menu_.chk030.isChecked()
		z = tb.menu_.chk031.isChecked()
		avg = tb.menu_.chk006.isChecked()
		loop = tb.menu_.chk007.isChecked()

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
print(os.path.splitext(os.path.basename(__file__))[0])
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
