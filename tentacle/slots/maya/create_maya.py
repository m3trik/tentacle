# !/usr/bin/python
# coding=utf-8
from tentacle.slots.maya import *
from tentacle.slots.create import Create


class Create_maya(Create, Slots_maya):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		ctx = self.sb.create.draggable_header.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add(self.sb.ComboBox, setObjectName='cmb000', setToolTip='')

		cmb = self.sb.create.draggable_header.ctxMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		cmb = self.sb.create.cmb001
		items = ['Polygon', 'NURBS', 'Light']
		cmb.addItems_(items)

		cmb = self.sb.create.cmb002
		items = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		cmb.addItems_(items)

		ctx = self.sb.create.tb000.ctxMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Translate', setObjectName='chk000', setChecked=True, setToolTip='Move the created object to the center point of any selected object(s).')
			ctx.add('QCheckBox', setText='Scale', setObjectName='chk001', setChecked=True, setToolTip='Uniformly scale the created object to match the averaged scale of any selected object(s).')


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
		'''
		'''
		cmb = self.sb.create.cmb001

		if index>=0:
			self.cmb002(index)


	def cmb002(self, index=-1):
		'''
		'''
		cmb = self.sb.create.cmb002

		polygons = ["Cube", "Sphere", "Cylinder", "Plane", "Circle", "Cone", "Pyramid", "Torus", "Tube", "GeoSphere", "Platonic Solids", "Text"]
		nurbs = ["Cube", "Sphere", "Cylinder", "Cone", "Plane", "Torus", "Circle", "Square"]
		lights = ["Ambient", "Directional", "Point", "Spot", "Area", "Volume"]

		if index==0: #shared menu. later converted to the specified type.
			cmb.addItems_(polygons, clear=True)

		if index==1:
			cmb.addItems_(nurbs, clear=True)

		if index==2:
			cmb.addItems_(lights, clear=True)


	@Slots_maya.attr
	def tb000(self, state=None):
		'''Create Primitive
		'''
		tb = self.sb.create.tb000

		baseType = self.sb.create.cmb001.currentText()
		subType = self.sb.create.cmb002.currentText()
		scale = tb.ctxMenu.chk001.isChecked()
		translate = tb.ctxMenu.chk000.isChecked()

		return self.createDefaultPrimitive(baseType, subType, scale, translate)


	def createDefaultPrimitive(self, baseType, subType, scale=False, translate=False, axis=[0,90,0]):
		'''
		'''
		baseType = baseType.lower()
		subType = subType.lower()

		selection = pm.ls(selection=1, transforms=1)

		primitives = {	
			'polygon': {
				'cube': 'pm.polyCube(axis=axis, width=5, height=5, depth=5, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1)',
				'sphere': 'pm.polySphere(axis=axis, radius=5, subdivisionsX=12, subdivisionsY=12)',
				'cylinder': 'pm.polyCylinder(axis=axis, radius=5, height=10, subdivisionsX=12, subdivisionsY=1, subdivisionsZ=1)',
				'plane': 'pm.polyPlane(axis=axis, width=5, height=5, subdivisionsX=1, subdivisionsY=1)',
				'circle': 'self.createCircle(axis=axis, numPoints=12, radius=5, mode=0)',
				'cone': 'pm.polyCone(axis=axis, radius=5, height=5, subdivisionsX=1, subdivisionsY=1, subdivisionsZ=1)',
				'pyramid': 'pm.polyPyramid(axis=axis, sideLength=5, numberOfSides=5, subdivisionsHeight=1, subdivisionsCaps=1)',
				'torus': 'pm.polyTorus(axis=axis, radius=10, sectionRadius=5, twist=0, subdivisionsX=5, subdivisionsY=5)',
				'pipe': 'pm.polyPipe(axis=axis, radius=5, height=5, thickness=2, subdivisionsHeight=1, subdivisionsCaps=1)',
				'geosphere': 'pm.polyPrimitive(axis=axis, radius=5, sideLength=5, polyType=0)',
				'platonic solids': 'pm.mel.eval("performPolyPrimitive PlatonicSolid 0;")',
			},

			'nurbs': {
				'cube': 'pm.nurbsCube(ch=1, d=3, hr=1, p=(0, 0, 0), lr=1, w=1, v=1, ax=(0, 1, 0), u=1)',
				'sphere': 'pm.sphere(esw=360, ch=1, d=3, ut=0, ssw=0, p=(0, 0, 0), s=8, r=1, tol=0.01, nsp=4, ax=(0, 1, 0))',
				'cylinder': 'pm.cylinder(esw=360, ch=1, d=3, hr=2, ut=0, ssw=0, p=(0, 0, 0), s=8, r=1, tol=0.01, nsp=1, ax=(0, 1, 0))',
				'cone': 'pm.cone(esw=360, ch=1, d=3, hr=2, ut=0, ssw=0, p=(0, 0, 0), s=8, r=1, tol=0.01, nsp=1, ax=(0, 1, 0))',
				'plane': 'pm.nurbsPlane(ch=1, d=3, v=1, p=(0, 0, 0), u=1, w=1, ax=(0, 1, 0), lr=1)',
				'torus': 'pm.torus(esw=360, ch=1, d=3, msw=360, ut=0, ssw=0, hr=0.5, p=(0, 0, 0), s=8, r=1, tol=0.01, nsp=4, ax=(0, 1, 0))',
				'circle': 'pm.circle(c=(0, 0, 0), ch=1, d=3, ut=0, sw=360, s=8, r=1, tol=0.01, nr=(0, 1, 0))',
				'square': 'pm.nurbsSquare(c=(0, 0, 0), ch=1, d=3, sps=1, sl1=1, sl2=1, nr=(0, 1, 0))',
			},

			'light': {
				'ambient': 'pm.ambientLight()', #defaults: 1, 0.45, 1,1,1, "0", 0,0,0, "1"
				'directional': 'pm.directionalLight()', #1, 1,1,1, "0", 0,0,0, 0
				'point': 'pm.pointLight()', #1, 1,1,1, 0, 0, 0,0,0, 1
				'spot': 'pm.spotLight()', #1, 1,1,1, 0, 40, 0, 0, 0, 0,0,0, 1, 0
				'area': 'pm.shadingNode("areaLight", asLight=True)', #1, 1,1,1, 0, 0, 0,0,0, 1, 0
				'volume': 'pm.shadingNode("volumeLight", asLight=True)', #1, 1,1,1, 0, 0, 0,0,0, 1
			},
		}

		node = eval(primitives[baseType][subType])

		if selection: #if originally there was a selected object, move the object to that objects's bounding box center.
			if translate:
				mtk.Xform.moveTo(node, selection)
				# center_pos = mtk.Xform.getCenterPoint(selection)
				# pm.xform(node, translation=center_pos, worldSpace=1, absolute=1)
			if scale:
				mtk.Xform.matchScale(node[0], selection, average=True)

		pm.selectMode(object=1) #place scene select type in object mode.
		pm.select(node) #select the transform node so that you can see any edits

		return mtk.Node.getHistoryNode(node)


	def b005(self):
		'''Create 6 sided poly cylinder
		'''
		obj = self.createPrimitive('Polygon', 'Cylinder')
		mtk.Node.setAttributesMEL(obj, verbose=True, subdivisionsAxis=6)


	@mtk.undo
	def createCircle(self, axis='y', numPoints=5, radius=5, center=[0,0,0], mode=0, name='pCircle'):
		'''Create a circular polygon plane.

		Parameters:
			axis (str): 'x','y','z' 
			numPoints(int): number of outer points
			radius=int
			center=[float3 list] - point location of circle center
			mode(int): 0 -no subdivisions, 1 -subdivide tris, 2 -subdivide quads

		Return:
			(list) [transform node, history node] ex. [nt.Transform('polySurface1'), nt.PolyCreateFace('polyCreateFace1')]

		Example: self.createCircle(axis='x', numPoints=20, radius=8, mode='tri')
		'''
		import math

		degree = 360/float(numPoints)
		radian = math.radians(degree) #or math.pi*degree/180 (pi * degrees / 180)

		vertexPoints=[]
		for _ in range(numPoints):
			# print("deg:", degree,"\n", "cos:",math.cos(radian),"\n", "sin:",math.sin(radian),"\n", "rad:",radian)
			if axis =='x': #x axis
				y = center[2] + (math.cos(radian) *radius)
				z = center[1] + (math.sin(radian) *radius)
				vertexPoints.append([0,y,z])
			if axis =='y': #y axis
				x = center[2] + (math.cos(radian) *radius)
				z = center[0] + (math.sin(radian) *radius)
				vertexPoints.append([x,0,z])
			else: # z axis
				x = center[0] + (math.cos(radian) *radius)
				y = center[1] + (math.sin(radian) *radius)
				vertexPoints.append([x,y,0]) #not working.

			radian = radian+math.radians(degree) #increment by original radian value that was converted from degrees
			#print(x,y,"\n")

		# pm.undoInfo (openChunk=True)
		node = pm.ls(pm.polyCreateFacet(point=vertexPoints, name=name)) #returns: ['Object name', 'node name']. pymel 'ls' converts those to objects.
		pm.polyNormal(node, normalMode=4) #4=reverse and propagate
		if mode==1:
			pm.polySubdivideFacet(divisions=1, mode=1)
		if mode==2:
			pm.polySubdivideFacet(divisions=1, mode=0)
		# pm.undoInfo (closeChunk=True)

		return node









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# deprecated:

	# self.rotation = {'x':[90,0,0], 'y':[0,90,0], 'z':[0,0,90], '-x':[-90,0,0], '-y':[0,-90,0], '-z':[0,0,-90], 'last':[]}
	# self.point=[0,0,0]

	# @property
	# def node(self):
	# 	'''Get the Transform Node
	# 	'''
	# 	transform = mtk.Node.getTransformNode()
	# 	if transform:
	# 		if not self.sb.create.txt003.text()==transform[0].name(): #make sure the same field reflects the current working node.
	# 			self.sb.create.txt003.setText(transform[0].name())

	# 	return transform

	# def rotateAbsolute(self, axis, node):
	# 	'''undo previous rotation and rotate on the specified axis.
	# 	uses an external rotation dictionary.

	# 	Parameters:
	# 		axis (str): axis to rotate on. ie. '-x'
	# 		node (obj): transform node.
	# 	'''
	# 	axis = self.rotation[axis]

	# 	rotateOrder = pm.xform(node, query=1, rotateOrder=1)
	# 	pm.xform(node, preserve=1, rotation=axis, rotateOrder=rotateOrder, absolute=1)
	# 	self.rotation['last'] = axis

	# def txt003(self):
	# 	'''Set Name
	# 	'''
	# 	if self.node:
	# 		pm.rename(self.node.name(), self.sb.create.txt003.text())

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


	# def chk000(self, state=None):
	# 	'''Rotate X Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk000', setUnChecked='chk001, chk002')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk001(self, state=None):
	# 	'''Rotate Y Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk001', setUnChecked='chk000, chk002')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk002(self, state=None):
	# 	'''Rotate Z Axis
	# 	'''
	# 	self.sb.toggleWidgets(setChecked='chk002', setUnChecked='chk000, chk001')
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)


	# def chk003(self, state=None):
	# 	'''Rotate Negative Axis
	# 	'''
	# 	if self.node:
	# 		self.rotateAbsolute(self.getAxis(), self.node)

		# def chk005(self, state=None):
		# '''Set Point
		# '''
		# #add support for averaging multiple components.
		# selection = pm.ls(selection=1, flatten=1)
		# try:
		# 	self.point = pm.xform(selection, query=1, translation=1, worldSpace=1, absolute=1)
		# except:
		# 	self.point = [0,0,0]
		# 	print('Warning: Nothing selected. Point set to origin [0,0,0].')

		# self.sb.create.s000.setValue(self.point[0])
		# self.sb.create.s001.setValue(self.point[1])
		# self.sb.create.s002.setValue(self.point[2])


	# def s000(self, value=None):
	# 	'''Set Translate X
	# 	'''
	# 	if self.node:
	# 		self.point[0] = self.sb.create.s000.value()
	# 		pm.xform(self.node, translation=self.point, worldSpace=1, absolute=1)


	# def s001(self, value=None):
	# 	'''Set Translate Y
	# 	'''
	# 	if self.node:
	# 		self.point[1] = self.sb.create.s001.value()
	# 		pm.xform(self.node, translation=self.point, worldSpace=1, absolute=1)


	# def s002(self, value=None):
	# 	'''Set Translate Z
	# 	'''
	# 	if self.node:
	# 		self.point[2] = self.sb.create.s002.value()
	# 		pm.xform (self.node, translation=self.point, worldSpace=1, absolute=1)