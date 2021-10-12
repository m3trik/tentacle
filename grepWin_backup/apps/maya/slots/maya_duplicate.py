# !/usr/bin/python
# coding=utf-8
# from __future__ import print_function, absolute_import
from builtins import super
import os.path

from maya_init import *



class Duplicate(Init):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)

		self.duplicate_ui.s000.valueChanged.connect(self.radialArray) #update radial array
		self.duplicate_ui.s001.valueChanged.connect(self.radialArray) 

		self.duplicate_ui.s002.valueChanged.connect(self.duplicateArray) #update duplicate array
		self.duplicate_ui.s003.valueChanged.connect(self.duplicateArray)
		self.duplicate_ui.s004.valueChanged.connect(self.duplicateArray)
		self.duplicate_ui.s005.valueChanged.connect(self.duplicateArray)
		self.duplicate_ui.s007.valueChanged.connect(self.duplicateArray) 
		self.duplicate_ui.s008.valueChanged.connect(self.duplicateArray)
		self.duplicate_ui.s009.valueChanged.connect(self.duplicateArray)


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.duplicate_ui.draggable_header

		if state is 'setMenu':
			dh.contextMenu.add(wgts.ComboBox, setObjectName='cmb000', setToolTip='')

			return


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.duplicate_ui.cmb000

		if index is 'setMenu':
			list_ = ['Duplicate Special']
			cmb.addItems_(list_, '')
			return

		if index>0:
			if index==cmd.items.index('Duplicate Special'):
				mel.eval('DuplicateSpecialOptions;')
			cmb.setCurrentIndex(0)
	

	def radialArray(self):
		'''Radial Array: Reset
		'''
		self.chk015() #calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg


	def duplicateArray(self):
		'''Duplicate: Reset
		'''
		self.chk016() #calling chk015 directly from valueChanged would pass the returned spinbox value to the create arg


	def chk007(self, state=None):
		'''Duplicate: Translate To Components
		'''
		if self.duplicate_ui.chk007.isChecked():
			self.toggleWidgets(setEnabled='chk008,b034,cmb000', setDisabled='chk000,chk009,s005')
			self.b008()
		else:
			self.toggleWidgets(setDisabled='chk008,b034,cmb000', setEnabled='chk000,chk009,s005')


	@Slots.message
	def chk010(self, state=None):
		'''Radial Array: Set Pivot
		'''
		global radialPivot
		radialPivot=[]
		#add support for averaging multiple components.
		if self.duplicate_ui.chk010.isChecked():
			selection = pm.ls (selection=1, flatten=1)
			if selection:
				vertices = pm.filterExpand(selectionMask=31) #get selected vertices
				if vertices is not None and vertices==1: #if a single vertex is selected, query that vertex position.
					pivot = pm.xform (selection, query=1, translation=1, worldSpace=1)
				else: #else, get the center of the objects bounding box.
					bb = pm.xform (selection, query=1, boundingBox=1, worldSpace=1)
					pivot = bb[0]+bb[3]/2, bb[1]+bb[4]/2, bb[2]+bb[5]/2 #get median of bounding box coordinates. from [min xyz, max xyz]
			else:
				self.toggleWidgets(setUnChecked='chk010')
				return 'Error: Nothing selected.'

			# radialPivot.extend ([pivot[0],pivot[1],pivot[2]])
			radialPivot.extend(pivot) #extend the list contents
			text = str(int(pivot[0]))+","+str(int(pivot[1]))+","+str(int(pivot[2]))
			self.duplicate_ui.chk010.setText(text)
		else:
			del radialPivot[:]
			self.duplicate_ui.chk010.setText("Set Pivot")


	def chk012(self, state=None):
		'''Radial Array: X Axis
		'''
		self.toggleWidgets(setChecked='chk012', setUnChecked='chk013,chk014')
		self.chk015()


	def chk013(self, state=None):
		'''Radial Array: Y Axis
		'''
		self.toggleWidgets(setChecked='chk013', setUnChecked='chk012,chk014')
		self.chk015()


	def chk014(self, state=None):
		'''Radial Array: Z Axis
		'''
		self.toggleWidgets(setChecked='chk014', setUnChecked='chk012,chk013')
		self.chk015()


	global radialArrayObjList
	radialArrayObjList=[]
	@Slots.message
	@Init.undoChunk
	def chk015(self, create=False):
		'''Radial Array: Preview
		'''
		setPivot = self.duplicate_ui.chk010.isChecked() #set pivot point
		instance = self.duplicate_ui.chk011.isChecked() #instance object

		if self.duplicate_ui.chk015.isChecked():
			self.toggleWidgets(setEnabled='b003')

			selection = pm.ls (selection=1, type="transform", flatten=1)
			if selection:
				if radialArrayObjList:
					try:
						pm.delete(radialArrayObjList) #delete all the geometry in the list
					except:
						pass
					del radialArrayObjList[:] #clear the list

				for object_ in selection:
					pm.select (object_)
					objectName = str(object_)

					numDuplicates = int(self.duplicate_ui.s000.value())
					angle = float(self.duplicate_ui.s001.value())

					x=y=z = 0
					if self.duplicate_ui.chk012.isChecked(): x = angle
					if self.duplicate_ui.chk013.isChecked(): y = angle
					if self.duplicate_ui.chk014.isChecked(): z = angle

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
								print('Error: No pivot point set.')
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
				self.toggleWidgets(setDisabled='b003', setUnChecked='chk015')
				return 'Error: Nothing selected.'
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

			self.toggleWidgets(setDisabled='b003')


	global duplicateObjList
	duplicateObjList=[]
	@Slots.message
	@Init.undoChunk
	def chk016(self, create=False):
		'''Duplicate: Preview
		'''
		if self.duplicate_ui.chk016.isChecked():
			self.toggleWidgets(setEnabled='b002')

			instance = self.duplicate_ui.chk000.isChecked()
			numOfDuplicates = int(self.duplicate_ui.s005.value())
			keepFacesTogether = self.duplicate_ui.chk009.isChecked()
			transXYZ = [float(self.duplicate_ui.s002.value()),float(self.duplicate_ui.s003.value()),float(self.duplicate_ui.s004.value())]
			rotXYZ =  [float(self.duplicate_ui.s007.value()),float(self.duplicate_ui.s008.value()),float(self.duplicate_ui.s009.value())]
			translateToComponent = self.duplicate_ui.chk007.isChecked()
			alignToNormal = self.duplicate_ui.chk008.isChecked()
			componentList = [self.duplicate_ui.cmb000.itemText(i) for i in range(self.duplicate_ui.cmb000.count())]

			try:
				pm.delete(duplicateObjList[1:]) #delete all the geometry in the list, except the original obj
			except e as error:
				print(e)

			del duplicateObjList[1:] #clear the list, leaving the original obj
			selection = pm.ls(selection=1, flatten=1, objectsOnly=1) #there will only be a selection when first called. After, the last selected item will have been deleted with the other duplicated objects, leaving only the original un-selected.

			if selection:
				obj = selection[0]
				duplicateObjList.insert(0, obj) #insert at first index
			elif duplicateObjList:
				obj = duplicateObjList[0]
				pm.select(obj)
			else:
				return 'Error: Nothing selected.'

			# pm.undoInfo (openChunk=1)
			if translateToComponent:
				if componentList:
					for num, component in componentList.iteritems():
						vertexPoint = self.getComponentPoint(component)

						pm.xform (obj, rotation=[rotXYZ[0], rotXYZ[1], rotXYZ[2]])
						pm.xform (obj, translation=[vertexPoint[0]+transXYZ[0], vertexPoint[1]+transXYZ[1], vertexPoint[2]+transXYZ[2]])

						if component != componentList[len(componentList)-1]: #if not at the end of the list, create a new instance of the obj.
							name = str(obj)+"_inst"+str(num)
							duplicatedObject = pm.instance (obj, name=name)
						# print("component:",component,"\n", "normal:",normal,"\n", "vertexPoint:",vertexPoint,"\n")

						duplicateObjList.append(duplicatedObject) #append duplicated object to list
				else:
					return 'Error: Component list empty.'
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

					duplicateObjList.append(duplicatedObject) #append duplicated object to list
					pm.select(duplicatedObject)
			# pm.undoInfo (closeChunk=1)

		else: #if chk016 is unchecked by user or by create button
			if create:
				# originalObj = duplicateObjList[0][:duplicateObjList[0].rfind("_")] #remove the trailing _ins# or _dup#. ie. pCube1 from pCube1_inst1
				# duplicateObjList.append(originalObj)
				# pm.polyUnite (duplicateObjList, name=originalObj+"_array") #combine objects. using the original name results in a duplicate object error on deletion
				print('Result: '+str(duplicateObjList))
				# pm.delete(duplicateObjList) #delete all duplicated geometry
				del duplicateObjList[:] #clear the list
				return
			pm.delete(duplicateObjList[1:]) #delete all the geometry in the list, except the original obj
			pm.select(duplicateObjList[:1]) #re-select the original object
			del duplicateObjList[:] #clear the list
			self.toggleWidgets(setDisabled='b002')


	def b001(self):
		''''''
		pass


	def b002(self):
		'''Duplicate: Create
		'''
		self.duplicate_ui.chk016.setChecked(False) #must be in the false unchecked state to catch the create flag in chk015
		self.chk016(create=True)


	def b003(self):
		'''Radial Array: Create
		'''
		self.duplicate_ui.chk015.setChecked(False) #must be in the false unchecked state to catch the create flag in chk015
		self.chk015(create=True)


	@staticmethod
	def getInstances(object_=None):
		'''get any intances of given object, or if no object given, get all instanced objects in the scene.
		:Parameters:
			object=<scene object>
		:Return:
			any instances.
		'''
		instances=[]

		if not object_: #get all instanced objects in the scene.
			import maya.OpenMaya as om

			iterDag = om.MItDag(om.MItDag.kBreadthFirst)
			while not iterDag.isDone():
				instanced = om.MItDag.isInstanced(iterDag)
				if instanced:
					instances.append(iterDag.fullPathName())
				iterDag.next()
		else:
			pm.select (object_, deselect=1)
			shapes = pm.listRelatives(object_, s=1)
			instances = listRelatives('+shapes[0]+', ap=1)

		return instances


	def b004(self):
		'''Select Instanced Objects
		'''
		selection = pm.ls(sl=1)

		if not selection: #select all instanced objects in the scene.
			instances = self.getInstances()
			pm.select(instances)
		else: #select instances of the selected objects.
			pm.select(deselect=1, all=1)
			for obj in selection:
				instance = self.getInstances(obj)
				pm.select(instance, add=1)


	def b005(self):
		'''Uninstance Selected Objects
		'''
		selection = pm.ls(sl=1)
		#uninstance:
		while len(selection):
			instances = self.getInstances()
			parent = pm.listRelatives(instances[0], parent=True)[0]
			pm.duplicate(parent, renameChildren=True)
			pm.delete(parent)


	def b008(self):
		'''Add Selected Components To cmb000
		'''
		self.comboBox (self.duplicate_ui.cmb000, pm.ls (selection=1, flatten=1))








#module name
print(os.path.splitext(os.path.basename(__file__))[0])
# -----------------------------------------------
# Notes
# -----------------------------------------------
	# b008, b009, b011
