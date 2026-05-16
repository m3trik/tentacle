#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.utilities.

Utilities is a small slot — mostly mel passthroughs. The unit with
distinct value here is b002 (Calculator), which is the only handler
that drives a marking menu instead of mel.eval; pin its key name.
"""
import unittest

try:
    from tentacle.slots.maya import utilities as utilities_module

    _AVAILABLE = True
except ImportError:
    utilities_module = None
    _AVAILABLE = False


class _FakeMarkingMenu:
    def __init__(self):
        self.shown = []

    def show(self, name):
        self.shown.append(name)


class _FakeHandlers:
    def __init__(self):
        self.marking_menu = _FakeMarkingMenu()


class _FakeSb:
    def __init__(self):
        self.handlers = _FakeHandlers()


@unittest.skipUnless(_AVAILABLE, "Requires tentacle import path")
class TestB002Calculator(unittest.TestCase):
    """b002 (Calculator) is the only marking-menu-driven handler in utilities."""

    def test_b002_routes_to_calculator(self):
        instance = utilities_module.Utilities.__new__(utilities_module.Utilities)
        instance.sb = _FakeSb()
        instance.b002()
        self.assertEqual(instance.sb.handlers.marking_menu.shown, ["calculator"])


if __name__ == "__main__":
    unittest.main()
