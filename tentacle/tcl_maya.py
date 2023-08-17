# !/usr/bin/python
# coding=utf-8
import sys
import mayatk as mtk
from tentacle.tcl import Tcl


INSTANCES = {}


class TclMaya(Tcl):
    """Tcl class overridden for use with Autodesk Maya.

    Parameters:
            parent = Application top level window instance.
    """

    def __init__(self, parent=None, slot_location="slots/maya", *args, **kwargs):
        """ """
        if not parent:
            try:
                parent = mtk.get_main_window()

            except Exception as error:
                print(__file__, error)

        super().__init__(parent, slot_location=slot_location, *args, **kwargs)

    def showEvent(self, event):
        """ """

        super().showEvent(event)  # super().showEvent(event)

    def hideEvent(self, event):
        """ """
        if __name__ == "__main__":
            self.app.quit()
            sys.exit()  # assure that the sys processes are terminated.

        super().hideEvent(event)  # super().hideEvent(event)


# --------------------------------------------------------------------------------------------


def getInstance(instanceID=None, *args, **kwargs):
    """Get an instance of this class using a given instanceID.
    The instanceID is either the object or the object's id.

    Parameters:
            instanceID () = The instanceID can be any immutable type.
            args/kwargs () = The args to be passed to the class instance when it is created.

    Returns:
            (obj) An instance of this class.

    Example: tentacle = getInstance(id(0), key_show='Key_F12') #returns the class instance with an instance ID of the value of `id(0)`.
    """
    import inspect

    if instanceID is None:
        instanceID = inspect.stack()[1][3]
    try:
        return INSTANCES[instanceID]

    except KeyError:
        INSTANCES[instanceID] = TclMaya(*args, **kwargs)
        return INSTANCES[instanceID]


def show(instanceID=None, *args, **kwargs):
    """Expands `getInstance` to get and then show an instance in a single command."""
    inst = getInstance(instanceID=instanceID, *args, **kwargs)
    inst.show()


# --------------------------------------------------------------------------------------------

if __name__ == "__main__":
    main = TclMaya()
    main.show("init#startmenu")

    # run app, show window, wait for input, then terminate program with a status code returned from app.
    exit_code = main.app.exec_()
    if exit_code != -1:
        sys.exit(exit_code)

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
