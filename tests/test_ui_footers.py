#!/usr/bin/python
# coding=utf-8
"""Regression guard for embedded Header/Footer widgets in tentacle UIs.

The invariant under test:

- Every top-level UI (anything that isn't a startmenu or submenu) must embed
  both a `<widget class="Header" name="header">` and a
  `<widget class="Footer" name="footer">` in its .ui file.
- Startmenu and submenu UIs must NOT embed either.

This locks in the design after the cross-cutting refactor that moved away
from MainWindow auto-creating a Footer at runtime. Embedding makes the
header/footer surface visible in Qt Designer and avoids tacking widgets
onto stacked sub-UIs that don't want them.
"""
from __future__ import annotations

import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

UI_DIR = Path(__file__).resolve().parent.parent / "tentacle" / "ui"


def _ui_files() -> list[Path]:
    return sorted(UI_DIR.glob("*.ui"))


def _classify(path: Path) -> str:
    """Return 'submenu', 'startmenu', or 'toplevel' based on filename."""
    stem = path.stem
    # Filenames look like "scene", "scene#submenu", "cameras#lower#submenu",
    # "cameras#startmenu". Anything containing the literal token decides it.
    parts = stem.split("#")
    if "submenu" in parts:
        return "submenu"
    if "startmenu" in parts:
        return "startmenu"
    return "toplevel"


def _has_named_widget(root: ET.Element, name: str, cls: str) -> bool:
    for w in root.iter("widget"):
        if w.get("name") == name and w.get("class") == cls:
            return True
    return False


class TestTentacleUIFooters(unittest.TestCase):
    """Embedded Header/Footer invariants for tentacle UIs."""

    @classmethod
    def setUpClass(cls):
        cls.files = _ui_files()
        if not cls.files:
            raise unittest.SkipTest(f"No UI files found in {UI_DIR}")
        cls.parsed = {p: ET.parse(p).getroot() for p in cls.files}

    def test_toplevel_uis_embed_header_and_footer(self):
        """Top-level UIs must declare both `header` and `footer` widgets.

        These were previously added by MainWindow at runtime; embedding makes
        them visible in Designer and survives any future MainWindow rewrites.
        """
        missing_header: list[str] = []
        missing_footer: list[str] = []
        for path, root in self.parsed.items():
            if _classify(path) != "toplevel":
                continue
            if not _has_named_widget(root, "header", "Header"):
                missing_header.append(path.name)
            if not _has_named_widget(root, "footer", "Footer"):
                missing_footer.append(path.name)

        self.assertEqual(
            missing_header,
            [],
            f"Top-level UIs missing embedded <widget class='Header'>: {missing_header}",
        )
        self.assertEqual(
            missing_footer,
            [],
            f"Top-level UIs missing embedded <widget class='Footer'>: {missing_footer}",
        )

    def test_submenu_and_startmenu_have_no_header_or_footer(self):
        """Stacked sub-UIs (startmenu/submenu) must NOT embed header or footer.

        These UIs are children of a parent MainWindow; their parent owns the
        footer. Embedding either here would double-render or steal layout.
        """
        offenders: list[str] = []
        for path, root in self.parsed.items():
            kind = _classify(path)
            if kind not in ("submenu", "startmenu"):
                continue
            if _has_named_widget(root, "header", "Header"):
                offenders.append(f"{path.name} (header)")
            if _has_named_widget(root, "footer", "Footer"):
                offenders.append(f"{path.name} (footer)")
        self.assertEqual(
            offenders,
            [],
            f"Sub-UIs must not embed header/footer: {offenders}",
        )

    def test_footer_customwidget_declared_when_used(self):
        """Any UI using <widget class='Footer'> must declare its <customwidget>.

        Without the customwidget entry, Qt's UI loader falls back to a plain
        QWidget, so the Footer's API and stylesheet hooks never fire.
        """
        offenders: list[str] = []
        for path, root in self.parsed.items():
            uses_footer = _has_named_widget(root, "footer", "Footer")
            if not uses_footer:
                continue
            declared = any(
                cw.findtext("class") == "Footer" for cw in root.iter("customwidget")
            )
            if not declared:
                offenders.append(path.name)
        self.assertEqual(
            offenders,
            [],
            f"Footer used but customwidget not declared: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
