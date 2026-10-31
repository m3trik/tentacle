# !/usr/bin/python
# coding=utf-8
"""Slots for the standalone Unity Workflow panel.

A DCC-agnostic sibling of ``UnityBridgeSlots`` (one class for Maya and Blender):
both subclass uitk's :class:`BridgeSlotsBase` (parameter widgets, presets, log
routing, the relabeled 'Unity Project' row, the project-actions menu), but this one
is driven by a picked **model file** instead of a live DCC selection -- a standalone
panel (``tentacle/tcl_standalone.py``), so it runs outside any DCC too. A host can
pre-fill the file through :meth:`set_model_path`.

Delivery is the single copy-to-Assets target via :class:`unitytk.FileToUnityBridge`
(the file-input engine sharing ``unitytk.CopyToAssetsDeliverer`` with the DCC
bridges): copy the model into the project's ``Assets/`` and optionally launch the
chosen Editor. The launcher actions (set / open / create a project) live on the
'Unity Project' field's option menu, co-located with the field they act on.
That shared Unity-panel behavior (the project row + actions, the mode combo, the
Editor combo, script management) is :class:`UnityPanelMixin`, which both Unity
panels take from ``_unity_bridge/_unity_panel.py``; this file owns the Model File
row, the engine and the ``b000`` send.

Note: *Unity Studio* is a separate paid, browser-based product (assets enter it via
Unity Cloud's Asset Manager), not this desktop FBX hand-off -- this panel does not
target it.
"""

from __future__ import annotations

import os
import traceback
from pathlib import Path
from typing import Optional

from qtpy import QtCore, QtWidgets

from tentacle import Slots

from ._unity_bridge._unity_panel import UnityPanelMixin
from ._unity_workflow import parameters as _params


# Unity-importable model formats offered in the file picker.
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


class UnityWorkflowSlots(UnityPanelMixin, Slots.BridgeSlotsBase):
    """Switchboard slots wired to ``unity_workflow.ui`` via :class:`BridgeSlotsBase`.

    Picks a model file, then copies it into a Unity project's ``Assets/`` via
    :class:`unitytk.FileToUnityBridge` (optionally launching the chosen Editor).
    """

    UI_NAME = "unity_workflow"
    #: Saved data: the folder the panel's presets have always been kept in.
    PRESETS_ROOT = Path("extapps/unity_workflow")
    LOG_TAG = "unity_workflow"

    OUTPUT_DIR_TOOLTIP = (
        "Path to the target Unity project -- the folder that contains the\n"
        "'Assets/' directory. The model file is copied into\n"
        "Assets/<subfolder>; Unity imports it on its next window focus.\n"
        "No project yet? Create one via 'New Unity Project...' in the field menu."
    )
    UNITY_FEATURE = "Unity Workflow"  # names the unitytk install prompt

    # Says where this panel differs from the DCC Unity Bridge, which a user may
    # know first: it copies a file as exported and exports nothing itself.
    HELP_SPEC = {
        "title": "Unity Workflow",
        "body": "Copy an exported model file into a Unity project's "
        "<b>Assets/</b> folder. Safe with Unity open: the copy lands whole, and "
        "Unity imports it on its next window focus.",
        "steps": [
            "Pick a <b>Model File</b> (FBX, OBJ, USD, Alembic, glTF or PLY).",
            "Set the <b>Unity Project</b> (the folder holding Assets/); the "
            "field's menu also opens or creates one.",
            "With <b>Copy to Project</b> in the top combo, click <b>Send to Unity</b>.",
        ],
        "sections": [
            (
                "Parameters",
                [
                    "<b>Assets Subfolder</b> — where under Assets/ the file "
                    "lands (blank = <i>Imported</i>; <i>/</i> = Assets/ itself).",
                    "<b>Asset Name</b> — optional; blank uses the file's name. "
                    "A same-named asset is replaced.",
                    "<b>Launch Unity</b> — after copying: <i>Don't launch</i>, "
                    "<i>Open Editor</i>, or <i>Headless (batch)</i> (import, then "
                    "quit; needs a batch-capable license). <b>Unity Version</b> "
                    "picks the Editor.",
                ],
            ),
        ],
        "notes": [
            "Unlike the Maya / Blender <b>Unity Bridge</b>, nothing is exported "
            "here (no Scope, material or texture rows): the file is copied as "
            "it is. unitytk's import scripts act on <b>.fbx</b> files only.",
            "<b>Manage Unity Scripts</b> (top combo): check the scripts, pick an "
            "<b>Action</b> (Status, Install / Update, Uninstall) for the "
            "project's embedded <i>com.m3trik.unitytk</i> package, and click "
            "Send to Unity. Per-channel import toggles: in Unity, Edit ▸ "
            "Project Settings ▸ unitytk.",
        ],
    }

    # ------------------------------------------------------------------ init
    def __init__(self, switchboard, **kwargs):
        self._initial_model: str = kwargs.get("model_path", "") or ""
        self._model_edit: Optional[QtWidgets.QLineEdit] = None
        super().__init__(switchboard)
        self._build_model_row()
        self._populate_unity_rows()  # UnityPanelMixin: Editor combo + SCRIPTS list

    # ------------------------------------------------------------------ base-class hooks
    @property
    def params_module(self):
        return _params.Parameters

    def make_bridge(self):
        """unitytk's file-input engine, or ``None`` while the optional unitytk is
        absent (:meth:`UnityPanelMixin._file_bridge`)."""
        return self._file_bridge()

    # ------------------------------------------------------------------ Model File row
    def _build_model_row(self) -> None:
        """Insert a 'Model File' row (option-box: recent history + browse) at the top.

        The edit is parented into the row layout (with stretch) before the option
        box wraps it, so the wrapping container fills the row (see
        ``BridgeSlotsBase._build_output_dir_row`` for the rationale).
        """
        layout = self.ui.grp_process.layout()

        row = QtWidgets.QWidget(self.ui.grp_process)
        hbox = QtWidgets.QHBoxLayout(row)
        hbox.setContentsMargins(0, 0, 0, 0)
        hbox.setSpacing(2)

        label = QtWidgets.QLabel("Model File:", row)
        label.setMinimumWidth(self.LABEL_MIN_WIDTH)
        label.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)

        edit = QtWidgets.QLineEdit(row)
        edit.setObjectName(f"{self.LOG_TAG}_model")
        edit.setPlaceholderText("(pick an FBX / OBJ / USD / glTF mesh to send)")
        edit.setMinimumHeight(19)
        edit.setMaximumHeight(19)
        edit.setToolTip(
            "Model file copied into the Unity project (FBX, OBJ, USD, Alembic,\n"
            "glTF, or a polygon-mesh PLY), as exported: nothing is re-exported."
        )
        if self._initial_model:
            edit.setText(self._initial_model)

        hbox.addWidget(label)
        hbox.addWidget(edit, 1)

        edit.option_box.recent(
            settings_key=f"{self.LOG_TAG}_model_recent",
            auto_record=True,
            display_format="auto",
        )
        edit.option_box.set_action(
            callback=self._pick_model,
            icon="folder",
            tooltip="Browse for a model file",
            settings_key=False,
        )

        layout.insertWidget(0, row)
        self._model_edit = edit

    def _model_start_dir(self) -> str:
        cur = self.resolved_model_path()
        if cur:
            return os.path.dirname(cur)
        return str(Path.home())

    def _pick_model(self) -> None:
        try:
            paths = self.sb.file_dialog(
                file_types=_MODEL_FILE_TYPES,
                title="Select a model file to send to Unity:",
                start_dir=self._model_start_dir(),
                allow_multiple=False,
            )
        except Exception:  # noqa: BLE001
            paths = None
        if not paths:
            return
        chosen = paths[0] if isinstance(paths, (list, tuple)) else paths
        if chosen and self._model_edit is not None:
            self._model_edit.setText(chosen)
            self._record_recent(self._model_edit, chosen)

    def resolved_model_path(self) -> str:
        if self._model_edit is None:
            return ""
        return self._model_edit.text().strip()

    def set_model_path(self, path: str) -> None:
        """Pre-fill the Model File field (public hand-off point for hosts).

        (Blender no longer calls it: it has a native Unity Bridge panel.)"""
        self._initial_model = path or ""
        if self._model_edit is not None:
            self._model_edit.setText(self._initial_model)
            self._record_recent(self._model_edit, self._initial_model)

    # ------------------------------------------------------------------ b000 -- send
    def b000(self) -> None:
        """Run the selected template: copy the model, or script management."""
        if self._run_manage_mode():
            return

        model = self.resolved_model_path()
        if not model:
            self.bridge.logger.warning(
                "Pick a model file first (use the Model File field's browse button)."
            )
            return
        if not os.path.isfile(model):
            self.bridge.logger.error(f"Model file not found: {model}")
            return

        project = self.resolved_output_dir()
        if not project:
            self.bridge.logger.error(
                "Set the Unity Project folder above (the one containing 'Assets/'), "
                "or create one via 'New Unity Project…'."
            )
            if self._output_dir_edit is not None:
                self._output_dir_edit.setFocus()
            return

        self.bridge.project_path = project
        self.bridge.logger.info(
            f"--- Send to Unity on {os.path.basename(model)} -> {project} ---"
        )
        try:
            with self.sb.progress(text="Working: Send to Unity"):
                self.bridge.send(
                    model_path=model,
                    template=self.MODE_COPY,
                    mode="",
                    params=self.collect_param_values(),
                )
        except Exception:
            self.bridge.logger.error("Bridge raised:\n" + traceback.format_exc())
