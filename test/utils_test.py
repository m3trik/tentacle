#unit testing
import os, sys
import unittest
import inspect

from utils import *


class Test(unittest.TestCase):
	'''
	'''
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



class Str_utils_test(Test, Str_utils):
	'''
	'''
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



class Iter_utils_test(Test, Iter_utils):
	'''
	'''
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



class File_utils_test(Test, File_utils):
	'''
	'''
	def test_formatPath(self):
		'''
		'''
		p1 = r'X:\n/dir1/dir3'
		p2 = r'X:\n/dir1/dir3/.vscode'
		p3 = r'X:\n/dir1/dir3/.vscode/tasks.json'
		p4 = r'\\192.168.1.240\nas/lost+found/file.ext'
		p5 = r'%programfiles%'

		self.perform_test({
			"self.formatPath(r'{}')".format(p1): 'X:/n/dir1/dir3',
			"self.formatPath(r'{}', 'path')".format(p1): 'X:/n/dir1/dir3',
			"self.formatPath(r'{}', 'path')".format(p2): 'X:/n/dir1/dir3/.vscode',
			"self.formatPath(r'{}', 'path')".format(p3): 'X:/n/dir1/dir3/.vscode',
			"self.formatPath(r'{}', 'path')".format(p4): r'\\192.168.1.240/nas/lost+found',
			"self.formatPath(r'{}', 'path')".format(p5): 'C:/Program Files',
			"self.formatPath(r'{}', 'dir')".format(p1): 'dir3',
			"self.formatPath(r'{}', 'dir')".format(p2): '.vscode',
			"self.formatPath(r'{}', 'dir')".format(p3): '.vscode',
			"self.formatPath(r'{}', 'dir')".format(p4): 'lost+found',
			"self.formatPath(r'{}', 'dir')".format(p5): 'Program Files',
			"self.formatPath(r'{}', 'file')".format(p1): '',
			"self.formatPath(r'{}', 'file')".format(p2): '',
			"self.formatPath(r'{}', 'file')".format(p3): 'tasks.json',
			"self.formatPath(r'{}', 'file')".format(p4): 'file.ext',
			"self.formatPath(r'{}', 'file')".format(p5): '',
			"self.formatPath(r'{}', 'name')".format(p1): '',
			"self.formatPath(r'{}', 'name')".format(p2): '',
			"self.formatPath(r'{}', 'name')".format(p3): 'tasks',
			"self.formatPath(r'{}', 'name')".format(p4): 'file',
			"self.formatPath(r'{}', 'name')".format(p5): '',
			"self.formatPath(r'{}', 'ext')".format(p1): '',
			"self.formatPath(r'{}', 'ext')".format(p2): '',
			"self.formatPath(r'{}', 'ext')".format(p3): 'json',
			"self.formatPath(r'{}', 'ext')".format(p4): 'ext',
			"self.formatPath(r'{}', 'ext')".format(p5): '',
			"self.formatPath({}, 'dir')".format([p1, p2]): ['dir3', '.vscode'],
		})


	def test_timeStamp(self):
		'''
		'''
		paths = [
			r'%ProgramFiles%',
			r'C:/',
		]

		self.perform_test({
			# "self.timeStamp({})".format(paths): [],
			# "self.timeStamp({}, False, '%m-%d-%Y  %H:%M', True)".format(paths): [],
			# "self.timeStamp({}, True)".format(paths): [],
		})


	def test_isValidPath(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))+'/test_files'
		file = path+'/file1.txt'

		self.perform_test({
			"self.isValidPath(r'{}')".format(file): 'file',
			"self.isValidPath(r'{}')".format(path): 'dir',
		})


	def test_writeToFile(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))+'/test_files'
		file = path+'/file1.txt'

		self.perform_test({
			"self.writeToFile(r'{}', 'some text')".format(file): None,
		})


	def test_getFileContents(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))+'/test_files'
		file = path+'/file1.txt'

		self.perform_test({
			"self.getFileContents(r'{}')".format(file): ['some text'],
		})


	def test_createDirectory(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))+'/test_files'

		self.perform_test({
			"self.createDirectory(r'{}')".format(path+'/sub-directory'): None,
		})


	def test_getDirectoryContents(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))+'/test_files'

		self.perform_test({
			"self.getDirectoryContents(r'{}', 'dirpaths')".format(path): [path+'\\sub-directory'],
			"self.getDirectoryContents(r'{}', 'files|dirs')".format(path): ['sub-directory', 'file1.txt', 'file2.txt', 'test.json'],
			"self.getDirectoryContents(r'{}', 'files', '*.txt', '', False, True, True)".format(path): ['file1', 'file2'],
			"self.getDirectoryContents(r'{}', 'files', '*.txt', reverse=True)".format(path): ['file2.txt', 'file1.txt'],
		})


	def test_getFilepath(self):
		'''
		'''
		path = os.path.abspath(os.path.dirname(__file__))

		self.perform_test({
			"self.getFilepath(__file__)": path,
			"self.getFilepath(__file__, True)": __file__,
		})



class Json_utils_test(Test, Json_utils):
	'''
	'''
	p = os.path.abspath(os.path.dirname(__file__))+'/test_files'
	path = '/'.join(p.split('\\')).rstrip('/')
	file = path+'/test.json'

	def test(self):
		'''
		'''
		self.perform_test({
			"self.setJsonFile(r'{}')".format(self.file): None,
			"self.getJsonFile()": self.file,
			"self.setJson('key', 'value')": None,
			"self.getJson('key')": 'value',
		})



class Img_utils_test(Test, Img_utils):
	'''
	'''
	def test_getImageDirectory(self):
		'''
		'''
		self.perform_test({
			# "self.getImageDirectory()": '',
		})


	def test_getImageFiles(self):
		'''
		'''
		self.perform_test({
			# "self.getImageFiles('*.png|*.jpg')": '',
		})


	def test_getImages(self):
		'''
		'''
		image_dir = r''

		self.perform_test({
			"self.getImages(r'{}')".format(image_dir): {},
		})


	def test_getImageBackground(self):
		'''
		'''
		image_dir = r''

		self.perform_test({
			# "self.getImageBackground(r'{}', None, False)".format(image_dir): tuple(),
		})


	def test_createMasks(self):
		'''
		'''
		images = []

		self.perform_test({
			"self.createMasks({})".format(images): [],
		})


	def test_fill(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.fill(r'{}', (0, 0, 0, 0))".format(image): '',
		})


	def test_fillMaskedArea(self):
		'''
		'''
		image = r''
		color = (0, 0, 0, 0)
		mask = r''

		self.perform_test({
			# "self.fillMaskedArea(r'{}', {}, r'{}')".format(image, color, mask): '',
		})


	def test_convert_rgb_to_gray(self):
		'''
		'''
		data = r''

		self.perform_test({
			# "self.convert_rgb_to_gray(r'{}')".format(data): (),
		})


	def test_convert_to_32bit_I(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.convert_to_32bit_I(r'{}')".format(image): '',
		})


	def test_convert_I_to_L(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.convert_I_to_L(r'{}')".format(image): '',
		})


	def test_all_pixels_identical(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.all_pixels_identical(r'{}')".format(image): False,
		})


	def test_setPixelColor(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.setPixelColor(r'{}', 150, 150, (255,255,255))".format(image): None,
		})


	def test_replaceColor(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.replaceColor(r'{}', (255,255,255), (0,0,0), 'RGBA')".format(image): '',
		})


	def test_setContrast(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.setContrast(r'{}', 255)".format(image): '',
		})


	def test_getImageType(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.getImageType(r'{}', False)".format(image): '',
		})


	def test_filterImagesByType(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.filterImagesByType(r'{}', '')".format(image): '',
		})


	def test_sortImagesByType(self):
		'''
		'''
		images = [
			r'',
		]

		self.perform_test({
			# "self.sortImagesByType({})".format(images): {},
		})


	def test_containsMapTypes(self):
		'''
		'''
		images = [
			r'',
		]

		self.perform_test({
			# "self.containsMapTypes({}, 'Normal_OpenGL|Normal_DirectX')".format(images): False,
		})


	def test_isNormalMap(self):
		'''
		'''
		image = r''

		self.perform_test({
			"self.isNormalMap(r'{}')".format(image): False,
		})


	def test_invertChannels(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.invertChannels(r'{}', 'G')".format(image): '',
		})


	def test_createDXFromGL(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.createDXFromGL(r'{}')".format(image): '',
		})


	def test_createGLFromDX(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.createGLFromDX(r'{}')".format(image): '',
		})


	def test_resizeImage(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.resizeImage(r'{}', 150, 150)".format(image): None,
		})


	def test_createImage(self):
		'''
		'''
		image = r''

		self.perform_test({
			# "self.createImage('RGBA', (4096, 4096), (0, 0, 0, 255))".format(image): '',
		})


	def test_saveImageFile(self):
		'''
		'''
		image = r''
		path = r''

		self.perform_test({
			# "self.saveImageFile(r'{}', {})".format(image, path): None,
		})



class Math_utils_test(Test, Math_utils):
	'''
	'''

	def test_areSimilar(self):
		'''
		'''
		self.perform_test({
			"self.areSimilar(1, 10, 9)": True,
			"self.areSimilar(1, 10, 8)": False,
		})


	def test_randomize(self):
		'''
		'''
		self.perform_test({
			# "self.randomize(range(10), 1.0)": [],
			# "self.randomize(range(10), 0.5)": [],
		})


	def test_getVectorFromTwoPoints(self):
		'''
		'''
		self.perform_test({
			"self.getVectorFromTwoPoints((1, 2, 3), (1, 1, -1))": (0, -1, -4),
		})


	def test_clamp(self):
		'''
		'''
		self.perform_test({
			"self.clamp(range(10), 3, 7)": [3, 3, 3, 3, 4, 5, 6, 7, 7, 7],
		})


	def test_normalize(self):
		'''
		'''
		self.perform_test({
			"self.normalize((2, 3, 4))": (0.3713906763541037, 0.5570860145311556, 0.7427813527082074),
			"self.normalize((2, 3))": (0.5547001962252291, 0.8320502943378437),
			"self.normalize((2, 3, 4), 2)": (0.7427813527082074, 1.1141720290623112, 1.4855627054164149),
		})


	def test_getMagnitude(self):
		'''
		'''
		self.perform_test({
			"self.getMagnitude((2, 3, 4))": 5.385164807134504,
			"self.getMagnitude((2, 3))": 3.605551275463989,
		})


	def test_dotProduct(self):
		'''
		'''
		self.perform_test({
			"self.dotProduct((1, 2, 3), (1, 1, -1))": 0,
			"self.dotProduct((1, 2), (1, 1))": 3,
			"self.dotProduct((1, 2, 3), (1, 1, -1), True)": 0,
		})


	def test_crossProduct(self):
		'''
		'''
		self.perform_test({
			"self.crossProduct((1, 2, 3), (1, 1, -1))": (-5, 4, -1),
			"self.crossProduct((3, 1, 1), (1, 4, 2), (1, 3, 4))": (7, 4, 2),
			"self.crossProduct((1, 2, 3), (1, 1, -1), None, 1)": (-0.7715167498104595, 0.6172133998483676, -0.1543033499620919),
		})


	def test_movePointRelative(self):
		'''
		'''
		self.perform_test({
			"self.movePointRelative((0, 5, 0), (0, 5, 0))": (0, 10, 0),
			"self.movePointRelative((0, 5, 0), 5, (0, 1, 0))": (0, 10, 0),
		})


	def test_movePointAlongVectorTowardPoint(self):
		'''
		'''
		self.perform_test({
			"self.movePointAlongVectorTowardPoint((0, 0, 0), (0, 10, 0), (0, 1, 0), 5)": (0.0, 5.0, 0.0),
		})


	def test_getDistanceBetweenTwoPoints(self):
		'''
		'''
		self.perform_test({
			"self.getDistanceBetweenTwoPoints((0, 10, 0), (0, 5, 0))": 5.0,
		})


	def test_getCenterPointBetweenTwoPoints(self):
		'''
		'''
		self.perform_test({
			"self.getCenterPointBetweenTwoPoints((0, 10, 0), (0, 5, 0))": (0.0, 7.5, 0.0),
		})


	def test_getAngleFrom2Vectors(self):
		'''
		'''
		self.perform_test({
			"self.getAngleFrom2Vectors((1, 2, 3), (1, 1, -1))": 1.5707963267948966,
			"self.getAngleFrom2Vectors((1, 2, 3), (1, 1, -1), True)": 90,
		})


	def test_getAngleFrom3Points(self):
		'''
		'''
		self.perform_test({
			"self.getAngleFrom3Points((1, 1, 1), (-1, 2, 3), (1, 4, -3))": 0.7904487543360762,
			"self.getAngleFrom3Points((1, 1, 1), (-1, 2, 3), (1, 4, -3), True)": 45.29,
		})


	def test_getTwoSidesOfASATriangle(self):
		'''
		'''
		self.perform_test({
			"self.getTwoSidesOfASATriangle(60, 60, 100)": (100.00015320566493, 100.00015320566493),
		})


	def test_xyzRotation(self):
		'''
		'''
		self.perform_test({
			"self.xyzRotation(2, (0, 1, 0))": (3.589792907376932e-09, 1.9999999964102069, 3.589792907376932e-09),
			"self.xyzRotation(2, (0, 1, 0), [], True)": (0.0, 114.59, 0.0),
		})









if __name__=='__main__':
	unittest.main()



# --------------------------------
# Notes
# --------------------------------

"""
def test_(self):
		'''
		'''
		self.perform_test({
			"self.()": ,
		})
"""

# Deprecated ---------------------