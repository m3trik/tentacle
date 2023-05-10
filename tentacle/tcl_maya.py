# !/usr/bin/python
# coding=utf-8
import sys

from PySide2 import QtCore

from mayatk import getMainWindow
from tentacle.tcl import Tcl


# constants
INSTANCES = {}


class TclMaya(Tcl):
    """Tcl class overridden for use with Autodesk Maya.

    Parameters:
            parent = Application top level window instance.
    """

    def __init__(self, parent=None, slots_location="slots/maya", *args, **kwargs):
        """ """
        if not parent:
            try:
                parent = getMainWindow()

            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slots_location=slots_location, *args, **kwargs)

    def showEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """

        Tcl.showEvent(self, event)  # super().showEvent(event)

    def hideEvent(self, event):
        """
        Parameters:
                event = <QEvent>
        """
        if __name__ == "__main__":
            self.app.quit()
            sys.exit()  # assure that the sys processes are terminated.

        Tcl.hideEvent(self, event)  # super().hideEvent(event)


# --------------------------------------------------------------------------------------------


def getInstance(instanceID=None, *args, **kwargs):
    """Get an instance of this class using a given instanceID.
    The instanceID is either the object or the object's id.

    Parameters:
            instanceID () = The instanceID can be any immutable type.
            args/kwargs () = The args to be passed to the class instance when it is created.

    Returns:
            (obj) An instance of this class.

    Example: tcl = getInstance(id(0), key_show='Key_F12') #returns the class instance with an instance ID of the value of `id(0)`.
    """
    import inspect

    if instanceID is None:
        instanceID = inspect.stack()[1][3]
    try:
        return INSTANCES[instanceID]

    except KeyError as error:
        INSTANCES[instanceID] = TclMaya(*args, **kwargs)
        return INSTANCES[instanceID]


def show(instanceID=None, *args, **kwargs):
    """Expands `getInstance` to get and then show an instance in a single command."""
    inst = getInstance(instanceID=instanceID, *args, **kwargs)
    inst.show()


# --------------------------------------------------------------------------------------------


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show("init#startmenu")

    # run app, show window, wait for input, then terminate program with a status code returned from app.
    exit_code = main.app.exec_()
    if exit_code != -1:
        sys.exit(exit_code)

# module name
print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# deprecated: -----------------------------------


# INSTANCES = {}

# def __init__(self, parent=None, id=None, slots='slots/maya', *args, **kwargs):
#   '''
#   '''
#   if not parent:
#       try:
#           parent = getMainWindow()

#       except Exception as error:
#           print(__file__, error)

#   super().__init__(parent, slots=slots, *args, **kwargs)

#   if id is not None:
#       TclMaya.INSTANCES[id] = self


# @classmethod
# def get_instance(cls, id, profile=False):
#   if id not in cls.INSTANCES:
#       cls.INSTANCES[id] = TclMaya(key_show='Key_F12', profile=profile, id=id)
#   return cls.INSTANCES[id]


# def show_instance(self):
#   self.send_key_press_event(self.key_show)

# #call
# from tentacle.tcl_maya import TclMaya
#   tcl = TclMaya.get_instance(id, profile=profile)
#   tcl.show_instance()


# class Instance(Instance):
#   '''Manage multiple instances of TclMaya.
#   '''
#   def __init__(self, *args, **kwargs):
#       '''
#       '''
#       super().__init__(*args, **kwargs)
#       self.Class = TclMaya


# if not pm.runTimeCommand('Hk_main', exists=1):
#   pm.runTimeCommand(
#       'Hk_main'
#       annotation='',
#       catagory='',
#       commandLanguage='python',
#       command=if 'tentacle' not in {**locals(), **globals()}: main = TclMaya.createInstance(); main.hide(); main.show(),
#       hotkeyCtx='',
#   )


# def hk_main_show():
#   '''hk_main_show
#   Display main marking menu.

#   profile: Prints the total running time, times each function separately, and tells you how many times each function was called.
#   '''
#   if 'main' not in locals() and 'main' not in globals():
#       from main_maya import Instance
#       main = Instance()

#   main.show_()
#   # import cProfile
#   # cProfile.run('main.show_()')
