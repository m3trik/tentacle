#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.rendering.

Bug history:
- Import guard did not define module-level pm when pymel import failed, causing
  AttributeError in headless environments.
- Rendering.b005 called self.load_vray_plugin(), but no such method exists.
  Correct behavior is to use mayatk.vray_plugin(query/load).

Fixed: 2026-02-20
"""

import unittest

from tentacle.slots.maya import rendering


class _FakeMel:
    def __init__(self):
        self.calls = []

    def eval(self, expression):
        self.calls.append(expression)


class _FakePm:
    def __init__(self):
        self.mel = _FakeMel()
        self.set_attr_calls = []

    def ls(self, selection=False):
        if selection:
            return ["pCube1"]
        return []

    def listRelatives(self, obj, s=1, ni=1):
        return ["pCubeShape1"]

    def setAttr(self, attr, value):
        self.set_attr_calls.append((attr, value))

    def sceneName(self):
        return ""


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


class TestRenderingHeadlessSafety(unittest.TestCase):
    def test_import_guard_defines_pm_placeholder(self):
        self.assertTrue(
            hasattr(rendering, "pm"),
            "rendering module should always define a pm name under import guard",
        )


class TestRenderingVrayAttributes(unittest.TestCase):
    def test_b005_uses_mayatk_vray_plugin(self):
        instance = rendering.Rendering.__new__(rendering.Rendering)

        original_pm = getattr(rendering, "pm", None)
        original_mtk = rendering.mtk
        fake_pm = _FakePm()
        fake_mtk = _FakeMtk()
        try:
            rendering.pm = fake_pm
            rendering.mtk = fake_mtk

            instance.b005()

            self.assertTrue(fake_mtk.query_called, "Expected VRay query call")
            self.assertTrue(fake_mtk.load_called, "Expected VRay load call")
            self.assertEqual(fake_pm.set_attr_calls, [("pCube1.vrayObjectID", 1)])
        finally:
            rendering.pm = original_pm
            rendering.mtk = original_mtk


if __name__ == "__main__":
    unittest.main()
