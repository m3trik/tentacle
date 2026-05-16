#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.maya.main.

The bulk of Main is UI-coupled (Workspace Browser, signal-wired open
handler). The one piece of pure logic worth pinning is the recursive
directory walker that backs the browser tree — depth limiting, hidden-dir
skipping, and OSError tolerance can silently break the panel.
"""
import os
import tempfile
import unittest

try:
    import maya.cmds  # noqa: F401  — just to confirm runtime is mayapy
    from tentacle.slots.maya import main as main_module

    _MAYA_AVAILABLE = True
except ImportError:
    main_module = None
    _MAYA_AVAILABLE = False


class _FakeItem:
    """Stand-in for the sublist item — exposes a nested sublist for recursion."""

    def __init__(self, label, data):
        self.label = label
        self.data = data
        self.sublist = _FakeSublist()


class _FakeSublist:
    """Captures .add() calls; supplies a nested sublist on each item."""

    def __init__(self):
        self.items = []

    def add(self, label, data=None):
        item = _FakeItem(label, data)
        self.items.append(item)
        return item


@unittest.skipUnless(_MAYA_AVAILABLE, "Requires tentacle import path")
class TestPopulateDirSublist(unittest.TestCase):
    """Main._populate_dir_sublist — directory tree walker for the browser."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="main_dirwalker_")
        # Build:
        #   root/
        #     visible_a/
        #       nested_x/
        #     visible_b/
        #     .hidden/
        os.makedirs(os.path.join(self.root, "visible_a", "nested_x"))
        os.makedirs(os.path.join(self.root, "visible_b"))
        os.makedirs(os.path.join(self.root, ".hidden"))

        # Bypass __init__ which needs a switchboard.
        self.instance = main_module.Main.__new__(main_module.Main)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.root, ignore_errors=True)

    def test_lists_visible_directories(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        labels = sorted(i.label for i in sublist.items)
        self.assertEqual(labels, ["visible_a", "visible_b"])

    def test_skips_hidden_directories(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        labels = [i.label for i in sublist.items]
        self.assertNotIn(".hidden", labels)

    def test_recurses_within_max_depth(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=2)
        visible_a = next(i for i in sublist.items if i.label == "visible_a")
        nested_labels = [i.label for i in visible_a.sublist.items]
        self.assertEqual(nested_labels, ["nested_x"])

    def test_stops_recursion_at_max_depth(self):
        """max_depth=1 must not descend into visible_a/nested_x."""
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        visible_a = next(i for i in sublist.items if i.label == "visible_a")
        self.assertEqual(visible_a.sublist.items, [])

    def test_stores_full_path_as_data(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        visible_a = next(i for i in sublist.items if i.label == "visible_a")
        self.assertEqual(visible_a.data, os.path.join(self.root, "visible_a"))

    def test_oserror_on_root_is_swallowed(self):
        """Unreadable root must not raise — browser stays alive."""
        sublist = _FakeSublist()
        # Non-existent path triggers OSError inside the try.
        self.instance._populate_dir_sublist(
            sublist, os.path.join(self.root, "does_not_exist"), max_depth=2
        )
        self.assertEqual(sublist.items, [])

    def test_oserror_on_subdir_is_swallowed(self):
        """An unreadable child must not nuke the whole listing."""
        # Make visible_b have a child that's a file (not a dir) named like a dir
        # would be — we then point the recursion at a path that will OSError.
        # Easier: monkey-patch os.listdir to fail on one specific subdir.
        original_listdir = os.listdir

        bad_path = os.path.join(self.root, "visible_a")

        def selective_listdir(path):
            if path == bad_path:
                raise OSError("simulated permission error")
            return original_listdir(path)

        os.listdir = selective_listdir
        try:
            sublist = _FakeSublist()
            self.instance._populate_dir_sublist(sublist, self.root, max_depth=2)
            # visible_b should still be listed even though visible_a OSError'd
            labels = [i.label for i in sublist.items]
            self.assertIn("visible_b", labels)
        finally:
            os.listdir = original_listdir


if __name__ == "__main__":
    unittest.main()
