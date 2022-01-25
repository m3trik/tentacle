# !/usr/bin/python
# coding=utf-8
from slots.maya import *
from slots.symmetry import Symmetry



class Symmetry_maya(Symmetry):
	def __init__(self, *args, **kwargs):
		Slots_maya.__init__(self, *args, **kwargs)
		Symmetry.__init__(self, *args, **kwargs)

		cmb = self.symmetry_ui.draggable_header.contextMenu.cmb000
		list_ = ['']
		cmb.addItems_(list_, '')

		#set initial checked state
		state = pm.symmetricModelling(query=True, symmetry=True) #application symmetry state
		axis = pm.symmetricModelling(query=True, axis=True)
		if axis == "x":
			self.symmetry_ui.chk000.setChecked(state)
			self.symmetry_submenu_ui.chk000.setChecked(state)
		if axis == "y":
			self.symmetry_ui.chk001.setChecked(state)
			self.symmetry_submenu_ui.chk001.setChecked(state)
		if axis == "z":
			self.symmetry_ui.chk002.setChecked(state)
			self.symmetry_submenu_ui.chk002.setChecked(state)


	def cmb000(self, index=-1):
		'''Editors
		'''
		cmb = self.symmetry_ui.draggable_header.contextMenu.cmb000

		# if index>0:
		# 	if index==cmd.items.index(''):
		# 		pass
		# 	cmb.setCurrentIndex(0)


	@Slots.message
	def chk005(self, state=None):
		'''Symmetry: Topo
		'''
		self.symmetry_ui.chk004.setChecked(False) #uncheck symmetry:object space
		if any ([self.symmetry_ui.chk000.isChecked(), self.symmetry_ui.chk001.isChecked(), self.symmetry_ui.chk002.isChecked()]): #(symmetry)
			pm.symmetricModelling(edit=True, symmetry=False)
			self.toggleWidgets(setUnChecked='chk000,chk001,chk002')
			return 'Note: First select a seam edge and then check the symmetry button to enable topographic symmetry'


	@Slots.message
	def setSymmetry(self, state, axis):
		space = "world" #workd space
		if self.symmetry_ui.chk004.isChecked(): #object space
			space = "object"
		elif self.symmetry_ui.chk005.isChecked(): #topological symmetry
			space = "topo"

		tolerance = 0.25
		pm.symmetricModelling(edit=True, symmetry=state, axis=axis, about=space, tolerance=tolerance)
		self.viewPortMessage("Symmetry:<hl>"+axis+' '+str(state)+"</hl>")









#module name
print (__name__)
# -----------------------------------------------
# Notes
# -----------------------------------------------