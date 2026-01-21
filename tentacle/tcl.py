# !/usr/bin/python
# coding=utf-8
from uitk import MarkingMenu


class Tcl(MarkingMenu):
    """Tcl is a marking menu specific to the Tentacle application.
    It inherits from the generic MarkingMenu in uitk.
    """

    pass


if __name__ == "__main__":
    mm = Tcl(slot_source="slots/maya")
    mm.show("screen", app_exec=True)
