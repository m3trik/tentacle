# !/usr/bin/python
# coding=utf-8
import os

try:
	import pymel.core as pm
	import maya.OpenMaya as om
	import maya.OpenMayaFX as omfx

	import MASH.api as mapi

except ImportError as error:
	print (__file__, error)


def MTcreateNetwork(network, objects, networkName='MASH#', geometry='Mesh', distType='linearNetwork', hideOnCreate=True):
	'''This proceedure creates a new MASH network.

	:Parameters:
		network (obj) = A mash api network instance. ie. mapi.Network()
		objects (str)(obj)(list) = The maya objects to construct the network for.
		networkName (str) = The network name. (default:'MASH#')
		geometry (str) = Particle instancer or mesh instancer (Repro node). (valid: 'Mesh' (default), 'Instancer')
		distType (str) = Distribution type. (valid: "linearNetwork", radialNetwork", "gridNetwork", "initialNetwork", "zeroNetwork")
		hideOnCreate (bool) = Hide the original object(s) on network creation.

	:Return:
		The names of the created Waiter, Instancer and Distribute Node.

	ex. mashNW = mapi.Network() #network instance
		mashNW.MTcreateNetwork(objects, geometry='Instancer', hideOnCreate=False) #create a MASH network
	'''
	loaded = int(pm.pluginInfo('MASH', query=1, l=1))
	if not loaded:
		pm.loadPlugin('MASH')

	waiter=distNode=instancer = ''

	if geometry=='Mesh':
		objects_ = pm.ls(obj, lf=1, ni=1, dag=1, type="mesh", l=1) #filter for valid mesh objects.
	else:
		objects_ = pm.ls(objects)

	if len(objects_) is 0:
		return pm.mel.MASHinViewMessage((pm.mel.getPluginResource("MASH", "kMASHMeshesOnly")), "Error") #error and bail if there was nothing usable selected

	if hideOnCreate:
		[pm.hide(obj) for obj in objects_] #hide the original objects

	waiter = pm.ls(pm.createNode('MASH_Waiter', n=networkName))[0] #create the waiter
	pm.addAttr(waiter, hidden=True, at='message', longName='instancerMessage')

	distNodeName = '{}_Distribute'.format(waiter.name())
	distNode = pm.ls(pm.createNode('MASH_Distribute', n=distNodeName))[0] #create a Distribute node

	pm.setAttr(distNode.mapDirection, 4) #for convenience we match the Map Direction to the initial linear distribution

	#connect the Distribute node to the Waiter
	pm.connectAttr(distNode.outputPoints, waiter.inputPoints, force=1)
	pm.connectAttr(distNode.waiterMessage, waiter.waiterMessage, f=1)

	if geometry=='Mesh': #create the repro node
		import mash_repro_utils; reload(mash_repro_utils)
		reproName = '{}_Repro'.format(waiter.name())		
		instancer = pm.ls(mash_repro_utils.create_mash_repro_node(None, reproName))[0]
	else: # create the instancer
		instancerName = '{}_Instancer'.format(waiter.name())
		instancer = pm.ls(pm.createNode('instancer', name=instancerName))[0]

	pm.connectAttr(waiter.outputPoints, instancer.inputPoints, force=1) #connect the Waiter to the Instancer or Repro node
	pm.addAttr(instancer, hidden=True, at='message', longName='instancerMessage') # add a message attribute to the instancer
	pm.connectAttr(waiter.instancerMessage, instancer.instancerMessage, f=1) #connect message attributes to the instancer so we can find it later if needed

	#if the user added more then one object to the network, set the number of points to reflect that
	size = len(objects_)
	if len(objects_)>1:
		pm.setAttr(distNode.pointCount, size)

	# add the objects to the instancer or Repro
	for transform in pm.ls(objects_, transforms=1):
		if geometry=='Mesh':
			import mash_repro_utils
			mash_repro_utils.connect_mesh_group(instancer.name(), transform.name(), new_connection=True) # connect the meshes to the Repro node
		else:
			import maya.mel as mel
			pm.mel.eval('instancer -e -a -obj {} {};'.format(transform, instancer.name())) #pm.instancer(instancerName, e=1, addObject=1, obj=transform)

	#set the Distribute node defaults
	if distType=="radialNetwork":
		pm.setAttr(distNode.arrangement, 2)
	elif distType=="gridNetwork":
		pm.setAttr(distNode.arrangement, 6)
	elif distType=="initialNetwork":
		pm.setAttr(distNode.arrangement, 7)
	elif distType=="zeroNetwork":
		pm.setAttr(distNode.amplitudeX, 0.0)

	#update the Repro interface
	if geometry=='Mesh':
		import mash_repro_aetemplate
		mash_repro_aetemplate.refresh_all_aetemplates(force=True)

	coreNodes = {'waiter':waiter, 'instancer':instancer, 'distribute':distNode}
	#add created nodes to the network.
	for k,v in coreNodes.items():
		if not hasattr(network, k):
			setattr(network, k, v)


	return coreNodes.values()


def MTbakeInstancer(network, instancer, bakeTranslate=True, bakeRotation=True, bakeScale=True, 
	bakeAnimation=False, bakeVisibility=True, bakeToIntances=False, upstreamNodes=False, _getMObjectFromName=None):
	'''Takes an instancer, and coverts all the particles being fed into it to actual geometry.

	:Parameters:
		network (obj) = A mash api network instance. ie. mapi.Network()
		instancer (str)(obj) = Instancer node or name of an instancer node.
		bakeAnimation (bool) = True=bake entire playback range, False=bake current frame.
		bakeTranslate (bool) = Bake translation.
		bakeRotation (bool) = Bake rotation.
		bakeScale (bool) = Bake scale.
		bakeVisibility (bool) = Bake visibility.
		bakeToInstances (bool) = Bake to instances rather than separate objects.
		upstreamNodes (bool) = The upstream nodes leading upto the selected nodes (along with their connections) are also duplicated.
		_getMObjectFromName (str) = Node name. Returns a maya.OpenMaya.MObject from the given instancer node name. Internal use only.

	:Return:
		(list) Baked objects.
	'''
	if _getMObjectFromName:
		sel = om.MSelectionList()
		sel.add(_getMObjectFromName)
		thisNode = om.MObject()
		sel.getDependNode(0, thisNode)
		return thisNode

	_instancer = pm.ls(instancer, type='instancer')[0]
	if not _instancer: #check that the nodeType is 'instancer'.
		raise Exception('"{}" is type: "{}". The required node type is "instancer".'.format(instancer, pm.nodeType(instancer)))

	#reused vars for the particles
	m = om.MMatrix()
	dp = om.MDagPath()
	dpa = om.MDagPathArray()
	sa = om.MScriptUtil()
	sa.createFromList([0.0, 0.0, 0.0], 3)
	sp = sa.asDoublePtr()

	#Get the instancer function set
	thisNode = MTbakeInstancer(network, _instancer, _getMObjectFromName=_instancer.name())
	fnThisNode = om.MFnDependencyNode(thisNode)

	#start frame, end frame, animaiton
	sf = int(pm.playbackOptions(q=True, min=True))-1
	ef = int(pm.playbackOptions(q=True, max=True))+2

	if bakeAnimation==False:
		sf = pm.currentTime(query=True)
		ef = sf+1

	result=[]
	for i in range(int(sf), int(ef)):
		#set the time
		pm.currentTime(i)
		g = '{}_objects'.format(_instancer.name())
		
		#get the visibility array - which isn't provided by the MFnInstancer function set
		inPointsAttribute = fnThisNode.attribute("inputPoints")
		inPointsPlug = om.MPlug( thisNode, inPointsAttribute )
		inPointsObj = inPointsPlug.asMObject()
		inputPPData = om.MFnArrayAttrsData(inPointsObj)
		visList = inputPPData.getDoubleData("visibility")[:]

		#if this is the first frame, create a transform to store everything under
		if i==sf:
			if pm.objExists(g)==True:
				pm.delete(g)
			g = pm.createNode("transform", n=g)

		#get the instancer
		sl = om.MSelectionList()
		sl.add(_instancer)
		sl.getDagPath(0, dp)
		#create mfninstancer function set
		fni = omfx.MFnInstancer(dp)

		#cycle through the particles
		for j in range(fni.particleCount()):
			visibility = visList[j]
			#get the instancer object
			fni.instancesForParticle(j, dpa, m)
			for i in range(dpa.length()):
				fullPathName = dpa[i].partialPathName() #get the instancer object name
				#support namespaces, refrences, crap names
				nameSpaceRemoved = fullPathName.rsplit(':', 1)[-1]
				pipesRemoved = nameSpaceRemoved.rsplit('|', 1)[-1]
				name = '{}_{}_{}'.format(instancer.name(), pipesRemoved, j)

				#duplicate the object
				if bakeToIntances:
					name = pm.instance(dpa[i].fullPathName(), leaf=1, name=name)[0]
				else:
					name = pm.duplicate(dpa[i].fullPathName(), returnRootsOnly=1, upstreamNodes=upstreamNodes, name=name)[0]

				#parent it to the transform we created above
				if pm.listRelatives(name, p=True) != g:
					try:
						name = pm.parent(name, g)[0]
					except:
						pass

					# if the object doesn't appear on frame 0(animated creation), set the visibility when it first appears
					pm.setKeyframe(name+".visibility", v=0, t=pm.currentTime(query=1)-1)
					pm.setKeyframe(name+".visibility", v=1)

				#empty transformMatrix for the particle
				tm = om.MTransformationMatrix(m)
				instancedPath = dpa[i]
				#get the matrix from the instancer
				instancedPathMatrix = instancedPath.inclusiveMatrix()
				finalMatrixForPath = instancedPathMatrix * m
				finalPoint = om.MPoint.origin * finalMatrixForPath;

				t = tm.getTranslation(om.MSpace.kWorld)
				#set the translate
				try:
					pm.setAttr(name+".t", finalPoint.x, finalPoint.y, finalPoint.z)
					if bakeTranslate and bakeAnimation:
						pm.setKeyframe(name+".t")
				except:
					pass

				#set the rotate
				r = tm.eulerRotation().asVector()
				try:
					pm.setAttr(name+".r", r[0]*57.2957795, r[1]*57.2957795, r[2]*57.2957795)
					if bakeRotation and bakeAnimation:
						pm.setKeyframe(name+".r")
				except:
					pass

				#set the scale
				tm.getScale(sp, om.MSpace.kWorld)
				if bakeScale:
					sx = om.MScriptUtil().getDoubleArrayItem(sp, 0)
					sy = om.MScriptUtil().getDoubleArrayItem(sp, 1)
					sz = om.MScriptUtil().getDoubleArrayItem(sp, 2)
					s = om.MTransformationMatrix(dpa[i].inclusiveMatrix()).getScale(sp, om.MSpace.kWorld)
					sx2 = om.MScriptUtil().getDoubleArrayItem(sp, 0)
					sy2 = om.MScriptUtil().getDoubleArrayItem(sp, 1)
					sz2 = om.MScriptUtil().getDoubleArrayItem(sp, 2)
					try:
						pm.setAttr(name+".s", sx*sx2, sy*sy2, sz*sz2)
						if bakeAnimation:
							pm.setKeyframe(name+".s")
					except:
						pass

				# set visibility
				if bakeVisibility:
					pm.setAttr(name+".v", visibility)
					if bakeAnimation:
						pm.setKeyframe(name+".v")

				result.append(name) #append the converted object to the return value.

		return result


try:
	# add each funtion as an network attribute.
	for k, v in {
		'MTcreateNetwork':MTcreateNetwork, 
		'MTbakeInstancer':MTbakeInstancer,
		}.items():

		if not hasattr(mapi.Network, k):
			setattr(mapi.Network, k, v)

except NameError as error: #import mapi failed.
	print (__file__, error)

# --------------------------------------------------------------------------------------------
from tentacle import addMembers
addMembers(__name__)









# print (__name__) #module name
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated: -----------------------------------
