import os
import setuptools

from tentacle import name, __version__
from pythontk import File


with open('docs/README.md', 'r') as f:
	long_description = f.read()

setuptools.setup(
	name=name,
	version=__version__,
	author='Ryan Simpson',
	author_email='m3trik@outlook.com',
	description='A Python3/PySide2 marking menu style toolkit for Maya, 3ds Max, and Blender.',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/m3trik/tentacle',
	packages=setuptools.find_packages(), #scan the directory structure and include all package dependancies.
	classifiers=[
		'Programming Language :: Python :: 3',
		# 'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
	],
	include_package_data = True,
	data_files=File.getDirContents('tentacle', 'filepaths', excFiles=['*.py', '*.pyc', '*.json']), #ie. ('tentacle/ui/0', ['tentacle/ui/0/init.ui']),
)

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# Deprecated ------------------------------------

# def gen_data_files(dirs, exc=[], inc=[]):
# 	'''
# 	'''
# 	dirs = itertk.makeList(dirs)
# 	exc = itertk.makeList(exc)
# 	inc = itertk.makeList(inc)

# 	results = []
# 	for src_dir in dirs:
# 		for root, dirs, files in os.walk(src_dir):
# 			filtered=[]
# 			for f in files:
# 				ext = filetk.formatPath(f, 'ext')
# 				if f in exc or '*.'+ext in exc:
# 					continue
# 				if any(inc): #filter inc for None values so not to get a false positive.
# 					if not f in inc and not '*.'+ext in inc:
# 						continue
# 				filtered.append(f)

# 			if filtered:
# 				results.append((root, list(map(lambda f:root + "/" + f, filtered))))
# 	return results

# # for i in gen_data_files('tentacle', exc=['*.py', '*.pyc', '*.json']):
# 	# print (i)