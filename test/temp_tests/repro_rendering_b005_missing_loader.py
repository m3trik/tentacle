#!/usr/bin/python
# coding=utf-8
"""Minimal repro for Rendering.b005 missing loader bug.

Expected: b005 should call mayatk.vray_plugin(query/load) and proceed.
Actual (before fix): raises AttributeError for self.load_vray_plugin.
"""

from tentacle.slots.maya import rendering


class _FakeMel:
    def __init__(self):
        self.calls = []

    def eval(self, expression):
        self.calls.append(expression)


class _FakePm:
    def __init__(self):
        self.mel = _FakeMel()

    def ls(self, selection=False):
        if selection:
            return ["pCube1"]
        return []

    def listRelatives(self, obj, s=1, ni=1):
        return ["pCubeShape1"]

    def setAttr(self, attr, value):
        self.mel.calls.append(f"setAttr {attr} {value}")


class _FakeMtk:
    def __init__(self):
        self.query_called = False
        self.load_called = False

    def vray_plugin(self, load=False, unload=False, query=False):
        if query:
            self.query_called = True
            return False
        if load:
            self.load_called = True


def run_repro():
    instance = rendering.Rendering.__new__(rendering.Rendering)

    original_pm = rendering.pm
    original_mtk = rendering.mtk
    try:
        rendering.pm = _FakePm()
        rendering.mtk = _FakeMtk()
        instance.b005()
    finally:
        rendering.pm = original_pm
        rendering.mtk = original_mtk


if __name__ == "__main__":
    run_repro()
