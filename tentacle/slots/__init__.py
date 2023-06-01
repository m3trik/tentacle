# !/usr/bin/python
# coding=utf-8
import sys, os.path
import inspect
from PySide2 import QtWidgets, QtCore
from pythontk import File, Iter, set_attributes


module = inspect.getmodule(inspect.currentframe())  # this module.
path = File.get_filepath(module)  # this modules directory.


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        """
        """
        self.sb = self.switchboard()

    def hideMain(fn):
        """A decorator that hides the stacked widget main window."""

        def wrapper(self, *args, **kwargs):
            fn(self, *args, **kwargs)  # execute the method normally.
            self.sb.parent().hide()  # Get the state of the widget in the current ui and set any widgets (having the methods name) in child or parent ui's accordingly.

        return wrapper

    def objAttrWindow(
        self, obj, checkable_label=False, fn=None, fn_args=[], **attributes
    ):
        """Launch a popup window containing the given objects attributes.

        Parameters:
                obj (obj): The object to get the attributes of.
                checkable_label (bool): Set the attribute labels as checkable.
                fn (method) = Set an alternative method to call on widget signal. ex. set_parameter_values
                                The first parameter of fn is always the given object. ex. fn(obj, {'attr':<value>})
                fn_args (list): Any additonal args to pass to fn.
                attributes (kwargs) = Explicitly pass in attribute:values pairs. Else, attributes will be pulled from mtk.Node.get_node_attributes for the given obj.

        Returns:
                (obj) the menu widget. (use menu.childWidgets to get the menu's child widgets.)

        Example: self.objAttrWindow(node, attrs, fn=mtk.set_parameter_values, fn_args='transformLimits')
        Example: self.objAttrWindow(transform[0], fn_args=['translateX','translateY','translateZ','rotateX','rotateY','rotateZ','scaleX','scaleY','scaleZ'], checkable_label=True)
        """
        import ast

        fn = fn if fn else set_attributes
        fn_args = Iter.make_list(fn_args)  # assure that fn_args is a list.

        try:  # get the objects name to as the window title:
            title = obj.name()
        except:
            try:
                title = obj.name
            except:
                title = str(obj)

        menu = self.sb.Menu(
            self.sb.parent(),
            menu_type="form",
            padding=2,
            title=title,
            position=(10, 125),
            alpha=0.01,
        )

        for a, v in attributes.items():
            if isinstance(v, (float, int, bool)):
                if type(v) == int or type(v) == bool:
                    s = menu.add(
                        "QSpinBox",
                        label=a,
                        checkable_label=checkable_label,
                        set_spinbox_by_value=v,
                    )

                elif type(v) == float:
                    v = float(
                        f"{v:g}"
                    )  ##remove any trailing zeros from the float value.
                    s = menu.add(
                        "QDoubleSpinBox",
                        label=a,
                        checkable_label=checkable_label,
                        set_spinbox_by_value=v,
                        setDecimals=3,
                    )

                s.valueChanged.connect(lambda v, a=a: fn(obj, *fn_args, **{a: v}))

            else:  # isinstance(v, (list, set, tuple)):
                w = menu.add(
                    "QLineEdit", label=a, checkable_label=checkable_label, setText=str(v)
                )
                w.returnPressed.connect(
                    lambda w=w, a=a: fn(
                        obj, *fn_args, **{a: ast.literal_eval(w.text())}
                    )
                )

        menu.show()

        return menu


# --------------------------------------------------------------------------------------------


# module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# depricated: -----------------------------------
