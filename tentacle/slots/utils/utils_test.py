#unit testing
import os, sys
import unittest
import inspect

from utils import Str_utils, Iter_utils


class Str_utils_test(unittest.TestCase, Str_utils):

	def perform_test(self, case):
		'''
		'''
		for expression, expected_result in case.items():
			m = expression.split('(')[0] #ie. 'self.setCase' from "self.setCase('xxx', 'upper')"
	
			try:
				path = os.path.abspath(inspect.getfile(eval(m)))
			except TypeError as error:
				path = ''

			result = eval(expression)
			self.assertEqual(
				result, 
				expected_result, 
				"\n\nError: {}\n  Call:     {}\n  Expected: {} {}\n  Returned: {} {}".format(path, expression.replace('self.', '', 1), type(expected_result), expected_result, type(result), result)
		)


	def test_setCase(self):
		'''
		'''
		self.perform_test({
			"self.setCase('xxx', 'upper')":'XXX',
			"self.setCase('XXX', 'lower')":'xxx',
			"self.setCase('xxx', 'capitalize')":'Xxx',
			"self.setCase('xxX', 'swapcase')":'XXx',
			"self.setCase('xxx XXX', 'title')":'Xxx Xxx',
			"self.setCase('xXx', 'pascalCase')":'XXx',
			"self.setCase('xXx', 'camelCase')":'xXx',
			"self.setCase(['xXx'], 'camelCase')":['xXx'],
			"self.setCase(None, 'camelCase')":None,
		})


	def test_splitAtChars(self):
		'''
		'''
		self.perform_test({
			"self.splitAtChars(['str|ing', 'string'])": [('str', 'ing'), ('string', '')],
			"self.splitAtChars('aCHARScCHARSd', 'CHARS', 0)": ('', 'a'),
		})


	def test_insert(self):
		'''
		'''
		self.perform_test({
			"self.insert('ins into str', 'substr ', ' ')": 'ins substr into str',
			"self.insert('ins into str', ' end of', ' ', -1, True)": 'ins into end of str',
			"self.insert('ins into str', 'insert this', 'atCharsThatDontExist')": 'ins into str',
			"self.insert('ins into str', 666, 0)": '666ins into str',
		})


	def test_rreplace(self):
		'''
		'''
		self.perform_test({
			"self.rreplace('aabbccbb', 'bb', 22)": 'aa22cc22',
			"self.rreplace('aabbccbb', 'bb', 22, 1)": 'aabbcc22',
			"self.rreplace('aabbccbb', 'bb', 22, 3)": 'aa22cc22',
			"self.rreplace('aabbccbb', 'bb', 22, 0)": 'aabbccbb',
		})


	def test_truncate(self):
		'''
		'''
		self.perform_test({
			"self.truncate('12345678', 4)": '..5678',
			"self.truncate('12345678', 4, False)": '1234..',
			"self.truncate('12345678', 4, False, '--')": '1234--',
			"self.truncate(None, 4)": None,
		})


	def test_getTrailingIntegers(self):
		'''
		'''
		self.perform_test({
			"self.getTrailingIntegers('p001Cube1')": 1,
			"self.getTrailingIntegers('p001Cube1', 0, True)": '1',
			"self.getTrailingIntegers('p001Cube1', 1)": 2,
			"self.getTrailingIntegers(None)": None,
		})


	def test_findStr(self):
		'''
		'''
		lst = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorder', 'keepBorderWeight', 'keepColorBorder', 'keepColorBorderWeight']
		rtn = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorderWeight', 'keepColorBorderWeight']

		self.perform_test({
			"self.findStr('*Weight*', {})".format(lst): rtn,
			"self.findStr('Weight$|Weights$', {}, regEx=True)".format(lst): rtn,
			"self.findStr('*weight*', {}, False, True)".format(lst): rtn,
			"self.findStr('*Weights|*Weight', {})".format(lst): rtn,
		})


	def test_findStrAndFormat(self):
		'''
		'''
		lst = ['invertVertexWeights', 'keepCreaseEdgeWeight', 'keepBorder', 'keepBorderWeight', 'keepColorBorder', 'keepColorBorderWeight']

		self.perform_test({
			"self.findStrAndFormat('*Weights', '', {})".format(lst): ['invertVertex'],
			"self.findStrAndFormat('*Weights', 'new name', {})".format(lst): ['new name'],
			"self.findStrAndFormat('*Weights', '*insert*', {})".format(lst): ['invertVertexinsert'],
			"self.findStrAndFormat('*Weights', '*_suffix', {})".format(lst): ['invertVertex_suffix'],
			"self.findStrAndFormat('*Weights', '**_suffix', {})".format(lst): ['invertVertexWeights_suffix'],
			"self.findStrAndFormat('*Weights', 'prefix_*', {})".format(lst): ['prefix_Weights'],
			"self.findStrAndFormat('*Weights', 'prefix_**', {})".format(lst): ['prefix_invertVertexWeights'],
			"self.findStrAndFormat('Weights$', 'new name', {}, True)".format(lst): ['new name'],
			"self.findStrAndFormat('*weights', 'new name', {}, False, True, True)".format(lst): [('invertVertexWeights', 'new name')],
		})


	def test_formatSuffix(self):
		'''
		'''
		self.perform_test({
			"self.formatSuffix('p001Cube1', '_suffix', 'Cube1')": 'p00_suffix',
			"self.formatSuffix('p001Cube1', '_suffix', ['Cu', 'be1'])": 'p00_suffix',
			"self.formatSuffix('p001Cube1', '_suffix', '', True)": 'p001Cube_suffix',
			"self.formatSuffix('pCube_GEO1', '_suffix', '', True, True)": 'pCube_suffix',
		})



class Iter_utils_test(unittest.TestCase, Iter_utils):

	def perform_test(self, case):
		'''
		'''
		for expression, expected_result in case.items():
			m = expression.split('(')[0] #ie. 'self.setCase' from "self.setCase('xxx', 'upper')"
	
			try:
				path = os.path.abspath(inspect.getfile(eval(m)))
			except TypeError as error:
				path = ''

			result = eval(expression)
			self.assertEqual(
				result, 
				expected_result, 
				"\n\nError: {}\n  Call:     {}\n  Expected: {} {}\n  Returned: {} {}".format(path, expression.replace('self.', '', 1), type(expected_result), expected_result, type(result), result)
		)


	def test_makeList(self):
		'''
		'''
		self.perform_test({
			"self.makeList('x')": ['x'],
			"self.makeList(1)": [1],
			"self.makeList('')": [''],
			"self.makeList({'x':'y'})": ['x'],
		})


	def test_formatReturn(self):
		'''
		'''
		self.perform_test({
			"self.formatReturn([''])": '',
			"self.formatReturn(['', ''])": ['', ''],
		})


	def test_hasNested(self):
		'''
		'''
		self.perform_test({
			"self.hasNested([[1, 2], [3, 4]])": True,
			"self.hasNested([1, 2, 3, 4])": False,
		})


	def test_flatten(self):
		'''
		'''
		self.perform_test({
			"list(self.flatten([[1, 2], [3, 4]]))": [1, 2, 3, 4],
		})


	def test_collapseList(self):
		'''
		'''
		lst = [19,22,23,24,25,26]

		self.perform_test({
			"self.collapseList({})".format(lst): '19, 22-6',
			"self.collapseList({}, 1)".format(lst): '19, ...',
			"self.collapseList({}, None, False, False)".format(lst): ['19', '22..26'],
		})


	def test_bitArrayToList(self):
		'''
		'''
		flags = bytes.fromhex('beef')
		bits =  [flags[i//8] & 1 << i%8 != 0 for i in range(len(flags) * 8)]

		self.perform_test({
			"self.bitArrayToList({})".format(bits): [2, 3, 4, 5, 6, 8, 9, 10, 11, 12, 14, 15, 16],
		})


	def test_rindex(self):
		'''
		'''
		self.perform_test({
			"self.rindex([0, 1, 2, 2, 3], 2)": 3,
			"self.rindex([0, 1, 2, 2, 3], 4)": -1,
		})


	def test_removeDuplicates(self):
		'''
		'''
		self.perform_test({
			"self.removeDuplicates([0, 1, 2, 3, 2])": [0, 1, 2, 3],
			"self.removeDuplicates([0, 1, 2, 3, 2], False)": [0, 1, 3, 2],
		})



if __name__=='__main__':
	unittest.main()



# --------------------------------
# Notes
# --------------------------------


# def test_(self):
	# 	'''
	# 	'''
	# 	self.perform_test({
	# 		"self.()": ,
	# 	})


# Deprecated ---------------------