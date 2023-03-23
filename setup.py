import os
import setuptools

from tentacle import __package__, __version__
from pythontk import File, Str


long_description = File.getFileContents('docs/README.md')
description = Str.getTextBetweenDelimiters(long_description, '<!-- short_description_start -->', '<!-- short_description_end -->', as_string=True)

setuptools.setup(
	name='tentacletk',
	version=__version__,
	author='Ryan Simpson',
	author_email='m3trik@outlook.com',
	description=description,
	long_description=long_description,
	long_description_content_type='text/markdown',
	url=f'https://github.com/m3trik/{__package__}',
	packages=setuptools.find_packages(), #scan the directory structure and include all package dependancies.
	classifiers=[
		'Programming Language :: Python :: 3',
		# 'License :: OSI Approved :: MIT License',
		'Operating System :: OS Independent',
	],
	include_package_data = True,
	data_files=File.getDirContents(__package__, 'filepaths', excFiles=['*.py', '*.pyc', '*.json']), #ie. ('tentacle/ui/0', ['tentacle/ui/0/init.ui']),
)

# --------------------------------------------------------------------------------------------









# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------



# Deprecated ------------------------------------

# def gen_data_files(dirs, exc=[], inc=[]):
# 	'''
# 	'''
# 	dirs = Iter.makeList(dirs)
# 	exc = Iter.makeList(exc)
# 	inc = Iter.makeList(inc)

# 	results = []
# 	for src_dir in dirs:
# 		for root, dirs, files in os.walk(src_dir):
# 			filtered=[]
# 			for f in files:
# 				ext = File.formatPath(f, 'ext')
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