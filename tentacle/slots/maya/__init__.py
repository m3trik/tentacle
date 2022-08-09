# !/usr/bin/python
# coding=utf-8
import os

from PySide2 import QtGui, QtWidgets, QtCore
import shiboken2

import maya.mel as mel
import pymel.core as pm
import maya.OpenMayaUI as omui

from slots import Slots
from tools_maya.node_tools_maya import Node_tools_maya
from tools_maya.component_tools_maya import Component_tools_maya




class Slots_maya(Slots, Node_tools_maya, Component_tools_maya):
	'''App specific methods inherited by all other slot classes.
	'''
	def __init__(self, *args, **kwargs):
		Slots.__init__(self, *args, **kwargs)


	def undo(fn):
		'''A decorator to place a function into Maya's undo chunk.
		Prevents the undo queue from breaking entirely if an exception is raised within the given function.

		:Parameters:
			fn (obj) = The decorated python function that will be placed into the undo que as a single entry.
		'''
		def wrapper(*args, **kwargs):
			with pm.UndoChunk():
				rtn = fn(*args, **kwargs)
				return rtn
		return wrapper

	# ----------------------------------------------------------------------









	# ======================================================================
		'MATH'
	# ======================================================================

	def getVectorFromComponents(components):
		'''Get a vector using the averaged vertex normals of the given components.

		:Parameters:
			components (list) = A list of component to get normals of.

		:Return:
			(vector) ex. [-4.5296159711938344e-08, 1.0, 1.6846732009412335e-08]
		'''
		vertices = pm.polyListComponentConversion(components, toVertex=1)

		norm = pm.polyNormalPerVertex(vertices, query=True, xyz=True)
		normal_vector = [sum(norm[0::3])/len(norm[0::3]), sum(norm[1::3])/len(norm[1::3]), sum(norm[2::3])/len(norm[2::3])] #averaging of all x,y,z points.

		return normal_vector

	# ----------------------------------------------------------------------









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
	def getMayaMainWindow():
		'''Get the main Maya window as a QtWidgets.QMainWindow instance

		:Return:
			QtGui.QMainWindow instance of the top level Maya windows
		'''
		ptr = omui.MQtUtil.mainWindow()
		if ptr:
			return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


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
		for f in ('findControl', 'findLayout', 'findMenuItem'):
			ptr = getattr(omui.MQtUtil, f)(name) #equivalent to: ex. omui.MQtUtil.findControl(name)
			if ptr:
				return shiboken2.wrapInstance(long(ptr), QtWidgets.QWidget)


	@classmethod
	def attr(cls, fn):
		'''A decorator for setAttributeWindow (objAttrWindow).
		'''
		def wrapper(self, *args, **kwargs):
			self.setAttributeWindow(fn(self, *args, **kwargs))
		return wrapper

	def setAttributeWindow(self, obj, attributes={}, include=[], exclude=[], checkableLabel=False, fn=None, fn_args=[]):
		'''Launch a popup window containing the given objects attributes.

		:Parameters:
			obj (str)(obj)(list) = The object to get the attributes of, or it's name. If given as a list, only the first index will be used.
			attributes (dict) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from self.getAttributesMax for the given obj.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']
			checkableLabel (bool) = Set the attribute labels as checkable.
			fn (method) = Set an alternative method to call on widget signal. ex. fn(obj, {'attr':<value>})
			fn_args (list) = Any additonal args to pass to fn.
				The first parameter of fn is always the given object, and the last parameter is the attribute:value pairs as a dict.

		ex. call: self.setAttributeWindow(node, attrs, fn=Slots_maya.setParameterValuesMEL, fn_args='transformLimits') #set attributes for the Maya command transformLimits.
		ex. call: self.setAttributeWindow(transform[0], include=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkableLabel=True)
		'''
		try:
			obj = pm.ls(obj)[0]
		except Exception as error:
			return 'Error: {}.setAttributeWindow: Invalid Object: {}'.format(__name__, obj)

		fn = fn if fn else self.setAttributesMEL

		if attributes:
			attributes = {k:v for k, v in attributes.items() 
				if not k in exclude and (k in include if include else k not in include)}
		else:
			attributes = self.getAttributesMEL(obj, include=include, exclude=exclude)

		menu = self.objAttrWindow(obj, attributes, checkableLabel=checkableLabel, fn=fn, fn_args=fn_args)

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









	# ======================================================================
		' SCRIPTING'
	# ======================================================================

	@staticmethod
	def convertMelToPy(mel, excludeFromInput=[], excludeFromOutput=['from pymel.all import *','s pm']):
		'''Convert a string representing mel code into a string representing python code.

		:Parameters:
			mel (str) = string containing mel code.
			excludeFromInput (list) (list) = of strings specifying series of chars to strip from the Input.
			excludeFromOutput (list) (list) = of strings specifying series of chars to strip from the Output.
		
		mel2PyStr Parameters:
			currentModule (str) = The name of the module that the hypothetical code is executing in. In most cases you will leave it at its default, the __main__ namespace.
			pymelNamespace (str) = The namespace into which pymel will be imported. the default is '', which means from pymel.all import *
			forceCompatibility (bool) = If True, the translator will attempt to use non-standard python types in order to produce python code which more exactly reproduces the behavior of the original mel file, but which will produce 'uglier' code. Use this option if you wish to produce the most reliable code without any manual cleanup.
			verbosity (int) = Set to non-zero for a lot of feedback.
		'''
		from pymel.tools import mel2py
		import re

		l = filter(None, re.split('[\n][;]', mel))

		python=[]
		for e in l:
			if not e in excludeFromInput:
				try:
					py = mel2py.mel2pyStr(e, pymelNamespace='pm')
					for i in excludeFromOutput:
						py = py.strip(i)
				except:
					py = e
				python.append(py)

		return ''.join(python)


	@staticmethod
	def commandHelp(command): #mel command help
		#:Parameters: command (str) = mel command
		command = ('help ' + command)
		modtext = (mel.eval(command))
		outputscrollField (modtext, "command help", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def keywordSearch (keyword): #keyword command search
		#:Parameters: keyword (str) = 
		keyword = ('help -list' + '"*' + keyword + '*"')
		array = sorted(mel.eval(keyword))
		outputTextField(array, "keyword search")


	@staticmethod
	def queryRuntime (command): #query runtime command info
		type       = ('whatIs '                           + command + ';')
		catagory   = ('runTimeCommand -query -category '  + command + ';')
		command	   = ('runTimeCommand -query -command '   + command + ';')
		annotation = ('runTimeCommand -query -annotation '+ command + ';')
		type = (mel.eval(type))
		catagory = (mel.eval(catagory))
		command = (mel.eval(command))
		annotation = (mel.eval(annotation))
		output_text = '{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}\n\n{}\n{}'.format(command, "Type:", type, "Annotation:", annotation, "Catagory:", catagory, "Command:", command)
		outputscrollField(output_text, "runTimeCommand", 1.0, 1.0) #text, window_title, width, height


	@staticmethod
	def searchMEL (keyword): #search autodest MEL documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/Commands/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPython (keyword): #Search autodesk Python documentation
		url = '{}{}{}'.format("http://help.autodesk.com/cloudhelp/2017/ENU/Maya-Tech-Docs/CommandsPython/",keyword,".html")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def searchPymel (keyword): #search online pymel documentation
		url = '{}{}{}'.format("http://download.autodesk.com/global/docs/maya2014/zh_cn/PyMel/search.html?q=",keyword,"&check_keywords=yes&area=default")
		pm.showHelp (url, absolute=True)


	@staticmethod
	def currentCtx(): #get current tool context
		output_text = mel.eval('currentCtx;')
		outputscrollField(output_text, "currentCtx", 1.0, 1.0)


	@staticmethod
	def sourceScript(): #Source External Script file
		import os.path

		mel_checkBox = checkBox('mel_checkBox', query=1, value=1)
		python_checkBox = checkBox('python_checkBox', query=1, value=1)

		if mel_checkBox == 1:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.mel")
			
		else:
			path = os.path.expandvars("%\CLOUD%/____graphics/Maya/scripts/*.py")

		file = pm.system.fileDialog (directoryMask=path)
		pm.openFile(file)


	@staticmethod
	def commandRef(): #open maya MEL commands list 
		pm.showHelp ('http://download.autodesk.com/us/maya/2011help/Commands/index.html', absolute=True)


	@staticmethod
	def globalVars(): #$g List all global mel variables in current scene
		mel.eval('scriptEditorInfo -clearHistory')
		array = sorted(mel.eval("env"))
		outputTextField(array, "Global Variables")


	@staticmethod
	def listUiObjects(): #lsUI returns the names of UI objects
		windows			= '{}\n{}\n{}\n'.format("Windows", "Windows created using ELF UI commands:", pm.lsUI (windows=True))
		panels			= '{}\n{}\n{}\n'.format("Panels", "All currently existing panels:", pm.lsUI (panels=True))
		editors			= '{}\n{}\n{}\n'.format("Editors", "All currently existing editors:", pm.lsUI (editors=True))
		controls		= '{}\n{}\n{}\n'.format("Controls", "Controls created using ELF UI commands: [e.g. buttons, checkboxes, etc]", pm.lsUI (controls=True))
		control_layouts = '{}\n{}\n{}\n'.format("Control Layouts", "Control layouts created using ELF UI commands: [e.g. formLayouts, paneLayouts, etc.]", pm.lsUI (controlLayouts=True))
		menus			= '{}\n{}\n{}\n'.format("Menus", "Menus created using ELF UI commands:", pm.lsUI (menus=True))
		menu_items	= '{}\n{}\n{}\n'.format("Menu Items", "Menu items created using ELF UI commands:", pm.lsUI (menuItems=True))
		contexts		= '{}\n{}\n{}\n'.format("Tool Contexts", "Tool contexts created using ELF UI commands:", pm.lsUI (contexts=True))
		output_text	= '{}\n{}\n{}\n{}\n{}\n{}\n{}\n{}'.format(windows, panels, editors, menus, menu_items, controls, control_layouts, contexts)
		outputscrollField(output_text, "Ui Elements", 6.4, 0.85)

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
# 				distance = Slots_maya.getDistanceBetweenTwoPoints(v1Pos, v2Pos)

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
				
	# 			distance = Slots_maya.getDistanceBetweenTwoPoints(vertexPosition, associatedVtxPosition)

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