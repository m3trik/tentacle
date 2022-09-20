# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.create import Create



class Create_max(Create, Slots_max):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		cmb = self.sb.create.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		cmb = self.sb.create.cmb001
		items = ['Mesh', 'Editable Poly', 'Editable Mesh', 'Editable Patch', 'NURBS', 'Light']
		cmb.addItems_(items)

		cmb = self.sb.create.cmb002
		items = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Text"] 
		cmb.addItems_(items)

		ctx = self.sb.create.tb000.ctxMenu
		ctx.chk001.setDisabled(True)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.create.draggable_header.ctxMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Create: Select Base Type
		'''
		cmb = self.sb.create.cmb001

		if index>=0:
			self.cmb001(index)


	def cmb001(self, index=-1):
		''''''
		cmb = self.sb.create.cmb002

		primitives = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Text"] 
		extendedPrimitives = ['Hedra', 'Torus Knot', 'Chamfer Box', 'Chamfer Cylinder', 'Oil Tank', 'Capsule', 'Spindle', 'L-Extrusion', 'Gengon', 'C-Extrusion', 'RingWave', 'Hose', 'Prism'] #Extended Primitives:
		nurbs = ["Cube", "Sphere", "Cylinder", "Cone", "Plane", "Torus", "Circle", "Square"]
		lights = ["Ambient", "Directional", "Point", "Spot", "Area", "Volume", "VRay Sphere", "VRay Dome", "VRay Rect", "VRay IES"]

		if index in (0, 1, 2, 3): #shared menu. later converted to the specified type.
			cmb.addItems_(primitives+extendedPrimitives, clear=True)

		if index==4:
			cmb.addItems_(nurbs, clear=True)

		if index==5:
			cmb.addItems_(lights, clear=True)


	@Slots_max.attr
	def tb000(self, state=None):
		'''Create Primitive
		'''
		tb = self.sb.create.tb000

		type_ = self.sb.create.cmb001.currentText()
		index = self.sb.create.cmb002.currentIndex()
		translate = tb.ctxMenu.chk000.isChecked()
		# scale = tb.ctxMenu.chk001.isChecked()

		selection = list(rt.selection)

		if not type_:
			type_ = 'Mesh' #set default type

		#Primitives
		if type_ in ['Mesh', 'Editable Poly', 'Polygon', 'Editable Mesh', 'Editable Patch', 'NURBS']:
			if index==0: #cube:
				node = rt.Box(width=15, length=15, height=15, lengthsegs=1, widthsegs=1, heightsegs=1)
			elif index==1: #sphere:
				node = rt.Sphere(radius=5, segs=12)
			elif index==2: #cylinder:
				node = rt.Cylinder(radius=5, height=10, sides=12, heightsegs=1, capsegs=1, smooth=True)
			elif index==3: #plane:
				node = rt.Plane(width=5, length=5, widthsegs=1, lengthsegs=1)
			elif index==4: #circle:
				node = self.createCircle(axis=[0,90,0], numPoints=5, radius=5, mode=None)
			elif index==5: #Cone:
				node = rt.Cone(radius1=5, radius2=1, height=5, capsegs=1, heightsegs=1, sides=12, smooth=True)
			elif index==6: #Pyramid
				node = rt.Pyramid(width=5, depth=3, height=5, widthsegs=1, depthSegs=1, heightsegs=1)
			elif index==7: #Torus:
				node = rt.Torus(radius1=10, radius2=5, segs=5)
			elif index==8: #Pipe
				node = rt.Tube(radius1=5, radius2=8, height=25, sides=12, capSegs=1, hightSegs=1)
			elif index==9: #Soccer ball
				node = rt.GeoSphere(radius=5, segs=2, baseType=2, smooth=True)

		#Extended Primitives:
		if type_ in ['Hedra', 'Torus Knot', 'Chamfer Box', 'Chamfer Cylinder', 'Oil Tank', 'Capsule', 'Spindle', 'L-Extrusion', 'Gengon', 'C-Extrusion', 'RingWave', 'Hose', 'Prism']:
			if index==10: #Hedra
				rt.Hedra(family=0, scalep=100, scaleq=100, scaler=100, mapcoords=True, radius=13.2914, pos=[2.80033,-6.07454,0], isSelected=True)
			elif index==11: #Torus Knot
				rt.Torus_Knot(smooth=2, Base_Curve=0, segments=120, sides=12, radius=12.9131, radius2=2.82649, p=2, q=3, Eccentricity=1, Twist=0, Lumps=0, Lump_Height=0, Gen_UV=1, U_Tile=1, V_Tile=1, U_Offset=0, V_Offset=0, Warp_Height=0, Warp_Count=0, pos=[1.17498,-28.5641,0], isSelected=True)
			elif index==12: #Chamfer Box
				rt.ChamferBox(width=25.9508, fillet=2.08099, length=21.103, height=10.9843, pos=[57.3517,3.11597,0.005], isSelected=True)
			elif index==13: #Chamfer Cylinder
				rt.ChamferCyl(radius=9.90455, height=20.6785, fillet=0.792669, pos=[13.4798,-19.4707,0], isSelected=True)
			elif index==14: #Oil Tank
				rt.OilTank(radius=9.40818, Cap_Height=2.35204, height=24.5722, Blend=0, sides=12, Height_Segments=1, Smooth_On=1, Slice_On=0, Slice_From=0, Slice_To=0, mapcoords=1, pos=[-0.580549,-43.851,0], isSelected=True)
			elif index==15: #Capsule
				rt.Capsule(radius=8.8111, height=28.4398, heighttype=0, sides=12, heightsegs=1, smooth=True, sliceon=False, slicefrom=0, sliceto=0, mapcoords=True, pos=[-9.87687,-6.62625,0], isSelected=True)
			elif index==16: #Spindle
				rt.Spindle(radius=8.22467, Cap_Height=2.42833, height=21.3872, Blend=0, sides=12, Height_Segments=1, cap_segments=5, Smooth_On=1, Slice_On=0, Slice_From=0, Slice_To=0, mapcoords=1, pos=[-6.07937,-23.7136,0], isSelected=True)
			elif index==17: #L-Extrusion
				rt.L_Ext(Side_Length=10.0896, Front_Length=-5.57165, centerCreate=False, pos=[23.9174,-54.3066,0], isSelected=True, Front_Width=2.52126, Side_Width=2.52126, height=12.0807)
			elif index==18: #Gengon
				rt.Gengon(sides=5, radius=11.053, fillet=1.19902, height=20.8109, Side_Segments=1, Fillet_Segments=1, Height_Segments=1, mapcoords=1, pos=[-12.2299,13.1004,0], isSelected=True)
			elif index==19: #C-Extrusion
				rt.C_Ext(Front_Length=-7.54399, Back_Length=-7.54399, Side_Length=8.52505, centerCreate=False, pos=[-5.72067,-60.0124,0], isSelected=True, Front_Width=1.38667, Back_Width=1.38667, Side_Width=1.38667, height=22.6349)
			elif index==20: #Ringwave
				rt.RingWave(time_on=0, time_growing=9600, display_until=16000, repeats=2, max_diameter=8.17418, ring_width=2.37046, ring_segments=200, Outer_Edge_Breakup=False, Major_Cycles_Outer=1, Major_Cycle_Flux_Outer=0, Major_Cycle_Flux_Per_Outer=16000, Minor_Cycles_Outer=1, Minor_Cycle_Flux_Outer=0, Minor_Cycle_Flux_Per_Outer=-16000, Inner_Edge_Breakup=True, Major_Cycles_Inner=11, Major_Cycle_Flux_Inner=25, Major_Cycle_Flux_Per_Inner=19360, Minor_Cycles_Inner=29, Minor_Cycle_Flux_Inner=10, Minor_Cycle_Flux_Per_Inner=-4320, height=0, Height_Segs=1, Radius_Segs=1, Mapping_Coords=True, Smoothing=True, pos=[14.9087,-62.8923,0], isSelected=True)
			elif index==21: #Hose
				rt.Hose(End_Placement_Method=1, Hose_Height=26.8204, Segments_Along_Hose=45, Smooth_Spring=0, Renderable_Hose=1, Hose_Cross_Section_Type=0, Round_Hose_Diameter=10.3709, Round_Hose_Sides=8, Rectangular_Hose_Width=10.3709, Rectangular_Hose_Depth=10.3709, Rectangular_Hose_Fillet_Size=0, Rectangular_Hose_Fillet_Segs=0, Rectangular_Hose_Section_Rotation=0, D_Section_Hose_Width=10.3709, D_Section_Hose_Depth=10.3709, D_Section_Hose_Fillet_Size=0, D_Section_Hose_Fillet_Segs=0, D_Section_Hose_Round_Segs=4, D_Section_Hose_Section_Rotation=0, Generate_Mapping_Coordinates=1, Flex_Section_Enabled=1, Flex_Section_Start=10, Flex_Section_Stop=90, Flex_Cycle_Count=5, Flex_Section_Diameter=-20, Top_Tension=100, Bottom_Tension=100, pos=[-24.722,-55.7553,0], isSelected=True)
			elif index==22: #Prism
				rt.Prism(side1Length=14.1038, side2Length=14.8447, side3Length=16.3529, height=22.8732, pos=[-13.7066,-71.6249,0], isSelected=True)


		#convert to the type selected in cmb001
		if type_ in ['Editable Poly', 'Polygons']: #Polygons
			rt.convertTo(node, rt.PolyMeshObject)

		elif type_=='NURBS': #NURBS
			rt.convertTo(node, rt.NURBSSurf)

		elif type_=='Editable Mesh': #Mesh
			rt.convertTo(node, rt.TriMeshGeometry)

		elif type_=='Editable Patch': #Patch
			rt.convertTo(node, rt.Editable_Patch)
		
		# lights
		elif type_=='Light':
			
			#
			if index==0:
				pass
			elif index==1:
				pass

		if selection: #if there is a current selection, move the object to that selection's bounding box center.
			if translate:
				obj = selection[0]
				if rt.subObjectLevel==1: #vertex
					vertex = Slots_max.bitArrayToArray(rt.polyop.getVertSelection(obj))
					x, y, z = pos = rt.polyop.getVert(obj, vertex[0]) #Returns the position of the specified vertex.
				else:
					x, y, z = pos = obj.position
				node.pos = rt.point3(x, y, z)

			# if scale:
			# 	Slots_max.matchScale(node, selection, average=True)

		# if self.sb.create.cmb001.currentIndex() == 0: #if create type: polygon; convert to editable poly
		# 	rt.convertTo(node, rt.PolyMeshObject) #convert after adding primitive attributes to spinboxes

		rt.select(node) #select the transform node so that you can see any edits
		rt.redrawViews()

		return node









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# deprecated ------------------------------------


	# self.rotation = {'x':[90,0,0], 'y':[0,90,0], 'z':[0,0,90], '-x':[-90,0,0], '-y':[0,-90,0], '-z':[0,0,-90], 'last':[]}
	# self.point=[0,0,0]


	# @property
	# def node(self):
	# 	'''Get the Transform Node
	# 	'''
	# 	selection = [i for i in rt.selection]
	# 	if not selection:
	# 		return None

	# 	transform = selection[0]
	# 	if not self.sb.create.txt003.text()==transform.name: #make sure the same field reflects the current working node.
	# 		self.sb.create.txt003.setText(transform.name)
	# 		self.constructAttributesForNode(transform) #update the attribute values for the current node.

	# 	return transform

	# def getAxis(self):
	# 	''''''
	# 	if self.sb.create.chk000.isChecked():
	# 		axis = 'x'
	# 	elif self.sb.create.chk001.isChecked():
	# 		axis = 'y'
	# 	elif self.sb.create.chk002.isChecked():
	# 		axis = 'z'
	# 	if self.sb.create.chk003.isChecked(): #negative
	# 		axis = '-'+axis
	# 	return axis

	# def rotateAbsolute(self, axis, node):
	# 	'''Undo previous rotation and rotate on the specified axis.
	# 	uses an external rotation dictionary.
	# 	:Parameters:
	# 		axis (str) = axis to rotate on. ie. '-x'
	# 		node (obj) = transform node.
	# 	'''
	# 	angle = [a for a in self.rotation[axis] if a!=0][0] #get angle. ie. 90 or -90
	# 	axis = self.rotation[axis] #get axis list from string key. In 3ds max, the axis key is used as bool values, ie. [0, 90, 0] will essentially be used as [0,1,0]

	# 	last = self.rotation['last']
	# 	if last: #if previous rotation stored: undo previous rotation
	# 		rt.rotate(node, rt.angleaxis(angle*-1, rt.point3(last[0], last[1], last[2]))) #multiplying the angle *1 inverts it. ie. -90 becomes 90
		
	# 	rt.rotate(node, rt.angleaxis(angle, rt.point3(axis[0], axis[1], axis[2]))) #perform new rotation
	# 	self.rotation['last'] = axis #store rotation
	# 	rt.redrawViews()


	# def s000(self, value=None):
	# 	'''Set Translate X
	# 	'''
	# 	if self.node:
	# 		self.point[0] = float(self.sb.create.s000.value())
	# 		self.node.pos = rt.point3(self.point[0], self.point[1], self.point[2])
	# 		rt.redrawViews()


	# def s001(self, value=None):
	# 	'''Set Translate Y
	# 	'''
	# 	if self.node:
	# 		self.point[1] = float(self.sb.create.s001.value())
	# 		self.node.pos = rt.point3(self.point[0], self.point[1], self.point[2])
	# 		rt.redrawViews()


	# def s002(self, value=None):
	# 	'''Set Translate Z
	# 	'''
	# 	if self.node:
	# 		self.point[2] = float(self.sb.create.s002.value())
	# 		self.node.pos = rt.point3(self.point[0], self.point[1], self.point[2])
	# 		rt.redrawViews()


	# def txt003(self):
	# 	'''Set Name
	# 	'''
	# 	if self.node:
	# 		self.node.name = self.sb.create.txt003.text()


	# def chk000(self, state=None):
	# 	'''Rotate X Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk000', setUnChecked='chk001,chk002')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk001(self, state=None):
	# 	'''Rotate Y Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk001', setUnChecked='chk000,chk002')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk002(self, state=None):
	# 	'''Rotate Z Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk002', setUnChecked='chk001,chk000')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk003(self, state=None):
	# 	'''Rotate Negative Axis
	# 	'''
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)



	# def chk005(self, state=None):
	# 	'''Set Point
	# 	'''
	# 	error=0
	# 	#add support for averaging multiple components and multiple component types.
	# 	obj = rt.selection[0]
	# 	if obj:
	# 		if rt.subObjectLevel==1: #vertex
	# 			vertex = Slots_max.bitArrayToArray(rt.polyop.getVertSelection(obj))
	# 			point = rt.polyop.getVert(obj, vertex[0]) #Returns the position of the specified vertex.
	# 			self.point = point
	# 		else:
	# 			self.point = obj.position
	# 	else:
	# 		error = 1
	# 		self.point = [0,0,0]

	# 	self.sb.create.s000.setValue(self.point[0])
	# 	self.sb.create.s001.setValue(self.point[1])
	# 	self.sb.create.s002.setValue(self.point[2])

	# 	if error==1:
	# 		return 'Error: Nothing selected. Point set to origin [0,0,0].'


	# def cmb002(self, index=None, attributes={}, clear=False, show=False):
	# 	'''
	# 	Get/Set Primitive Attributes.

	# 	:Parameters:
	# 		index (int) = parameter on activated, currentIndexChanged, and highlighted signals.
	# 		attributes (dict) = Attibute and it's corresponding value. ie. {width:10}
	# 		clear (bool) = Clear any previous items.
	# 		show (bool) = Show the popup menu immediately after adding items.
	# 	'''
	# 	cmb = self.sb.create.cmb002

	# 	if index=='setMenu':
	# 		cmb.popupStyle = 'qmenu'
	# 		return

	# 	attributes = {k:v for k,v in attributes.items() if isinstance(v,(int, float, bool))} #get only attributes of int, float, bool type.

	# 	n = len(attributes)
	# 	if n and index is None:
	# 		names = 's000-'+str(n-1)

	# 		if clear:
	# 			cmb.menu_.clear()

	# 		#add spinboxes
	# 		[cmb.add('QDoubleSpinBox', setObjectName=name, setMinMax_='0.00-100 step1') for name in self.unpackNames(names)]

	# 		#set values
	# 		self.setSpinboxes(cmb, names, attributes)

	# 		#set signal/slot connections
	# 		self.sb.connect(names, 'valueChanged', self.sXXX, cmb.menu_)

	# 		if show:
	# 			cmb.showPopup()


	# def constructAttributesForNode(self, node):
	# 	'''
	# 	Populate the attributes comboBox with attributes of the given node.

	# 	:Parameters:
	# 		node (obj) = Scene object.
	# 	'''
	# 	exclude = ['getmxsprop', 'setmxsprop', 'typeInHeight', 'typeInLength', 'typeInPos', 'typeInWidth', 'typeInDepth', 
	# 		'typeInRadius', 'typeInRadius1', 'typeInRadius2', 'typeinCreationMethod', 'edgeChamferQuadIntersections', 
	# 		'edgeChamferType', 'hemisphere', 'realWorldMapSize', 'mapcoords']

	# 	attributes = self.getAttributesMax(node, exclude=exclude)
	# 	self.cmb002(attributes=attributes, clear=True, show=True)


	# def sXXX(self, index=None):
	# 	'''
	# 	Set node attributes from multiple spinbox values.

	# 	:Parameters:
	# 		index(int) = optional index of the spinbox that called this function. ie. 5 from s005
	# 	'''
	# 	spinboxValues = {s.prefix().rstrip(': '):s.value() for s in self.sb.create.cmb002.children_()} #current spinbox values. ie. from s000 get the value of six and add it to the list
	# 	self.setAttributesMax(self.node, spinboxValues) #set attributes for the history node
