#!/usr/bin/python
# coding=utf-8
"""Switchboard slots for the Substance Workflow UI.

A standalone panel (``tentacle/tcl_standalone.py``) over extapps' Painter
engine. The panel wires the UI to :class:`PainterConnection`: launch a fresh
Painter, then dispatch registered ops (``project.*``, ``bake.*``, …) over
the JSON-RPC bridge. Engine/domain logic lives in the op modules — these
slots only collect widget state and invoke ops by name. A run's stages go
off the GUI thread (``uitk.BackgroundTask``), one after another: a bake can
take minutes, and the panel -- and a DCC hosting it -- stays live and can
cancel.
"""

import logging
import os
import traceback
from typing import Any, Callable, Dict, List, NamedTuple, Optional

import pythontk as ptk
from extapps import DOCS_BASE_URL, PainterConnection, PainterFinder
from qtpy import QtCore, QtWidgets

from tentacle import Slots

AttributeSpec = Slots.AttributeSpec

# ---------------------------------------------------------------------------
# Mesh formats Painter accepts for project creation.
# ---------------------------------------------------------------------------
MESH_EXTS = [
    "*.fbx",
    "*.obj",
    "*.abc",
    "*.gltf",
    "*.glb",
    "*.ply",
    "*.usd",
    "*.usda",
    "*.usdc",
]

# ---------------------------------------------------------------------------
# Workflow stages: (object_name, label, tooltip, default_on). Order here is
# both the menu order and the canonical execution order.
# ---------------------------------------------------------------------------
PIPELINE_STAGES = [
    (
        "stage_open",
        "Open / Create Project",
        "Open the .spp at the save path if it exists, else create a new project from the mesh file.",
        True,
    ),
    (
        "stage_bake",
        "Bake Lighting → Diffuse",
        "iray-backed AO (+ optional curvature) composited onto the base color channel.",
        True,
    ),
    (
        "stage_save",
        "Save Project",
        "Save the project (save-as to the save path on first save).",
        True,
    ),
    (
        "stage_export",
        "Export Textures",
        "Export textures via a preset. NOTE: export.* ops are not yet implemented.",
        False,
    ),
]

BLEND_MODES = ["Multiply", "Overlay", "Normal", "Darken", "LinearBurn"]
BAKE_RESOLUTIONS = ["256", "512", "1024", "2048", "4096"]

# ---------------------------------------------------------------------------
# Advanced bake parameters — one labeled row per spec in the Advanced popup.
# Field widgets come from uitk.make_widget driven by these AttributeSpecs
# (same factory as metashape_workflow). object_name == spec.key, so
# self.ui.<key> resolves each field via findChild.
# ---------------------------------------------------------------------------
ADVANCED_PARAMS = [
    AttributeSpec(
        key="cmb_bake_res",
        label="Bake Resolution:",
        kind="choice",
        default="1024",
        choices=BAKE_RESOLUTIONS,
        tooltip="Mesh-map bake output size (square, power of two).",
    ),
    AttributeSpec(
        key="spn_ao_rays",
        label="AO Rays:",
        kind="int",
        default=64,
        minimum=1,
        maximum=256,
        step=8,
        tooltip="AO secondary-ray sample count (Painter: 1-256). Higher = cleaner, slower.",
    ),
    AttributeSpec(
        key="spn_ao_max",
        label="AO Max Dist:",
        kind="float",
        default=1.0,
        minimum=0.001,
        maximum=1.0,
        step=0.01,
        decimals=3,
        tooltip="Max occluder distance, as a fraction of the mesh's bounding box.",
    ),
    AttributeSpec(
        key="spn_ao_min",
        label="AO Min Dist:",
        kind="float",
        default=0.0,
        minimum=0.0,
        maximum=1.0,
        step=0.001,
        decimals=3,
        tooltip="Min occluder distance (bias against self-shadow noise), as a fraction of the bounding box.",
    ),
    AttributeSpec(
        key="spn_ao_spread",
        label="AO Spread (deg):",
        kind="float",
        default=162.0,
        minimum=0.0,
        maximum=180.0,
        step=1.0,
        decimals=1,
        tooltip="Hemisphere spread angle in degrees.",
    ),
    AttributeSpec(
        key="spn_ao_subsample",
        label="AO Subsample:",
        kind="int",
        default=1,
        minimum=1,
        maximum=8,
        tooltip="Antialiasing: 1 none, 2 / 4 / 8 for 2x2 / 4x4 / 8x8 subsampling.",
    ),
    AttributeSpec(
        key="spn_ao_intensity",
        label="AO Intensity:",
        kind="float",
        default=1.0,
        minimum=0.0,
        maximum=4.0,
        step=0.05,
        decimals=2,
        tooltip="Multiplier applied to the AO contribution when compositing.",
    ),
    AttributeSpec(
        key="cmb_blend",
        label="Blend Mode:",
        kind="choice",
        default="Multiply",
        choices=BLEND_MODES,
        tooltip="Blend mode for the inserted AO lighting layer.",
    ),
    AttributeSpec(
        key="chk_curvature",
        label="Include Curvature:",
        kind="bool",
        default=False,
        tooltip="Also bake curvature and stack it as an overlay layer.",
    ),
    AttributeSpec(
        key="spn_curv_intensity",
        label="Curvature Intensity:",
        kind="float",
        default=0.3,
        minimum=0.0,
        maximum=4.0,
        step=0.05,
        decimals=2,
        tooltip="Curvature multiplier when 'Include Curvature' is on.",
    ),
    AttributeSpec(
        key="chk_skip_bakes",
        label="Skip Existing Bakes:",
        kind="bool",
        default=False,
        tooltip="Only bake when the AO mesh map is missing.",
    ),
]

_LOG_LEVELS = {
    "Log Level: DEBUG": 10,
    "Log Level: INFO": 20,
    "Log Level: WARNING": 30,
    "Log Level: ERROR": 40,
}


class _Stage(NamedTuple):
    """One stage of a run, ready to go off the GUI thread."""

    #: The stage's name in the Stages menu (and in the run's messages).
    label: str
    #: The work: bridge calls only, no widget -- it runs on a BackgroundTask.
    #: Returns the stage's line for the run's report.
    call: Callable[[], str]
    #: Set: a failure only warns (this text, then the error) and the run goes on.
    skip_note: str = ""


class _WorkflowRun:
    """One Run Workflow in flight: its stages, how far it got, its cancel.

    The GUI thread alone reads and writes it (the stages only return values),
    and the panel holds the run it is on: a callback that finds another one --
    or none -- belongs to a run that has already ended.
    """

    def __init__(self, report: bool, run_label: str):
        self.stages: List[_Stage] = []
        self.index = 0  # the stage running, or next to run
        self.lines: List[str] = []  # the report lines of the stages that ran
        self.report = report  # INFO on: the run's boxes and groups are logged
        self.run_label = run_label  # the Run button's own text, given back at the end
        #: Cancel button and the footer's Esc-hold both land here; checked
        #: between stages -- an op mid-call cannot be stopped over the bridge.
        self.cancel = ptk.CancelScope("Substance Workflow")

    @property
    def stage(self) -> Optional[_Stage]:
        """The stage running (or next to run); ``None`` past the last."""
        return self.stages[self.index] if self.index < len(self.stages) else None


class SubstanceWorkflowSlots(Slots, ptk.LoggingMixin):
    """Switchboard slots for the Substance Workflow UI."""

    # Logged once at panel open as a clickable anchor (the compositor's intro
    # and the BridgeSlotsBase panels do the same). Not a bridge panel, so the
    # line is emitted here rather than by ``BridgeSlotsBase._show_docs_link``.
    DOCS_URL = DOCS_BASE_URL + "docs/substance_workflow.md"
    DOCS_LABEL = "Detailed docs (bridge, op registry, batch API)"

    #: The Advanced popup's fields, built at runtime from :data:`ADVANCED_PARAMS`
    #: (each spec's ``key`` is its objectName), which no ``.ui`` can list.
    RUNTIME_WIDGETS = (
        "cmb_bake_res",
        "spn_ao_rays",
        "spn_ao_max",
        "spn_ao_min",
        "spn_ao_spread",
        "spn_ao_subsample",
        "spn_ao_intensity",
        "cmb_blend",
        "chk_curvature",
        "spn_curv_intensity",
        "chk_skip_bakes",
    )

    # The header help, as data like the BridgeSlotsBase panels' HELP_SPEC;
    # not a bridge panel, so ``header_init`` hands it to the header itself.
    # It says where this panel differs from the DCC Substance Bridge, which a
    # user may know first.
    HELP_SPEC = {
        "title": "Substance Workflow",
        "body": "Create or open a Substance 3D Painter project from files on "
        "disk, bake AO lighting into Base Color, and save. Every launch starts "
        "a <b>new</b> Painter running this panel's own bridge; an open Painter "
        "is never touched.",
        "steps": [
            "Set a <b>Mesh File</b> (and an optional <b>Template</b> .spt) to "
            "create a project, and/or a <b>Project Save Path</b> (.spp): an "
            "existing .spp is opened instead, mesh ignored.",
            "Pick the <b>Painter</b> install.",
            "Choose the <b>Stages</b>; tune the AO and curvature bake under "
            "<b>Advanced</b>.",
            "Click <b>Run Workflow</b> (it launches Painter when needed). "
            "While it runs the button reads <b>Cancel</b> (or hold Esc): the "
            "stage under way finishes, and no later one starts.",
        ],
        "notes": [
            "Once Painter runs, the launch button reads <b>Close Painter</b>: "
            "it force-closes the Painter this panel launched, losing unsaved "
            "changes. Closing the panel leaves Painter running.",
            "<i>Export Textures</i> is not implemented yet: the stage is "
            "skipped with a warning.",
            "Unlike the Maya / Blender <b>Substance Bridge</b>: no scene "
            "selection, no templates or reimport into a running Painter, and "
            "nothing is installed into Painter's plugins folder.",
        ],
    }

    def __init__(self, switchboard, log_level: int = 20):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.substance_workflow

        self.logger.setLevel(log_level)
        self.logger.hide_logger_name(True)
        # uitk's Qt handler, not pythontk's Qt-free default (which is what a
        # bare redirect attaches): it routes the pane's anchors, so the docs
        # line below is a live link, and it reports the pane's width, which
        # the run's boxes are sized to.
        self.logger.set_text_handler(self.sb.TextEditLogHandler)
        self.logger.setup_logging_redirect(self.ui.txt003)

        # The session is the process-wide connection: a rebuilt panel picks up
        # the Painter an earlier one launched instead of orphaning it with a
        # second launch.
        self.conn: PainterConnection = PainterConnection.get_instance()
        # The Run Workflow in flight (its stages run off the GUI thread).
        self._run: Optional[_WorkflowRun] = None
        # Painter can quit from its own window: while a session is up, look
        # every 2 s so the button (and Run) follow it.
        self._shown_connected: bool = False
        self._session_timer = QtCore.QTimer()
        self._session_timer.setInterval(2000)
        self._session_timer.timeout.connect(self._check_session)
        # Scan once at startup; reused by the Painter picker and status line.
        self._installs: Dict[str, str] = PainterFinder.find_installs()

        self._log_status()
        self.logger.info(
            f'{self.DOCS_LABEL}: <a href="{self.DOCS_URL}">{self.DOCS_URL}</a>'
        )
        self._sync_launch_button()

    # ------------------------------------------------------------------ status

    def _log_status(self) -> None:
        if not self._installs:
            self.logger.warning(
                "No Substance 3D Painter install detected. Set the path via "
                "the Painter field or pass app_path."
            )
        else:
            self.logger.info(f"Found {len(self._installs)} Painter install(s).")

    @property
    def _connected(self) -> bool:
        return self.conn.is_connected

    @property
    def _busy(self) -> bool:
        """A run is in flight (read from it: no second flag to drift)."""
        return self._run is not None

    # ------------------------------------------------------------------ header

    def header_init(self, widget) -> None:
        if widget.is_initialized:
            return
        widget.menu.add(
            self.sb.registered_widgets.ComboBox,
            setObjectName="cmb003",
            add=_LOG_LEVELS,
            setCurrentIndex=1,
            setToolTip="Set the log level.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(**self.HELP_SPEC), url=self.DOCS_URL
        )

    # ------------------------------------------------------------------ fields

    def txt000_init(self, widget) -> None:
        """Mesh File"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Mesh File:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent("substance_mesh_files", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_mesh",
            setToolTip="Select a mesh file to create a project from.",
        )

    def txt001_init(self, widget) -> None:
        """Template (optional)"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Template (optional):")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.clear_option = True
        widget.option_box.recent("substance_templates", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_template",
            setToolTip="Select a Painter project template (.spt).",
        )

    def txt002_init(self, widget) -> None:
        """Project Save Path"""
        if widget.is_initialized:
            return
        widget.option_box.menu.setTitle("Project Save Path:")
        widget.option_box.menu.add_defaults_button = False
        widget.option_box.recent("substance_project_paths", auto_record=True)
        widget.option_box.menu.add(
            "QPushButton",
            setText="Browse...",
            setObjectName="btn_browse_project",
            setToolTip="Select where to save / open the .spp project.",
        )

    def cmb000_init(self, widget) -> None:
        """Painter install picker"""
        items = self._installs if self._installs else {"Auto-detect": None}
        widget.add(items, clear=True)

    # ------------------------------------------------------------------ stages

    def btn_stages_init(self, widget) -> None:
        """Stages popup — QMenu of checkboxes attached to the button."""
        if widget.is_initialized:
            return
        menu = QtWidgets.QMenu(widget)
        for object_name, label, tooltip, default_on in PIPELINE_STAGES:
            chk = QtWidgets.QCheckBox(label, menu)
            chk.setObjectName(object_name)
            chk.setChecked(default_on)
            chk.setToolTip(tooltip)
            action = QtWidgets.QWidgetAction(menu)
            action.setDefaultWidget(chk)
            menu.addAction(action)
        widget.setMenu(menu)

    # ------------------------------------------------------------------ advanced

    def btn_advanced_init(self, widget) -> None:
        """Advanced-params popup — labeled form inside a QMenu via QWidgetAction.

        Field widgets come from :func:`uitk.make_widget` driven by the
        :class:`AttributeSpec` entries in :data:`ADVANCED_PARAMS` — same
        factory as metashape_workflow, so spec changes flow through with no
        per-kind switch here.
        """
        if widget.is_initialized:
            return
        menu = QtWidgets.QMenu(widget)
        form_host = QtWidgets.QWidget(menu)
        vbox = QtWidgets.QVBoxLayout(form_host)
        vbox.setContentsMargins(2, 4, 2, 2)
        vbox.setSpacing(0)

        for spec in ADVANCED_PARAMS:
            row = QtWidgets.QWidget(form_host)
            hbox = QtWidgets.QHBoxLayout(row)
            hbox.setContentsMargins(0, 0, 0, 0)
            hbox.setSpacing(2)

            lbl = QtWidgets.QLabel(spec.label, row)
            lbl.setMinimumWidth(110)
            lbl.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
            lbl.setToolTip(spec.tooltip)

            field = self.sb.KindFactory.make_widget(spec, row)
            field.setMinimumHeight(19)
            field.setMaximumHeight(19)

            hbox.addWidget(lbl)
            hbox.addWidget(field, 1)
            vbox.addWidget(row)

        action = QtWidgets.QWidgetAction(menu)
        action.setDefaultWidget(form_host)
        menu.addAction(action)
        widget.setMenu(menu)

    # ------------------------------------------------------------------ buttons

    def cmb003(self, widget) -> None:
        """Log level changed"""
        self.logger.setLevel(int(widget.currentData()))

    def btn_launch(self, widget) -> None:
        """Toggle the Painter session."""
        if self._shown_connected and not self._connected:
            # Painter quit since the button last said Close: the click brings
            # the button up to date (and ends a run on it) -- it does what it
            # said, never a launch.
            self._check_session()
            return
        if self._busy:
            self.logger.warning("Busy — Cancel the run, or wait for it to finish.")
            return
        if self._connected:
            self._close_painter()
        else:
            self._launch_painter()

    def b000(self) -> None:
        """Run Workflow -- while a run is in flight, the button is its Cancel."""
        if self._busy:
            self._cancel_run()
            return
        self.ui.txt003.clear()
        self._run_workflow()

    # Option-box browse callbacks
    def set_mesh_path(self, path: str) -> None:
        """Pre-fill the mesh field (e.g. a host exported the current selection to it).

        Public hand-off point for a host that drives this panel. (Blender no
        longer does: it has a native Substance Bridge panel of its own.)"""
        self.ui.txt000.setText(path or "")

    def btn_browse_mesh(self) -> None:
        f = self.sb.file_dialog(
            file_types=MESH_EXTS,
            title="Select Mesh File",
            start_dir=os.path.dirname(self.ui.txt000.text()) or os.getcwd(),
            filter_description="Mesh Files",
            allow_multiple=False,
        )
        if f:
            self.ui.txt000.setText(f)

    def btn_browse_template(self) -> None:
        f = self.sb.file_dialog(
            file_types=["*.spt"],
            title="Select Project Template",
            start_dir=os.path.dirname(self.ui.txt001.text()) or os.getcwd(),
            filter_description="Painter Templates",
            allow_multiple=False,
        )
        if f:
            self.ui.txt001.setText(f)

    def btn_browse_project(self) -> None:
        # save_file_dialog (getSaveFileName) — a new project's .spp won't exist
        # yet, so an open dialog couldn't pick it.
        f = self.sb.save_file_dialog(
            file_types=["*.spp"],
            title="Select / Name Project File",
            start_dir=os.path.dirname(self.ui.txt002.text()) or os.getcwd(),
            filter_description="Painter Projects",
        )
        if f:
            self.ui.txt002.setText(f)

    # ------------------------------------------------------------------ session

    def _launch_painter(self) -> bool:
        exe = self.ui.cmb000.currentData()
        try:
            with self.sb.progress(text="Launching Substance 3D Painter..."):
                ok = self.conn.connect(gui=True, app_path=exe)
            if ok:
                self.logger.info("Connected to the Painter bridge.")
                self.logger.info(f"Project: {self.conn.invoke('project.info')}")
            else:
                self.logger.error("Painter launched but the bridge never came up.")
            return ok
        except Exception as e:
            self.logger.error(f"Launch failed: {e}")
            self.logger.debug(traceback.format_exc())
            return False
        finally:
            self._sync_launch_button()

    def _close_painter(self) -> None:
        try:
            self.conn.shutdown(force=True)
            self.logger.info("Painter session closed.")
        except Exception as e:
            self.logger.error(f"Failed to close Painter: {e}")
        self._sync_launch_button()

    def _sync_launch_button(self) -> None:
        """Keep the launch button's label -- and the watch on the session --
        in step with the session."""
        connected = self._connected
        self._shown_connected = connected
        self.ui.btn_launch.setText("Close Painter" if connected else "Launch Painter")
        if connected and not self._session_timer.isActive():
            self._session_timer.start()
        elif not connected:
            self._session_timer.stop()

    def _check_session(self) -> None:
        """The watch: a Painter that quit by itself is said, the button
        follows, and a run on it ends here -- its call out on the dead bridge
        is not waited on."""
        if self._shown_connected and not self._connected:
            self.logger.warning("Painter was closed outside the panel.")
            self._sync_launch_button()
            if self._run is not None:
                self._end_run(self._run)

    # ------------------------------------------------------------------ helpers

    def _collect_stages(self) -> Dict[str, bool]:
        return {
            name: bool(getattr(self.ui, name).isChecked())
            for name, _, _, _ in PIPELINE_STAGES
        }

    def _collect_bake_params(self) -> Dict[str, Any]:
        return {
            "bake_resolution": int(self.ui.cmb_bake_res.currentText()),
            "ao_secondary_rays": int(self.ui.spn_ao_rays.value()),
            "ao_max_distance": float(self.ui.spn_ao_max.value()),
            "ao_min_distance": float(self.ui.spn_ao_min.value()),
            "ao_spread_angle": float(self.ui.spn_ao_spread.value()),
            "ao_subsample": int(self.ui.spn_ao_subsample.value()),
            "ao_intensity": float(self.ui.spn_ao_intensity.value()),
            "blend_mode": self.ui.cmb_blend.currentText() or "Multiply",
            "include_curvature": bool(self.ui.chk_curvature.isChecked()),
            "curvature_intensity": float(self.ui.spn_curv_intensity.value()),
            "skip_existing_bakes": bool(self.ui.chk_skip_bakes.isChecked()),
        }

    def _validate(self, stages: Dict[str, bool]) -> bool:
        mesh = self.ui.txt000.text().strip()
        save_path = self.ui.txt002.text().strip()
        if stages.get("stage_open") and not (mesh or os.path.isfile(save_path)):
            self.logger.error(
                "Provide a Mesh File to create a project, or an existing "
                ".spp Project Save Path to open."
            )
            return False
        if stages.get("stage_save"):
            creating_new = stages.get("stage_open") and not os.path.isfile(save_path)
            if creating_new and not save_path:
                self.logger.error(
                    "Set a Project Save Path to save the project — a newly "
                    "created project has no file yet, so 'Save Project' needs a "
                    "destination (or an existing .spp to open)."
                )
                return False
        return True

    # ------------------------------------------------------------------ run

    def _plan_stages(
        self, stages: Dict[str, bool], mesh: str, template: Optional[str], save_path: str
    ) -> List[_Stage]:
        """The checked stages, in order, as calls a BackgroundTask can make.

        What they need from the widgets is read here, on the GUI thread, at
        Run: a stage touches no widget, and a field edited mid-run changes
        nothing in the run.
        """
        labels = {name: label for name, label, _, _ in PIPELINE_STAGES}
        conn = self.conn
        plan: List[_Stage] = []

        if stages["stage_open"]:

            def open_project() -> str:
                if save_path and os.path.isfile(save_path):
                    return f"Opened : {conn.invoke('project.open', path=save_path)}"
                created = conn.invoke(
                    "project.create", mesh_path=mesh, template_path=template
                )
                return f"Created: {created}"

            plan.append(_Stage(labels["stage_open"], open_project))

        if stages["stage_bake"]:
            params = self._collect_bake_params()

            def bake() -> str:
                # A real bake outlasts the client's 60 s default: wait as long
                # as the bridge lets the op run.
                result = conn.invoke(
                    "bake.lighting_to_diffuse",
                    timeout=PainterConnection.op_timeout(),
                    **params,
                )
                return f"Baked  : {result}"

            plan.append(_Stage(labels["stage_bake"], bake))

        if stages["stage_save"]:

            def save() -> str:
                # Asked when it runs: a project this run created has no file yet.
                if save_path and not os.path.isfile(save_path):
                    conn.invoke("project.save_as", path=save_path)
                else:
                    conn.invoke("project.save")
                return "Saved  : project written"

            plan.append(_Stage(labels["stage_save"], save))

        if stages["stage_export"]:
            out = os.path.join(os.path.dirname(save_path) or os.getcwd(), "export")

            def export() -> str:
                conn.invoke("export.textures", output_path=out, preset="")
                return f"Exported: {out}"

            plan.append(
                _Stage(labels["stage_export"], export, "Export skipped (not implemented)")
            )
        return plan

    def _run_workflow(self) -> None:
        """Start a run and return: its stages go off the GUI thread one at a
        time (:meth:`_next_stage`) -- a bake waits minutes on Painter, which on
        the GUI thread froze the panel and a DCC hosting it. Run reads Cancel
        until :meth:`_end_run` gives the panel back."""
        stages = self._collect_stages()
        if not self._validate(stages):
            return

        if not self._connected and not self._launch_painter():
            return

        mesh = self.ui.txt000.text().strip()
        template = self.ui.txt001.text().strip() or None
        save_path = self.ui.txt002.text().strip()

        run = _WorkflowRun(self.logger.isEnabledFor(logging.INFO), self.ui.b000.text())
        self._run = run
        self.ui.b000.setText("Cancel")
        # Every cancel of this run (the button, the footer's Esc-hold) comes in
        # on the GUI thread, so the listener may touch the widgets.
        run.cancel.add_listener(lambda _scope: self._show_cancel(run))
        try:
            run.stages = self._plan_stages(stages, mesh, template, save_path)
            if run.report:
                self.logger.log_box(
                    "SUBSTANCE WORKFLOW",
                    [
                        f"Mesh    : {os.path.basename(mesh) or '(none)'}",
                        f"Project : {os.path.basename(save_path) or '(unsaved)'}",
                        f"Stages  : {', '.join(k for k, v in stages.items() if v)}",
                    ],
                )
            # Started inside the run's scope, the bar's Esc-hold cancels the
            # run itself -- not just the bar, with the stages going on.
            with run.cancel.activate():
                self.ui.footer.start_progress(
                    total=len(run.stages) or None, text="Working: Substance Workflow"
                )
        except Exception as e:
            self._end_run(run, e)
            return
        self._next_stage(run)

    def _next_stage(self, run: _WorkflowRun) -> None:
        """Start *run*'s next stage on a BackgroundTask, or end the run: no
        stage left, or a cancel came while the last one ran."""
        stage = run.stage
        if stage is None or run.cancel.poll():
            self._end_run(run)
            return
        try:
            task = self.sb.BackgroundTask(stage.call, name="substance-workflow-stage")
            task.when_done(self.ui, lambda: self._stage_done(run, task))
            # Last: the tick pumps the loop, and a quick stage may end inside it.
            self.ui.footer.update_progress(
                run.index, f"{stage.label} ({run.index + 1}/{len(run.stages)})"
            )
        except Exception as e:
            self._end_run(run, e)

    def _stage_done(self, run: _WorkflowRun, task: Any) -> None:
        """A stage's task ended: its line joins the report and the next stage
        starts -- here, on the GUI thread, like every widget and log touch of
        a run."""
        if run is not self._run:
            return  # that run already ended (Painter closed under it)
        stage = run.stage
        try:
            line = task.result()
        except Exception as e:
            if not stage.skip_note:
                self._end_run(run, e)
                return
            # Warnings stay their own record — they're the actionable line,
            # and must not inherit the group's muted item colour.
            self.logger.warning(f"{stage.skip_note}: {e}")
        else:
            run.lines.append(line)
        run.index += 1
        self._next_stage(run)

    def _cancel_run(self) -> None:
        """Cancel (the Run button while a run is in flight)."""
        if self._run is not None:
            self._run.cancel.cancel("cancel button")

    def _show_cancel(self, run: _WorkflowRun) -> None:
        """A cancel came: said at once, though it lands between stages -- the
        bridge cannot stop an op mid-call, so the one under way finishes."""
        if run is not self._run or run.stage is None:
            return
        self.ui.b000.setText("Cancelling…")
        self.ui.b000.setEnabled(False)
        text = f"Cancelling: {run.stage.label} finishes first, then the run stops."
        self.ui.footer.setStatusText(text)
        self.logger.info(text)

    def _end_run(self, run: _WorkflowRun, error: Optional[BaseException] = None) -> None:
        """Say how *run* ended and give the panel back -- on every way out: all
        stages run, a cancel, a stage that raised, Painter closed under it."""
        if run is not self._run:
            return
        self._run = None
        # Logging pumps the loop: no click starts the next run mid-report.
        self.ui.b000.setEnabled(False)
        status = "Workflow ended."
        try:
            status = self._report_run(run, error)
        finally:
            self.ui.b000.setText(run.run_label)
            self.ui.b000.setEnabled(True)
            self.ui.footer.finish_progress(status)

    def _report_run(self, run: _WorkflowRun, error: Optional[BaseException]) -> str:
        """Log how *run* ended; returns the footer's closing text."""
        lines, stage = run.lines, run.stage
        if error is None and stage is None:
            if run.cancel.cancelled:
                self.logger.warning(
                    "The cancel came during the last stage, which finished: "
                    "the workflow ran to the end."
                )
            if run.report:
                # Guarded: nothing is checked in the stage menu is a legal (if
                # pointless) run, and log_group degrades an empty list to a
                # bare orphan title.
                if lines:
                    self.logger.log_group("Stages", lines)
                self.logger.log_box(
                    "WORKFLOW COMPLETE", [f"Stages run : {len(lines)}"], level="SUCCESS"
                )
            return "Workflow complete."

        label = stage.label if stage is not None else "the run"
        level = logging.ERROR
        if not self._connected:
            title, status = "Stages completed before Painter closed", "Painter closed."
            message = f"Workflow stopped: Painter closed during {label}."
        elif error is not None:
            title, status = "Stages completed before the failure", "Workflow failed."
            message = f"Workflow failed: {error}"
        else:  # a cancel: asked for, not a fault
            title, status = "Stages completed before the cancel", "Workflow cancelled."
            message, level = f"Workflow cancelled before {label}.", logging.WARNING
        # Whatever completed still gets reported — otherwise a late stop hides
        # every stage that did succeed.
        if run.report and lines:
            self.logger.log_group(title, lines)
        self.logger.log(level, message)
        if error is not None:
            # Stays at debug (as it always was): the panel's Log Level combo
            # defaults to INFO, and promoting the traceback would dump a full
            # stack on every failure for users who never asked for one. It is
            # a single multi-line string, so it is already one record.
            self.logger.debug(
                "".join(traceback.format_exception(type(error), error, error.__traceback__))
            )
        return status
