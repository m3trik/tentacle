# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.symmetry import Symmetry



class Symmetry_max(Symmetry, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Symmetry.__init__(self, *args, **kwargs)

		cmb = self.symmetry_ui.draggable_header.contextMenu.cmb000
		items = ['']
		cmb.addItems_(items, '')

		#symmetry: set initial checked state
		# state = pm.symmetricModelling(query=True, symmetry=True) #application symmetry state
		# axis = pm.symmetricModelling(query=True, axis=True)
		# if axis == "x":
		# 	self.symmetry_ui.chk000.setChecked(state)
		# 	self.symmetry_submenu_ui.chk000.setChecked(state)
		# if axis == "y":
		# 	self.symmetry_ui.chk001.setChecked(state)
		# 	self.symmetry_submenu_ui.chk001.setChecked(state)
		# if axis == "z":
		# 	self.symmetry_ui.chk002.setChecked(state)
		# 	self.symmetry_submenu_ui.chk002.setChecked(state)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.symmetry_ui.draggable_header.contextMenu.cmb000

		if index>0:
			text = cmb.items[index]
			if text=='':
				pass
			cmb.setCurrentIndex(0)


	@Slots.message
	def chk005(self, state=None):
		'''Symmetry: Topo
		'''
		self.symmetry_ui.chk004.setChecked(False) #uncheck symmetry:object space
		# if any ([self.symmetry_ui.chk000.isChecked(), self.symmetry_ui.chk001.isChecked(), self.symmetry_ui.chk002.isChecked()]): #(symmetry)
		# 	pm.symmetricModelling(edit=True, symmetry=False)
		# 	self.toggleWidgets(setUnChecked='chk000-2')
		# 	return 'Note: First select a seam edge and then check the symmetry button to enable topographic symmetry'


	@Slots.message
	def setSymmetry(self, state, axis):
		''''''
		# space = "world" #workd space
		# if self.symmetry_ui.chk004.isChecked(): #object space
		# 	space = "object"
		# elif self.symmetry_ui.chk005.isChecked(): #topological symmetry
		# 	space = "topo"

		if axis=='x':
			_axis=0 #0(x), 1,(y), 2(z)
		if axis=='y':
			_axis=1
		if axis=='z':
			_axis=2

		for obj in rt.selection:
			#check if modifier exists
			mod = obj.modifiers[rt.Symmetry]
			if mod==None: #if not create
				mod = rt.symmetry()
				rt.addModifier (obj, mod)
		
			#set attributes
			mod.enabled = state
			mod.threshold = 0.01
			mod.axis = _axis
			mod.flip = negative

		rt.redrawViews()
		return 'Symmetry: '+axis.capitalize()+' <hl>'+str(state)+'</hl>'









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------