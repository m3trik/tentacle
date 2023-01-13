# !/usr/bin/python
# coding=utf-8
import os, sys
import unittest
import inspect


class Main(unittest.TestCase):
	'''
	'''
	def perform_test(self, case):
		'''
		'''
		for expression, expected_result in case.items():
			m = str(expression).split('(')[0] #ie. 'self.setCase' from "self.setCase('xxx', 'upper')"

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

# -----------------------------------------------------------------------------






# -----------------------------------------------------------------------------

if __name__=='__main__':

	appendPaths('O:/Cloud/Code/_scripts/tentacle', verbose=False)

	from tentacle import import_submodules
	import test
	import_submodules('test')

	unittest.main(exit=False)



# -----------------------------------------------------------------------------
# Notes
# -----------------------------------------------------------------------------