# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Marmoset Workflow panel.

A DCC-agnostic sibling of ``MarmosetBridgeSlots`` (one class for Maya and
Blender): both subclass uitk's :class:`BridgeSlotsBase` (template combo,
parameter widgets, presets, log routing), but this one drives the engine from a
picked **model file** instead of a scene selection -- a standalone panel
(``tentacle/tcl_standalone.py``), so it runs outside any DCC too. The engine is
extapps' :class:`MarmosetWorkflow` (its vendored Toolbag engine).

Scoped to "open + set up a project": the ``import`` and ``lookdev``
templates. The bake (high/low) workflow stays with the host panel.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import List, Optional, Tuple

import pythontk as ptk
from extapps import MarmosetWorkflow
from qtpy import QtCore, QtWidgets

from tentacle import Slots

from ._marmoset_workflow import parameters as _params


# Templates this panel exposes (the "set up a project" subset).
_ALLOWED_TEMPLATES = ("import", "lookdev")

# Toolbag-importable model formats offered in the file picker.
_MODEL_FILE_TYPES = [
    "*.fbx",
    "*.obj",
    "*.usd",
    "*.usdc",
    "*.usda",
    "*.abc",
    "*.gltf",
    "*.glb",
    "*.ply",
]


class MarmosetWorkflowSlots(Slots.BridgeSlotsBase):
    """Switchboard slots wired to ``marmoset_workflow.ui``.

    Picks a model file, then launches Toolbag with the chosen template
    (``import`` / ``lookdev``) via extapps' :class:`MarmosetWorkflow`.
    """

    UI_NAME = "marmoset_workflow"
    #: Saved data: the folder the panel's presets have always been kept in.
    PRESETS_ROOT = Path("extapps/marmoset_workflow")
    LOG_TAG = "marmoset_workflow"
    # The set-up-a-project templates run interactively (send_to); there's no
    # user-facing artifact dir to require -- the rendered script is a throwaway.
    REQUIRE_OUTPUT_DIR = False

    # Uses the base's default header menu (Clear Log; the template rows are on
    # the template combo's context menu); only the help differs, so it's
    # declared as data. It says where this panel differs from the DCC
    # Marmoset Bridge, which a user may know first.
    HELP_SPEC = {
        "title": "Marmoset Workflow",
        "body": "Open a model file from disk in Marmoset Toolbag, ready for "
        "look-dev. No DCC required -- each click starts a new Toolbag.",
        "steps": [
            "Pick a <b>Model File</b> (FBX, OBJ, USD, Alembic, glTF / GLB, "
            "or a mesh PLY).",
            "Choose a template: <b>import</b> (the model only) or "
            "<b>lookdev</b> (plus a sky and framing; the default).",
            "For lookdev, set the <b>Sky</b> and <b>Frame on Open</b>.",
            "Click <b>Set Up in Marmoset</b>.",
        ],
        "notes": [
            "Nothing is saved for you: save the scene in Toolbag.",
            "Unlike the Maya / Blender <b>Marmoset Bridge</b>, no textures are "
            "wired (the materials are what Toolbag's import of the file gives) "
            "and there is no bake: both stay with the bridge.",
            "Gaussian-splat PLYs are not meshes and won't render in Toolbag.",
        ],
    }

    def __init__(self, switchboard, **kwargs):
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        super().__init__(switchboard)
        self._build_model_row()

    # ------------------------------------------------------------------
    # Required base-class hooks
    # ------------------------------------------------------------------

    @property
    def params_module(self):
        return _params.Parameters

    @property
    def template_dir(self) -> Path:
        return MarmosetWorkflow.TEMPLATE_DIR

    def make_bridge(self) -> MarmosetWorkflow:
        return MarmosetWorkflow()

    def list_template_modes(self) -> List[Tuple[str, str]]:
        """Engine templates filtered to the 'set up a project' subset."""
        return [
            (t, m)
            for (t, m) in MarmosetWorkflow.list_template_modes()
            if t in _ALLOWED_TEMPLATES
        ]

    def select_initial_template_index(self, pairs: List[Tuple[str, str]]) -> int:
        """Prefer 'lookdev (send_to)', else first entry."""
        if ("lookdev", ptk.SEND_TO) in pairs:
            return pairs.index(("lookdev", ptk.SEND_TO))
        return 0

    # ------------------------------------------------------------------
    # Model-file row (this panel's analogue of a DCC selection)
    # ------------------------------------------------------------------

    def _build_model_row(self) -> None:
        """Insert a 'Model File' line edit + browse at the top of grp_process."""
        layout = self.ui.grp_process.layout()

        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        label = QtWidgets.QLabel("Model File:", row)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setPlaceholderText("(pick an FBX / OBJ / USD / glTF mesh to import)")
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(
            "Model file imported into Toolbag (FBX, OBJ, USD, Alembic, glTF, "
            "or a polygon-mesh PLY). Note: Gaussian-splat PLYs are not meshes "
            "and won't render in Toolbag."
        )
        if self._initial_model:
            edit.setText(self._initial_model)

        browse = QtWidgets.QPushButton("...", row)
        browse.setFixedWidth(22)
        browse.setMinimumHeight(19)
        browse.setMaximumHeight(19)
        browse.clicked.connect(self._pick_model)

        hbox.addWidget(label)
        hbox.addWidget(edit, 1)
        hbox.addWidget(browse)

        layout.insertWidget(0, row)
        self._model_edit = edit

    def _start_dir(self) -> str:
        cur = self.resolved_model_path()
        if cur:
            return os.path.dirname(cur)
        return str(Path.home())

    def _pick_model(self) -> None:
        try:
            paths = self.sb.file_dialog(
                file_types=_MODEL_FILE_TYPES,
                title="Select a model file to set up in Marmoset:",
                start_dir=self._start_dir(),
                allow_multiple=False,
            )
        except Exception:  # noqa: BLE001
            paths = None
        if not paths:
            return
        chosen = paths[0] if isinstance(paths, (list, tuple)) else paths
        if chosen and self._model_edit is not None:
            self._model_edit.setText(chosen)

    def resolved_model_path(self) -> str:
        if self._model_edit is None:
            return ""
        return self._model_edit.text().strip()

    def set_model_path(self, path: str) -> None:
        """Pre-fill the Model File field (e.g. a host exported the current selection to it).

        Public hand-off point for a host that drives this panel. (Blender no
        longer does: it has a native Marmoset Bridge panel of its own.)"""
        self._initial_model = path or ""
        if self._model_edit is not None:
            self._model_edit.setText(self._initial_model)

    # ------------------------------------------------------------------
    # Header menu
    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # b000 -- the send action
    # ------------------------------------------------------------------

    def b000(self) -> None:
        """Set up the picked model in Toolbag using the chosen template + mode."""
        model = self.resolved_model_path()
        if not model:
            self.bridge.logger.warning(
                "Pick a model file first (use the '...' button next to Model File)."
            )
            return
        if not os.path.isfile(model):
            self.bridge.logger.error(f"Model file not found: {model}")
            return

        pair = self._selected_template_mode()
        if not pair:
            self.bridge.logger.warning(
                "No template chosen. Pick one from the dropdown above."
            )
            return
        template, mode = pair

        if not self.bridge.toolbag_path:
            self.bridge.logger.error(MarmosetWorkflow.APP.not_found_msg)
            return

        self.bridge.logger.info(
            f"--- {template} ({mode}) on {os.path.basename(model)} ---"
        )

        try:
            with self.sb.progress(text=f"Working: Marmoset {template} ({mode})"):
                result = self.bridge.send(
                    model_path=model,
                    output_dir=self.require_output_dir() or None,
                    template=template,
                    mode=mode,
                    params=self.collect_param_values(),
                )
        except Exception:
            self.bridge.logger.error("Engine raised:\n" + traceback.format_exc())
            return

        if result is None:
            return  # logger already explained why
