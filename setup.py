import os
import setuptools

from tentacle import __version__

from utils import Utils


def gen_data_files(dirs, exclude=[], include=[]):
	'''
	'''
	dirs = Utils.makeList(dirs)
	exclude = Utils.makeList(exclude)
	include = Utils.makeList(include)

	results = []
	for src_dir in dirs:
		for root, dirs, files in os.walk(src_dir):
			filtered=[]
			for f in files:
				ext = Utils.formatFilepath(f, 'ext')
				if f in exclude or '*.'+ext in exclude:
					continue
				if any(include): #filter include for None values so not to get a false positive.
					if not f in include and not '*.'+ext in include:
						continue
				filtered.append(f)

			if filtered:
				results.append((root, list(map(lambda f:root + "/" + f, filtered))))
	return results

# for i in gen_data_files('tentacle', exclude=['*.py', '*.pyc', '*.json']):
	# print (i)

with open('docs/README.md', 'r') as f:
	long_description = f.read()

setuptools.setup(
	name='tcl-toolkit',
	version=__version__,
	author='Ryan Simpson',
	author_email='m3trik@outlook.com',
	description='A Python3/PySide2 marking menu style toolkit for Maya, 3ds Max, and Blender.',
	long_description=long_description,
	long_description_content_type='text/markdown',
	url='https://github.com/m3trik/tentacle',
	packages=setuptools.find_packages(),
	classifiers=[
		'Programming Language :: Python :: 3',
		# 'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
	],
	include_package_data = True,
	data_files=gen_data_files('tentacle', exclude=['*.py', '*.pyc', '*.json']), #ie. ('tentacle/ui/0', ['tentacle/ui/0/init.ui']),
)