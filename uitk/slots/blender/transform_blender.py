# !/usr/bin/python
# coding=utf-8
from uitk.slots.blender import *
from uitk.slots.transform import Transform



class Transform_blender(Transform, Slots_blender):
	def __init__(self, *args, **kwargs):
		'''
		'''
		Slots_blender.__init__(self, *args, **kwargs)
		Transform.__init__(self, *args, **kwargs)

		cmb = self.sb.transform.draggable_header.ctxMenu.cmb000
		files = ['']
		cmb.addItems_(files, '')

		cmb = self.sb.transform.cmb001
		cmb.popupStyle = 'qmenu'
		cmb.menu_.setTitle('Constaints')
		#query and set current states:
		# edge_constraint = True if pm.xformConstraint(query=1, type=1)=='edge' else False
		# surface_constraint = True if pm.xformConstraint(query=1, type=1)=='surface' else False
		# live_object = True if pm.ls(live=1) else False
		# values = [('chk024', 'Edge', edge_constraint), ('chk025', 'Surface', surface_constraint), ('chk026', 'Make Live', live_object)]
		# [cmb.menu_.add(self.sb.CheckBox, setObjectName=chk, setText=typ, setChecked=state) for chk, typ, state in values]

		cmb = self.sb.transform.cmb002
		items = []
		cmb.addItems_(items, 'Align To')

		cmb = self.sb.transform.cmb003
		cmb.popupStyle = 'qmenu'
		cmb.menu_.setTitle('Snap')
		# moveValue = pm.manipMoveContext('Move', q=True, snapValue=True)
		# scaleValue = pm.manipScaleContext('Scale', q=True, snapValue=True)
		# rotateValue = pm.manipRotateContext('Rotate', q=True, snapValue=True)
		# values = [('chk021', 'Move: <b>Off</b>'), ('s021', 'increment:', moveValue, '1.00-1000 step2.8125'), 
		# 		('chk022', 'Scale: <b>Off</b>'), ('s022', 'increment:', scaleValue, '1.00-1000 step2.8125'), 
		# 		('chk023', 'Rotate: <b>Off</b>'), ('s023', 'degrees:', rotateValue, '1.00-360 step2.8125')]
		# [cmb.menu_.add(self.sb.CheckBox, setObjectName=i[0], setText=i[1], setTristate=1) if len(i)==2 
		# 	else cmb.menu_.add('QDoubleSpinBox', setObjectName=i[0], setPrefix=i[1], setValue=i[2], setMinMax_=i[3], setDisabled=1) for i in values]


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.transform.draggable_header.ctxMenu.cmb000

		if index>0:
			if index==cmd.list.index(''):
				pass
			cmb.setCurrentIndex(0)


	def cmb001(self, index=-1):
		'''Transform Constraints

		constrain along normals #checkbox option for edge amd surface constaints
		setXformConstraintAlongNormal false;
		'''
		cmb = self.sb.transform.cmb001


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


	def cmb003(self, index=-1):
		'''Transform Tool Snapping
		'''
		cmb = self.sb.transform.cmb003


	def chk024(self, state=None):
		'''Transform Constraints: Edge
		'''
		if state:
			pm.xformConstraint(type='edge') #pm.manipMoveSetXformConstraint(edge=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb = self.sb.transform.cmb001
		cmb.setCurrentText('Constrain: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk025.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: <hl style="color:green;">On</hl>')


	def chk025(self, state=None):
		'''Transform Contraints: Surface
		'''
		if state:
			pm.xformConstraint(type='surface') #pm.manipMoveSetXformConstraint(surface=True);
		else:
			pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);

		cmb = self.sb.transform.cmb001
		cmb.setCurrentText('Constrain: <hl style="color:white;">Off</hl>') if not any((state, cmb.menu_.chk024.isChecked(), cmb.menu_.chk026.isChecked())) else cmb.setCurrentText('Constrain: <hl style="color:green;">On</hl>')


	def chk026(self, state=None):
		'''Transform Contraints: Make Live
		'''
		cmb = self.sb.transform.cmb001
		chk = cmb.menu_.chk026

		selection = pm.ls(sl=1, objectsOnly=1)
		if state and selection:
			live_object = pm.ls(live=1)
			shape = self.getShapeNode(selection[0])
			if not shape in live_object:
				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
				# self.mtk.viewportMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
		else:
			pm.makeLive(none=True)
			# self.mtk.viewportMessage('Make Live: <hl>Off</hl>')

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


	def tb000(self, state=None):
		'''Drop To Grid
		'''
		tb = self.sb.transform.tb000

		align = tb.ctxMenu.cmb004.currentText()
		origin = tb.ctxMenu.chk014.isChecked()
		centerPivot = tb.ctxMenu.chk016.isChecked()
		freezeTransforms = tb.ctxMenu.chk017.isChecked()

		objects = pm.ls(sl=1, objectsOnly=1)
		mtk.XformmoveTo(objects, align, origin, centerPivot, freezeTransforms)
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
				componentsOnPath = Slots_blender.getPathAlongLoop([selection[0], selection[-1]])
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
			else:
				return 'Error: Operation requires a component selection.'

		#align
		x = tb.ctxMenu.chk029.isChecked()
		y = tb.ctxMenu.chk030.isChecked()
		z = tb.ctxMenu.chk031.isChecked()
		avg = tb.ctxMenu.chk006.isChecked()
		loop = tb.ctxMenu.chk007.isChecked()

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
		cmb = self.sb.transform.cmb001
		cmb.setCurrentIndex(0)


	@Slots.hideMain
	def b000(self):
		'''Object Transform Attributes
		'''
		node = pm.ls(sl=1, objectsOnly=1)
		if not node:
			return 'Error: <b>Nothing selected.</b><br>The operation requires a single selected object.'
		transform = Slots_blender.getTransformNode(node)

		self.setAttributeWindow(transform[0], inc=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)


	def b001(self):
		'''Match Scale
		'''
		selection = pm.ls(sl=1)
		if not selection:
			return 'Error: <b>Nothing selected.</b><br>The operation requires at least two selected objects.'

		frm = selection[0]
		to = selection[1:]

		self.matchScale(frm, to)


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
		sel = pm.ls(sl=1, transforms=1)
		if not sel:
			return 'Error: <b>Nothing selected.</b><br>The operation requires at least two selected objects.'

		objects = sel[:-1]
		target = sel[-1]

		pm.matchTransform(objects, target, position=1, rotation=1, scale=0, pivots=1) #move object to center of the last selected items bounding box
		pm.select(objects)


	def b012(self):
		'''Make Live (Toggle)
		'''
		cmb = self.sb.transform.cmb001
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


	@Slots_blender.undoChunk
	def resetTranslation(self, objects):
		'''Reset the transformations on the given object(s). (unfreeze transforms)

		:Parameters:
			objects (str)(obj)(list): The object(s) to reset transforms for.
		'''
		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects):
			pos = pm.objectCenter(obj) #get the object's current position.
			mtk.XformmoveTo(obj, origin=1, centerPivot=1) #move to origin and center pivot.
			pm.makeIdentity(obj, apply=1, t=1, r=1, s=1, n=0, pn=1) #bake transforms
			pm.xform(obj, translation=pos) #move the object back to it's original position.
		# pm.undoInfo(closeChunk=1)


	def moveTo(self, obj, target, targetCenter=True):
		'''Move an object(s) to the given target.

		:Parameters:
			obj (str)(obj)(list): The objects to move.
			target (str)(obj): The object to move to.
			targetCenter (bool): Move to target pivot pos, or the bounding box center of the target.
		'''
		if targetCenter: #temporarily move the targets pivot to it's bounding box center.
			orig_target_piv = pm.xform(target, q=1, worldSpace=1, rp=1) #get target pivot position.
			pm.xform(target, centerPivots=1) #center target pivot.
			target_pos = pm.xform(target, q=1, worldSpace=1, rp=1) #get the pivot position at center of object.
			pm.xform(target, worldSpace=1, rp=orig_target_piv) #return the target pivot to it's orig position.
		else:
			target_pos = pm.xform(target, q=1, worldSpace=1, rp=1) #get the pivot position.

		pm.xform(obj, translation=target_pos, worldSpace=1, relative=1)


	@Slots_blender.undoChunk
	def dropToGrid(self, objects, align='Mid', origin=False, centerPivot=False, freezeTransforms=False):
		'''Align objects to Y origin on the grid using a helper plane.

		:Parameters:
			objects (str)(obj)(list): The objects to translate.
			align (bool): Specify which point of the object's bounding box to align with the grid. (valid: 'Max','Mid'(default),'Min')
			origin (bool): Move to world grid's center.
			centerPivot (bool): Center the object's pivot.
			freezeTransforms (bool): Reset the selected transform and all of its children down to the shape level.

		ex. dropToGrid(obj, align='Min') #set the object onto the grid.
		'''
		# pm.undoInfo(openChunk=1)
		for obj in pm.ls(objects, transforms=1):
			osPivot = pm.xform(obj, query=1, rotatePivot=1, objectSpace=1) #save the object space obj pivot.
			wsPivot = pm.xform(obj, query=1, rotatePivot=1, worldSpace=1) #save the world space obj pivot.

			pm.xform(obj, centerPivots=1) #center pivot
			plane = pm.polyPlane(name='temp#')

			if not origin:
				pm.xform(plane, translation=(wsPivot[0], 0, wsPivot[2]), absolute=1, ws=1) #move the object to the pivot location

			pm.align(obj, plane, atl=1, x='Mid', y=align, z='Mid')
			pm.delete(plane)

			if not centerPivot:
				pm.xform(obj, rotatePivot=osPivot, objectSpace=1) #return pivot to orig position.

			if freezeTransforms:
				pm.makeIdentity(obj, apply=True)
		# pm.undoInfo (closeChunk=1)


	def setTranslationToPivot(self, node):
		'''Set an object’s translation value from its pivot location.
		:Parameters:
			node (str)(obj): An object, or it's name.
		'''
		x, y, z = pivot = pm.xform(node, query=True, worldSpace=True, rotatePivot=True)
		pm.xform(node, relative=True, translation=[-x,-y,-z])
		pm.makeIdentity(node, apply=True, translate=True)
		pm.xform(node, translation=[x, y, z])


	@Slots_blender.undoChunk
	def alignPivotToSelection(self, alignFrom=[], alignTo=[], translate=True):
		'''Align one objects pivot point to another using 3 point align.
		:Parameters:
			alignFrom (list): At minimum; 1 object, 1 Face, 2 Edges, or 3 Vertices.
			alignTo (list): The object to align with.
			translate (bool): Move the object with it's pivot.
		'''
		# pm.undoInfo(openChunk=1)
		pos = pm.xform(alignTo, q=1, translation=True, worldSpace=True)
		center_pos = [ #Get center by averaging of all x,y,z points.
			sum(pos[0::3]) / len(pos[0::3]), 
			sum(pos[1::3]) / len(pos[1::3]), 
			sum(pos[2::3]) / len(pos[2::3])]

		vertices = pm.ls(pm.polyListComponentConversion(alignTo, toVertex=True), flatten=True)
		if len(vertices) < 3:
			return

		for obj in pm.ls(alignFrom, flatten=1):

			plane = pm.polyPlane(name="_hptemp#", width=1, height=1, subdivisionsX=1, subdivisionsY=1, axis=[0, 1, 0], createUVs=2, constructionHistory=True)[0] #Create and align helper plane.

			pm.select("%s.vtx[0:2]" % plane, vertices[0:3])
			pm.mel.snap3PointsTo3Points(0)

			pm.xform(obj, rotation=pm.xform(plane, q=True, rotation=True, worldSpace=True), worldSpace=True)

			if translate:
				pm.xform(obj, translation=center_pos, worldSpace=True)
				
			pm.delete(plane)
		# pm.undoInfo(closeChunk=1)


	def aimObjectAtPoint(self, obj, target_pos, aim_vect=(1,0,0), up_vect=(0,1,0)):
		'''Aim the given object at the given world space position.

		Args:
			obj (str)(obj): Transform node.
			target_pos (tuple): The (x,y,z) world position to aim at.
			aim_vect (tuple): Local axis to aim at the target position.
			up_vect (tuple): Secondary axis aim vector.
		 '''
		target = pm.createNode('transform')

		pm.xform(target, translation=target_pos, absolute=True)
		const = pm.aimConstraint((target, obj), aim=aim_vect, worldUpVector=up_vect, worldUpType="vector")

		pm.delete(const, target)


	def rotateAxis(self, obj, target_pos):
		''' Aim the given object at the given world space position.
		All rotations in rotated channel, geometry is transformed so it does not appear to move during this transformation

		Args:
			obj (str)(obj): Transform node.
			target_pos (tuple): An (x,y,z) world position.
		'''
		obj = pm.ls(obj)[0]
		self.aimObjectAtPoint(obj, target_pos)

		try:
			c = obj.v[:]
		except TypeError:
			c = obj.cv[:]

		wim = pm.getAttr(obj.worldInverseMatrix)
		pm.xform(c, matrix=wim)

		pos = pm.xform(obj, q=True, translation=True, absolute=True, worldSpace=True)
		pm.xform(c, translation=pos, relative=True, worldSpace=True)


	def getOrientation(self, obj, returnType='point'):
		'''Get an objects orientation.

		:Parameters:
			obj (str)(obj): The object to get the orientation of.
			returnType (str): The desired returned value type. (valid: 'point', 'vector')(default: 'point')

		:Return:
			(tuple)
		'''
		obj = pm.ls(obj)[0]

		world_matrix = pm.xform(obj, q=True, matrix=True, worldSpace=True)
		rAxis = pm.getAttr(obj.rotateAxis)
		if any((rAxis[0], rAxis[1], rAxis[2])):
			print('# Warning: {} has a modified .rotateAxis of {} which is included in the result. #'.format(obj, rAxis))

		if returnType=='vector':
			from maya.api.OpenMaya import MVector

			result = (
				MVector(world_matrix[0:3]),
				MVector(world_matrix[4:7]),
				MVector(world_matrix[8:11])
			)

		else:
			result = (
				world_matrix[0:3],
				world_matrix[4:7],
				world_matrix[8:11]
			)

		return result


	def getDistanceBetweenTwoObjects(self, obj1, obj2):
		'''Get the magnatude of a vector using the center points of two given objects.

		:Parameters:
			obj1 (obj)(str): Object, object name, or point (x,y,z).
			obj2 (obj)(str): Object, object name, or point (x,y,z).

		:Return:
			(float)

		# xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(startAndEndCurves)
		'''
		x1, y1, z1 = pm.objectCenter(obj1)
		x2, y2, z2 = pm.objectCenter(obj2)

		from math import sqrt
		distance = sqrt(pow((x1-x2),2) + pow((y1-y2),2) + pow((z1-z2),2))

		return distance


	def getCenterPoint(self, objects):
		'''Get the bounding box center point of any given object(s).
		
		:Parameters:
			objects (str)(obj(list): The objects or components to get the center of.

		:Return:
			(list) position as [x,y,z].
		'''
		objects = pm.ls(objects, flatten=True)
		pos = [i for sublist in [pm.xform(s, q=1, translation=1, worldSpace=1, absolute=1) for s in objects] for i in sublist]
		center_pos = [ #Get center by averaging of all x,y,z points.
			sum(pos[0::3]) / len(pos[0::3]), 
			sum(pos[1::3]) / len(pos[1::3]), 
			sum(pos[2::3]) / len(pos[2::3])
		]
		return center_pos


	def getComponentPoint(self, component, alignToNormal=False):
		'''Get the center point from the given component.

		:Parameters:
			component (str)(obj): Object component.
			alignToNormal (bool): Constain to normal vector.

		:Return: [float list] - x, y, z  coordinate values.
		'''
		if ".vtx" in str(component):
			x = pm.polyNormalPerVertex (component, query=1, x=1)
			y = pm.polyNormalPerVertex (component, query=1, y=1)
			z = pm.polyNormalPerVertex (component, query=1, z=1)
			xyz = [sum(x) / float(len(x)), sum(y) / float(len(y)), sum(z) / float(len(z))] #get average
		elif ".e" in str(component):
			componentName = str(component).split(".")[0]
			vertices = pm.polyInfo (component, edgeToVertex=1)[0]
			vertices = vertices.split()
			vertices = [componentName+".vtx["+vertices[2]+"]",componentName+".vtx["+vertices[3]+"]"]
			x=[];y=[];z=[]
			for vertex in vertices:
				x_ = pm.polyNormalPerVertex (vertex, query=1, x=1)
				x.append(sum(x_) / float(len(x_)))
				y_ = pm.polyNormalPerVertex (vertex, query=1, y=1)
				x.append(sum(y_) / float(len(y_)))
				z_ = pm.polyNormalPerVertex (vertex, query=1, z=1)
				x.append(sum(z_) / float(len(z_)))
			xyz = [sum(x) / float(len(x)), sum(y) / float(len(y)), sum(z) / float(len(z))] #get average
		else:# elif ".f" in str(component):
			xyz = pm.polyInfo (component, faceNormals=1)
			xyz = xyz[0].split()
			xyz = [float(xyz[2]), float(xyz[3]), float(xyz[4])]

		if alignToNormal: #normal constraint
			normal = mel.eval("unit <<"+str(xyz[0])+", "+str(xyz[1])+", "+str(xyz[2])+">>;") #normalize value using MEL
			# normal = [round(i-min(xyz)/(max(xyz)-min(xyz)),6) for i in xyz] #normalize and round value using python

			constraint = pm.normalConstraint(component, object_,aimVector=normal,upVector=[0,1,0],worldUpVector=[0,1,0],worldUpType="vector") # "scene","object","objectrotation","vector","none"
			pm.delete(constraint) #orient object_ then remove constraint.

		vertexPoint = pm.xform (component, query=1, translation=1) #average vertex points on destination to get component center.
		x = vertexPoint [0::3]
		y = vertexPoint [1::3]
		z = vertexPoint [2::3]

		return list(round(sum(x) / float(len(x)),4), round(sum(y) / float(len(y)),4), round(sum(z) / float(len(z)),4))


	def matchScale(self, to, frm, scale=True, average=False):
		'''Scale each of the given objects to the combined bounding box of a second set of objects.

		:Parameters:
			to (str)(obj)(list): The object(s) to scale.
			frm (str)(obj)(list): The object(s) to get a bounding box size from.
			scale (bool): Scale the objects. Else, just return the scale value.
			average (bool): Average the result across all axes.

		:Return:
			(list) scale values as [x,y,z,x,y,z...]
		'''
		to = pm.ls(to, flatten=True)
		frm = pm.ls(frm, flatten=True)

		xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(frm)
		ax, ay, az = aBoundBox = [xmax-xmin, ymax-ymin, zmax-zmin]

		result=[]
		for obj in to:

			xmin, ymin, zmin, xmax, ymax, zmax = pm.exactWorldBoundingBox(obj)
			bx, by, bz = bBoundBox = [xmax-xmin, ymax-ymin, zmax-zmin]

			oldx, oldy, oldz = bScaleOld = pm.xform(obj, q=1, s=1, r=1)

			try:
				diffx, diffy, diffz = boundDifference = [ax/bx, ay/by, az/bz]
			except ZeroDivisionError as error:
				diffx, diffy, diffz = boundDifference = [1, 1, 1]

			bScaleNew = [oldx*diffx, oldy*diffy, oldz*diffz]

			if average:
				bScaleNew = [sum(bScaleNew)/len(bScaleNew) for _ in range(3)]

			if scale:
				pm.xform(obj, scale=bScaleNew)

			[result.append(i) for i in bScaleNew]

		return result


	@Slots_blender.undoChunk
	def alignVertices(self, mode, average=False, edgeloop=False):
		'''Align vertices.

		:Parameters:
			mode (int): possible values are align: 0-YZ, 1-XZ, 2-XY, 3-X, 4-Y, 5-Z, 6-XYZ 
			average (bool): align to average of all selected vertices. else, align to last selected
			edgeloop (bool): align vertices in edgeloop from a selected edge

		:Example: alignVertices(mode=3, average=True, edgeloop=True)
		'''
		# pm.undoInfo (openChunk=True)
		selectTypeEdge = pm.selectType (query=True, edge=True)

		if edgeloop:
			pm.mel.SelectEdgeLoopSp() #select edgeloop

		pm.mel.PolySelectConvert(3) #convert to vertices

		selection = pm.ls(selection=1, flatten=1)
		lastSelected = pm.ls(tail=1, selection=1, flatten=1)
		alignTo = pm.xform(lastSelected, query=1, translation=1, worldSpace=1)
		alignX = alignTo[0]
		alignY = alignTo[1]
		alignZ = alignTo[2]
		
		if average:
			xyz = pm.xform(selection, query=1, translation=1, worldSpace=1)
			x = xyz[0::3]
			y = xyz[1::3]
			z = xyz[2::3]
			alignX = float(sum(x))/(len(xyz)/3)
			alignY = float(sum(y))/(len(xyz)/3)
			alignZ = float(sum(z))/(len(xyz)/3)

		if len(selection)<2:
			if len(selection)==0:
				Slots_blender.mtk.viewportMessage("No vertices selected")
			Slots_blender.mtk.viewportMessage("Selection must contain at least two vertices")

		for vertex in selection:
			vertexXYZ = pm.xform(vertex, query=1, translation=1, worldSpace=1)
			vertX = vertexXYZ[0]
			vertY = vertexXYZ[1]
			vertZ = vertexXYZ[2]
			
			modes = {
				0:(vertX, alignY, alignZ), #align YZ
				1:(alignX, vertY, alignZ), #align XZ
				2:(alignX, alignY, vertZ), #align XY
				3:(alignX, vertY, vertZ),
				4:(vertX, alignY, vertZ),
				5:(vertX, vertY, alignZ),
				6:(alignX, alignY, alignZ), #align XYZ
			}

			pm.xform(vertex, translation=modes[mode], worldSpace=1)

		if selectTypeEdge:
			pm.selectType (edge=True)
		# pm.undoInfo (closeChunk=True)









#module name
print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# deprecated ------------------------------------



	# def lbl001(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.sb.transform.cmb003
	# 	self.sb.toggleWidgets(setUnChecked='chk021-23')
	# 	cmb.setCurrentText('Off') if not any((cmb.menu_.chk021.isChecked(), cmb.menu_.chk022.isChecked(), cmb.menu_.chk023.isChecked())) else cmb.setCurrentText('On')


	# def lbl002(self):
	# 	'''Transform Tool Snapping: Disable All
	# 	'''
	# 	cmb = self.sb.transform.cmb001
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
	# 	cmb = self.sb.transform.cmb001

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
	# 			selection = pm.ls(sl=1, objectsOnly=1)
	# 			if not selection and not live_object:
	# 				print ('not selection and not live_object')
	# 				cmb.setCurrentIndex(0)
	# 				return 'Error: Nothing Selected.'

	# 			if not live_object:
	# 				print ('not live_object')
	# 				pm.makeLive(selection) #construction planes, nurbs surfaces and polygon meshes can be made live. makeLive supports one live object at a time.
	# 				self.mtk.viewportMessage('Make Live: <hl>On</hl> {0}'.format(selection[0].name()))
	# 	else:
	# 		print ('0')
	# 		pm.xformConstraint(type='none') #pm.manipMoveSetXformConstraint(none=True);
	# 		if live_object:
	# 			print ('none')
	# 			pm.makeLive(none=True)
	# 			self.mtk.viewportMessage('Make Live: <hl>Off</hl>')
