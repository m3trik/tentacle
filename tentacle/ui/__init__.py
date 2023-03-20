import inspect

from pythontk.File import getFilepath

module = inspect.getmodule(inspect.currentframe()) #this module.
path = getFilepath(module) #this modules directory.