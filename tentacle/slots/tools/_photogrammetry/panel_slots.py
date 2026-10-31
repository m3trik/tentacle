# !/usr/bin/python
# coding=utf-8
"""Shared scaffolding for the photogrammetry workflow panels.

Metashape, RealityCapture, and Brush all present the *same* panel shape — a
:class:`uitk.bridge.BridgeSlotsBase` with a Project-Name row, an engine-specific
input row, a run-mode combo, semantic presets shared with the headless CLI, an
Output-Root row, a header menu (Cancel / Open Output Folder / Clear Log + help),
and an async ``b000`` that streams a long bake into the log pane. That common
~70% lives here so each engine's slots stay thin and can't drift apart:

* :class:`PhotogrammetryPanelSlots` — the base. A subclass declares a few class
  attrs (engine label, preset scope, output-dir copy) and supplies the engine
  hooks: :meth:`make_bridge`, :attr:`params_module`, :meth:`default_output_dir`,
  :meth:`list_template_modes`, :meth:`_build_source_rows` +
  :meth:`_resolve_input_argv` (its input row), :meth:`help_spec`, and optionally
  :meth:`_mode_argv` (extra ``--stop-after`` / ``--publish`` flags).
* :class:`FramesSourceMixin` — the frames/video "Source" row + single browser
  shared by the two photogrammetry (image-in) panels (Metashape, RealityCapture).
  Brush takes a COLMAP dir instead, so it doesn't use this mixin.
"""
from __future__ import annotations

import os
import traceback
from typing import List, Optional

from extapps import DOCS_BASE_URL, IMAGE_EXTS, Profile
from qtpy import QtCore, QtGui, QtWidgets

from tentacle import Slots

from .shared_parameters import PREPROCESS_MASTER_KEY, PREPROCESSING_KNOB_KEYS

# File-dialog patterns for the frames/video Source browser. Videos extract to
# frames; images mean "use this existing frames folder".
_VIDEO_EXTS = ["*.mp4", "*.avi", "*.mov", "*.mkv", "*.wmv", "*.flv", "*.m4v"]
_IMAGE_EXTS = [f"*{e}" for e in IMAGE_EXTS]
# Lowercase suffixes for routing a picked file by type (derived from the dialog
# patterns so the two can't drift apart).
_VIDEO_SUFFIXES = tuple(p.lstrip("*").lower() for p in _VIDEO_EXTS)


class PhotogrammetryPanelSlots(Slots.BridgeSlotsBase):
    """Base for the photogrammetry workflow panels (engine-agnostic scaffolding)."""

    # --- engine identity / copy (subclasses override) -----------------------
    ENGINE_LABEL = "Engine"           # human name used in log lines
    PRESET_ENGINE = ""                # preset_store scope ("metashape", ...)
    MISSING_ENGINE_MESSAGE = "Engine executable not found."
    NAME_PLACEHOLDER = "(basename for the project + outputs)"
    NAME_TOOLTIP = "Project basename (--name). Outputs land in <output-root>/<name>/."
    OUTPUT_FOLDER_TOOLTIP = "Open <output-root>/<name>/ — this run's outputs land here."
    # mode value -> one-line description logged when the run-mode combo changes.
    MODE_DESC: dict = {}

    # Docs link logged at panel open (see BridgeSlotsBase._show_docs_link).
    # TUNING.md is the one page all three engines share -- the noise-control
    # levers, where each lives (CLI-reachable vs GUI-only), and the shipped
    # presets -- so it is the base's default; an engine with a page of its own
    # (Metashape) overrides.
    DOCS_URL = DOCS_BASE_URL + "extapps/photogrammetry/TUNING.md"
    DOCS_LABEL = "Tuning guide + shipped presets (TUNING.md)"

    PRESETS_ROOT = None  # semantic presets supply their own dirs via the store

    def __init__(self, switchboard, **kwargs):
        self._initial_name: str = kwargs.get("project_name", "") or ""
        self._name_edit: Optional[QtWidgets.QLineEdit] = None
        # Output folder captured at launch, so "Open Output Folder" / the
        # completion log point at the run that actually ran even if the Name /
        # Output Root fields are edited afterward.
        self._last_output_dir: str = ""
        self._init_inputs(kwargs)
        super().__init__(switchboard)
        self._build_input_rows()
        self._wire_preprocess_master()
        self._log_availability()

    # ------------------------------------------------------------------ hooks
    def _init_inputs(self, kwargs) -> None:
        """Capture any input-field initial values from *kwargs* (subclass)."""

    def _build_source_rows(self) -> None:
        """Insert the engine's input row(s) at the top of grp_process (subclass)."""
        raise NotImplementedError

    def _resolve_input_argv(self) -> Optional[List[str]]:
        """Validate the input field(s); return the argv fragment (e.g.
        ``["--frames-dir", path]``) or ``None`` after logging an error."""
        raise NotImplementedError

    # Run-mode token shared by the image-in panels: dry-run the input curation
    # (``--curate-preview``) instead of reconstructing. Both runners accept the
    # flag; the Metashape runner routes it to the panel's venv (metashape.exe's
    # bundled Python has no cv2).
    PREP_PREVIEW_MODE = "prep_preview"

    def _mode_argv(self) -> List[str]:
        """Extra flags from the run-mode combo (``--stop-after`` / ``--publish``
        / the shared curation-preview mode). Default: preview only."""
        pair = self._selected_template_mode()
        if pair and pair[1] == self.PREP_PREVIEW_MODE:
            return ["--curate-preview"]
        return []

    def header_menu_items(self):
        """Process-runner header menu: Cancel Run / Open Output Folder / Clear
        Log (the script-template bridges' base default is Open/Refresh
        Templates). Built dynamically so the tooltips carry the engine label
        and the output-folder description."""
        return (
            (
                "Cancel Run", "btn_cancel_run",
                f"Kill the in-flight {self.ENGINE_LABEL} process.", "cancel_run",
            ),
            (
                "Open Output Folder", "btn_open_output",
                self.OUTPUT_FOLDER_TOOLTIP, "open_output_folder",
            ),
            ("Clear Log", "btn_clear_log", "Clear the log panel below.", "clear_log"),
        )

    def make_preset_store(self):
        """Semantic-preset mode: the engine-scoped store the headless runner uses
        — so a preset saved here is *that engine's* preset (it never appears in
        another engine's list)."""
        return Profile.preset_store(self.PRESET_ENGINE)

    def _apply_param_dict(self, data) -> int:
        """Apply a preset as **defaults + overlay**, exactly like the CLI.

        The base class overlays onto *current widget state*, which persists
        across sessions — so knobs a previously applied preset set (masking,
        preselection, smoothing…) ride along invisibly into every later run
        under a different preset ("preset residue"). Resetting the keys the
        preset does NOT name to their registry defaults first makes a preset
        mean the same thing in the panel as ``run_combined --preset``.

        Keys the preset names but this panel doesn't surface are logged (not
        silently dropped): e.g. RealityScan's ``specular_metal`` carries
        ``mask_background``, which RC's panel has no widget for — the user
        must act on it in the GUI, so they need to see it.
        """
        for key, spec in self.params_module.PARAMS.items():
            if key in data or key not in self._param_widgets:
                continue
            try:
                self._write_param(key, spec.default)
            except Exception:  # noqa: BLE001 - one bad handler can't abort the reset
                continue
        ignored = sorted(
            k for k in data
            if k not in self._param_widgets and not str(k).startswith("_")
        )
        if ignored:
            try:
                self.bridge.logger.warning(
                    "preset keys with no widget on this panel (NOT applied - "
                    "handle them per TUNING.md): " + ", ".join(ignored)
                )
            except Exception:  # noqa: BLE001
                pass
        return super()._apply_param_dict(data)

    # ------------------------------------------------------------------ template combo
    @staticmethod
    def _format_combo_label(template: str, mode: str) -> str:
        # Run modes carry their flag value in *mode*; show only the human label.
        return template

    def _relevant_param_keys(self):
        """Defer to the params module's relevance declaration, feeding it the
        selected run mode — the run-mode analogue of the DCC bridges feeding
        template script text to ``referenced_keys``. The base centrally manages
        the row show/hide + height fit from the returned set.

        Then apply the input-pre-processing master toggle: when it's off, the
        per-stage knobs collapse (only the toggle stays visible). No-op for
        engines without the stage (Brush has no ``preprocess_input`` widget)."""
        pair = self._selected_template_mode()
        if not pair:
            return None
        _template, mode = pair
        used = set(self.params_module.referenced_keys(mode))
        if (PREPROCESS_MASTER_KEY in self._param_widgets
                and not self._read_param(PREPROCESS_MASTER_KEY)):
            used -= PREPROCESSING_KNOB_KEYS
        return used

    def _wire_preprocess_master(self) -> None:
        """Live-refresh the param visibility when the pre-processing master
        toggle flips, so its knobs collapse/expand in place. No-op for engines
        without the stage (Brush)."""
        widget = self._param_widgets.get(PREPROCESS_MASTER_KEY)
        if widget is None:
            return
        # uitk CheckBox emits stateChanged; fall back to toggled defensively.
        signal = getattr(widget, "stateChanged", None) or getattr(
            widget, "toggled", None
        )
        if signal is not None:
            signal.connect(lambda *_: self._refresh_param_visibility())
        self._refresh_param_visibility()  # apply the toggle's initial state

    def _log_template_description(self) -> None:
        pair = self._selected_template_mode()
        if not pair:
            return
        template, mode = pair
        desc = self.MODE_DESC.get(mode)
        if not desc:
            return
        try:
            self.bridge.logger.info(f"[{template}] {desc}")
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ input rows
    def _build_input_rows(self) -> None:
        """Engine input row(s) then the Project Name row, so Name ends on top."""
        self._build_source_rows()
        self._name_edit = self._insert_top_row(
            label="Project Name:",
            placeholder=self.NAME_PLACEHOLDER,
            tooltip=self.NAME_TOOLTIP,
            initial=self._initial_name,
            buttons=[],
        )

    def _insert_top_row(self, label, placeholder, tooltip, initial, buttons):
        """Build a labelled line-edit row (+ optional buttons), insert at top.
        Returns the line edit."""
        layout = self.ui.grp_process.layout()
        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        lbl = QtWidgets.QLabel(label, row)
        lbl.setMinimumWidth(self.LABEL_MIN_WIDTH)
        lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setPlaceholderText(placeholder)
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(tooltip)
        if initial:
            edit.setText(initial)

        hbox.addWidget(lbl)
        hbox.addWidget(edit, 1)
        for text, handler in buttons:
            btn = QtWidgets.QPushButton(text, row)
            btn.setMinimumHeight(19)
            btn.setMaximumHeight(19)
            if text == "...":
                btn.setFixedWidth(22)
            btn.clicked.connect(handler)
            hbox.addWidget(btn)

        layout.insertWidget(0, row)
        return edit

    def resolved_project_name(self) -> str:
        return self._name_edit.text().strip() if self._name_edit else ""

    # ------------------------------------------------------------------ availability
    def _log_availability(self) -> None:
        if self.bridge.is_available():
            self.bridge.logger.info(f"{self.ENGINE_LABEL} found: {self.bridge.exe}")
        else:
            self.bridge.logger.error(self.MISSING_ENGINE_MESSAGE)
        # Engine-specific readiness beyond "is the exe present?" — e.g.
        # RealityScan also needs to be launched + signed in with its REST plugin
        # enabled. Subclasses log actionable guidance here (default: nothing).
        try:
            self._log_extra_availability()
        except Exception:  # noqa: BLE001 - readiness hints must never break panel init
            pass

    def _log_extra_availability(self) -> None:
        """Hook: log engine-specific readiness detail after the exe line (e.g. a
        plugin / running-app / sign-in requirement). Default: none."""

    def cancel_run(self) -> None:
        if self.bridge.is_running():
            self.bridge.logger.warning(f"Cancelling {self.ENGINE_LABEL} run…")
            self.bridge.cancel()
        else:
            self.bridge.logger.info("No run in progress.")

    def _resolved_output_project_dir(self) -> str:
        """The run's output folder ``<output-root>/<name>/``. Empty when the name
        or output root can't be resolved yet."""
        name = self.resolved_project_name()
        root = self.resolved_output_dir() or self.default_output_dir()
        return os.path.join(root, name) if (root and name) else ""

    def open_output_folder(self) -> None:
        """Reveal the output folder. Prefers the last run's folder; before any
        run, falls back to where the current inputs would write."""
        self.reveal_folder(
            self._last_output_dir or self._resolved_output_project_dir()
        )

    # ------------------------------------------------------------------ dispatch
    def b000(self) -> None:
        """Run Workflow."""
        if self.bridge.is_running():
            self.bridge.logger.warning(
                f"A {self.ENGINE_LABEL} run is already in progress."
            )
            return
        if not self.bridge.is_available():
            self.bridge.logger.error(self.MISSING_ENGINE_MESSAGE)
            return

        name = self.resolved_project_name()
        if not name:
            self.bridge.logger.error("Project Name is required.")
            if self._name_edit is not None:
                self._name_edit.setFocus()
            return
        input_argv = self._resolve_input_argv()
        if input_argv is None:
            return  # subclass logged + focused the field
        output_root = self.require_output_dir()
        if output_root is None:
            return  # base logged + focused the field
        # Capture where this run writes (the runner uses <output-root>/<name>/).
        self._last_output_dir = os.path.join(output_root, name)

        argv = ["--name", name, *input_argv, "--output-root", output_root]
        argv += self.params_module.to_argv(self.collect_param_values())
        argv += self._mode_argv()

        self.ui.txt000.clear()
        self.ui.b000.setEnabled(False)
        self.bridge.logger.info(
            f"--- {self.ENGINE_LABEL}: {name} ({self._active_template()}) ---"
        )
        self.bridge.logger.info(f"exe: {self.bridge.exe}")
        self.bridge.logger.info("flags: " + " ".join(argv))
        try:
            os.makedirs(output_root, exist_ok=True)
            self.bridge.start(
                argv,
                on_line=self._append_output,
                on_done=self._on_run_done,
                cwd=output_root,
            )
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Failed to launch {self.ENGINE_LABEL}: {e}")
            self.bridge.logger.debug(traceback.format_exc())
            self.ui.b000.setEnabled(True)

    def _append_output(self, text: str) -> None:
        """Append streamed runner stdout to the log pane."""
        te = self.ui.txt000
        te.moveCursor(QtGui.QTextCursor.End)
        te.insertPlainText(text)
        te.moveCursor(QtGui.QTextCursor.End)

    def _on_run_done(self, code: int) -> None:
        self.ui.b000.setEnabled(True)
        if code == 0:
            out = self._last_output_dir or self._resolved_output_project_dir()
            msg = "Workflow completed successfully."
            if out:
                # Emit the output dir as a clickable link (the log pane is a
                # QTextBrowser with openLinks off + anchorClicked wired to the
                # base's open handler) so a click reveals the folder, both
                # standalone and in Maya. The header's 'Open Output Folder'
                # action stays as a redundant affordance.
                msg += f" Output: {self.bridge.log_link(out, 'open', path=out)}"
            self.bridge.logger.info(msg)
        elif code == -1:
            self.bridge.logger.error(f"{self.ENGINE_LABEL} failed to launch.")
        else:
            self.bridge.logger.error(f"Workflow failed (exit code {code}).")


class FramesSourceMixin:
    """A single 'Source' row + browser for image-in panels (Metashape, RC).

    Pick video clip(s) → frames are extracted (sharpest-per-second) into a
    folder; or pick any frame from an existing frames folder → that folder
    becomes the source. (Qt has no native dialog that returns *either* a file or
    a folder, so a frame stands in for its folder; routing is by extension.)
    """

    SOURCE_LABEL = "Source:"
    SOURCE_PLACEHOLDER = "(source images, or video clip(s) to extract)"
    SOURCE_TOOLTIP = (
        "The capture source for this run (--frames-dir). One browser for both:\n"
        "  •  pick video clip(s) → frames are extracted (sharpest-per-second) "
        "into a folder, OR\n"
        "  •  pick any frame from an existing frames folder → that folder becomes "
        "the source."
    )

    def _init_inputs(self, kwargs) -> None:
        self._initial_frames: str = kwargs.get("frames_dir", "") or ""
        self._frames_edit: Optional[QtWidgets.QLineEdit] = None

    def _build_source_rows(self) -> None:
        self._frames_edit = self._insert_top_row(
            label=self.SOURCE_LABEL,
            placeholder=self.SOURCE_PLACEHOLDER,
            tooltip=self.SOURCE_TOOLTIP,
            initial=self._initial_frames,
            buttons=[("...", self._pick_source)],
        )

    def resolved_frames_dir(self) -> str:
        return self._frames_edit.text().strip() if self._frames_edit else ""

    def _resolve_input_argv(self) -> Optional[List[str]]:
        frames = self.resolved_frames_dir()
        if not frames or not os.path.isdir(frames):
            self.bridge.logger.error(
                f"Source frames dir is required and must exist: {frames or '(empty)'}"
            )
            if self._frames_edit is not None:
                self._frames_edit.setFocus()
            return None
        return ["--frames-dir", frames]

    def _pick_source(self) -> None:
        try:
            sel = self.sb.file_dialog(
                file_types=[*_VIDEO_EXTS, *_IMAGE_EXTS],
                title="Select Frame or Video Clip(s)",
                start_dir=self.resolved_frames_dir() or os.getcwd(),
                filter_description="Frames or video clips",
                allow_multiple=True,
            )
        except Exception:  # noqa: BLE001
            sel = None
        if not sel:
            return
        if isinstance(sel, str):
            sel = [sel]

        videos = [f for f in sel if f.lower().endswith(_VIDEO_SUFFIXES)]
        if videos:
            self._extract_videos(videos)
        elif self._frames_edit is not None:
            # Frames already on disk — use the folder the picked frame(s) live in.
            self._frames_edit.setText(os.path.dirname(sel[0]))

    def _extract_videos(self, videos: List[str]) -> None:
        """Extract frames from *videos* into the source dir (runs in the panel's
        full Python — the engines' bundled Python may lack cv2)."""
        out_dir = self.resolved_frames_dir()
        if not out_dir:
            out_dir = os.path.join(os.path.dirname(videos[0]), "frames")
            if self._frames_edit is not None:
                self._frames_edit.setText(out_dir)

        from extapps import PrepStagesMixin

        # Honor the panel's Video Window knob (shared pre-processing spec);
        # fall back to the extractor default when the widget is absent (Brush
        # panel has no pre-processing section).
        window_sec = 1.0
        try:
            val = self._read_param("video_window_sec")
            if val:
                window_sec = max(0.1, float(val))
        except Exception:  # noqa: BLE001 - a bad widget value can't block extraction
            pass

        try:
            self.bridge.logger.info(
                f"Extracting frames from {len(videos)} video(s) → '{out_dir}' "
                f"(window {window_sec:g}s)"
            )
            frames = PrepStagesMixin.extract_videos_to_dir(
                videos, out_dir, window_sec=window_sec, log=self.bridge.logger.info
            )
            self.bridge.logger.info(
                f"Extracted {len(frames)} frame(s) total." if frames
                else "Frame extraction returned no files (is OpenCV installed?)."
            )
        except Exception as e:  # noqa: BLE001
            self.bridge.logger.error(f"Frame extraction failed: {e}")
            self.bridge.logger.debug(traceback.format_exc())
