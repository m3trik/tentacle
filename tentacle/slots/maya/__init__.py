# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtWidgets

try:
	import maya.mel as mel
	import pymel.core as pm
	import maya.OpenMayaUI as omui
except ImportError as error:
	print (__file__, error)

from tentacle.slots import Slots
from tentacle.slots import tk
from tentacle.slots.maya import mayatk as mtk


class Slots_maya(Slots, mtk.Componenttls, mtk.Riggingtls):
	'''App specific methods inherited by all other slot classes.
	'''
	undo = mtk.undo

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)


	# ======================================================================
		'UI'
	# ======================================================================

	@staticmethod
	def getSelectedChannels():
		'''Get any attributes (channels) that are selected in the channel box.

		:Return:
			(str) list of any selected attributes as strings. (ie. ['tx', ry', 'sz'])
		'''
		channelBox = mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;') #fetch maya's main channelbox
		attrs = pm.channelBox(channelBox, q=True, sma=True)

		if attrs is None:
			attrs=[]
		return attrs


	@staticmethod
	def getPanel(*args, **kwargs):
		'''Returns panel and panel configuration information.
		A fix for the broken pymel command of the same name.

		:Parameters:
			[allConfigs=boolean], [allPanels=boolean], [allScriptedTypes=boolean], [allTypes=boolean], [configWithLabel=string], [containing=string], [invisiblePanels=boolean], [scriptType=string], [type=string], [typeOf=string], [underPointer=boolean], [visiblePanels=boolean], [withFocus=boolean], [withLabel=string])

		:Return:
			(str) An array of panel names.
		'''
		from maya.cmds import getPanel #pymel getPanel is broken in ver: 2022.

		result = getPanel(*args, **kwargs)

		return result


	@staticmethod
	def convertToWidget(name):
		'''
		:Parameters:
			name (str) = name of a Maya UI element of any type. ex. name = mel.eval('$tmp=$gAttributeEditorForm') (from MEL global variable)

		:Return:
			(QWidget) If the object does not exist, returns None
		'''
		import shiboken2
		for f in ('findControl', 'findLayout', 'findMenuItem'):
			ptr = getattr(omui.MQtUtil, f)(name) #equivalent to: ex. omui.MQtUtil.findControl(name)
			if ptr:
				return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


	@classmethod
	def attr(cls, fn):
		'''A decorator for setAttributeWindow (objAttrWindow).
		'''
		def wrapper(self, *args, **kwargs):
			rtn = fn(self, *args, **kwargs)
			self.setAttributeWindow(rtn)
			return rtn
		return wrapper

	def setAttributeWindow(self, obj, include=[], exclude=[], checkableLabel=False, fn=None, fn_args=[], **attributes):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (str)(obj)(list) = The object to get the attributes of, or it's name. If given as a list, only the first index will be used.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. setParameterValuesMEL
					The first parameter of fn is always the given object. ex. fn(obj, {'attr':<value>})
			fn_args (str)(list) = Any additonal args to pass to the given fn.
			attributes (kwargs) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from mtk.getAttributesMEL for the given obj.

		ex. call: self.setAttributeWindow(node, attrs, fn=mtk.setParameterValuesMEL, 'transformLimits') #set attributes for the Maya command transformLimits.
		ex. call: self.setAttributeWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		try:
			obj = pm.ls(obj)[0]
		except Exception as error:
			return 'Error: {}.setAttributeWindow: Invalid Object: {}'.format(__name__, obj)

		fn = fn if fn else mtk.setAttributesMEL

		if attributes:
			attributes = {k:v for k, v in attributes.items() 
				if not k in exclude and (k in include if include else k not in include)}
		else:
			attributes = mtk.getAttributesMEL(obj, include=include, exclude=exclude)

		menu = self.objAttrWindow(obj, checkableLabel=checkableLabel, fn=fn, fn_args=fn_args, **attributes)

		if checkableLabel:
			for c in menu.childWidgets:
				if c.__class__.__name__=='QCheckBox':
					attr = getattr(obj, c.objectName())
					c.stateChanged.connect(lambda state, obj=obj, attr=attr: pm.select(attr, deselect=not state, add=1))
					if attr in pm.ls(sl=1):
						c.setChecked(True)


	@staticmethod
	def mainProgressBar(size, name="progressBar_", stepAmount=1):
		'''#add esc key pressed return False

		:Parameters:
			size (int) = total amount
			name (str) = name of progress bar created
			stepAmount(int) = increment amount

		example use-case:
		mainProgressBar (len(edges), progressCount)
			pm.progressBar ("progressBar_", edit=1, step=1)
			if pm.progressBar ("progressBar_", query=1, isCancelled=1):
				break
		pm.progressBar ("progressBar_", edit=1, endProgress=1)

		to use main progressBar: name=string $gMainProgressBar
		'''
		status = "processing: "+str(size)+"."
		edit=0
		if pm.progressBar(name, exists=1):
			edit=1
		pm.progressBar(name, edit=edit,
						beginProgress=1,
						isInterruptable=True,
						status=status,
						maxValue=size,
						step=stepAmount)


	@staticmethod
	def mainProgressBar(gMainProgressBar, numFaces, count):
		''''''
		num=str(numFaces)
		status="iterating through " + num + " faces"
		pm.progressBar(gMainProgressBar, 
			edit=1, 
			status=status, 
			isInterruptable=True, 
			maxValue=count, 
			beginProgress=1)


	@staticmethod
	def viewPortMessage(message='', statusMessage='', assistMessage='', position='topCenter'):
		'''
		:Parameters:
			message (str) = The message to be displayed, (accepts html formatting). General message, inherited by -amg/assistMessage and -smg/statusMessage.
			statusMessage (str) = The status info message to be displayed (accepts html formatting).
			assistMessage (str) = The user assistance message to be displayed, (accepts html formatting).
			position (str) = position on screen. possible values are: topCenter","topRight","midLeft","midCenter","midCenterTop","midCenterBot","midRight","botLeft","botCenter","botRight"

		ex. viewPortMessage("shutting down:<hl>"+str(timer)+"</hl>")
		'''
		fontSize=10
		fade=1
		fadeInTime=0
		fadeStayTime=1000
		fadeOutTime=500
		alpha=75

		if message:
			pm.inViewMessage(message=message, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec
		elif statusMessage:
			pm.inViewMessage(statusMessage=statusMessage, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec
		elif assistMessage:
			pm.inViewMessage(assistMessage=assistMessage, position=position, fontSize=fontSize, fade=fade, fadeInTime=fadeInTime, fadeStayTime=fadeStayTime, fadeOutTime=fadeOutTime, alpha=alpha) #1000ms = 1 sec


	@staticmethod
	def outputText (text, window_title):
		'''output text
		'''
		#window_title = mel.eval(python("window_title"))
		window = str(pm.window(	widthHeight=(300, 300), 
								topLeftCorner=(65,265),
								maximizeButton=False,
								resizeToFitChildren=True,
								toolbox=True,
								title=window_title))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		text_field = str(pm.text(label=text, align='left'))
		print(text_field)
		pm.setParent('..')
		pm.showWindow(window)
		return

	# #output textfield parsed by ';'
	# def outputTextField2(text):
	# 	window = str(pm.window(	widthHeight=(250, 650), 
	# 							topLeftCorner=(50,275),
	# 							maximizeButton=False,
	# 							resizeToFitChildren=False,
	# 							toolbox=True,
	# 							title=""))
	# 	scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
	# 									horizontalScrollBarThickness=16))
	# 	pm.columnLayout(adjustableColumn=True)
	# 	print(text)
	# 	#for item in array:
	# 	text_field = str(pm.textField(height=20,
	# 										width=250, 
	# 										editable=False,
	# 										insertText=str(text)))
	# 	pm.setParent('..')
	# 	pm.showWindow(window)
	# 	return


	@staticmethod
	def outputscrollField (text, window_title, width, height):
		'''Create an output scroll layout.
		'''
		window_width  = width  * 300
		window_height = height * 600
		scroll_width  = width  * 294
		scroll_height = height * 590
		window = str(pm.window(	widthHeight=(window_width, window_height),
								topLeftCorner=(45, 0),
								maximizeButton=False,
								sizeable=False,
								title=window_title
								))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		text_field = str(pm.scrollField(text=(text),
										width=scroll_width,
										height=scroll_height,))
		print(window)
		pm.setParent('..')
		pm.showWindow(window)
		return


	@staticmethod
	def outputTextField (array, window_title):
		'''Create an output text field.
		'''
		window = str(pm.window(	widthHeight=(250, 650), 
								topLeftCorner=(65,275),
								maximizeButton=False,
								resizeToFitChildren=False,
								toolbox=True,
								title=window_title))
		scrollLayout = str(pm.scrollLayout(verticalScrollBarThickness=16, 
										horizontalScrollBarThickness=16))
		pm.columnLayout(adjustableColumn=True)
		for item in array:
			text_field = str(pm.textField(height=20,
											width=500, 
											editable=False,
											insertText=str(item)))
		pm.setParent('..')
		pm.showWindow(window)
		return

	# ----------------------------------------------------------------------









#module name
# print (__name__)
# ======================================================================
# Notes
# ======================================================================





#deprecated -------------------------------------


# def getBorderFacesOfFaces(faces, includeBordered=False):
# 	'''
# 	Get any faces attached to the given faces.

# 	:Parameters:
# 		faces (unicode, str, list) = faces to get bordering faces for.
# 		includeBordered (bool) = optional. return the bordered face along with the results.

# 	:Return:
# 		list - the border faces of the given faces.
# 	'''
# 	adjEdges = pm.polyListComponentConversion(faces, fromFace=1, toEdge=1)
# 	adjFaces = pm.polyListComponentConversion(adjEdges, toFace=1, fromEdge=1)
# 	expanded = pm.filterExpand(adjFaces, expand=True, selectionMask=34) #keep faces as individual elements.

# 	if includeBordered:
# 		return list(str(f) for f in expanded) #convert unicode to str.
# 	else:
# 		return list(str(f) for f in expanded if f not in faces) #convert unicode to str and exclude the original faces.



	# def getComponents(objects, type_, flatten=True):
	# 	'''
	# 	Get the components of the given type from the given object.

	# 	:Parameters:
	# 		objects (obj)(list) = The polygonal object(s) to get the components of.
	# 		flatten (bool) = Flattens the returned list of objects so that each component is identified individually. (much faster)

	# 	:Return:
	# 		(list) component objects.
	# 	'''
	# 	if isinstance(objects, (str, unicode)):
	# 		objects = pm.ls(objects)

	# 	if not isinstance(objects, (list, set, tuple)):
	# 		objects=[objects]

	# 	types = {'vertices':'vtx', 'edges':'e', 'faces':'f'}

	# 	components=[]
	# 	for obj in objects:
	# 		cmpts = pm.ls('{}.{}[*]'.format(obj, types[type_]), flatten=flatten)
	# 		components+=cmpts

	# 	return components


	# @staticmethod
	# def getSelectedComponents(componentType, objects=None, returnType=str):
	# 	'''
	# 	Get the component selection of the given type.

	# 	:Parameters:
	# 		componentType (str) = The desired component type. (valid values are: 'vertices', 'edges', 'faces')
	# 		objects (obj)(list) = If polygonal object(s) are given, then only selected components from those object(s) will be returned.
	# 		returnType (str) = Desired output style.
	# 				ex. str (default) = [u'test_cube:pCube1.vtx[0]']
	# 					int = {nt.Mesh(u'test_cube:pCube1Shape'): set([0])}
	# 					object = [MeshVertex(u'test_cube:pCube1Shape.vtx[0]')]

	# 	:Return:
	# 		(list)(dict) components (based on given 'componentType' and 'returnType' value).
	# 	'''
	# 	types = {'vertices':31, 'edges':32, 'faces':34}

	# 	if objects:
	# 		selection = pm.ls(objects, sl=1)
	# 		components = pm.filterExpand(selection, selectionMask=types[componentType])
	# 	else:
	# 		components = pm.filterExpand(selectionMask=types[componentType])


	# 	if returnType==str:
	# 		selectedComponents = components

	# 	if returnType==int:
	# 		selectedComponents={}
	# 		for c in components:
	# 			obj = pm.ls(c, objectsOnly=1)[0]
	# 			componentNum = int(c.split('[')[-1].rstrip(']'))

	# 			if obj in selectedComponents:
	# 				selectedComponents[obj].add(componentNum)
	# 			else:
	# 				selectedComponents[obj] = {componentNum}

	# 	if returnType==object:
	# 		attrs = {'vertices':'vtx', 'edges':'e', 'faces':'f'}
	# 		selectedComponents = [getattr(pm.ls(c, objectsOnly=1)[0], attrs[componentType])[n] for n, c in enumerate(components)] if components else []


	# 	return selectedComponents



# @staticmethod
# 	def getSelectedComponents(type_, obj=None):
# 		'''
# 		Get the component selection of the given type.

# 		:Parameters:
# 			obj (obj) = If a polygonal object is given, then only selected components from that object will be returned.

# 		:Return:
# 			(list) component objects.
# 		'''
# 		types = {'vertices':31, 'edges':32, 'faces':34}

# 		if obj:
# 			components = pm.filterExpand(pm.ls(obj, sl=1), selectionMask=types[type_])
# 		else:
# 			components = pm.filterExpand(selectionMask=types[type_])

# 		selectedComponents = [c.split('[')[-1].rstrip(']') for c in components] if components else []

# 		return selectedComponents

# def getClosestVerts(set1, set2, tolerance=100):
# 		'''
# 		Find the two closest vertices between the two sets of vertices.

# 		:Parameters:
# 			set1 (list) = The first set of vertices.
# 			set2 (list) = The second set of vertices.
# 			tolerance (int) = Maximum search distance.

# 		:Return:
# 			(list) closest vertex pair (<vertex from set1>, <vertex from set2>).
# 		'''
# 		closestDistance=tolerance
# 		closestVerts=None
# 		for v1 in set1:
# 			v1Pos = pm.pointPosition(v1, world=1)
# 			for v2 in set2:
# 				v2Pos = pm.pointPosition(v2, world=1)
# 				distance = Slots_maya.getDistBetweenTwoPoints(v1Pos, v2Pos)

# 				if distance < closestDistance:
# 					closestDistance = distance
# 					if closestDistance < tolerance:
# 						closestVerts = [v1, v2]

# 		return closestVerts


	# @staticmethod
	# def shortestEdgePath():
	# 	'''
	# 	Select shortest edge path between (two or more) selected edges.
	# 	'''
	# 	#:Return: list of lists. each containing an edge paths components
	# 	selectTypeEdge = pm.filterExpand (selectionMask=32) #returns True if selectionMask=Edges
	# 	if (selectTypeEdge): #if selection is polygon edges, convert to vertices.
	# 		mel.eval("PolySelectConvert 3;")
	# 	selection=pm.ls (selection=1, flatten=1)

	# 	vertList=[]

	# 	for objName in selection:
	# 		objName = str(objName) #ex. "polyShape.vtx[176]"
	# 		index1 = objName.find("[")
	# 		index2 = objName.find("]")
	# 		vertNum = objName[index1+1:index2] #ex. "176"
	# 		# position = pm.pointPosition(objName) 
	# 		object_ = objName[:index1-4] #ex. "polyShape"
	# 		# print(object_, index1, index2#, position)
	# 		vertList.append(vertNum)

	# 	if (selectTypeEdge):
	# 		pm.selectType (edge=True)

	# 	paths=[]
	# 	for index in range(3): #get edge path between vertList[0],[1] [1],[2] [2],[3] to make sure everything is selected between the original four vertices/two edges
	# 		edgePath = pm.polySelect(object_, shortestEdgePath=(int(vertList[index]), int(vertList[index+1])))
	# 		paths.append(edgePath)

	# 	return paths



	# def snapToClosestVertex(vertices, obj, tolerance=0.125):
	# 	'''
	# 	This Function Snaps Vertices To Onto The Reference Object.

	# 	:Parameters:
	# 		obj (str) = The object to snap to.
	# 		vertices (list) = The vertices to snap.
	# 		tolerance (float) = Max distance.
	# 	'''
	# 	Slots_maya.loadPlugin('nearestPointOnMesh')
	# 	nearestPointOnMeshNode = mel.eval('{} {}'.format('nearestPointOnMesh', obj))
	# 	pm.delete(nearestPointOnMeshNode)

	# 	pm.undoInfo(openChunk=True)
	# 	for vertex in vertices:

	# 		vertexPosition = pm.pointPosition(vertex, world=True)
	# 		pm.setAttr('{}.inPosition'.format(nearestPointOnMeshNode), vertexPosition[0], vertexPosition[1], vertexPosition[2])
	# 		associatedFaceId = pm.getAttr('{}.nearestFaceIndex'.format(nearestPointOnMeshNode))
	# 		vtxsFaces = pm.filterExpand(pm.polyListComponentConversion('{0}.f[{1}]'.format(obj, associatedFaceId), fromFace=True,  toVertexFace=True), sm=70, expand=True)

	# 		closestDistance = 2**32-1

	# 		closestPosition=[]
	# 		for vtxsFace in vtxsFaces:
	# 			associatedVtx = pm.polyListComponentConversion(vtxsFace, fromVertexFace=True, toVertex=True)
	# 			associatedVtxPosition = pm.pointPosition(associatedVtx, world=True)
				
	# 			distance = Slots_maya.getDistBetweenTwoPoints(vertexPosition, associatedVtxPosition)

	# 			if distance<closestDistance:
	# 				closestDistance = distance
	# 				closestPosition = associatedVtxPosition
				
	# 			if closestDistance<tolerance:
	# 				pm.move(closestPosition[0], closestPosition[1], closestPosition[2], vertex, worldSpace=True)

	# 	# pm.delete(nearestPointOnMeshNode)
	# 	pm.undoInfo(closeChunk=True)








# def getContigiousIslands(faces, faceIslands=[]):
# 	'''
# 	Get a list containing sets of adjacent polygon faces grouped by islands.
# 	:Parameters:
# 		faces (list) = polygon faces to be filtered for adjacent.
# 		faceIslands (list) = optional. list of sets. ability to add faces from previous calls to the return value.
# 	:Return:
# 		list of sets of adjacent faces.
# 	'''
# 	face=None
# 	faces = list(str(f) for f in faces) #work on a copy of the argument so that removal of elements doesn't effect the passed in list.
# 	prevFaces=[]

# 	for _ in range(len(faces)):
# 		# print ''
# 		if not face:
# 			try:
# 				face = faces[0]
# 				island=set([face])
# 			except:
# 				break

# 		adjFaces = [f for f in Slots_maya.getBorderComponents(face) if not f in prevFaces and f in faces]
# 		prevFaces.append(face)
# 		# print '-face     ','   *',face
# 		# print '-adjFaces ','  **',adjFaces
# 		# print '-prevFaces','    ',prevFaces

# 		try: #add face to current island if it hasn't already been added, and is one of the faces specified by the faces argument.
# 			island.add(adjFaces[0])
# 			face = adjFaces[0]

# 		except: #if there are no adjacent faces, start a new island set.
# 			faceIslands.append(island)
# 			face = None
# 			# print '-island   ','   $',island
# 			# print '\n',40*'-'
# 		faces.remove(prevFaces[-1])

# 	return faceIslands