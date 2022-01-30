# !/usr/bin/python
# coding=utf-8
from slots.max import *
from slots.symmetry import Symmetry



class Symmetry_max(Symmetry, Slots_max):
	def __init__(self, *args, **kwargs):
		Slots_max.__init__(self, *args, **kwargs)
		Symmetry.__init__(self, *args, **kwargs)

		cmb000 = self.symmetry_ui.draggable_header.contextMenu
		items = ['']
		cmb000.addItems_(items, '')

		#set initial checked state
		# state = pm.symmetricModelling(query=True, symmetry=True) #application symmetry state
		# axis = pm.symmetricModelling(query=True, axis=True)
		# widget = 'chk000' if axis=='x' else 'chk001' if axis=='y' else 'chk002'
		# getattr(self.symmetry_ui, widget).setChecked(state)
		# getattr(self.symmetry_submenu_ui, widget).setChecked(state)


	def cmb000(self, index=None):
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

		state = state if state==0 else 1 #for case when checkbox gives a state of 2.

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