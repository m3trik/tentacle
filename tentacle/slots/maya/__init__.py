# !/usr/bin/python
# coding=utf-8
try:
    import pymel.core as pm
except ImportError as error:
    print(__file__, error)
from tentacle.slots import Slots


class SlotsMaya(Slots):
    """App specific methods inherited by all other app specific slot classes."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


# --------------------------------------------------------------------------------------------


# module name
# print (__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------


# Deprecated: -------------------------------------
