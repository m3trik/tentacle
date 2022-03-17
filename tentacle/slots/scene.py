# !/usr/bin/python
# coding=utf-8
from slots import Slots



class Scene(Slots):
	'''
	'''
	def __init__(self, *args, **kwargs):
		'''
		:Parameters: 
			**kwargs (inherited from this class's respective slot child class, and originating from switchboard.setClassInstanceFromUiName)
				properties:
					tcl (class instance) = The tentacle stacked widget instance. ie. self.tcl
					<name> (ui object) = The ui of <name> ie. self.polygons for the ui of filename polygons. ie. self.polygons
				functions:
					current (lambda function) = Returns the current ui if it is either the parent or a child ui for the class; else, return the parent ui. ie. self.current()
					'<name>' (lambda function) = Returns the class instance of that name.  ie. self.polygons()
		'''
		self.scene_ui.t000.returnPressed.connect(self.t001) #preform rename on returnPressed

		ctx = self.scene_ui.draggable_header.contextMenu
		if not ctx.containsMenuItems:
			ctx.add(self.tcl.wgts.ComboBox, setObjectName='cmb000', setToolTip='Scene Editors')

		ctx = self.scene_ui.t000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QCheckBox', setText='Ignore Case', setObjectName='chk000', setToolTip='Search case insensitive.')
			ctx.add('QCheckBox', setText='Regular Expression', setObjectName='chk001', setToolTip='When checked, regular expression syntax is used instead of the default \'*\' and \'|\' wildcards.')

		ctx = self.scene_ui.tb000.contextMenu
		if not ctx.containsMenuItems:
			ctx.add('QComboBox', addItems=['capitalize', 'upper', 'lower', 'swapcase', 'title'], setObjectName='cmb001', setToolTip='Set desired python case operator.')


	def draggable_header(self, state=None):
		'''Context menu
		'''
		dh = self.scene_ui.draggable_header


	def t000(self, state=None):
		'''Find
		'''
		t000 = self.scene_ui.t000


	@staticmethod
	def getTrailingIntegers(string, inc=0):
		'''Returns any integers from the end of the given string.

		:Parameters:
			inc (int) = Increment by a step amount. 0 does not increment and returns the original number. (default: 0)

		"Return:
			(int)

		ex. n = getTrailingIntegers('p001Cube1', inc=1) #returns: 2
		'''
		import re

		m = re.findall(r"\d+\s*$", string)
		result = int(m[0])+inc if m else None

		return result


	@staticmethod
	def findStr(what, where, regEx=False, ignoreCase=False):
		'''Find matches of a string in a list.

		:Parameters:
			what (str) = The search string. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe chars.
				wildcards:
					*what* - search contains chars.
					*what - search endswith chars.
					what* - search startswith chars.
					what|what - search any of.  can be used in conjuction with other modifiers.
				regular expressions (if regEx True):
					(.) match any char. ex. re.match('1..', '1111') #returns the regex object <111>
					(^) match start. ex. re.match('^11', '011') #returns None
					($) match end. ex. re.match('11$', '011') #returns the regex object <11>
					(|) or. ex. re.match('1|0', '011') #returns the regex object <0>
					(\A,\Z) beginning of a string and end of a string. ex. re.match(r'\A011\Z', '011') #
					(\b) empty string. (\B matches the empty string anywhere else). ex. re.match(r'\b(011)\b', '011 011 011') #
			where (list) = The string list to search in.
			ignoreCase (bool) = Search case insensitive.

		:Return:
			(list)

		ex. list_ = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorder', 'keepBorderWeight', 'keepColorBorder', 'keepColorBorderWeight']
			findStr('*Weight*', list_) #find any element that contains the string 'Weight'.
			findStr('Weight$|Weights$', list_, regEx=True) #find any element that endswith 'Weight' or 'Weights'.
		'''
		if regEx: #search using a regular expression.
			import re

			try:
				if ignoreCase:
					result = [i for i in where if re.search(what, i, re.IGNORECASE)]
				else:
					result = [i for i in where if re.search(what, i)]
			except Exception as e:
				print ('# Error findStr: in {}: {}. #'.format(what, e))
				result = []

		else: #search using wildcards.
			for w in what.split('|'): #split at pipe chars.
				w_ = w.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

				#modifiers
				if w.startswith('*') and w.endswith('*'): #contains
					if ignoreCase:				
						result = [i for i in where if w_.lower() in i.lower()] #case insensitive.
					else:
						result = [i for i in where if w_ in i]

				elif w.startswith('*'): #prefix
					if ignoreCase:
						result = [i for i in where if i.lower().endswith(w_.lower())] #case insensitive.
					else:
						result = [i for i in where if i.endswith(w_)]

				elif w.endswith('*'): #suffix
					if ignoreCase:
						result = [i for i in where if i.lower().startswith(w_.lower())] #case insensitive.
					else:
						result = [i for i in where if i.startswith(w_)]

				else: #exact match
					if ignoreCase:
						result = [i for i in where if i.lower()==w_.lower()] #case insensitive.
					else:
						result = [i for i in where if i==w_]

		return result


	@staticmethod
	def findStrAndFormat(frm, to, where, regEx=False, ignoreCase=False):
		'''Search a list for matching strings and re-format them.
		Useful for things such as finding and renaming objects.

		:Parameters:
			frm (str) = Current name. An asterisk denotes startswith*, *endswith, *contains*, and multiple search strings can be separated by pipe ('|') chars.
				*frm* - Search contains chars.
				*frm - Search endswith chars.
				frm* - Search startswith chars.
				frm|frm - Search any of.  can be used in conjuction with other modifiers.
			to (str) = Desired name: An optional asterisk modifier can be used for formatting. An empty to string will attempt to remove the part of the string designated in the from argument.
				"" - (empty string) - strip chars.
				*to* - replace only.
				*to - replace suffix.
				**to - append suffix.
				to* - replace prefix.
				to** - append prefix.
			where (list) = A list of string objects to search.
			regEx (bool) = If True, regex syntax is used instead of '*' and '|'.
			ignoreCase (bool) = Ignore case when searching. Applies only to the 'frm' parameter's search.

		:Return:
			(list) list of two element tuples containing the original and modified string pairs. [('frm','to')]

		ex. findStrAndFormat(r'Cube', '*001', regEx=True) #replace chars after frm on any object with a name that contains 'Cube'. ie. 'polyCube001' from 'polyCube'
		ex. findStrAndFormat(r'Cube', '*001', regEx=True) #append chars on any object with a name that contains 'Cube'. ie. 'polyCube1001' from 'polyCube1'
		'''
		import re

		if frm: #filter for matching strings if a frm argument is given. else; use all.
			where = Scene.findStr(frm, where, regEx=regEx, ignoreCase=ignoreCase)

		frm_ = re.sub('[^A-Za-z0-9_:]+', '', frm) #strip any special chars other than '_'.
		to_ = to.strip('*').rstrip('*') #remove any modifiers from the left and right end chars.

		result=[]
		for name in where:

			#modifiers
			if to.startswith('*') and to.endswith('*'): #replace chars
				if ignoreCase:
					n = re.sub(frm_, to_, name, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
				else:
					n = name.replace(frm_, to_)

			elif to.startswith('**'): #append suffix
				n = name+to_

			elif to.startswith('*'): #replace suffix
				if ignoreCase:
					end_index = re.search(frm_, name, flags=re.IGNORECASE).start() #get the starting index of 'frm_'.
					n = name[:index]+to_
				else:
					n = name.split(frm_)[0]+to_

			elif to.endswith('**'): #append prefix
				n = to_+name

			elif to.endswith('*'): #replace prefix
				if ignoreCase:
					end_index = re.search(frm_, name, flags=re.IGNORECASE).end() #get the ending index of 'frm_'.
					n = to_+name[index:]
				else:
					n = to_+frm_+name.split(frm_)[-1]

			else:
				if not to_: #if 'to_' is an empty string:
					if ignoreCase:
						n = re.sub(frm_, '', name, flags=re.IGNORECASE) #remove frm_ from the string (case in-sensitive).
					else:
						n = name.replace(frm_, '') #remove frm_ from the string.
				else: #else; replace whole name
					n = to_

			result.append((name, n))

		return result


	