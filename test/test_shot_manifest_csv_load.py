#!/usr/bin/python
# coding=utf-8
"""Regression tests for the Shot Manifest controller's ``_load_csv`` failures.

Covers the bug where a failed CSV load (missing file, unreadable cloud
placeholder, or malformed CSV) returned early *before* enabling the CSV
path widgets -- leaving the field disabled so the user could neither
inspect nor correct the bad path -- and a URL source: it skips the
file-exists gate, and a fetch failure is reported as a fetch failure.

Needs Qt, no host: ``_load_csv`` is exercised as an unbound method against a
stub ``self`` so no Qt window / switchboard construction is required.
"""

import os
import types
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pythontk as ptk  # noqa: E402
from pythontk import ColumnMap, TooltipFormat  # noqa: E402

from tentacle.slots.tools._shot_manifest.controller import (  # noqa: E402
    ShotManifestController,
)

# Where _load_csv lives (and reads ManifestModel from).
_SOURCE = "tentacle.slots.tools._shot_manifest.manifest_source"


def _make_stub_controller():
    """A stub carrying only the collaborators ``_load_csv`` touches."""
    ctrl = types.SimpleNamespace()
    ctrl._set_footer = MagicMock()
    ctrl._load_data = MagicMock()
    ctrl._refresh_ranges = MagicMock()
    ctrl._fill_missing_assets = MagicMock()
    ctrl._recent_csv_option = MagicMock()
    # The controller's MappingPickerMixin hook: the scene's template and
    # options for this sheet, applied before the parse.
    ctrl._adopt_sheet_options = MagicMock()
    # ...and its undo when the sheet does not load.
    ctrl._sheet_read_state = MagicMock(return_value=())
    ctrl._restore_sheet_read_state = MagicMock()
    ctrl._active_mapping = None
    ctrl._column_map = ColumnMap()
    ctrl._csv_path = ""
    ctrl.logger = MagicMock()
    ctrl.ui = MagicMock()
    # _load_csv delegates its OSError message to this static method; bind the
    # real one so the stub exercises the genuine diagnosis.
    ctrl._describe_read_failure = ShotManifestController._describe_read_failure
    # The tooltip/invalid helpers are plain methods; bind the real ones so the
    # stub renders genuine uitk-formatted tooltips.
    ctrl.sb = types.SimpleNamespace(tooltip=TooltipFormat)
    ctrl._csv_source_tooltip = lambda problem=None: (
        ShotManifestController._csv_source_tooltip(ctrl, problem)
    )
    ctrl._mark_csv_invalid = lambda reason: ShotManifestController._mark_csv_invalid(
        ctrl, reason
    )
    ctrl._drop_excluded = lambda steps: ShotManifestController._drop_excluded(
        ctrl, steps
    )
    return ctrl


class LoadCsvFailureTest(unittest.TestCase):
    """Every _load_csv failure path must leave the field usable."""

    def test_missing_file_leaves_the_field_usable(self):
        """A non-existent path is reported on the field and returns False."""
        ctrl = _make_stub_controller()
        ok = ShotManifestController._load_csv(ctrl, "X:/no/such/file.csv")

        self.assertFalse(ok)
        ctrl._load_data.assert_not_called()
        ctrl.ui.txt_csv_path.set_action_color.assert_called_with("invalid")

    def test_unreadable_oserror_leaves_the_field_usable(self):
        """An OSError on read (e.g. errno 22) is reported, not loaded."""
        ctrl = _make_stub_controller()
        with (
            patch("os.path.isfile", return_value=True),
            patch("pythontk.FileUtils.free_space", return_value=None),
            patch(
                f"{_SOURCE}.ManifestModel.parse_csv",
                side_effect=OSError(22, "Invalid argument"),
            ),
        ):
            ok = ShotManifestController._load_csv(ctrl, "X:/cloud/only.csv")

        self.assertFalse(ok)
        ctrl._load_data.assert_not_called()
        ctrl.ui.txt_csv_path.set_action_color.assert_called_with("invalid")

    def test_malformed_csv_still_leaves_the_field_usable(self):
        """A non-OSError parse failure is reported, not loaded."""
        ctrl = _make_stub_controller()
        with (
            patch("os.path.isfile", return_value=True),
            patch(
                f"{_SOURCE}.ManifestModel.parse_csv",
                side_effect=ValueError("bad header"),
            ),
        ):
            ok = ShotManifestController._load_csv(ctrl, "X:/data/bad.csv")

        self.assertFalse(ok)
        ctrl._load_data.assert_not_called()


class LoadCsvNoStepsTest(unittest.TestCase):
    """A sheet the template reads no step of is not loaded: it says why on
    the field, and nothing stands in for it (2026-10-11: a production sheet read
    as 0 steps under a ``classic`` Step IDs choice, and Assess detected the
    scene's animation over it)."""

    def test_a_sheet_reading_no_steps_is_reported_not_loaded(self):
        ctrl = _make_stub_controller()
        with (
            patch("os.path.isfile", return_value=True),
            patch(f"{_SOURCE}.ManifestModel.parse_csv", return_value=[]),
        ):
            ok = ShotManifestController._load_csv(ctrl, "X:/docs/sheet.csv")

        self.assertFalse(ok)
        ctrl._load_data.assert_not_called()
        ctrl.ui.txt_csv_path.set_action_color.assert_called_with("invalid")
        self.assertIn("Step IDs", ctrl._set_footer.call_args.args[0])

    def test_a_sheet_whose_steps_are_all_excluded_still_loads(self):
        """The context menu's exclusions are the user's, not a misread sheet:
        such a sheet loads (empty), its field never blamed on Step IDs."""
        ctrl = _make_stub_controller()
        ctrl._column_map = ColumnMap(exclude_steps=("A01",))
        steps = [ptk.BuilderStep("A01", "A", "Doors", "d")]
        with (
            patch("os.path.isfile", return_value=True),
            patch(f"{_SOURCE}.ManifestModel.parse_csv", return_value=steps),
        ):
            ok = ShotManifestController._load_csv(ctrl, "X:/docs/sheet.csv")

        self.assertTrue(ok)
        self.assertEqual(ctrl._load_data.call_args.args[0], [])
        ctrl.ui.txt_csv_path.set_action_color.assert_not_called()

    @staticmethod
    def _ensure_ctrl(field_text, source=""):
        ctrl = types.SimpleNamespace()
        ctrl._steps = []
        ctrl._populate_from_source = MagicMock()  # loads nothing
        ctrl.detect = MagicMock()
        ctrl._set_footer = MagicMock()
        ctrl.logger = MagicMock()
        ctrl.ui = MagicMock()
        ctrl.ui.txt_csv_path.text.return_value = field_text
        ctrl._source = source
        ctrl._sheet_steps = []  # the sheet's own steps, before Local Edits
        return ctrl

    def test_assess_never_detects_over_a_named_sheet(self):
        ctrl = self._ensure_ctrl("X:/docs/sheet.csv")
        self.assertFalse(ShotManifestController._ensure_steps(ctrl))
        ctrl.detect.assert_not_called()
        self.assertIn("did not load", ctrl._set_footer.call_args.args[0])

    def test_a_loaded_sheet_with_every_step_excluded_says_so(self):
        ctrl = self._ensure_ctrl("X:/docs/sheet.csv", source="csv")
        self.assertFalse(ShotManifestController._ensure_steps(ctrl))
        ctrl.detect.assert_not_called()
        self.assertIn("excluded", ctrl._set_footer.call_args.args[0])

    def test_a_loaded_sheet_with_every_step_hidden_says_so(self):
        """Local Edits hid every step the sheet has: "excluded" sent the user
        to the context menu's exclusions, which hold none of them."""
        ctrl = self._ensure_ctrl("X:/docs/sheet.csv", source="csv")
        ctrl._sheet_steps = [ptk.BuilderStep("A01", "A", "Doors", "d")]
        self.assertFalse(ShotManifestController._ensure_steps(ctrl))
        self.assertIn("hidden", ctrl._set_footer.call_args.args[0])

    def test_an_empty_field_still_detects(self):
        ctrl = self._ensure_ctrl("")
        ShotManifestController._ensure_steps(ctrl)
        ctrl.detect.assert_called_once()


class LoadCsvUrlSourceTest(unittest.TestCase):
    """A URL is a CSV source: it skips the file gate, and a fetch failure is
    reported as a fetch failure, never as the local disk/sync diagnosis."""

    _URL = "https://docs.google.com/spreadsheets/d/1AbC/edit#gid=0"

    def test_url_skips_the_file_gate_and_loads(self):
        ctrl = _make_stub_controller()
        steps = [ptk.BuilderStep("A01", "A", "Doors", "d")]
        with patch(f"{_SOURCE}.ManifestModel.parse_csv", return_value=steps) as parse:
            ShotManifestController._load_csv(ctrl, self._URL)

        self.assertEqual(parse.call_args.args[0], self._URL)
        ctrl._load_data.assert_called_once()
        ctrl.ui.txt_csv_path.reset_action_color.assert_called_once()

    def test_fetch_failure_reports_the_fetch_not_the_disk(self):
        ctrl = _make_stub_controller()
        err = ptk.RemoteFile.Error("Can't fetch https://x: HTTP 404 Not Found.")
        with patch(f"{_SOURCE}.ManifestModel.parse_csv", side_effect=err):
            ok = ShotManifestController._load_csv(ctrl, self._URL)

        self.assertFalse(ok)
        ctrl._load_data.assert_not_called()
        ctrl.ui.txt_csv_path.set_action_color.assert_called_with("invalid")
        msg = ctrl._set_footer.call_args.args[0].lower()
        self.assertIn("can't fetch", msg)
        self.assertNotIn("disk may be full", msg)

    def test_fetch_failure_reason_reaches_the_tooltip_too(self):
        ctrl = _make_stub_controller()
        err = ptk.RemoteFile.Error("Can't fetch https://x: HTTP 404 Not Found.")
        with patch(f"{_SOURCE}.ManifestModel.parse_csv", side_effect=err):
            ShotManifestController._load_csv(ctrl, self._URL)

        tip = ctrl.ui.txt_csv_path.setToolTip.call_args.args[0]
        self.assertIn("HTTP 404", tip)
        self.assertIn("CSV Source", tip)


class DescribeReadFailureTest(unittest.TestCase):
    """The read-failure message names a checkable cause, never guesses one.

    Regression for a misdiagnosis: the old message asserted "online-only
    cloud file, make it available offline", which is usually wrong (cloud
    files hydrate on demand) and useless when the real cause is a full disk.
    """

    @staticmethod
    def _describe(path, *, free, placeholder):
        exc = OSError(22, "Invalid argument")
        with (
            patch("pythontk.FileUtils.free_space", return_value=free),
            patch("pythontk.FileUtils.is_cloud_placeholder", return_value=placeholder),
        ):
            return ShotManifestController._describe_read_failure(path, exc).lower()

    def test_low_disk_surfaces_free_space_figure(self):
        """Low free space appends the actual figure (a fact, not an assertion)."""
        msg = self._describe("X:/seq/m.csv", free=786 * 1024 * 1024, placeholder=True)
        # Pin the converted figure + drive, not just the literal "MB free" (that
        # is in the format string regardless, so it wouldn't catch a unit bug).
        self.assertIn("786 mb free", msg)
        self.assertIn("x:", msg)
        self.assertIn("disk may be full", msg)  # still enumerated, not asserted
        # Must NOT revert to the old "make available offline" misdiagnosis.
        self.assertNotIn("available offline", msg)

    def test_cloud_file_includes_sync_client_cause(self):
        """A cloud file lists the sync client among the causes, not 'offline'."""
        msg = self._describe("X:/seq/m.csv", free=10 * 1024**3, placeholder=True)
        self.assertIn("cloud", msg)
        self.assertIn("sync", msg)
        self.assertNotIn("available offline", msg)
        self.assertNotIn("mb free", msg)  # ample space -> no figure appended

    def test_local_file_omits_cloud_cause(self):
        """A local file with ample space enumerates causes without the cloud one."""
        msg = self._describe("C:/local/m.csv", free=10 * 1024**3, placeholder=False)
        self.assertIn("disk may be full", msg)
        self.assertNotIn("cloud", msg)
        self.assertNotIn("mb free", msg)

    def test_unknown_free_space_still_explains(self):
        """When free space can't be queried (None), it still returns a message."""
        msg = self._describe("C:/local/m.csv", free=None, placeholder=False)
        self.assertIn("disk", msg)
        self.assertNotIn("mb free", msg)


class CsvPathEditingTest(unittest.TestCase):
    """Committing a typed/pasted path loads it (editable-field support)."""

    @staticmethod
    def _ctrl(*, text, csv_path=""):
        ctrl = types.SimpleNamespace()
        ctrl._load_csv = MagicMock()
        ctrl._on_csv_browsed = MagicMock()
        ctrl._csv_path = csv_path
        ctrl.ui = MagicMock()
        ctrl.ui.txt_csv_path.text.return_value = text
        return ctrl

    def test_valid_changed_path_loads(self):
        ctrl = self._ctrl(text="X:/seq/new.csv", csv_path="X:/old.csv")
        ShotManifestController._on_csv_path_edited(ctrl)
        ctrl._load_csv.assert_called_once_with("X:/seq/new.csv")

    def test_unchanged_path_does_not_reload(self):
        ctrl = self._ctrl(text="X:/same.csv", csv_path="X:/same.csv")
        ShotManifestController._on_csv_path_edited(ctrl)
        ctrl._load_csv.assert_not_called()

    def test_empty_path_does_nothing(self):
        ctrl = self._ctrl(text="   ", csv_path="")
        ShotManifestController._on_csv_path_edited(ctrl)
        ctrl._load_csv.assert_not_called()

    def test_changed_path_delegates_to_load(self):
        """Any changed path is handed to _load_csv (the authority on validity),
        which reports a missing file / cloud error itself."""
        ctrl = self._ctrl(text="X:/missing.csv", csv_path="")
        ShotManifestController._on_csv_path_edited(ctrl)
        ctrl._load_csv.assert_called_once_with("X:/missing.csv")

    def test_pasted_path_is_stripped(self):
        """Surrounding whitespace (common when pasting) is stripped before load."""
        ctrl = self._ctrl(text="  X:/seq/new.csv  ", csv_path="")
        ShotManifestController._on_csv_path_edited(ctrl)
        ctrl._load_csv.assert_called_once_with("X:/seq/new.csv")

    def test_recent_selection_loads(self):
        """Picking a path from the recent list loads it via _on_csv_browsed."""
        ctrl = self._ctrl(text="X:/recent.csv", csv_path="")
        ShotManifestController._on_csv_recent_selected(ctrl, "X:/recent.csv")
        ctrl._on_csv_browsed.assert_called_once_with("X:/recent.csv")


if __name__ == "__main__":
    unittest.main(exit=False)
