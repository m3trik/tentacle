# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest's Export button (beside Assess): a live preview of the
export -- the manifest's rows, those the table shows or the selected ones, as
CSV, JSON or Markdown (``pythontk.ManifestExport``) -- with its options beside
the text, which renders again as each is set; then Copy, or Save As a file.
What a row says is what the table says: Local Edits applied, the names read
from a step's text or filled from the scene, the frames, and the status an
Assess gave.  While it is open the preview follows the table.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

import os
from typing import Any, Dict, List

from pythontk import BuilderStep, ManifestExport

from .manifest_data import ERROR_COLOR


class ExportPreviewMixin:
    """The Export button's preview, mixed into ``ShotManifestController``.

    Uses the controller's ``ui`` (``b004``, ``tbl_steps``), ``sb``,
    ``_settings``, ``_steps``, ``_csv_path``, ``_last_results``,
    ``_last_resolved``, ``_use_short_names``, ``_rows()`` and
    ``_set_footer()``.
    """

    #: Each option's choices: ``(label, value, tooltip)``.
    EXPORT_CHOICES = {
        "format": (
            ("CSV", "csv", "A spreadsheet: Excel, Google Sheets."),
            ("JSON", "json", "Each row whole, for a script or a pipeline."),
            ("Markdown", "markdown", "A table for a review, a ticket or a chat."),
        ),
        "rows": (
            ("Shown", "shown", "Every row the table shows."),
            ("Selected", "selected", "The selected rows (an object row: its step)."),
        ),
        "objects": (
            (
                "A Row Each",
                "rows",
                "Each object on a row of its own, its step's cells on the first "
                "-- as a sheet lists them.",
            ),
            ("One Cell", "cell", "One row per step, its objects a line each."),
        ),
    }
    #: What each option is, for its tooltip.
    EXPORT_HINTS = {
        "format": "What the export is written as.",
        "rows": "Which rows go.",
        "objects": "How a step's objects are laid out in CSV and Markdown.",
        "columns": "Which columns go, in this order.",
    }
    #: The options as a new user finds them.
    EXPORT_DEFAULTS = {
        "format": "csv",
        "rows": "shown",
        "objects": "rows",
        "columns": [k for k, _h in ManifestExport.COLUMNS if k != "voice"],
    }
    #: What the export says with no steps to export.
    _NOTHING_LOADED = "Nothing to export: load a sheet, or the scene's shots."
    #: The open preview (``sb.preview_dialog``), else ``None``.
    _export_preview = None
    #: ``(records, problem)`` the preview's text last rendered.
    _export_shown = ([], "")

    def _setup_export_button(self) -> None:
        """Say on the Export button what a click does, and keep an open
        preview of the selected rows on the table's selection."""
        btn = getattr(self.ui, "b004", None)
        if btn is not None:
            btn.setToolTip(
                "Preview the export: set its format, rows, object layout and\n"
                "columns beside the text it gives, then Copy it or Save it As\n"
                "a file."
            )
        self.ui.tbl_steps.itemSelectionChanged.connect(self._on_steps_selected)

    def _on_steps_selected(self) -> None:
        """The table's selection changed: an open preview of the SELECTED
        rows renders again; one of every row shown has nothing new to show."""
        if (
            self._shown_export_preview() is not None
            and self._export_options()["rows"] == "selected"
        ):
            self._refresh_export_preview()

    def _export_specs(self) -> List[Dict[str, Any]]:
        """The preview's option rows: Format, Rows, Objects and Columns."""
        choices = dict(self.EXPORT_CHOICES)
        choices["columns"] = tuple((h, k) for k, h in ManifestExport.COLUMNS)
        return [
            {
                "key": key,
                "label": label,
                "kind": "check_list" if key == "columns" else "choice",
                "choices": choices[key],
                "tooltip": self.EXPORT_HINTS[key],
            }
            for key, label in (
                ("format", "Format"),
                ("rows", "Rows"),
                ("objects", "Objects"),
                ("columns", "Columns"),
            )
        ]

    def _export_options(self) -> Dict[str, Any]:
        """The Export options, a saved value that is no longer a choice
        replaced by its default."""
        saved = self._settings.value("export_options", {})
        if not isinstance(saved, dict):
            saved = {}
        options = dict(
            self.EXPORT_DEFAULTS, columns=list(self.EXPORT_DEFAULTS["columns"])
        )
        for key, entries in self.EXPORT_CHOICES.items():
            if saved.get(key) in {value for _l, value, _t in entries}:
                options[key] = saved[key]
        if isinstance(saved.get("columns"), list):
            options["columns"] = ManifestExport.columns(saved["columns"])
        return options

    def _set_export_option(self, key: str, value) -> None:
        """Keep one Export option (per user, for every scene)."""
        options = self._export_options()
        options[key] = list(value) if key == "columns" else value
        self._settings.setValue("export_options", options)  # stored as JSON
        self._sync_export_widgets()

    def _shown_export_preview(self):
        """The open preview, or ``None``: none made, closed, or gone with the
        panel's window."""
        preview = self._export_preview
        try:
            return preview if preview is not None and preview.isVisible() else None
        except RuntimeError:  # its C++ side went with its window
            self._export_preview = None
            return None

    def _sync_export_widgets(self) -> None:
        """JSON lays no objects out: its Objects row greys out."""
        preview = self._shown_export_preview()
        if preview is None:
            return
        widget = preview.preview_widgets.get("objects")
        if widget is not None:
            widget.setEnabled(self._export_options()["format"] != "json")

    @classmethod
    def _export_label(cls, fmt: str) -> str:
        """``"csv"`` -> ``"CSV"``."""
        return next(label for label, v, _t in cls.EXPORT_CHOICES["format"] if v == fmt)

    def _export_rows(self, which: str) -> list:
        """The table's ``(step, shot)`` rows, all of them or the selected ones
        (an object row selects its step's row)."""
        from qtpy.QtCore import Qt

        rows = self._rows()
        if which != "selected":
            return rows
        picked = set()
        for item in self.ui.tbl_steps.selectedItems():
            row = item.parent() if item.parent() is not None else item
            data = row.data(0, Qt.UserRole)
            if isinstance(data, BuilderStep):
                picked.add(("step", data.step_id))
            elif getattr(data, "shot_id", None) is not None:
                picked.add(("shot", data.shot_id))
        return [
            (step, shot)
            for step, shot in rows
            if (("step", step.step_id) if step is not None else ("shot", shot.shot_id))
            in picked
        ]

    def _export_records(self, rows: list) -> List[Dict[str, Any]]:
        """*rows* as the table shows them: the frames it shows a step with no
        shot at, the showing assessment's statuses, its object names."""
        return ManifestExport.records(
            rows,
            ranges={sid: (s, e) for sid, s, e, _user in self._last_resolved},
            statuses={r.step_id: r.status for r in self._last_results},
            object_name=self.manifest_host.leaf_name if self._use_short_names else None,
        )

    def _export_plan(self, options: Dict[str, Any]):
        """``(records, problem)`` for *options*: the records that would go,
        or ``[]`` and why nothing would."""
        if not self._steps:
            return [], self._NOTHING_LOADED
        if not options["columns"]:
            return [], "Nothing to export: tick a column."
        rows = self._export_rows(options["rows"])
        if not rows:
            return [], (
                "Nothing to export: select the rows to export in the table, or "
                "set Rows to Shown."
            )
        return self._export_records(rows), ""

    def _render_export(self, options: Dict[str, Any]) -> str:
        """The text *options* export -- what the preview shows -- or why
        nothing would go.  Keeps the plan for :meth:`_export_status`, which
        the preview asks next."""
        records, problem = self._export_shown = self._export_plan(options)
        if problem:
            return problem
        return ManifestExport.render(
            records, options["format"], options["columns"], options["objects"]
        )

    def _export_status(self, options: Dict[str, Any], _text: str) -> str:
        """The preview's footer: how many rows the text just rendered holds,
        as what."""
        records, problem = self._export_shown
        if problem:
            return "Nothing to export."
        return f"{len(records)} rows as {self._export_label(options['format'])}."

    def export(self) -> None:
        """Open the preview of the export (or bring the open one up): its
        options beside the text they give, then Copy or Save As."""
        if not self._steps:
            self._set_footer(self._NOTHING_LOADED, color=ERROR_COLOR)
            return
        preview = self._shown_export_preview()
        if preview is not None:
            preview.refresh_preview()
            preview.present()
            return
        if self._export_preview is not None:
            try:
                self._export_preview.deleteLater()  # closed: a new one is made
            except RuntimeError:
                pass
        self._export_preview = self.sb.preview_dialog(
            self._render_export,
            self._export_specs(),
            values=self._export_options(),
            on_change=self._set_export_option,
            actions={
                "Copy": lambda _preview: self._export_copy(),
                "SaveAs": lambda _preview: self._export_save(),
            },
            status=self._export_status,
            title="Export the Shot Manifest",
            parent=self.ui,
        )
        self._sync_export_widgets()

    def _refresh_export_preview(self) -> None:
        """Render an open preview again: the rows it shows changed."""
        preview = self._shown_export_preview()
        if preview is not None:
            preview.refresh_preview()

    def _export_done(self, message: str, error: bool = False) -> None:
        """Say *message* in the panel's footer and an open preview's."""
        self._set_footer(message, color=ERROR_COLOR if error else "")
        preview = self._shown_export_preview()
        if preview is not None:
            preview.footer.setText(message)

    def _export_copy(self) -> None:
        """Copy the export as the options say."""
        options = self._export_options()
        records, problem = self._export_plan(options)
        if problem:
            self._export_done(problem, error=True)
            return
        fmt = options["format"]
        self._export_to_clipboard(records, fmt, options["columns"], options["objects"])
        paste = " -- paste it into a spreadsheet" if fmt == "csv" else ""
        self._export_done(
            f"Copied {len(records)} rows as {self._export_label(fmt)}{paste}."
        )

    def _export_save(self) -> None:
        """Save the export, as the options say, to a file the user picks."""
        options = self._export_options()
        records, problem = self._export_plan(options)
        if problem:
            self._export_done(problem, error=True)
            return
        path = self._export_path(options["format"])
        if not path:
            return
        try:
            ManifestExport.write(path, records, options["columns"], options["objects"])
        except (OSError, ValueError) as exc:
            self._export_done(f"Couldn't export: {exc}", error=True)
            return
        self._settings.setValue("export_dir", os.path.dirname(path))
        self._export_done(f"Exported {len(records)} rows to {os.path.basename(path)}.")

    def _export_to_clipboard(self, records, fmt, columns, layout) -> None:
        """Put *records* on the clipboard: CSV as a table a spreadsheet pastes
        (HTML, with tab-separated text), the others as their text."""
        from qtpy.QtCore import QMimeData
        from qtpy.QtWidgets import QApplication

        if fmt != "csv":
            text = ManifestExport.render(records, fmt, columns, layout)
            QApplication.clipboard().setText(text)
            return
        tsv, html = ManifestExport.clipboard(
            ManifestExport.table(records, columns, layout)
        )
        mime = QMimeData()
        mime.setText(tsv)
        mime.setHtml(html)
        QApplication.clipboard().setMimeData(mime)

    def _export_path(self, fmt: str) -> str:
        """Ask where to save a *fmt* export ("" if cancelled): beside the last
        export, else the sheet, named after the sheet.  The loaded sheet
        itself is refused -- the manifest never writes it."""
        ext = ManifestExport.FORMATS[fmt]
        sheet = self._csv_path if os.path.isfile(self._csv_path or "") else ""
        stem = os.path.splitext(os.path.basename(sheet))[0] if sheet else "shot"
        folder = self._settings.value("export_dir", "") or os.path.dirname(sheet)
        path = self.sb.save_file_dialog(
            file_types=[f"*{ext}"],
            title="Export the Shot Manifest",
            start_dir=os.path.join(folder, f"{stem}_manifest{ext}"),
            filter_description=f"{self._export_label(fmt)} Files",
        )
        if not path:
            return ""
        if ManifestExport.format_of(path) != fmt:
            path += ext
        if sheet and os.path.normcase(os.path.abspath(path)) == os.path.normcase(
            os.path.abspath(sheet)
        ):
            self._export_done(
                "That is the loaded sheet: the manifest never writes it -- "
                "export under another name.",
                error=True,
            )
            return ""
        return path
