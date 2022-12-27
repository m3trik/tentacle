# !/usr/bin/python
# coding=utf-8
import sys, os

import importlib
import inspect

try:
	import pymel.core as pm
except ImportError as error:
	print (__file__, error)

from tentacle.slots.tk import itertk


class Mayatk():
	'''
	'''
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


	@staticmethod
	def getMainWindow():
		'''Get maya's main window object.

		:Return:
			(QWidget)
		'''
		from PySide2.QtWidgets import QApplication

		app = QApplication.instance()
		if not app:
			print ('{} in getMainWindow\n\t# Warning: Could not find QApplication instance. #'.format(__file__))
			return None

		main_window = next(iter(w for w in app.topLevelWidgets() if w.objectName()=='MayaWindow'), None)
		if not main_window:
			print ('{} in getMainWindow\n\t# Warning: Could not find main window instance. #'.format(__file__))
			return None

		return main_window


	@classmethod
	def mfnMeshGenerator(cls, objects):
		'''Generate mfn mesh from the given list of objects.

		:Parameters:
			objects (str)(obj(list) = The objects to convert to mfn mesh.

		:Return:
			(generator)
		'''
		import maya.OpenMaya as om

		selectionList = om.MSelectionList()
		for mesh in cls.getShapeNode(pm.ls(objects)):
			selectionList.add(mesh)

		for i in range(selectionList.length()):    
			dagPath = om.MDagPath()
			selectionList.getDagPath(i, dagPath)
			# print (dagPath.fullPathName()) #debug
			mfnMesh = om.MFnMesh(dagPath)
			yield mfnMesh


	@classmethod
	def getType(cls, objects):
		'''Get the object type as a string.

		:Parameters:
			objects (str)(obj)(list) = The object(s) to query.

		:Return:
			(str)(list) The node type. A list is always returned when 'objects' is given as a list.
		'''
		types=[]
		for obj in pm.ls(objects):

			if cls.isGroup(obj):
				typ = 'group'
			else:
				typ = comptk.getComponentType(obj)
			if not typ:
				typ = pm.objectType(obj)
			types.append(typ)

		return itertk.formatReturn(types, objects)


	@classmethod
	def getTransformNode(cls, nodes, returnType='str', attributes=False, include=[], exclude=[]):
		'''Get transform node(s) or node attributes.

		:Parameters:
			nodes (str)(obj)(list) = A relative of a transform Node.
			returnType (str) = The desired returned object type. Not valid with the `attributes` parameter.
				(valid: 'str'(default), 'obj').
			attributes (bool) = Return the attributes of the node, rather then the node itself.

		:Return:
			(obj)(list) node(s) or node attributes. A list is always returned when 'nodes' is given as a list.
		'''
		result=[]
		for node in pm.ls(nodes):
			transforms = pm.ls(node, type='transform')
			if not transforms: #from shape
				shapeNodes = pm.ls(node, objectsOnly=1)
				transforms = pm.listRelatives(shapeNodes, parent=1)
				if not transforms: #from history
					try:
						transforms = pm.listRelatives(pm.listHistory(node, future=1), parent=1)
					except Exception as error:
						transforms=[]
			for n in transforms:
				result.append(n)

		if attributes:
			result = pm.listAttr(result, read=1, hasData=1)

		#convert element type.
		result = cls.convertArrayType(result, returnType=returnType, flatten=True)
		#filter
		result = itertk.filterList(result, include, exclude)
		#return as list if `nodes` was given as a list.
		return itertk.formatReturn(list(set(result)), nodes)


	@classmethod
	def getShapeNode(cls, nodes, returnType='str', attributes=False, include=[], exclude=[]):
		'''Get shape node(s) or node attributes.

		:Parameters:
			nodes (str)(obj)(list) = A relative of a shape Node.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).
			attributes (bool) = Return the attributes of the node, rather then the node itself.

		:Return:
			(obj)(list) node(s) or node attributes. A list is always returned when 'nodes' is given as a list.
		'''
		result=[]
		for node in pm.ls(nodes):
			shapes = pm.listRelatives(node, children=1, shapes=1) #get shape node from transform: returns list ie. [nt.Mesh('pConeShape1')]
			if not shapes:
				shapes = pm.ls(node, type='shape')
				if not shapes: #get shape from transform
					try:
						transforms = pm.listRelatives(pm.listHistory(node, future=1), parent=1)
						shapes = cls.getShapeNode(transforms)
					except Exception as error:
						shapes = []
			for n in shapes:
				result.append(n)

		if attributes:
			result = pm.listAttr(result, read=1, hasData=1)

		#convert element type.
		result = cls.convertArrayType(result, returnType=returnType, flatten=True)
		#filter
		result = itertk.filterList(result, include, exclude)
		#return as list if `nodes` was given as a list.
		return itertk.formatReturn(list(set(result)), nodes)


	@classmethod
	def getHistoryNode(cls, nodes, returnType='str', attributes=False, include=[], exclude=[]):
		'''Get history node(s) or node attributes.

		:Parameters:
			nodes (str)(obj)(list) = A relative of a history Node.
			returnType (str) = The desired returned object type. 
				(valid: 'str'(default), 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level).
			attributes (bool) = Return the attributes of the node, rather then the node itself.

		:Return:
			(obj)(list) node(s) or node attributes. A list is always returned when 'nodes' is given as a list.
		'''
		result=[]
		for node in pm.ls(nodes):
			shapes = pm.listRelatives(node, children=1, shapes=1) #get shape node from transform: returns list ie. [nt.Mesh('pConeShape1')]
			try:
				history = pm.listConnections(shapes, source=1, destination=0)[-1] #get incoming connections: returns list ie. [nt.PolyCone('polyCone1')]
			except IndexError as error:
				try:
					history = node.history()[-1]
				except AttributeError as error:
					print ('{} in getHistoryNode\n\t# Error: {} #'.format(__file__, error))
					continue
			result.append(history)

		if attributes:
			result = pm.listAttr(result, read=1, hasData=1)

		#convert element type.
		result = cls.convertArrayType(result, returnType=returnType, flatten=True)
		#filter
		result = itertk.filterList(result, include, exclude)
		#return as list if `nodes` was given as a list.
		return itertk.formatReturn(list(set(result)), nodes)


	@staticmethod
	def isGroup(objects):
		'''Determine if each of the given object(s) is a group.
		A group is defined as a transform with children.

		:Parameters:
			nodes (str)(obj)(list) = The object(s) to query.

		:Return:
			(bool)(list) A list is always returned when 'objects' is given as a list.
		'''
		result=[]
		for n in pm.ls(objects):
			try:
				q = all((
					type(n)==pm.nodetypes.Transform,
					all(([type(c)==pm.nodetypes.Transform for c in n.getChildren()])),
				))
			except AttributeError as error:
				q = False
			result.append(q)

		return itertk.formatReturn(result, objects)


	@classmethod
	def getGroups(cls, empty=False):
		'''Get all groups in the scene.

		:Parameters:
			empty (bool) = Return only empty groups.

		:Return:
			(bool)
		'''
		transforms =  pm.ls(type='transform')

		groups=[]
		for t in transforms:
			if cls.isGroup(t):
				if empty:
					children = pm.listRelatives(t, children=True)
					if children:
						continue
				groups.append(t)

		return groups


	@staticmethod
	def getParent(node, all=False):
		'''List the parents of an object.
		'''
		if all:
			objects = pm.ls(node, l=1)
			tokens=[]
			return objects[0].split("|")

		try:
			return pm.listRelatives(node, parent=True, type='transform')[0]
		except IndexError as error:
			return None


	@staticmethod
	def getChildren(node):
		'''List the children of an object.
		'''
		try:
			return  pm.listRelatives(node, children=True, type='transform')
		except IndexError as error:
			return []


	@staticmethod
	def getArrayType(lst):
		'''Determine if the given element(s) type.

		:Parameters:
			obj (str)(obj)(list) = The components(s) to query.

		:Return:
			(list) 'str', 'obj'(shape node), 'transform'(as string), 'int'(valid only at sub-object level)

		ex. call:
		getArrayType('cyl.vtx[0]') #returns: 'transform'
		getArrayType('cylShape.vtx[:]') #returns: 'str'
		'''
		try:
			o = itertk.makeList(lst)[0]
		except IndexError as error:
			# print ('{}\n# Error: getArrayType: Operation requires at least one object. #\n	{}'.format(__file__, error))
			return ''

		return 'str' if isinstance(o, str) else 'int' if isinstance(o, int) else 'obj'


	@staticmethod
	def convertArrayType(lst, returnType='str', flatten=False):
		'''Convert the given element(s) to <obj>, 'str', or int values.

		:Parameters:
			lst (str)(obj)(list) = The components(s) to convert.
			returnType (str) = The desired returned array element type.
				valid: 'str'(default), 'obj', 'int'(valid only at sub-object level).
			flatten (bool) = Flattens the returned list of objects so that each component is it's own element.

		:Return:
			(list)(dict) return a dict only with a return type of 'int' and more that one object given.

		ex. call:
		convertArrayType('obj.vtx[:2]', 'str') #returns: ['objShape.vtx[0:2]']
		convertArrayType('obj.vtx[:2]', 'str', True) #returns: ['objShape.vtx[0]', 'objShape.vtx[1]', 'objShape.vtx[2]']
		convertArrayType('obj.vtx[:2]', 'obj') #returns: [MeshVertex('objShape.vtx[0:2]')]
		convertArrayType('obj.vtx[:2]', 'obj', True) #returns: [MeshVertex('objShape.vtx[0]'), MeshVertex('objShape.vtx[1]'), MeshVertex('objShape.vtx[2]')]
		convertArrayType('obj.vtx[:2]', 'int')) #returns: {nt.Mesh('objShape'): [(0, 2)]}
		convertArrayType('obj.vtx[:2]', 'int', True)) #returns: {nt.Mesh('objShape'): [0, 1, 2]}
		'''
		lst = pm.ls(lst, flatten=flatten)
		if not lst or isinstance(lst[0], int):
			return []

		if returnType=='int':
			result={}
			for c in lst:
				obj = pm.ls(c, objectsOnly=1)[0]
				num = c.split('[')[-1].rstrip(']')

				try:
					if flatten:
						componentNum = int(num)
					else:
						n = [int(n) for n in num.split(':')]
						componentNum = tuple(n) if len(n)>1 else n[0]

					if obj in result: #append to existing object key.
						result[obj].append(componentNum)
					else:
						result[obj] = [componentNum]
				except ValueError as error: #incompatible object type.
					print ('{} in convertArrayType\n\t# Error: unable to convert {} {} to int. #\n\t{}'.format(__file__, obj, num, error))
					break

			objects = set(pm.ls(lst, objectsOnly=True))
			if len(objects)==1: #flatten the dict values from 'result' and remove any duplicates.
				flattened = itertk.flatten(result.values())
				result = itertk.removeDuplicates(flattened)

		elif returnType=='str':
			result = list(map(str, lst))

		else:
			result = lst

		return result


	@staticmethod
	def getParameterValuesMEL(node, cmd, parameters):
		'''Query a Maya command, and return a key:value pair for each of the given parameters.

		:Parameters:
			node (str)(obj)(list) = The object to query attributes of.
			parameters (list) = The command parameters to query. ie. ['enableTranslationX','translationX']

		:Return:
			(dict) {'parameter name':<value>} ie. {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]}

		ex. call: getParameterValuesMEL(obj, 'transformLimits', ['enableTranslationX','translationX'])
		'''
		cmd = getattr(pm, cmd)
		node = pm.ls(node)[0]

		result={}
		for p in parameters:
			values = cmd(node, **{'q':True, p:True}) #query the parameter to get it's value.

			result[p] = values

		return result


	@staticmethod
	def setParameterValuesMEL(node, cmd, parameters):
		'''Set parameters using a maya command.

		:Parameters:
			node (str)(obj)(list) = The object to query attributes of.
			parameters (dict) = The command's parameters and their desired values. ie. {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]}

		ex. call: setParameterValuesMEL(obj, 'transformLimits', {'enableTranslationX': [False, False], 'translationX': [-1.0, 1.0]})
		'''
		cmd = getattr(pm, cmd)
		node = pm.ls(node)[0]

		for p, v in parameters.items():
		 	cmd(node, **{p:v})


	@staticmethod
	def getAttributesMEL(node, include=[], exclude=[]):
		'''Get node attributes and their corresponding values as a dict.

		:Parameters:
			node (obj) = The node to get attributes for.
			include (list) = Attributes to include. All other will be omitted. Exclude takes dominance over include. Meaning, if the same attribute is in both lists, it will be excluded.
			exclude (list) = Attributes to exclude from the returned dictionay. ie. ['Position','Rotation','Scale','renderable','isHidden','isFrozen','selected']

		:Return:
			(dict) {'string attribute': current value}
		'''
		# print('node:', node); print('attr:', , read=1, hasData=1))
		attributes={}
		for attr in pm.listAttr(node, read=1, hasData=1):
			if not attr in exclude and (attr in include if include else attr not in include): #ie. pm.getAttr('polyCube1.subdivisionsDepth')
				try:
					attributes[attr] = pm.getAttr(getattr(node, attr), silent=True) #get the attribute's value.
				except Exception as error:
					print (error)

		return attributes


	@staticmethod
	def setAttributesMEL(nodes, verbose=False, **attributes):
		'''Set node attribute values.

		:Parameters:
			nodes (str)(obj)(list) = The node(s) to set attributes for.
			verbose (bool) = Print feedback messages such as errors to the console.
			attributes (dict) = Attributes and their correponding value to set. ie. {'string attribute': value}

		ex call: setAttributesMEL(node, translateY=6)
		'''
		for node in pm.ls(nodes):

			for attr, value in attributes.items():
				try:
					a = getattr(node, attr)
					pm.setAttr(a, value) #ie. pm.setAttr('polyCube1.subdivisionsDepth', 5)
				except (AttributeError, TypeError) as error:
					if verbose:
						print ('# Error:', __file__, error, node, attr, value, '#')
					pass


	@staticmethod
	def connectAttributes(attr, place, file):
		'''A convenience procedure for connecting common attributes between two nodes.

		:Parameters:
			attr () = 
			place () = 
			file () = 

		ex. call:
		Use convenience command to connect attributes which share 
		their names for both the placement and file nodes.
			connectAttributes('coverage', 'place2d', fileNode')
			connectAttributes('translateFrame', 'place2d', fileNode')
			connectAttributes('rotateFrame', 'place2d', fileNode')
			connectAttributes('mirror', 'place2d', fileNode')
			connectAttributes('stagger', 'place2d', fileNode')
			connectAttributes('wrap', 'place2d', fileNode')
			connectAttributes('wrapV', 'place2d', fileNode')
			connectAttributes('repeatUV', 'place2d', fileNode')
			connectAttributes('offset', 'place2d', fileNode')
			connectAttributes('rotateUV', 'place2d', fileNode')

		These two are named differently.
			connectAttr -f ( $place2d + ".outUV" ) ( $fileNode + ".uv" );
			connectAttr -f ( $place2d + ".outUvFilterSize" ) ( $fileNode + ".uvFilterSize" );
		'''
		pm.connectAttr('{}.{}'.format(place, attr), '{}.{}'.format(file, attr), f=1)


	@classmethod
	def createRenderNode(cls, nodeType, flag='asShader', flag2='surfaceShader', name='', tex='', place2dTexture=False, postCommand='', **kwargs):
		'''Procedure to create the node classified as specified by the inputs.

		:Parameters:
			nodeType (str) = The type of node to be created. ie. 'StingrayPBS' or 'aiStandardSurface'
			flag (str) = A flag specifying which how to classify the node created.
				valid:	as2DTexture, as3DTexture, asEnvTexture, asShader, asLight, asUtility
			flag2 (str) = A secondary flag used to make decisions in combination with 'asType'
				valid:	-asBump : defines a created texture as a bump
						-asNoShadingGroup : for materials; create without a shading group
						-asDisplacement : for anything; map the created node to a displacement material.
						-asUtility : for anything; do whatever the $as flag says, but also classify as a utility
						-asPostProcess : for any postprocess node
			name (str) = The desired node name.
			tex (str) = The path to a texture file for those nodes that support one.
			place2dTexture (bool) = If not needed, the place2dTexture node will be deleted after creation.
			postCommand (str) = A command entered by the user when invoking createRenderNode.
					The command will substitute the string %node with the name of the
					node it creates.  createRenderWindow will be closed if a command
					is not the null string ("").
			kwargs () = Set additional node attributes after creation. ie. colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1

		:Return:
			(obj) node

		ex. call: createRenderNode('StingrayPBS')
		ex. call: createRenderNode('file', flag='as2DTexture', tex=f, place2dTexture=True, colorSpace='Raw', alphaIsLuminance=1, ignoreColorSpaceFileRules=1)
		ex. call: createRenderNode('aiSkyDomeLight', tex=pathToHdrMap, name='env', camera=0, skyRadius=0) #turn off skydome and viewport visibility.
		'''
		node = pm.PyNode(pm.mel.createRenderNodeCB('-'+flag, flag2, nodeType, postCommand)) # node = pm.shadingNode(typ, asTexture=True)

		if not place2dTexture:
			pm.delete(pm.listConnections(node, type='place2dTexture', source=True, exactType=True))

		if tex:
			try:
				node.fileTextureName.set(tex)
			except Exception as error:
				print ('# Error:', __file__, error, '#')

		if name:
			try:
				pm.rename(node, name)

			except RuntimeError as error:
				print ('# Error:', __file__, error, '#')

		cls.setAttributesMEL(node, **kwargs)
		return node


	@staticmethod
	def getIncomingNodeByType(node, typ, exact=True):
		'''Get the first connected node of the given type with an incoming connection to the given node.

		:Parameters:
			node (str)(obj) = A node with incoming connections.
			typ (str) = The node type to search for. ie. 'StingrayPBS'
			exact (bool) = Only consider nodes of the exact type. Otherwise, derived types are also taken into account.

		:Return:
			(obj)(None) node if found.

		ex. call: env_file_node = getIncomingNodeByType(env_node, 'file') #get the incoming file node.
		'''
		nodes = pm.listConnections(node, type=typ, source=True, exactType=exact)
		return itertk.formatReturn([pm.PyNode(n) for n in nodes])


	@staticmethod
	def getOutgoingNodeByType(node, typ, exact=True):
		'''Get the connected node of the given type with an outgoing connection to the given node.

		:Parameters:
			node (str)(obj) = A node with outgoing connections.
			typ (str) = The node type to search for. ie. 'file'
			exact (bool) = Only consider nodes of the exact type. Otherwise, derived types are also taken into account.

		:Return:
			(list)(obj)(None) node(s)

		ex. call: srSG_node = getOutgoingNodeByType(sr_node, 'shadingEngine') #get the outgoing shadingEngine node.
		'''
		nodes = pm.listConnections(node, type=typ, destination=True, exactType=exact)
		return itertk.formatReturn([pm.PyNode(n) for n in nodes])


	@staticmethod
	def connectMultiAttr(*args, force=True):
		'''Connect multiple node attributes at once.

		:Parameters:
			args (tuple) = Attributes as two element tuples. ie. (<connect from attribute>, <connect to attribute>)

		ex. call: connectMultiAttr(
			(node1.outColor, node2.aiSurfaceShader),
			(node1.outColor, node3.baseColor),
			(node4.outNormal, node5.normalCamera),
		)
		'''
		for frm, to in args:
			try:
				pm.connectAttr(frm, to)
			except Exception as error:
				print ('# Error:', __file__, error, '#')


	@staticmethod
	def nodeExists(n, search='name'):
		'''Check if the node exists in the current scene.

		:Parameters:
			search (str) = The search parameters. valid: 'name', 'type', 'exactType'

		:Return:
			(bool)
		'''
		if search=='name':
			return bool(pm.ls(n))
		elif search=='type':
			return bool(pm.ls(type=n))
		elif search=='exactType':
			return bool(pm.ls(exactType=n))


	@staticmethod
	def getSelectedChannels():
		'''Get any attributes (channels) that are selected in the channel box.

		:Return:
			(str) list of any selected attributes as strings. (ie. ['tx', ry', 'sz'])
		'''
		channelBox = pm.mel.eval('global string $gChannelBoxName; $temp=$gChannelBoxName;') #fetch maya's main channelbox
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
	def mainProgressBar(size, name="progressBar#", stepAmount=1):
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
		status = 'processing: {} items ..'.format(size)

		edit=False
		if pm.progressBar(name, exists=1):
			edit=True

		pm.progressBar(name, edit=edit,
						beginProgress=1,
						isInterruptable=True,
						status=status,
						maxValue=size,
						step=stepAmount)


	@staticmethod
	def viewportMessage(message='', statusMessage='', assistMessage='', position='topCenter'):
		'''
		:Parameters:
			message (str) = The message to be displayed, (accepts html formatting). General message, inherited by -amg/assistMessage and -smg/statusMessage.
			statusMessage (str) = The status info message to be displayed (accepts html formatting).
			assistMessage (str) = The user assistance message to be displayed, (accepts html formatting).
			position (str) = position on screen. possible values are: topCenter","topRight","midLeft","midCenter","midCenterTop","midCenterBot","midRight","botLeft","botCenter","botRight"

		ex. viewportMessage("shutting down:<hl>"+str(timer)+"</hl>")
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
		#window_title = pm.mel.eval(python("window_title"))
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

# -----------------------------------------------
from tentacle import import_submodules, addMembers
addMembers(__name__)
import_submodules(__name__)





# print (__package__, __file__)
# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------
