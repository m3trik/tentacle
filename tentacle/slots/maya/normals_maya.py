# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.normals import Normals



class Normals_maya(Normals, Slots_maya):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Normals.__init__(self, *args, **kwargs)

		cmb = self.normals_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.normals_ui.draggable_header.contextMenu.cmb000

		if index>0:
			if index==cmd.items.index(''):
				pass
			cmb.setCurrentIndex(0)


	def tb000(self, state=None):
		'''Display Face Normals
		'''
		tb = self.normals_ui.tb000

		size = float(tb.contextMenu.s001.value())
		# state = pm.polyOptions (query=True, displayNormal=True)
		state = self.cycle([1,2,3,0], 'displayNormals')
		if state ==0: #off
			pm.polyOptions (displayNormal=0, sizeNormal=0)
			pm.polyOptions (displayTangent=False)
			self.viewPortMessage("Normals Display <hl>Off</hl>.")

		if state ==1: #facet
			pm.polyOptions (displayNormal=1, facet=True, sizeNormal=size)
			pm.polyOptions (displayTangent=False)
			self.viewPortMessage("<hl>Facet</hl> Normals Display <hl>On</hl>.")

		if state ==2: #Vertex
			pm.polyOptions (displayNormal=1, point=True, sizeNormal=size)
			pm.polyOptions (displayTangent=False)
			self.viewPortMessage("<hl>Vertex</hl> Normals Display <hl>On</hl>.")

		if state ==3: #tangent
			pm.polyOptions (displayTangent=True)
			pm.polyOptions (displayNormal=0)
			self.viewPortMessage("<hl>Tangent</hl> Display <hl>On</hl>.")


	def tb001(self, state=None):
		'''Harden Edge Normals
		'''
		tb = self.normals_ui.tb001

		hardAngle = tb.contextMenu.s002.value()
		hardenCreased = tb.contextMenu.chk005.isChecked()
		hardenUvBorders = tb.contextMenu.chk006.isChecked()
		softenOther = tb.contextMenu.chk004.isChecked()
		softEdgeDisplay = tb.contextMenu.chk007.isChecked()

		objects = pm.ls(sl=True, objectsOnly=True)

		for obj in objects:
			selection = pm.ls(obj, sl=True, l=True)
			if not selection:
				continue
			selEdges = pm.ls(pm.polyListComponentConversion(selection, toEdge=1), flatten=1)
			allEdges = edges = pm.ls(pm.polyListComponentConversion(obj, toEdge=1), flatten=1)

			if hardenCreased:
				creasedEdges = self.crease().getCreasedEdges(allEdges)
				selEdges = selEdges + creasedEdges if not selEdges==allEdges else creasedEdges

			if hardenUvBorders:
				uv_border_edges = self.uv().getUvShellBorderEdges(selection)
				selEdges = selEdges + uv_border_edges if not selEdges==allEdges else uv_border_edges

			pm.polySoftEdge(selEdges, angle=hardAngle, constructionHistory=0) #set hard edges.

			if softenOther:
				invEdges = [e for e in allEdges if e not in selEdges]
				if invEdges:
					pm.polySoftEdge(invEdges, angle=180, constructionHistory=0) #set soft edges.

			if softEdgeDisplay:
				pm.polyOptions(obj, se=1)

			pm.select(selEdges, add=True)


	@Slots_maya.attr
	def tb002(self, state=None):
		'''Set Normals By Angle
		'''
		tb = self.normals_ui.tb002

		normalAngle = str(tb.contextMenu.s000.value())

		objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
		for obj in objects:
			sel = pm.ls(obj, sl=1)
			pm.polySetToFaceNormal(sel, setUserNormal=1) #reset to face
			polySoftEdge = pm.polySoftEdge(sel, angle=normalAngle) #smooth if angle is lower than specified amount. default:60
			if len(objects)==1:
				return polySoftEdge


	def tb003(self, state=None):
		'''Lock/Unlock Vertex Normals
		'''
		tb = self.normals_ui.tb003

		all_ = tb.contextMenu.chk001.isChecked()
		state = tb.contextMenu.chk002.isChecked() #pm.polyNormalPerVertex(vertex, query=1, freezeNormal=1)
		selection = pm.ls (selection=1, objectsOnly=1)
		maskObject = pm.selectMode (query=1, object=1)
		maskVertex = pm.selectType (query=1, vertex=1)

		if not selection:
			self.messageBox('Operation requires at least one selected object.')
			return

		if (all_ and maskVertex) or maskObject:
			for obj in selection:
				vertices = Slots_maya.getComponents(obj, 'vertices', flatten=1)
				for vertex in vertices:
					if not state:
						pm.polyNormalPerVertex(vertex, unFreezeNormal=1)
					else:
						pm.polyNormalPerVertex(vertex, freezeNormal=1)
				if not state:
					self.viewPortMessage("Normals <hl>UnLocked</hl>.")
				else:
					self.viewPortMessage("Normals <hl>Locked</hl>.")
		elif maskVertex and not maskObject:
			if not state:
				pm.polyNormalPerVertex(unFreezeNormal=1)
				self.viewPortMessage("Normals <hl>UnLocked</hl>.")
			else:
				pm.polyNormalPerVertex(freezeNormal=1)
				self.viewPortMessage("Normals <hl>Locked</hl>.")
		else:
			self.messageBox('Selection must be object or vertex.', messageType='Warning')
			return


	def tb004(self, state=None):
		'''Average Normals
		'''
		tb = self.normals_ui.tb004

		byUvShell = tb.contextMenu.chk003.isChecked()

		objects = pm.ls(selection=1, objectsOnly=1, flatten=1)
		self.averageNormals(objects, byUvShell=byUvShell)


	def b001(self):
		'''Soften Edge Normals
		'''
		pm.polySoftEdge(angle=180, constructionHistory=0)


	def b002(self):
		'''Transfer Normals
		'''
		source, *target = pm.ls(sl=1)
		self.transferNormals(source, target)


	def b003(self):
		'''Soft Edge Display
		'''
		g_cond = pm.polyOptions(q=1, ae=1)
		if g_cond[0]:
			pm.polyOptions(se=1)
		else:
			pm.polyOptions(ae=1)


	def b005(self):
		'''Maya Bonus Tools: Adjust Vertex Normals
		'''
		pm.mel.bgAdjustVertexNormalsWin()


	def b006(self):
		'''Set To Face
		'''
		pm.polySetToFaceNormal()


	def b010(self):
		'''Reverse Normals
		'''
		for obj in pm.ls(sl=1, objectsOnly=1):
			sel = pm.ls(obj, sl=1)
			pm.polyNormal(sel, normalMode=3, userNormalMode=1) #3: reverse and cut a new shell on selected face(s). 4: reverse and propagate; Reverse the normal(s) and propagate this direction to all other faces in the shell.


	@Slots_maya.undo
	def averageNormals(self, objects, byUvShell=False):
		'''Average Normals

		:Parameters:
			byUvShell (bool) = Average each UV shell individually.
		'''
		# pm.undoInfo(openChunk=1)
		for obj in objects:

			if byUvShell:
				obj = pm.ls(obj, transforms=1)
				sets_ = self.uv().getUvShellSets(obj)
				for set_ in sets_:
					pm.polySetToFaceNormal(set_)
					pm.polyAverageNormal(set_)
			else:
				sel = pm.ls(obj, sl=1)
				if not sel:
					sel = obj
				pm.polySetToFaceNormal(sel)
				pm.polyAverageNormal(sel)
		# pm.undoInfo(closeChunk=1)


	def getNormalVector(self, name=None):
		'''Get the normal vectors from the given poly object.
		If no argument is given the normals for the current selection will be returned.
		:Parameters:
			name (str) = polygon mesh or component.
		:Return:
			dict - {int:[float, float, float]} face id & vector xyz.
		'''
		type_ = pm.objectType(name)

		if type_=='mesh': #get face normals
			normals = pm.polyInfo(name, faceNormals=1)

		elif type_=='transform': #get all normals for the given obj
			numFaces = pm.polyEvaluate(name, face=1) #returns number of faces as an integer
			normals=[]
			for n in range(0, numFaces): #for (number of faces):
				array = pm.polyInfo('{0}[{1}]'.format(name, n) , faceNormals=1) #get normal info from the rest of the object's faces
				string = ' '.join(array)
				n.append(str(string))

		else: #get face normals from the user component selection.
			normals = pm.polyInfo(faceNormals=1) #returns the face normals of selected faces

		regEx = "[A-Z]*_[A-Z]* *[0-9]*: "

		dict_={}
		for n in normals:
			l = list(s.replace(regEx,'') for s in n.split() if s) #['FACE_NORMAL', '150:', '0.935741', '0.110496', '0.334931\n']

			key = int(l[1].strip(':')) #int face number as key ie. 150
			value = list(float(i) for i in l[-3:])  #vector list as value. ie. [[0.935741, 0.110496, 0.334931]]
			dict_[key] = value

		return dict_


	def getFacesWithSimilarNormals(self, faces, transforms=[], similarFaces=[], rangeX=0.1, rangeY=0.1, rangeZ=0.1, returnType='str', returnNodeType='transform'):
		'''Filter for faces with normals that fall within an X,Y,Z tolerance.

		:Parameters:
			faces (list) = ['polygon faces'] - faces to find similar normals for.
			similarFaces (list) = optional ability to add faces from previous calls to the return value.
			transforms (list) = [<shape nodes>] - objects to check faces on. If none are given the objects containing the given faces will be used.
			rangeX = float - x axis tolerance
			rangeY = float - y axis tolerance
			rangeZ = float - z axis tolerance
			returnType (str) = The desired returned object type. (valid: 'unicode'(default), 'str', 'int', 'object')
			returnNodeType (str) = Specify whether the components are returned with the transform or shape nodes (valid only with str and unicode returnTypes). (valid: 'transform', 'shape'(default)) ex. 'pCylinder1.f[0]' or 'pCylinderShape1.f[0]'

		:Return:
			(list) faces that fall within the given normal range.

		ex. getFacesWithSimilarNormals(selectedFaces, rangeX=0.5, rangeY=0.5, rangeZ=0.5)
		'''
		faces = pm.ls(faces, flatten=1) #work on a copy of the argument so that removal of elements doesn't effect the passed in list.
		for face in faces:
			normals = self.getNormalVector(face)

			for k, v in normals.items():
				sX = v[0]
				sY = v[1]
				sZ = v[2]

				if not transforms:
					transforms = Slots_maya.getObjectFromComponent(face)

				for node in transforms:
					for f in Slots_maya.getComponents(node, 'faces', returnType=returnType, returnNodeType=returnNodeType, flatten=1):

						n = self.getNormalVector(f)
						for k, v in n.items():
							nX = v[0]
							nY = v[1]
							nZ = v[2]

							if sX<=nX + rangeX and sX>=nX - rangeX and sY<=nY + rangeY and sY>=nY - rangeY and sZ<=nZ + rangeZ and sZ>=nZ - rangeZ:
								similarFaces.append(f)
								if f in faces: #If the face is in the loop que, remove it, as has already been evaluated.
									faces.remove(f)

		return similarFaces


	@Slots_maya.undo
	def transferNormals(self, source, target):
		'''Transfer normal information from one object to another.

		:parameters:
			source (str)(obj)(list) = The transform node to copy normals from.
			target (str)(obj)(list) = The transform node(s) to copy normals to.
		'''
		# pm.undoInfo(openChunk=1)
		s, *other = pm.ls(source)
		#store source transforms
		sourcePos = pm.xform(s, q=1, t=1, ws=1)
		sourceRot = pm.xform(s, q=1, ro=1, ws=1)
		sourceScale = pm.xform(s, q=1, s=1, ws=1)

		for t in pm.ls(target):
			#store target transforms
			targetPos = pm.xform(t, q=1, t=1, ws=1)
			targetRot = pm.xform(t, q=1, ro=1, ws=1)
			targetScale = pm.xform(t, q=1, s=1, ws=1)

			#move target to source position
			pm.xform(t, t=sourcePos, ws=1)
			pm.xform(t, ro=sourceRot, ws=1)
			pm.xform(t, s=sourceScale, ws=1)

			#copy normals
			pm.polyNormalPerVertex(t, ufn=0)
			pm.transferAttributes(s, t, pos=0, nml=1, uvs=0, col=0, spa=0, sm=3, clb=1)
			pm.delete(t, ch=1)

			#restore t position
			pm.xform(t, t=targetPos, ws=1)
			pm.xform(t, ro=targetRot, ws=1)
			pm.xform(t, s=targetScale, ws=1)
		# pm.undoInfo(closeChunk=1)



		



#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------
