# !/usr/bin/python
# coding=utf-8
"""The Find & Copy panel's plan table: what a Collect would do, row by row.

A dry run fills it with the host engine's plan (``plan_find_and_copy``, rows
of ``ptk.FileCollect.plan``): each texture node and lightmap, the file it
reads, where it would land and what happens to it. A row several different
same-named files could be has a picker in its Source cell; picking one
re-derives every destination through the one ``ptk.FileCollect.plan`` call (a
picked file may clash with another row's), and Apply commits :attr:`rows` --
exactly the plan on screen.

Private to :mod:`tentacle.slots.tools.texture_path_editor`.
"""

import os
from typing import Any, Dict, List

import pythontk as ptk
from qtpy import QtCore, QtWidgets


class CollectPlanTable:
    """The plan on screen, over a uitk ``TableWidget``.

    Parameters:
        table: The ``TableWidget`` the plan is shown in.
    """

    COLUMNS = ("Node", "Source", "Destination", "Status")
    SOURCE_COLUMN = 1
    #: The picker's first entry while no file is chosen.
    PICK = "Pick a file…"

    def __init__(self, table):
        self.table = table
        #: The plan rows on screen, picks applied: what Apply commits.
        self.rows: List[Dict[str, Any]] = []
        self.dest_dir = ""
        self.mode = "copy"
        self.choices: Dict[Any, str] = {}
        self.table.setVisible(False)

    @property
    def pending(self) -> bool:
        """Whether a row still waits for its file to be picked."""
        return any(r["status"] == ptk.FileCollect.AMBIGUOUS for r in self.rows)

    def show(self, rows, dest_dir: str, mode: str = "copy") -> None:
        """Show a fresh plan (a dry run's); earlier picks are dropped."""
        self.rows = [dict(r) for r in rows or []]
        self.dest_dir = dest_dir or ""
        self.mode = mode
        self.choices = {}
        self._fill()

    def pick(self, key, path: str) -> None:
        """Take *path* as the file of the row *key* names
        (``ptk.FileCollect.row_key``) and re-derive the plan around it."""
        if not path or path == self.PICK:
            return
        self.choices[key] = path
        self.rows = ptk.FileCollect.plan(self.rows, self.dest_dir, self.choices)
        self._fill()

    def clear(self) -> None:
        """Drop the plan: its scope or answers are no longer the panel's."""
        self.rows, self.choices = [], {}
        self.table.setRowCount(0)
        self.table.setVisible(False)

    # ------------------------------------------------------------------ cells
    def status_text(self, row) -> str:
        """What happens to *row*, in the panel's words."""
        Collect = ptk.FileCollect
        status = row["status"]
        if status == Collect.RELOCATE:
            text = "Move" if self.mode == "move" and not row.get("keep_source") else "Copy"
            return text + (f" — kept apart in {row['folder']}/" if row["folder"] else "")
        moved = self.mode == "move" and not row.get("keep_source")
        return {
            Collect.REUSE: "Reuse — the same file is there"
            + ("; the original is removed" if moved else ""),
            Collect.IN_PLACE: "In place",
            Collect.AMBIGUOUS: f"Pick one of {len(row['candidates'])} files",
            Collect.MISSING: "Not found — keeps its path",
            Collect.BLOCKED: "No free folder — left where it is",
        }.get(status, status)

    def destination_text(self, row) -> str:
        """Where *row* lands, relative to the destination when inside it."""
        destination = row.get("destination") or ""
        if not destination:
            return ""
        if self.dest_dir and ptk.FileUtils.is_under(destination, self.dest_dir):
            return os.path.relpath(destination, self.dest_dir).replace("\\", "/")
        return destination

    def _fill(self) -> None:
        table = self.table
        if not self.rows:
            self.clear()
            return
        table.add(
            [
                [
                    str(row["owner"]),
                    row.get("source") or "",
                    self.destination_text(row),
                    self.status_text(row),
                ]
                for row in self.rows
            ],
            headers=list(self.COLUMNS),
        )
        for index, row in enumerate(self.rows):
            for col in range(table.columnCount()):
                item = table.item(index, col)
                if item is not None:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
            if row.get("candidates"):
                table.setCellWidget(index, self.SOURCE_COLUMN, self._picker(row))
        table.resizeColumnsToContents()
        table.setVisible(True)

    def _picker(self, row) -> QtWidgets.QComboBox:
        """The Source cell of a row several files could be: its candidates."""
        combo = QtWidgets.QComboBox()
        combo.addItems([self.PICK, *row["candidates"]])
        combo.setToolTip(
            "Several different files carry this name -- pick the one this "
            "texture means. The plan is derived again around it."
        )
        if row["status"] != ptk.FileCollect.AMBIGUOUS and row.get("source"):
            combo.setCurrentText(row["source"])
        combo.currentTextChanged.connect(
            lambda path, key=ptk.FileCollect.row_key(row): QtCore.QTimer.singleShot(
                0, lambda: self.pick(key, path)
            )
        )
        return combo
