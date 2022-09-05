# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.duplicate import Duplicate



class Duplicate_maya(Duplicate, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Duplicate.__init__(self, *args, **kwargs)

		dh = self.sb.duplicate.draggable_header
		items = ['Duplicate Special']
		dh.contextMenu.cmb000.addItems_(items, 'Maya Menus')

		tb000 = self.sb.duplicate.tb000
		tb000.contextMenu.add('QCheckBox', setText='Match Vertex Orientaion', setObjectName='chk001', setChecked=False, setToolTip='Attempt to match 3 points of the source to the same 3 points of the target.')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.sb.duplicate.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index('Duplicate Special'):
				mel.eval('DuplicateSpecialOptions;')
			cmb.setCurrentIndex(0)


	def chk010(self, state=None):
		'''Radial Array: Set Pivot
		'''
		global radialPivot
		radialPivot=[]
		#add support for averaging multiple components.
		if self.duplicate_radial_ui.chk010.isChecked():
			selection = pm.ls (selection=1, flatten=1)
			if selection:
				vertices = pm.filterExpand(selectionMask=31) #get selected vertices
				if vertices is not None and vertices==1: #if a single vertex is selected, query that vertex position.
					pivot = pm.xform (selection, query=1, translation=1, worldSpace=1)
				else: #else, get the center of the objects bounding box.
					bb = pm.xform (selection, query=1, boundingBox=1, worldSpace=1)
					pivot = bb[0]+bb[3]/2, bb[1]+bb[4]/2, bb[2]+bb[5]/2 #get median of bounding box coordinates. from [min xyz, max xyz]
			else:
				self.toggleWidgets(self.duplicate_radial_ui, setUnChecked='chk010')
				self.messageBox('Nothing selected.')
				return

			# radialPivot.extend ([pivot[0],pivot[1],pivot[2]])
			radialPivot.extend(pivot) #extend the list contents
			text = str(int(pivot[0]))+","+str(int(pivot[1]))+","+str(int(pivot[2]))
			self.duplicate_radial_ui.chk010.setText(text)
		else:
			del radialPivot[:]
			self.duplicate_radial_ui.chk010.setText("Set Pivot")


	global radialArrayObjList
	radialArrayObjList=[]
	@Slots_maya.undo
	def chk015(self, create=False):
		'''Radial Array: Preview
		'''
		setPivot = self.duplicate_radial_ui.chk010.isChecked() #set pivot point
		instance = self.duplicate_radial_ui.chk011.isChecked() #instance object

		if self.duplicate_radial_ui.chk015.isChecked():
			self.toggleWidgets(self.duplicate_radial_ui, setEnabled='b003')

			selection = pm.ls(selection=1, type="transform", flatten=1)
			if selection:
				if radialArrayObjList:
					try:
						pm.delete(radialArrayObjList) #delete all the geometry in the list
					except:
						pass
					del radialArrayObjList[:] #clear the list

				for obj in selection:
					pm.select (obj)
					objectName = str(obj)

					numDuplicates = int(self.duplicate_radial_ui.s000.value())
					angle = float(self.duplicate_radial_ui.s001.value())

					x=y=z = 0
					if self.duplicate_radial_ui.chk012.isChecked(): x = angle
					if self.duplicate_radial_ui.chk013.isChecked(): y = angle
					if self.duplicate_radial_ui.chk014.isChecked(): z = angle

					# pm.undoInfo (openChunk=1)
					for i in range(1,numDuplicates):
						if instance:
							name = objectName+"_ins"+str(i)
							pm.instance (name=name)
						else:
							name = objectName+"_dup"+str(i)
							pm.duplicate (returnRootsOnly=1, name=name)
						if setPivot:
							if len(radialPivot):
								pm.rotate (x, y, z, relative=1, pivot=radialPivot) #euler=1
							else:
								self.messageBox('No pivot point set.')
						else:
							pm.rotate (x, y, z, relative=1) #euler=1
						radialArrayObjList.append(name)
					#if in isolate select mode; add object	
					currentPanel = pm.paneLayout('viewPanes', q=True, pane1=True) #get the current modelPanel view
					if pm.isolateSelect(currentPanel, query=1, state=1):
						for obj_ in radialArrayObjList:
							pm.isolateSelect (currentPanel, addDagObject=obj_)
					#re-select the original selected object
					pm.select(objectName)
					# pm.undoInfo (closeChunk=1)
			else: #if both lists objects are empty:
				self.toggleWidgets(self.duplicate_radial_ui, setDisabled='b003', setUnChecked='chk015')
				self.messageBox('Nothing selected.')
				return
		else: #if chk015 is unchecked by user or by create button
			if create:
				originalObj = radialArrayObjList[0][:radialArrayObjList[0].rfind("_")] #remove the trailing _ins# or _dup#. ie. pCube1 from pCube1_inst1
				radialArrayObjList.append(originalObj)
				pm.polyUnite (radialArrayObjList, name=originalObj+"_array") #combine objects. using the original name results in a duplicate object error on deletion
				print('Result: '+str(radialArrayObjList))
				pm.delete (radialArrayObjList); del radialArrayObjList[:] #delete all geometry and clear the list
				return
			try:
				pm.delete(radialArrayObjList) #delete all the geometry in the list
			except:
				pass
			del radialArrayObjList[:] #clear the list

			self.toggleWidgets(self.duplicate_radial_ui, setDisabled='b003')


	global duplicateObjList
	duplicateObjList=[]
	@Slots_maya.undo
	def chk016(self, create=False):
		'''Duplicate: Preview
		'''
		if self.duplicate_linear_ui.chk016.isChecked():
			self.toggleWidgets(self.duplicate_linear_ui, setEnabled='b002')

			instance = self.duplicate_linear_ui.chk000.isChecked()
			numOfDuplicates = int(self.duplicate_linear_ui.s005.value())
			keepFacesTogether = self.duplicate_linear_ui.chk009.isChecked()
			transXYZ = [float(self.duplicate_linear_ui.s002.value()),float(self.duplicate_linear_ui.s003.value()),float(self.duplicate_linear_ui.s004.value())]
			rotXYZ = [float(self.duplicate_linear_ui.s007.value()),float(self.duplicate_linear_ui.s008.value()),float(self.duplicate_linear_ui.s009.value())]
			scaleXYZ = [float(self.duplicate_linear_ui.s010.value()),float(self.duplicate_linear_ui.s011.value()),float(self.duplicate_linear_ui.s012.value())]
			translateToComponent = self.duplicate_linear_ui.chk007.isChecked()
			alignToNormal = self.duplicate_linear_ui.chk008.isChecked()
			componentList = [self.duplicate_linear_ui.cmb001.itemText(i) for i in range(self.duplicate_linear_ui.cmb001.count())]

			try:
				pm.delete(duplicateObjList[1:]) #delete all the geometry in the list, except the original obj
			except Exception as error:
				print(error)

			del duplicateObjList[1:] #clear the list, leaving the original obj
			selection = pm.ls(selection=1, flatten=1, objectsOnly=1) #there will only be a selection when first called. After, the last selected item will have been deleted with the other duplicated objects, leaving only the original un-selected.

			if selection:
				obj = selection[0]
				duplicateObjList.insert(0, obj) #insert at first index
			elif duplicateObjList:
				obj = duplicateObjList[0]
				pm.select(obj)
			else:
				self.messageBox('Nothing selected.')

				return

			# pm.undoInfo (openChunk=1)
			if translateToComponent:
				if componentList:
					for num, component in componentList.iteritems():
						vertexPoint = self.sb.transform.slots.getComponentPoint(component)

						pm.xform (obj, rotation=[rotXYZ[0], rotXYZ[1], rotXYZ[2]])
						pm.xform (obj, translation=[vertexPoint[0]+transXYZ[0], vertexPoint[1]+transXYZ[1], vertexPoint[2]+transXYZ[2]])
						pm.xform (obj, scale=[scaleXYZ[0], scaleXYZ[1], scaleXYZ[2]])

						if component != componentList[len(componentList)-1]: #if not at the end of the list, create a new instance of the obj.
							name = str(obj)+'_INST'+str(num)
							duplicatedObject = pm.instance (obj, name=name)
						# print("component:",component,"\n", "normal:",normal,"\n", "vertexPoint:",vertexPoint,"\n")

						duplicateObjList.append(duplicatedObject) #append duplicated object to list
				else:
					self.messageBox('Component list empty.')
					self.toggleWidgets(self.duplicate_linear_ui, setDisabled='b002', setChecked='chk016')
					return
			else:
				for _ in range(numOfDuplicates):
					if ".f" in str(obj): #face
						duplicatedObject = pm.duplicate(name="pExtract1")[0]

						selectedFaces=[duplicatedObject+"."+face.split(".")[1] for face in obj] #create a list of the original selected faces numbers but with duplicated objects name
						
						numFaces = pm.polyEvaluate(duplicatedObject, face=1)
						allFaces = [duplicatedObject+".f["+str(num)+"]" for num in range(numFaces)] #create a list of all faces on the duplicated object

						pm.delete(set(allFaces) -set(selectedFaces)) #delete faces in 'allFaces' that were not in the original obj 

					elif ".e" in str(obj): #edge
						duplicatedObject = pm.polyToCurve(form=2, degree=3, conformToSmoothMeshPreview=1)
					
					elif instance:
						duplicatedObject = pm.instance()

					else:
						duplicatedObject = pm.duplicate()

					pm.xform (duplicatedObject, rotation=rotXYZ, relative=1)
					pm.xform (duplicatedObject, translation=transXYZ, relative=1)
					pm.xform (duplicatedObject, scale=scaleXYZ, relative=1)

					duplicateObjList.append(duplicatedObject) #append duplicated object to list
					pm.select(duplicatedObject)
			# pm.undoInfo (closeChunk=1)

		else: #if chk016 is unchecked by user or by create button
			if create:
				# originalObj = duplicateObjList[0][:duplicateObjList[0].rfind("_")] #remove the trailing _ins# or _dup#. ie. pCube1 from pCube1_INST1
				# duplicateObjList.append(originalObj)
				# pm.polyUnite (duplicateObjList, name=originalObj+"_array") #combine objects. using the original name results in a duplicate object error on deletion
				print('Result: '+str(duplicateObjList))
				# pm.delete(duplicateObjList) #delete all duplicated geometry
				del duplicateObjList[:] #clear the list
				return
			pm.delete(duplicateObjList[1:]) #delete all the geometry in the list, except the original obj
			pm.select(duplicateObjList[:1]) #re-select the original object
			del duplicateObjList[:] #clear the list
			self.toggleWidgets(self.duplicate_linear_ui, setDisabled='b002')


	def tb000(self, state=None):
		'''Convert to Instances
		'''
		tb = self.sb.duplicate.tb000

		transformByVertexOrder = tb.contextMenu.chk001.isChecked()

		selection = pm.ls(sl=1, transforms=1)
		if not selection:
			self.messageBox('<strong>Nothing selected</strong>.<br>Operation requires an object selection.')
			return

		if not pm.selectPref(q=1, trackSelectionOrder=1): #if ordered selection is not on, turn it on. If off, the current selection is likely not ordered.
			pm.selectPref(trackSelectionOrder=1)
		self.convertToInstances(selection, transformByVertexOrder=transformByVertexOrder)


	def b000(self):
		'''Create Instances
		'''
		selection = pm.ls(sl=1, transforms=1)
		if not selection:
			self.messageBox('<strong>Nothing selected</strong>.<br>Operation requires an object selection.')
			return

		instances = [pm.instance(obj, name=obj.name()+'_INST') 
							for obj in selection]

		pm.select(instances)


	def b004(self):
		'''Select Instanced Objects
		'''
		selection = pm.ls(sl=1)

		if not selection: #select all instanced objects in the scene.
			instances = self.getInstances()
			pm.select(instances)
		else: #select instances of the selected objects.
			instance = self.getInstances(selection)
			pm.select(instances)


	def b005(self):
		'''Uninstance Selected Objects
		'''
		selection = pm.ls(sl=1)

		self.unInstance(selection)



	def getInstances(self, objects=None, returnParentObjects=False):
		'''get any intances of given object, or if None given; get all instanced objects in the scene.

		:Parameters:
			objects (str)(obj)(list) = Parent object/s.
			returnParentObjects (bool) = Return instances and the given parent objects together.

		:Return:
			(list)
		'''
		instances=[]

		if objects is None: #get all instanced objects in the scene.
			import maya.OpenMaya as om

			iterDag = om.MItDag(om.MItDag.kBreadthFirst)
			while not iterDag.isDone():
				instanced = om.MItDag.isInstanced(iterDag)
				if instanced:
					instances.append(iterDag.fullPathName())
				iterDag.next()
		else:
			shapes = pm.listRelatives(objects, s=1)
			instances = pm.listRelatives(shapes, ap=1)
			if not returnParentObjects:
				[instances.remove(obj) for obj in objects]

		return instances


	@Slots_maya.undo
	def convertToInstances(self, objects=[], transformByVertexOrder=False, append=''):
		'''The first selected object will be instanced across all other selected objects.

		:Parameters:
			objects (list) = A list of objects to convert to instances. The first object will be the instance parent.
			append (str) = Append a string to the end of any instanced objects. ie. '_INST'
			transformByVertexOrder (bool) = Transform the instanced object by matching the transforms of the vertices between the two objects.

		:Return:
			(list) The instanced objects.

		ex. call: convertToInstances(pm.ls(sl=1))
		'''
		# pm.undoInfo(openChunk=1)
		p0x, p0y, p0z = pm.xform(objects[0], query=1, rotatePivot=1, worldSpace=1) #get the world space obj pivot.
		pivot = pm.xform(objects[0], query=1, rotatePivot=1, objectSpace=1) #get the obj pivot.

		for obj in objects[1:]:

			name = obj.name()
			objParent = pm.listRelatives(obj, parent=1)

			instance = pm.instance(objects[0])

			self.unInstance(obj)
			pm.makeIdentity(obj, apply=1, translate=1, rotate=0, scale=0)
			
			if transformByVertexOrder:
				self.sb.transform.slots.matchTransformByVertexOrder(instance, obj)
				if not self.sb.transform.slots.isOverlapping(instance, obj):
					print ('# {}: Unable to match {} transforms. #'.format(instance, obj))
			else:
				pm.matchTransform(instance, obj, position=1, rotation=1, scale=1, pivots=1) #move object to center of the last selected items bounding box # pm.xform(instance, translation=pos, worldSpace=1, relative=1) #move to the original objects location.

			try:
				pm.parent(instance, objParent) #parent the instance under the original objects parent.
			except RuntimeError as error: #It is already a child of the parent.
				pass
	
			pm.delete(obj, constructionHistory=True) #delete history for the object so that the namespace is cleared.
			pm.delete(obj)
			pm.rename(instance, name+append)
		pm.select(objects[1:])
		return objects[1:]
		# pm.undoInfo(closeChunk=1)


	def unInstance(self, objects):
		'''Un-Instance the given objects.

		:Parameters:
			objects (str)(obj)(list) = The objects to un-instance. If 'all' is given all instanced objects in the scene will be uninstanced.
		'''
		if objects=='all':
			objects = self.getInstances()

		for obj in pm.ls(objects):

			children = pm.listRelatives(obj, fullPath=1, children=1)
			parents = pm.listRelatives(children[0], fullPath=1, allParents=1)

			if len(parents)>1:
				duplicatedObject = pm.duplicate(obj)
				pm.delete(obj)
				pm.rename(duplicatedObject[0], obj)









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------
	# b008, b009, b011


#deprecated:

	# @Slots_maya.undo
	# def convertToInstances(self, objects=[], leaf=False, append=''):
	# 	'''The first selected object will be instanced across all other selected objects.

	# 	:Parameters:
	# 		objects (list) = A list of objects to convert to instances. The first object will be the instance parent.
	# 		leaf (bool) = Instances leaf-level objects. Acts like duplicate except leaf-level objects are instanced.
	# 		append (str) = Append a string to the end of any instanced objects. ie. '_INST'
	# 		transformByVertexOrder (bool) = Transform the instanced object by matching the transforms of the vertices between the two objects.

	# 	:Return:
	# 		(list) The instanced objects.

	# 	ex. call: convertToInstances(pm.ls(sl=1))
	# 	'''
	# 	# pm.undoInfo(openChunk=1)
	# 	p0x, p0y, p0z = pm.xform(objects[0], query=1, rotatePivot=1, worldSpace=1) #get the world space obj pivot.
	# 	pivot = pm.xform(objects[0], query=1, rotatePivot=1, objectSpace=1) #get the obj pivot.

	# 	for obj in objects[1:]:

	# 		name = obj.name()
	# 		objParent = pm.listRelatives(obj, parent=1)

	# 		instance = pm.instance(objects[0], leaf=leaf)

	# 		# if transformByVertexOrder:
	# 		# 	self.sb.transform.slots.matchTransformByVertexOrder(instance, obj)
	# 		# 	if not self.sb.transform.slots.isOverlapping(instance, obj):
	# 		# 		print ('# {}: Unable to match {} transforms. #'.format(instance, obj))
	# 		# else:
	# 		self.sb.transform.slots.moveTo(instance, obj) #source, target
	# 		pm.matchTransform(instance, obj, position=0, rotation=1, scale=0, pivots=0) #move object to center of the last selected items bounding box # pm.xform(instance, translation=pos, worldSpace=1, relative=1) #move to the original objects location.

	# 		try:
	# 			pm.parent(instance, objParent) #parent the instance under the original objects parent.
	# 		except RuntimeError as error: #It is already a child of the parent.
	# 			pass
	
	# 		pm.delete(obj, constructionHistory=True) #delete history for the object so that the namespace is cleared.
	# 		pm.delete(obj)
	# 		pm.rename(instance, name+append)
	# 	pm.select(objects[1:])
	# 	return objects[1:]
	# 	# pm.undoInfo(closeChunk=1)