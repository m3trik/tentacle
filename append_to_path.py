import sys, os


def appendPaths(app,  exclude=('grepWin_backup', '__pycache__', 'docs', '.vscode', 'blender', 'max', 'maya'), verbose=False):
	'''Append all relevant directories to the python path for the given parent app.

	:Parameters:
		app (str) = The parent app to append paths for. (valid: 'maya', 'blender', 'max')
		exclude (list) = Exclude directories by name.
		verbose (bool) = Output the results to the console. (Debug)
	'''
	path = (__file__.rstrip(__file__.split('\\')[-1])+'tentacle') #get the path to this module.
	sys.path.insert(0, path)
	if verbose:
		print (path)

	exclude = [i for i in exclude if i!=app]

	#recursively append subdirectories to the system path
	for root, dirs, files in os.walk(path):
		for dir_name in dirs:

			if not any([(e in root or e==dir_name) for e in exclude]):
				dir_path = os.path.join(root, dir_name)
				sys.path.insert(0, dir_path)
				if verbose:
					print (dir_path)