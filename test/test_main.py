#!/usr/bin/python
# coding=utf-8
"""Regression tests for tentacle.slots.main's directory walker.

The Workspace tab's dir browser is plain filesystem work in both hosts
(``MainSlots._populate_dir_sublist``): depth limiting, hidden-dir skipping and
OSError tolerance can silently break the panel. The tab's workspace flow is
pinned in ``test_main_workspace.py``.
"""
import os
import tempfile
import types
import unittest

from tentacle.slots.main import MainSlots


class _FakeItem:
    """Stand-in for the sublist item -- exposes a nested sublist for recursion."""

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


class TestPopulateDirSublist(unittest.TestCase):
    """MainSlots._populate_dir_sublist -- the directory tree walker for the browser."""

    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="main_dirwalker_")
        # root/
        #   visible_a/
        #     nested_x/
        #   visible_b/
        #   .hidden/
        os.makedirs(os.path.join(self.root, "visible_a", "nested_x"))
        os.makedirs(os.path.join(self.root, "visible_b"))
        os.makedirs(os.path.join(self.root, ".hidden"))

        # Bypass __init__, which needs a switchboard. The walker decorates every
        # row through the switchboard's IconManager (a real-QLabel operation), so a
        # stub records the calls instead and pins that access path.
        self.instance = MainSlots.__new__(MainSlots)
        self.icon_calls = []

        def record(item, name, *a, **k):
            self.icon_calls.append((item, name))

        self.instance.sb = types.SimpleNamespace(
            IconManager=types.SimpleNamespace(set_label_icon=record)
        )

    def tearDown(self):
        import shutil

        shutil.rmtree(self.root, ignore_errors=True)

    def test_lists_visible_directories(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        labels = sorted(i.label for i in sublist.items)
        self.assertEqual(labels, ["visible_a", "visible_b"])
        # Every dir row carries the filled-folder icon (the dir/action differentiator).
        iconed = [item for item, _ in self.icon_calls]
        self.assertTrue(all(i in iconed for i in sublist.items))
        self.assertTrue(all(n == "folder_filled" for _, n in self.icon_calls))

    def test_skips_hidden_directories(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=1)
        self.assertNotIn(".hidden", [i.label for i in sublist.items])

    def test_recurses_within_max_depth(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=2)
        visible_a = next(i for i in sublist.items if i.label == "visible_a")
        self.assertEqual([i.label for i in visible_a.sublist.items], ["nested_x"])

    def test_a_folder_without_sub_folders_gets_no_flyout(self):
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(sublist, self.root, max_depth=2)
        visible_b = next(i for i in sublist.items if i.label == "visible_b")
        self.assertEqual(visible_b.sublist.items, [])

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
        """An unreadable root must not raise -- the browser stays alive."""
        sublist = _FakeSublist()
        self.instance._populate_dir_sublist(
            sublist, os.path.join(self.root, "does_not_exist"), max_depth=2
        )
        self.assertEqual(sublist.items, [])

    def test_oserror_on_subdir_is_swallowed(self):
        """An unreadable child must not nuke the whole listing."""
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
            self.assertIn("visible_b", [i.label for i in sublist.items])
        finally:
            os.listdir = original_listdir


if __name__ == "__main__":
    unittest.main()
