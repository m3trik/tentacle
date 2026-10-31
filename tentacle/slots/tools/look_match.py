# !/usr/bin/python
# coding=utf-8
"""Slots for the Look Match panel: light a baked scene to match a reference image.

The engine computes every look: ``ptk.LookMatch`` predicts a mix and scores
it, ``ptk.LookScore.summary`` reads each region the way a person does,
``ptk.LookFit`` and ``LookMatch.solve`` propose weights, ``ptk.LookSheet``
draws a region close up and the difference of two frames, ``ptk.LookCapture``
renders in the real WebXR viewer, and ``LookMatch.to_rig`` writes the rig the
library keeps. This module wires them to the widgets: edits are undo steps,
a fit or a solve is a proposal until it is accepted, and what takes seconds
runs off the UI thread (``uitk.BackgroundTask``). A standalone panel
(``tentacle/tcl_standalone.py``).
"""

from __future__ import annotations

import hashlib
import json
import os
import threading
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pythontk as ptk
from qtpy import QtCore, QtGui, QtWidgets

from tentacle import Slots

#: The engine's own document: the panel's help links to it.
DOCS_URL = "https://github.com/m3trik/pythontk/blob/main/docs/look_match.md"


class _MixEdit(QtGui.QUndoCommand):
    """One change to the mix, undone and redone whole. Edits that share a
    *merge_key* (a wheel's notches on one layer) merge into one step."""

    def __init__(self, slots, before, after, text: str, merge_key=None):
        super().__init__(text)
        self._slots, self.before, self.after = slots, before, after
        self.merge_key = merge_key

    def redo(self) -> None:
        self._slots._apply_mix(self.after)

    def undo(self) -> None:
        self._slots._apply_mix(self.before)

    def id(self) -> int:
        return 1 if self.merge_key is not None else -1

    def mergeWith(self, other) -> bool:
        if getattr(other, "merge_key", None) != self.merge_key:
            return False
        self.after = other.after
        return True


class _NoService:
    """The capture client a session's loop holds until this panel starts its own
    service: never the default address, where someone else's could answer."""

    def invoke(self, op, timeout=None, **request):
        raise RuntimeError("No capture service started by this panel yet.")


class _LookMatchSlotsInternal:
    """Conversions behind :class:`LookMatchSlots` (no widget state)."""

    @staticmethod
    def mix_key(mix) -> str:
        """A mix's identity: what a render records, so it can say it is stale."""
        text = json.dumps(mix.entries(), sort_keys=True)
        return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]

    @staticmethod
    def status_glyph(row: Dict[str, Any]) -> str:
        """A region's state in a shape, not only a colour: within, brighter,
        darker, or off in colour."""
        if row["within"] is None:
            return "-"
        if row["within"]:
            return "✓"
        brightness = row.get("brightness")
        if brightness is not None and abs(brightness) >= 0.1:
            return "▲" if brightness > 0 else "▼"
        return "●"

    @staticmethod
    def brightness_text(value: Optional[float]) -> str:
        return "" if value is None else f"{value * 100:+.0f}%"


class LookMatchSlots(Slots, _LookMatchSlotsInternal):
    """The Look Match panel (see the module docstring)."""

    DOCS_URL = DOCS_URL

    #: One letter where a column is a tick (its header tooltip says what): the
    #: names need the width.
    COLUMNS = ("S", "M", "F", "Layer", "Weight", "Kelvin", "Specular", "Share")
    SOLO, MUTE, FREE, LAYER, WEIGHT, KELVIN, SPECULAR, SHARE = range(len(COLUMNS))
    REGION_COLUMNS = ("", "Region", "Brightness", "Colour", "Weight")
    #: The region table's editable columns (while editing regions).
    REGION_NAME, REGION_WEIGHT = 1, 4
    #: Draw tools (``uitk.ImageView`` tool names) -> the region shape each draws.
    DRAW_TOOLS = {"rect": "rect", "ellipse": "ellipse", "polygon": "poly", "line": "line"}
    #: The comparison's modes: (label, CompareView mode or "difference").
    VIEW_MODES = (
        ("Split", "split"),
        ("Side by side", "side"),
        ("Blink", "blink"),
        ("Difference", "difference"),
        ("A only", "a"),
        ("B only", "b"),
    )
    #: Weights span decades (a narrow spot 50, a wide area light 0.1): a log bar.
    WEIGHT_RANGE = (0.001, 100.0)
    KELVIN_RANGE = (1800.0, 12000.0)
    KELVIN_RAMP = ((0.0, "#ff8a2a"), (0.3, "#ffcf9a"), (0.5, "#fff3e6"), (1.0, "#a6c6ff"))
    #: A middle-drag doubles (or halves) a weight every this many pixels; a
    #: wheel notch multiplies it by this (Shift: the fine step).
    SCRUB_DOUBLING_PX = 80.0
    WHEEL_STEP, WHEEL_FINE = 1.1, 1.02
    #: Kinds in the order the mix table groups them, with their section titles.
    SECTIONS = (("light", "Lights"), ("emission", "Emission"), ("panel", "Panels"))
    GHOST_ROLE = QtCore.Qt.UserRole + 11
    NAME_ROLE = QtCore.Qt.UserRole + 12
    #: Residual band a region is "within" (0.1 is about a 10% miss): the fit's default.
    TOLERANCE = 0.1
    #: Milliseconds of quiet after a gesture before the scores catch up; after a
    #: typed edit or an undo, before everything does.
    SETTLE_MS, EDIT_MS = 300, 30
    STATUS_COLORS = {True: "#59c27a", False: "#e0a33a", None: "#888888"}
    #: Seconds the bake worker stays up after the last renewal (the panel renews
    #: while it bakes), and how often it renews; how long a worker it launched
    #: may take to come up (a GUI Maya opening a production scene).
    LEASE_S, LEASE_RENEW_MS, WORKER_START_S = 300.0, 60_000, 900.0

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.ui = self.sb.loaded_ui.look_match
        self.session: Optional[str] = None
        self.data: Dict[str, Any] = {}
        self.match = None
        self.size: Tuple[int, int] = (0, 0)
        self.reference = None
        self.preview = None
        self.score = None
        self.summary: List[Dict[str, Any]] = []
        self.region: Optional[str] = None
        self.proposal = None
        self._proposal_label = self._proposal_text = ""
        self.frames: Dict[str, Dict[str, Any]] = {}
        self.service: Optional[Tuple[Any, str]] = None
        # One start at a time (a render and an Update can ask together), and
        # the session the service was started on: never another's renders.
        self._service_lock = threading.Lock()
        self._service_session: Optional[str] = None
        self.loop = None  # ptk.LookLoop over the open session: bakes, captures
        # The queues of the bake workers this panel launched (stop_worker ends
        # those, never another's), and the one an Update in progress renews.
        self._worker_queues: List[Any] = []
        self._leased_queue = None
        # The timers die with the panel: a lease renewed past it would keep
        # the worker (a Maya) up for the host's whole life.
        self._lease_timer = QtCore.QTimer(self.ui)
        self._lease_timer.setInterval(self.LEASE_RENEW_MS)
        self._lease_timer.timeout.connect(self._renew_lease)
        self.undo = QtGui.QUndoStack(self.ui)  # lives and dies with the panel
        self._solo: set = set()
        self._mute: set = set()
        self._free: set = set()
        self._rows: Dict[str, int] = {}
        self._filling = False
        self._scrub: Optional[Tuple[str, float, Any]] = None
        self._batch: Optional[Dict[str, Dict[str, Any]]] = None
        self._owners: Dict[str, List[Tuple[str, float]]] = {}
        self._tasks: Dict[str, Any] = {}  # name -> its uitk BackgroundTask
        self._saved_mixes: Dict[str, Tuple[float, Any]] = {}
        # Two tiers: during a drag or a wheel roll only the picture follows
        # (predicted at half size); the scores, shares and close-up follow
        # once the gesture pauses.
        self._refresh_timer = QtCore.QTimer(self.ui)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._refresh)
        self._quick_timer = QtCore.QTimer(self.ui)
        self._quick_timer.setSingleShot(True)
        self._quick_timer.setInterval(0)
        self._quick_timer.timeout.connect(self._quick_refresh)
        self._opening: Optional[str] = None
        self._shares: Dict[str, float] = {}
        self._detail = None  # the selected region's close-up (a PIL image)
        self._stale = False  # the mix moved while an analysis ran
        self._solve_picked = False  # the user chose the layer to solve
        self._windows: Dict[str, Tuple[int, int, int, int]] = {}  # outline-less regions' bounds
        self.undo.indexChanged.connect(lambda *_: self._sync_undo_buttons())
        self.ui.run_when_ready(self._initialize_ui)

    # ------------------------------------------------------------------ setup
    def _initialize_ui(self) -> None:
        # The mix and the scores are the session's, not settings: no cell is a
        # value to restore, and a combo filled per session must not have an
        # index restored into it.
        # Editing regions starts off: a restored check would show the button on
        # with its tools hidden.
        for name in ("tbl_mix", "tbl_regions", "cmb_session", "cmb_mix", "cmb_a", "cmb_b", "cmb_solve", "b_edit_regions"):
            getattr(self.ui, name).restore_state = False
        self.ui.footer.setDefaultStatusText("Open a session to begin.")
        self.ui.frm_proposal.setVisible(False)
        self.ui.frm_region_tools.setVisible(False)
        self.ui.b_edit_regions.setChecked(False)  # whatever was restored first
        for keys, action in (
            ("Ctrl+Z", self.undo.undo),
            ("Ctrl+Shift+Z", self.undo.redo),
            ("Ctrl+Y", self.undo.redo),
        ):
            shortcut = QtWidgets.QShortcut(QtGui.QKeySequence(keys), self.ui)
            shortcut.setContext(QtCore.Qt.WidgetWithChildrenShortcut)
            shortcut.activated.connect(action)
        sizes = self.ui.settings.value("splitter_sizes", None)
        if sizes:
            self.ui.spl_main.setSizes([int(s) for s in sizes])
        else:
            self.ui.spl_main.setSizes([470, 620, 360])
        self.ui.spl_main.splitterMoved.connect(
            lambda *_: self.ui.settings.setValue("splitter_sizes", self.ui.spl_main.sizes())
        )
        app = QtWidgets.QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop_service)
            app.aboutToQuit.connect(self.stop_worker)
        self._sync_undo_buttons()
        recent = self._recent()
        if recent and os.path.isfile(recent[0]):
            self.open_session(recent[0])

    def header_init(self, widget) -> None:
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Look Match",
                body="Match a scene's lighting to a reference image, by eye and "
                "region by region, from light layers baked once.",
                steps=[
                    "Open a session (the <b>Session</b> combo's option box).",
                    "Change the mix: type a weight, drag it with the middle "
                    "button, or roll the wheel over it (Shift: finer).",
                    "Pick a region to see which lights own it; <b>Solve</b> or "
                    "<b>Fit</b> propose weights you accept or discard.",
                    "<b>Render in WebXR</b> shows the real viewer, highlights "
                    "included; <b>Save to Rig Library</b> hands the mix to Maya.",
                ],
            ),
            url=self.DOCS_URL,
        )
        widget.menu.add(
            "QPushButton",
            setText="Open Session…",
            setObjectName="btn_open_session",
            clicked=lambda *_: self.browse_session(),
        )
        widget.menu.add(
            "QPushButton",
            setText="Reveal Session Folder",
            setObjectName="btn_reveal_session",
            clicked=lambda *_: self._reveal(os.path.dirname(self.session or "")),
        )

    def cmb_session_init(self, widget) -> None:
        widget.option_box.menu.setTitle("Sessions")
        widget.option_box.menu.add(
            "QPushButton",
            setText="Open…",
            setObjectName="btn_session_open",
            setToolTip="Open a look-match session file.",
            clicked=lambda *_: self.browse_session(),
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Reveal",
            setObjectName="btn_session_reveal",
            setToolTip="Open the session's folder.",
            clicked=lambda *_: self._reveal(os.path.dirname(self.session or "")),
        )
        widget.option_box.menu.add(
            "QPushButton",
            setText="Forget",
            setObjectName="btn_session_forget",
            setToolTip="Take this session off the list (its files stay).",
            clicked=lambda *_: self._forget_session(),
        )
        self._fill_session_combo()
        widget.currentIndexChanged.connect(self._on_session_picked)

    def cmb_mix_init(self, widget) -> None:
        widget.option_box.menu.setTitle("Mixes")
        for text, name, tip, call in (
            ("Save", "btn_mix_save", "Write the mix over the one picked.", self.save_mix),
            ("Save As…", "btn_mix_save_as", "Write the mix under a new name.", self.save_mix_as),
            ("Delete", "btn_mix_delete", "Delete the picked mix's file.", self.delete_mix),
        ):
            widget.option_box.menu.add(
                "QPushButton",
                setText=text,
                setObjectName=name,
                setToolTip=tip,
                clicked=lambda *_, c=call: c(),
            )
        widget.currentIndexChanged.connect(self._on_mix_picked)

    def b_undo_init(self, widget) -> None:
        widget.setIcon(self.sb.get_icon("undo"))

    def b_redo_init(self, widget) -> None:
        widget.setIcon(self.sb.get_icon("redo"))

    def b_undo(self) -> None:
        self.undo.undo()

    def b_redo(self) -> None:
        self.undo.redo()

    def b_fit_init(self, widget) -> None:
        menu = widget.option_box.menu
        menu.setTitle("Fit")
        menu.add(
            "QCheckBox",
            setText="Selected region only",
            setObjectName="chk_fit_selected",
            setChecked=True,
            setToolTip="Score the fit on the selected region alone (none selected: every region).",
        )
        menu.add(
            "QCheckBox",
            setText="Also colour temperature",
            setObjectName="chk_fit_kelvin",
            setChecked=False,
            setToolTip="Fit the colour temperature too -- one layer at a time: fitting "
            "several layers' colours at once trades one for another.",
        )
        menu.add(
            "QDoubleSpinBox",
            setObjectName="spn_fit_regularize",
            setPrefix="Stay close: ",
            setMinimum=0.0,
            setMaximum=5.0,
            setSingleStep=0.1,
            setValue=0.3,
            setToolTip="How strongly the fit keeps weights near where they are.",
        )
        menu.add(
            "QDoubleSpinBox",
            setObjectName="spn_fit_tolerance",
            setPrefix="Good enough: ",
            setMinimum=0.0,
            setMaximum=1.0,
            setSingleStep=0.05,
            setValue=self.TOLERANCE,
            setToolTip="A miss this small counts as a match (0.1 is about 10%).",
        )

    def tbl_mix_init(self, widget) -> None:
        widget.setColumnCount(len(self.COLUMNS))
        widget.setHorizontalHeaderLabels(list(self.COLUMNS))
        widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        header = widget.horizontalHeader()
        for column in (self.SOLO, self.MUTE, self.FREE):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.Fixed)
            widget.setColumnWidth(column, 24)
        header.setSectionResizeMode(self.LAYER, QtWidgets.QHeaderView.Stretch)
        header.setMinimumSectionSize(24)
        for column, width in ((self.WEIGHT, 110), (self.KELVIN, 90), (self.SPECULAR, 60), (self.SHARE, 70)):
            widget.setColumnWidth(column, width)
        header_tips = {
            self.SOLO: "Solo: show only the soloed layers (the preview and a render; the mix is unchanged).",
            self.MUTE: "Mute: hide a layer from the preview and a render (the mix is unchanged).",
            self.FREE: "Fit: what Fit may change.",
            self.WEIGHT: "The layer's weight, in its bake's own units (a log scale).",
            self.KELVIN: "Colour temperature (lights only).",
            self.SPECULAR: "Highlight level: shows in a WebXR render only (the preview "
            "holds highlights at their baked level).",
            self.SHARE: "The layer's share of the light in the selected region.",
        }
        for column, tip in header_tips.items():
            item = widget.horizontalHeaderItem(column)
            if item is not None:
                item.setToolTip(tip)
        widget.setItemDelegateForColumn(
            self.WEIGHT,
            self.sb.ValueBarDelegate(
                widget,
                minimum=self.WEIGHT_RANGE[0],
                maximum=self.WEIGHT_RANGE[1],
                scale="log",
                formatter=lambda v: f"{v:.3g}",
                ghost_role=self.GHOST_ROLE,
            ),
        )
        widget.setItemDelegateForColumn(
            self.KELVIN,
            self.sb.ValueBarDelegate(
                widget,
                minimum=self.KELVIN_RANGE[0],
                maximum=self.KELVIN_RANGE[1],
                gradient=self.KELVIN_RAMP,
                formatter=lambda v: f"{v:.0f}K",
            ),
        )
        widget.setItemDelegateForColumn(
            self.SHARE,
            self.sb.ValueBarDelegate(widget, formatter=lambda v: f"{v * 100:.0f}%"),
        )
        widget.set_scrub_columns([self.WEIGHT])
        widget.set_wheel_scrub_columns([self.WEIGHT])
        widget.cellChanged.connect(self._on_mix_cell_changed)
        widget.cellScrubStarted.connect(self._on_scrub_started)
        widget.cellScrubMoved.connect(self._on_scrub_moved)
        widget.cellScrubFinished.connect(self._on_scrub_finished)
        widget.cellWheelScrolled.connect(self._on_wheel)
        widget.editBatchStarted.connect(self._begin_batch)
        widget.editBatchFinished.connect(self._end_batch)

    def chk_all_init(self, widget) -> None:
        widget.setChecked(bool(self.ui.settings.value("all_layers", False) in (True, "true")))
        widget.toggled.connect(self._on_all_layers)

    def tbl_regions_init(self, widget) -> None:
        widget.setColumnCount(len(self.REGION_COLUMNS))
        widget.setHorizontalHeaderLabels(list(self.REGION_COLUMNS))
        widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        widget.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        header = widget.horizontalHeader()
        for column in (0, 2, 3, self.REGION_WEIGHT):
            header.setSectionResizeMode(column, QtWidgets.QHeaderView.ResizeToContents)
        header.setSectionResizeMode(self.REGION_NAME, QtWidgets.QHeaderView.Stretch)
        widget.setColumnHidden(self.REGION_WEIGHT, True)  # shown while editing regions
        widget.itemSelectionChanged.connect(self._on_region_selected)
        widget.cellChanged.connect(self._on_region_cell_changed)

    def cmb_mode_init(self, widget) -> None:
        widget.addItems([label for label, _ in self.VIEW_MODES])
        widget.setCurrentIndex(0)
        widget.currentIndexChanged.connect(lambda *_: self._show_compare())

    def cmb_a_init(self, widget) -> None:
        widget.currentIndexChanged.connect(lambda *_: self._show_compare())

    def cmb_b_init(self, widget) -> None:
        widget.currentIndexChanged.connect(lambda *_: self._show_compare())

    def cmb_solve_init(self, widget) -> None:
        # ``activated``: a choice the user made (a refill sets the owner instead).
        widget.activated.connect(lambda *_: setattr(self, "_solve_picked", True))

    def cmp_view_init(self, widget) -> None:
        widget.overlay_clicked.connect(self._on_overlay_clicked)
        widget.hovered.connect(self._on_hovered)
        widget.view_a.shape_drawn.connect(self._on_shape_drawn)

    # ------------------------------------------------------------------ sessions
    def _recent(self) -> List[str]:
        value = self.ui.settings.value("recent_sessions", []) or []
        return [str(v) for v in (value if isinstance(value, (list, tuple)) else [value])]

    def _fill_session_combo(self) -> None:
        combo = self.ui.cmb_session
        combo.blockSignals(True)
        try:
            combo.clear()
            for path in self._recent():
                combo.addItem(self._session_label(path), path)
            if self.session:
                index = combo.findData(self.session)
                combo.setCurrentIndex(index if index >= 0 else -1)
        finally:
            combo.blockSignals(False)

    @staticmethod
    def _session_label(path: str) -> str:
        folder = os.path.basename(os.path.dirname(path))
        name = os.path.splitext(os.path.basename(path))[0]
        return folder if name == "session" else f"{folder}/{name}"

    def _on_session_picked(self, index: int) -> None:
        path = self.ui.cmb_session.itemData(index)
        if path and path != self.session:
            self.open_session(path)

    def browse_session(self) -> None:
        start = os.path.dirname(self.session) if self.session else os.path.expanduser("~")
        path = self.sb.file_dialog(
            file_types=["*.json"],
            title="Open a look-match session",
            start_dir=start,
            filter_description="Look-match sessions",
            allow_multiple=False,
        )
        if path:
            self.open_session(path if isinstance(path, str) else path[0])

    def _forget_session(self) -> None:
        if not self.session:
            return
        recent = [p for p in self._recent() if os.path.normcase(p) != os.path.normcase(self.session)]
        self.ui.settings.setValue("recent_sessions", recent)
        self._fill_session_combo()

    def open_session(self, path: str) -> bool:
        """Start opening the session file at *path*; whether it started (a file
        that is not a session is refused at once, with why). The layers load
        off the UI thread -- seconds for a production store -- and the session
        open now stays usable until the new one is ready."""
        path = os.path.abspath(path)
        try:
            data = ptk.LookSession.read(path)
        except Exception as error:  # a file that is not a session: say so, keep the open one
            self.ui.footer.setStatusText(f"Could not open {os.path.basename(path)}: {error}", level="error")
            return False
        self._opening = path
        self.ui.footer.start_progress(text=f"Opening {self._session_label(path)}…")

        def load():
            match = ptk.LookMatch.open(path)
            size = tuple(match.size or (820, 480))
            reference = match.reference(size)
            # The first analysis here too: it reads and sizes the mix's layers
            # and builds the regions' masks (painted ones take seconds), once;
            # and the half size a drag predicts at, so the first drag is quick.
            analysis = self._analyse(match, match.mix, size, reference, None, self.TOLERANCE, 0)
            match.predictor.linear(match.mix, self._half(size))
            return match, size, reference, analysis

        task = self.sb.BackgroundTask(load, "look-match-open")

        def done() -> None:
            if self._opening != path:  # another was asked for since
                return
            self._opening = None
            try:
                match, size, reference, analysis = task.result()
            except Exception as error:
                self.ui.footer.finish_progress(f"Could not open {os.path.basename(path)}: {error}")
                return
            self._opened(path, data, match, size, reference, analysis)

        task.when_done(self.ui, done)
        return True

    def _opened(self, path: str, data, match, size, reference, analysis) -> None:
        """A loaded session in: the panel shows it."""
        if self.session and os.path.normcase(self.session) != os.path.normcase(path):
            self.stop_service(wait=False)
        self.session, self.data, self.match = path, data, match
        self.size, self.reference = size, reference
        self.loop = ptk.LookLoop(path, client=_NoService(), match=match)
        self.loop.worker_stale = self.WORKER_START_S
        self.undo.clear()
        self.proposal, self.region, self.frames = None, None, {}
        self._owners, self._saved_mixes = {}, {}
        # Nothing is free until ticked: a fit of everything at once is what
        # misled (it traded the corner glows away to chase one rim).
        self._solo, self._mute, self._free = set(), set(), set()
        recent = [path] + [p for p in self._recent() if os.path.normcase(p) != os.path.normcase(path)]
        self.ui.settings.setValue("recent_sessions", recent[:12])
        self._fill_session_combo()
        self._fill_mix_combo()
        self._fill_source_combos()
        self._fill_mix_table()
        self._fill_solve_combo()
        self._show_proposal()
        self._apply_analysis(analysis)
        self._sync_update_button()
        self.ui.footer.finish_progress(
            f"Opened {self._session_label(path)}: {len(match.layers.names())} layers, "
            f"{len(match.target.regions)} regions."
        )

    # ------------------------------------------------------------------ mixes on disk
    def _mix_store(self):
        """The session's saved mixes: the engine's store (``LookSession.mixes``)."""
        return ptk.LookSession.mixes(self.session, self.data)

    def _mix_files(self) -> List[str]:
        store = self._mix_store()
        return [str(store.path(name)) for name in store.list()]

    def _fill_mix_combo(self) -> None:
        combo = self.ui.cmb_mix
        current = ptk.LookSession.resolve(self.session, self.data, self.data.get("mix"))
        combo.blockSignals(True)
        try:
            combo.clear()
            for path in self._mix_files():
                combo.addItem(os.path.splitext(os.path.basename(path))[0], path)
            index = combo.findData(current) if current else -1
            combo.setCurrentIndex(index)
        finally:
            combo.blockSignals(False)

    def _picked_mix_path(self) -> Optional[str]:
        return self.ui.cmb_mix.itemData(self.ui.cmb_mix.currentIndex()) if self.ui.cmb_mix.count() else None

    def _on_mix_picked(self, index: int) -> None:
        path = self.ui.cmb_mix.itemData(index)
        if not path or self.match is None:
            return
        try:
            mix = ptk.LightMix.load(path)
        except Exception as error:
            self.ui.footer.setStatusText(f"Could not read {os.path.basename(path)}: {error}", level="error")
            return
        self._push(mix, f"Open mix {os.path.basename(path)}")
        self._fill_mix_table()

    def save_mix(self) -> None:
        path = self._picked_mix_path()
        if not path:
            self.save_mix_as()
            return
        try:
            self._mix_store().save(os.path.splitext(os.path.basename(path))[0], self.match.mix.to_dict())
        except OSError as error:
            self.ui.footer.setStatusText(f"Could not save {os.path.basename(path)}: {error}", level="error")
            return
        self._saved_mixes.pop(path, None)
        self.ui.footer.setStatusText(f"Saved {os.path.basename(path)}.", level="success")

    def save_mix_as(self) -> None:
        if self.match is None:
            return
        name, ok = QtWidgets.QInputDialog.getText(self.ui, "Save Mix As", "Mix name:")
        name = ptk.StrUtils.to_legal_filename(name.strip()) if ok and name and name.strip() else ""
        if not name:
            return
        store = self._mix_store()
        # The name the store files it under (its own spelling rules), which is
        # what the list and the footer show.
        name = store.sanitize_preset_name(name)
        if store.exists(name) and not self._confirm(f"{name} exists. Replace it?"):
            return
        try:
            path = str(store.save(name, self.match.mix.to_dict()))
        except OSError as error:
            self.ui.footer.setStatusText(f"Could not save {name}: {error}", level="error")
            return
        name = os.path.splitext(os.path.basename(path))[0]
        self._fill_mix_combo()
        self._fill_source_combos()  # a new mix to compare against
        self.ui.cmb_mix.blockSignals(True)
        self.ui.cmb_mix.setCurrentIndex(self.ui.cmb_mix.findData(path))
        self.ui.cmb_mix.blockSignals(False)
        self.ui.footer.setStatusText(f"Saved {name}.", level="success")

    def delete_mix(self) -> None:
        """Delete the picked mix: to the platform's trash, where it can be
        restored; permanently only where no trash would take it, and said so."""
        path = self._picked_mix_path()
        if not path:
            return
        name = os.path.splitext(os.path.basename(path))[0]
        trash = ptk.FileUtils.trash_name()
        permanent = not ptk.FileUtils.can_trash(path)
        if not self._confirm(
            f"Delete {name} permanently? The {trash} will not take it, so this cannot be undone."
            if permanent
            else f"Move {name} to the {trash}?"
        ):
            return
        try:
            gone = self._mix_store().delete(name, trash=not permanent)
        except OSError as error:
            self.ui.footer.setStatusText(f"Could not delete {name}: {error}", level="error")
            return
        if not gone:
            self.ui.footer.setStatusText(f"The {trash} would not take {name}; it is still there.", level="warning")
            return
        self._fill_mix_combo()
        self._fill_source_combos()
        self.ui.footer.setStatusText(
            f"Deleted {name}." if permanent else f"Moved {name} to the {trash}.", level="success"
        )

    def _confirm(self, text: str) -> bool:
        answer = QtWidgets.QMessageBox.question(self.ui, "Look Match", text)
        return answer == QtWidgets.QMessageBox.Yes

    # ------------------------------------------------------------------ the mix table
    def _names_shown(self) -> List[str]:
        layers = self.match.layers
        names = set(layers.names()) if self.ui.chk_all.isChecked() else set(self.match.mix.names())
        return sorted(n for n in names if n in layers)

    def _fill_mix_table(self) -> None:
        table = self.ui.tbl_mix
        mix, layers = self.match.mix, self.match.layers
        shown = self._names_shown()
        self._filling = True
        try:
            table.setRowCount(0)
            self._rows = {}
            groups = {kind: [n for n in shown if layers.info(n).get("kind", "light") == kind] for kind, _ in self.SECTIONS}
            known = {kind for kind, _ in self.SECTIONS}
            groups["other"] = [n for n in shown if layers.info(n).get("kind", "light") not in known]
            for kind, title in self.SECTIONS + (("other", "Other"),):
                names = groups.get(kind) or []
                if not names:
                    continue
                self.sb.TableWidget.add_section_row(table, title)
                for name in names:
                    row = table.rowCount()
                    table.insertRow(row)
                    self._rows[name] = row
                    self._fill_row(row, name, mix)
        finally:
            self._filling = False

    def _check_item(self, checked: bool, tip: str) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem()
        item.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsSelectable)
        item.setCheckState(QtCore.Qt.Checked if checked else QtCore.Qt.Unchecked)
        item.setToolTip(tip)
        return item

    def _number_item(self, value: Optional[float], editable: bool) -> QtWidgets.QTableWidgetItem:
        item = QtWidgets.QTableWidgetItem()
        flags = QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable
        if editable:
            flags |= QtCore.Qt.ItemIsEditable
        item.setFlags(flags)
        if value is None:
            item.setText("—")
        else:
            item.setData(QtCore.Qt.EditRole, float(value))
        return item

    def _fill_row(self, row: int, name: str, mix) -> None:
        table = self.ui.tbl_mix
        kind = self.match.layers.kind(name)
        table.setItem(row, self.SOLO, self._check_item(name in self._solo, "Solo"))
        table.setItem(row, self.MUTE, self._check_item(name in self._mute, "Mute"))
        table.setItem(row, self.FREE, self._check_item(name in self._free, "Fit may change it"))
        label = QtWidgets.QTableWidgetItem(name)
        label.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable)
        label.setData(self.NAME_ROLE, name)
        info = self.match.layers.info(name)
        label.setToolTip(
            f"{name}: {info.get('kind', 'light')} layer"
            + ("" if kind.shippable else " (viewer only: no export carries it)")
        )
        table.setItem(row, self.LAYER, label)
        table.setItem(row, self.WEIGHT, self._number_item(mix.weight(name), True))
        table.setItem(row, self.KELVIN, self._number_item(mix.kelvin(name) if kind.tinted else None, kind.tinted))
        table.setItem(row, self.SPECULAR, self._number_item(mix.specular(name) if kind.lights else None, kind.lights))
        table.setItem(row, self.SHARE, self._number_item(None, False))
        self._style_row(row, mix.weight(name) > 0)

    def _style_row(self, row: int, active: bool) -> None:
        item = self.ui.tbl_mix.item(row, self.LAYER)
        if item is not None:
            color = self.ui.tbl_mix.palette().color(
                QtGui.QPalette.Text if active else QtGui.QPalette.PlaceholderText
            )
            item.setForeground(color)

    def _row_name(self, row: int) -> Optional[str]:
        item = self.ui.tbl_mix.item(row, self.LAYER)
        return item.data(self.NAME_ROLE) if item is not None else None

    def _update_mix_cells(self, names: Optional[Sequence[str]] = None) -> None:
        """The table's values from the mix (no rebuild: selection and scroll
        stay); only *names*' rows when given (a drag's one layer)."""
        mix = self.match.mix
        ghost = self.proposal
        if any(n not in self._rows and n in self.match.layers for n in mix.names()):
            self._fill_mix_table()  # a layer the table does not show yet
        rows = self._rows if names is None else {n: self._rows[n] for n in names if n in self._rows}
        self._filling = True
        try:
            for name, row in rows.items():
                kind = self.match.layers.kind(name)
                weight = self.ui.tbl_mix.item(row, self.WEIGHT)
                if weight is not None:
                    weight.setData(QtCore.Qt.EditRole, float(mix.weight(name)))
                    weight.setData(
                        self.GHOST_ROLE,
                        float(ghost.weight(name)) if ghost is not None and ghost.weight(name) != mix.weight(name) else None,
                    )
                kelvin = self.ui.tbl_mix.item(row, self.KELVIN)
                if kelvin is not None and kind.tinted:
                    if mix.kelvin(name):
                        kelvin.setData(QtCore.Qt.EditRole, float(mix.kelvin(name)))
                    else:  # white: no temperature
                        kelvin.setData(QtCore.Qt.EditRole, None)
                        kelvin.setText("—")
                specular = self.ui.tbl_mix.item(row, self.SPECULAR)
                if specular is not None and kind.lights:
                    specular.setData(QtCore.Qt.EditRole, float(mix.specular(name)))
                self._style_row(row, mix.weight(name) > 0)
        finally:
            self._filling = False

    def _on_all_layers(self, checked: bool) -> None:
        self.ui.settings.setValue("all_layers", bool(checked))
        if self.match is not None:
            self._fill_mix_table()
            self._schedule_refresh()

    def _on_mix_cell_changed(self, row: int, column: int) -> None:
        if self._filling or self.match is None:
            return
        name = self._row_name(row)
        if name is None:
            return
        item = self.ui.tbl_mix.item(row, column)
        if column in (self.SOLO, self.MUTE, self.FREE):
            target = {self.SOLO: self._solo, self.MUTE: self._mute, self.FREE: self._free}[column]
            (target.add if item.checkState() == QtCore.Qt.Checked else target.discard)(name)
            if column != self.FREE:
                self._schedule_refresh()
            return
        field = {self.WEIGHT: "weight", self.KELVIN: "kelvin", self.SPECULAR: "specular"}.get(column)
        if field is None:
            return
        try:
            value = float(item.data(QtCore.Qt.EditRole))
        except (TypeError, ValueError):
            self._update_mix_cells()  # not a number: show the mix's own value again
            return
        if field in ("weight", "specular") and value < 0:
            value = 0.0
        if self._batch is not None:
            self._batch.setdefault(name, {})[field] = value
            return
        self._edit({name: {field: value}}, f"Set {name} {field}")

    def _begin_batch(self) -> None:
        self._batch = {}

    def _end_batch(self) -> None:
        changes, self._batch = self._batch or {}, None
        if changes:
            self._edit(changes, f"Set {len(changes)} layers")

    def _on_scrub_started(self, row: int, column: int) -> None:
        name = self._row_name(row)
        if name is not None and self.match is not None:
            self._scrub = (name, max(self.match.mix.weight(name), self.WEIGHT_RANGE[0]), self.match.mix)

    def _on_scrub_moved(self, row: int, column: int, dx: int, dy: int) -> None:
        if self._scrub is None:
            return
        name, start, before = self._scrub
        weight = self._clamp_weight(start * 2.0 ** (dx / self.SCRUB_DOUBLING_PX))
        self.match.mix = before.with_weights({name: weight})  # live; one undo step at the end
        self._update_mix_cells([name])
        self._schedule_refresh(quick=True)

    def _on_scrub_finished(self, row: int, column: int) -> None:
        if self._scrub is None:
            return
        name, _start, before = self._scrub
        self._scrub = None
        after = self.match.mix
        if after.weight(name) != before.weight(name):
            self._discard_proposal()
            self.undo.push(_MixEdit(self, before, after, f"Drag {name} weight"))

    def _on_wheel(self, row: int, column: int, steps: int, modifiers) -> None:
        name = self._row_name(row)
        if name is None or self.match is None:
            return
        step = self.WHEEL_FINE if modifiers & QtCore.Qt.ShiftModifier else self.WHEEL_STEP
        weight = self._clamp_weight(max(self.match.mix.weight(name), self.WEIGHT_RANGE[0]) * step**steps)
        self._edit({name: {"weight": weight}}, f"Roll {name} weight", merge_key=("wheel", name))
        self._schedule_refresh(quick=True)
        self.ui.tbl_mix.refresh_active_editor()

    def _clamp_weight(self, weight: float) -> float:
        return min(max(weight, self.WEIGHT_RANGE[0]), self.WEIGHT_RANGE[1])

    # ------------------------------------------------------------------ edits and undo
    def _edit(self, changes: Dict[str, Dict[str, Any]], text: str, merge_key=None) -> None:
        """Change the mix by *changes* (``{layer: {field: value}}``), one undo step."""
        before = self.match.mix
        self._push(before.with_entries(changes), text, merge_key)

    def _push(self, after, text: str, merge_key=None) -> None:
        self._discard_proposal()
        self.undo.push(_MixEdit(self, self.match.mix, after, text, merge_key))

    def _apply_mix(self, mix) -> None:
        """What an undo step does: the mix in, the view after it."""
        self.match.mix = mix
        self._update_mix_cells()
        self._schedule_refresh()

    def _sync_undo_buttons(self) -> None:
        try:
            states = (
                (self.ui.b_undo, self.undo.canUndo(), self.undo.undoText()),
                (self.ui.b_redo, self.undo.canRedo(), self.undo.redoText()),
            )
        except RuntimeError:  # the stack clears itself as the panel is destroyed
            return
        for button, can, text in states:
            button.setEnabled(can)
            if can:
                button.setToolTip(text)

    # ------------------------------------------------------------------ the view
    def _effective_mix(self):
        """The mix as shown: solo and mute applied (the mix itself is unchanged)."""
        mix = self.match.mix
        off = {n: {"weight": 0.0} for n in mix.names() if n in self._mute or (self._solo and n not in self._solo)}
        return mix.with_entries(off) if off else mix

    def _schedule_refresh(self, quick: bool = False) -> None:
        """Refresh soon: *quick* (a gesture) shows the picture now and the rest
        once the gesture pauses."""
        if quick:
            self._quick_timer.start()
        self._refresh_timer.start(self.SETTLE_MS if quick else self.EDIT_MS)

    def _quick_refresh(self) -> None:
        """The picture alone, predicted at half size and shown at full: fast
        enough to follow a drag (the scores follow when it pauses)."""
        if self.match is None:
            return
        import numpy as np

        width, height = self.size
        small = self.match.predict(self._effective_mix(), self._half(self.size))
        big = np.repeat(np.repeat(small, 2, axis=0), 2, axis=1)[:height, :width]
        if big.shape[:2] != (height, width):  # an odd size: the last row or column again
            big = np.pad(big, ((0, height - big.shape[0]), (0, width - big.shape[1]), (0, 0)), mode="edge")
        self.preview = big
        self._show_compare()

    @staticmethod
    def _half(size: Tuple[int, int]) -> Tuple[int, int]:
        """The size a drag predicts at."""
        return (max(1, size[0] // 2), max(1, size[1] // 2))

    def _refresh(self) -> None:
        """Bring the view up to the mix: the picture at once (half size), the
        full frame, scores, shares and close-up from an analysis off the UI
        thread (one at a time; a mix that moved meanwhile is analysed again)."""
        if self.match is None:
            return
        self._quick_refresh()  # the picture now, whatever is still being scored
        if "analyse" in self._tasks:
            self._stale = True
            return
        mix, region, tolerance = self._effective_mix(), self.region, self._tolerance()
        width = max(240, self.ui.lbl_detail.width() or 300)
        match, size, reference = self.match, self.size, self.reference
        task = self.sb.BackgroundTask(
            lambda: self._analyse(match, mix, size, reference, region, tolerance, width),
            "look-match-analyse",
        )
        self._tasks["analyse"] = task

        def done() -> None:
            self._tasks.pop("analyse", None)
            if match is not self.match:  # another session since
                return
            try:
                analysis = task.result()
            except Exception as error:
                self.ui.footer.setStatusText(f"Could not score the mix: {error}", level="error")
                return
            current = (self.mix_key(self._effective_mix()), self.region)
            if self._stale or current != (self.mix_key(mix), region):
                # The mix (or the region) moved meanwhile: this one is old --
                # the picture already follows; analyse the mix as it is now.
                self._stale = False
                self._refresh()
                return
            self._apply_analysis(analysis)

        task.when_done(self.ui, done, poll_ms=15)

    @staticmethod
    def _analyse(match, mix, size, reference, region, tolerance, width) -> Dict[str, Any]:
        """Everything the view shows of *mix*, computed off the UI thread."""
        preview = match.predict(mix, size)
        score = ptk.LookScore(preview, reference, match.target, match.measures)
        shares = match.contributions(region, mix, size) if region else {}
        detail = (
            ptk.LookSheet(width=width).region_row(preview, reference, match.target, region, score, shares)
            if region
            else None
        )
        windows = {
            r.name: r.window("ours", size) for r in match.target.regions if r.outline("ours") is None
        }
        return {
            "preview": preview,
            "score": score,
            "windows": windows,
            "summary": score.summary(tolerance),
            "region": region,
            "shares": shares,
            "detail": detail,
        }

    def _apply_analysis(self, analysis: Dict[str, Any]) -> None:
        self.preview, self.score = analysis["preview"], analysis["score"]
        self.summary, self._windows = analysis["summary"], analysis["windows"]
        self._shares, self._detail = analysis["shares"], analysis["detail"]
        self._show_regions()
        self._show_compare()
        self._show_shares(self._shares)
        self._show_detail()
        self._show_trust()

    def _tolerance(self) -> float:
        spin = getattr(self.ui.b_fit.option_box.menu, "spn_fit_tolerance", None)
        return float(spin.value()) if spin is not None else self.TOLERANCE

    def _fill_source_combos(self) -> None:
        mixes = [(f"Mix: {os.path.splitext(os.path.basename(p))[0]}", f"mix:{p}") for p in self._mix_files()]
        items = [("Preview", "preview"), ("Reference", "reference"), ("WebXR frame", "webxr")] + mixes
        for combo, default in ((self.ui.cmb_a, "preview"), (self.ui.cmb_b, "reference")):
            current = combo.itemData(combo.currentIndex()) if combo.count() else default
            combo.blockSignals(True)
            try:
                combo.clear()
                for label, key in items:
                    combo.addItem(label, key)
                index = combo.findData(current)
                combo.setCurrentIndex(index if index >= 0 else combo.findData(default))
            finally:
                combo.blockSignals(False)

    def _source(self, key: Optional[str]):
        """``(image, label)`` for a source key."""
        if key == "preview":
            return self.preview, "Preview"
        if key == "reference":
            return self.reference, "Reference"
        if key == "webxr":
            frame = self.frames.get("webxr")
            return (frame["image"], "WebXR frame") if frame else (None, "WebXR frame (none rendered)")
        if key and key.startswith("mix:"):
            path = key[4:]
            stamp = os.path.getmtime(path) if os.path.isfile(path) else None
            cached = self._saved_mixes.get(path)
            if cached is None or cached[0] != stamp:
                try:
                    image = self.match.predict(ptk.LightMix.load(path), self.size)
                except Exception:
                    image = None
                cached = self._saved_mixes[path] = (stamp, image)
            return cached[1], f"Mix: {os.path.splitext(os.path.basename(path))[0]}"
        return None, ""

    def _show_compare(self) -> None:
        if self.match is None:
            return
        a, label_a = self._source(self.ui.cmb_a.itemData(self.ui.cmb_a.currentIndex()))
        b, label_b = self._source(self.ui.cmb_b.itemData(self.ui.cmb_b.currentIndex()))
        mode = self.VIEW_MODES[max(0, self.ui.cmb_mode.currentIndex())][1]
        view = self.ui.cmp_view
        if mode == "difference":
            if a is not None and b is not None:
                import numpy as np

                diff = np.asarray(ptk.LookSheet().difference(a, b))
                view.set_images(diff, None)
                view.set_labels(f"{label_a} against {label_b}: red brighter, blue darker", "")
            view.set_mode("a")
        else:
            view.set_images(a, b)
            view.set_labels(label_a, label_b)
            view.set_mode(mode)
        view.set_overlays(self._overlays())

    def _overlays(self) -> List[Dict[str, Any]]:
        width, height = self.size
        states = {row["region"]: row["within"] for row in self.summary}
        out = []
        for region in self.match.target.regions:
            outline = region.outline("ours")
            if outline is None:  # painted or object regions: their bounds, once analysed
                if region.name not in self._windows:
                    continue
                x0, y0, x1, y1 = self._windows[region.name]
                points, closed = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], True
            else:
                normalised, closed = outline
                points = [(x * width, y * height) for x, y in normalised]
            out.append(
                {
                    "key": region.name,
                    "points": points,
                    "closed": closed,
                    "color": self.STATUS_COLORS[states.get(region.name)],
                    "label": region.name if region.name == self.region else None,
                    "selected": region.name == self.region,
                }
            )
        return out

    def _show_regions(self) -> None:
        table = self.ui.tbl_regions
        rows = self.summary
        within = sum(1 for r in rows if r["within"])
        measured = sum(1 for r in rows if r["within"] is not None)
        self.ui.lbl_headline.setText(f"{within} of {measured} regions within tolerance")
        self.ui.lbl_headline.setToolTip(f"Fit cost {self.score.cost(self._tolerance()):.3f} (lower is closer).")
        if table.state() == QtWidgets.QAbstractItemView.EditingState:
            return  # a name or weight being typed: the next refresh shows the rest
        weights = {r.name: r.weight for r in self.match.target.regions}
        table.blockSignals(True)
        try:
            table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                glyph = QtWidgets.QTableWidgetItem(self.status_glyph(row))
                glyph.setForeground(QtGui.QColor(self.STATUS_COLORS[row["within"]]))
                glyph.setToolTip(
                    "within tolerance" if row["within"] else f"furthest out: {row['worst']} ({row['miss']:.2f})"
                )
                name = QtWidgets.QTableWidgetItem(row["region"])
                name.setData(self.NAME_ROLE, row["region"])
                weight = QtWidgets.QTableWidgetItem()
                weight.setData(QtCore.Qt.EditRole, float(weights.get(row["region"], 1.0)))
                cells = (
                    glyph,
                    name,
                    QtWidgets.QTableWidgetItem(self.brightness_text(row["brightness"])),
                    QtWidgets.QTableWidgetItem(row["colour"]),
                    weight,
                )
                for column, cell in enumerate(cells):
                    if column not in (self.REGION_NAME, self.REGION_WEIGHT):
                        cell.setFlags(cell.flags() & ~QtCore.Qt.ItemIsEditable)
                    table.setItem(i, column, cell)
                if row["region"] == self.region:
                    table.selectRow(i)
        finally:
            table.blockSignals(False)

    def _on_region_selected(self) -> None:
        items = self.ui.tbl_regions.selectedItems()
        name = None
        for item in items:
            if item.data(self.NAME_ROLE):
                name = item.data(self.NAME_ROLE)
        self._select_region(name)

    def _on_overlay_clicked(self, key) -> None:
        self._select_region(key)
        if key is not None:
            for i in range(self.ui.tbl_regions.rowCount()):
                item = self.ui.tbl_regions.item(i, 1)
                if item is not None and item.data(self.NAME_ROLE) == key:
                    self.ui.tbl_regions.blockSignals(True)
                    self.ui.tbl_regions.selectRow(i)
                    self.ui.tbl_regions.blockSignals(False)

    def _select_region(self, name: Optional[str]) -> None:
        if name == self.region:
            return
        self.region = name
        self._solve_picked = False  # a new region: its owner first
        self.ui.cmp_view.set_overlays(self._overlays())
        self._detail, self._shares = None, {}
        self._show_shares({})
        self._show_detail()
        self._fill_solve_combo()
        self._schedule_refresh()
        if name and name not in self._owners and "owners" not in self._tasks:
            self._find_owners(name)

    def _show_shares(self, shares: Optional[Dict[str, float]] = None) -> None:
        """Each layer's share of the selected region (*shares*; written only
        where it changed: a cell write repaints its row)."""
        if self.match is None:
            return
        shares = shares or {}
        self._filling = True
        try:
            for name, row in self._rows.items():
                item = self.ui.tbl_mix.item(row, self.SHARE)
                if item is None:
                    continue
                value = float(shares[name]) if name in shares else None
                if item.data(QtCore.Qt.EditRole) != value:
                    item.setData(QtCore.Qt.EditRole, value)
        finally:
            self._filling = False

    def _show_detail(self) -> None:
        label = self.ui.lbl_detail
        if self.match is None or not self.region:
            label.clear()
            label.setText("Pick a region to see it close up.")
            self.ui.lbl_litby.setText("")
            return
        if self._detail is None:
            label.clear()
            label.setText("\u2026")
        else:
            label.setPixmap(self.sb.ImageView.to_pixmap(self._detail))
        owners = self._owners.get(self.region)
        self.ui.lbl_litby.setText(
            "Lit most by: " + ", ".join(f"{n} ×{s:.1f}" for n, s in owners[:4])
            if owners
            else "Finding which lights own it…"
            if "owners" in self._tasks
            else ""
        )

    def _show_trust(self) -> None:
        notes = [
            "Preview: the baked layers summed -- within about 1% of WebXR on matte "
            "surfaces; metal reads 10-15% darker, and a specular scale shows only in a WebXR render."
        ]
        frame = self.frames.get("webxr")
        if frame:
            same = frame["mix"] == self.mix_key(self._effective_mix())
            notes.append(
                f"WebXR frame: {'this mix' if same else 'an earlier mix'}, rendered {time.strftime('%H:%M', time.localtime(frame['time']))}."
            )
        scene = self.loop.scene if self.loop is not None else None
        if scene and os.path.isfile(scene):
            stale = self.loop.stale_layers()
            if stale:
                notes.append(f"{len(stale)} layers were baked from an older save of the scene: Update layers.")
            template = ptk.LookSession.resolve(self.session, self.data, self.data.get("template"))
            if template and os.path.isfile(template) and os.path.getmtime(template) < os.path.getmtime(scene):
                notes.append("The template GLB is older than the scene: export it again for a WebXR render of the scene as it is.")
        self.ui.lbl_trust.setText("  ".join(notes))

    def _on_hovered(self, x: int, y: int) -> None:
        if x < 0 or self.preview is None:
            self.ui.footer.setStatusText(None)
            return
        height, width = self.preview.shape[:2]
        if not (0 <= x < width and 0 <= y < height):
            return
        ours = [int(v * 255 + 0.5) for v in self.preview[y, x]]
        ref = [int(v * 255 + 0.5) for v in self.reference[y, x]]
        self.ui.footer.setStatusText(f"{x}, {y}   preview {ours}   reference {ref}")

    # ------------------------------------------------------------------ proposals
    def _fill_solve_combo(self) -> None:
        combo = self.ui.cmb_solve
        if self.match is None:
            return
        owners = [n for n, _ in self._owners.get(self.region, [])]
        names = owners + [n for n in self.match.layers.names("light") if n not in owners]
        # The region's owner first and picked; a pick the user made stays.
        current = combo.currentText() if self._solve_picked else (owners[0] if owners else "")
        combo.blockSignals(True)
        try:
            combo.clear()
            combo.addItems(names)
            index = combo.findText(current)
            combo.setCurrentIndex(index if index >= 0 else 0)
        finally:
            combo.blockSignals(False)
        self.ui.b_solve.setEnabled(bool(self.region and names))

    def _find_owners(self, region: str) -> None:
        match, size = self.match, self.size
        task = self.sb.BackgroundTask(lambda: match.owners(region, size), "look-match-owners")
        self._tasks["owners"] = task

        def done() -> None:
            self._tasks.pop("owners", None)
            if match is not self.match:  # asked of another session (a name may recur)
                return
            try:
                self._owners[region] = task.result()
            except Exception:
                self._owners[region] = []
            if region == self.region:
                self._fill_solve_combo()
                self._show_detail()

        task.when_done(self.ui, done)

    def b_solve(self) -> None:
        layer, region = self.ui.cmb_solve.currentText(), self.region
        if not layer or not region or self._busy("solve"):
            return
        match, mix, key = self.match, self.match.mix, self.mix_key(self.match.mix)
        judge = self._judge()
        self.ui.footer.setStatusText(f"Solving {layer} for {region}…")

        def work():
            weight = match.solve(layer, region, mix, size=self.size)
            proposed = mix.with_weights({layer: weight})
            return weight, proposed, judge(proposed)

        task = self.sb.BackgroundTask(work, "look-match-solve")
        self._tasks["solve"] = task

        def done() -> None:
            self._tasks.pop("solve", None)
            try:
                weight, proposed, within = task.result()
            except ValueError as error:  # the region cannot be reached by this layer
                self.ui.footer.setStatusText(str(error), level="warning")
                return
            except Exception as error:
                self.ui.footer.setStatusText(f"The solve failed: {error}", level="error")
                return
            if match is not self.match or self.mix_key(self.match.mix) != key:
                self.ui.footer.setStatusText("The mix changed while solving: solve again.", level="warning")
                return
            self._propose(
                proposed,
                f"Solve: {layer} {mix.weight(layer):.3g} → {weight:.3g} for {region}",
                within,
            )

        task.when_done(self.ui, done, poll_ms=30)

    def b_fit(self) -> None:
        if self.match is None or self._busy("fit"):
            return
        free = sorted(n for n in self._free if n in self.match.layers)
        if not free:
            self.ui.footer.setStatusText("Tick the layers Fit may change (the Fit column).", level="warning")
            return
        menu = self.ui.b_fit.option_box.menu
        kelvin: Sequence[str] = ()
        if menu.chk_fit_kelvin.isChecked():
            if len(free) == 1 and self.match.layers.kind(free[0]).tinted:
                kelvin = free
            else:
                self.ui.footer.setStatusText(
                    "Colour temperature is fitted for one light at a time: tick one.", level="warning"
                )
                return
        weights = None
        if menu.chk_fit_selected.isChecked() and self.region:
            weights = {r.name: (1.0 if r.name == self.region else 0.0) for r in self.match.target.regions}
            weights["(frame)"] = 0.0
        match = self.match
        fit = ptk.LookFit(
            self.match.predictor,
            self.match.target,
            self.size,
            self.match.measures,
            tolerance=float(menu.spn_fit_tolerance.value()),
            regularize=float(menu.spn_fit_regularize.value()),
            region_weights=weights,
        )
        mix, key = self.match.mix, self.mix_key(self.match.mix)
        judge = self._judge()
        self.ui.footer.start_progress(text=f"Fitting {len(free)} layers…")

        def work():
            result = fit.run(mix, free, kelvin=kelvin)
            return result, judge(result.mix)

        task = self.sb.BackgroundTask(work, "look-match-fit")
        self._tasks["fit"] = task

        def done() -> None:
            self._tasks.pop("fit", None)
            try:
                result, within = task.result()
            except Exception as error:
                self.ui.footer.finish_progress(f"The fit failed: {error}")
                return
            self.ui.footer.finish_progress("Fit done.")
            if match is not self.match or self.mix_key(self.match.mix) != key:
                self.ui.footer.setStatusText("The mix changed while fitting: fit again.", level="warning")
                return
            moved = sum(1 for before, after in result.changes.values() if abs(after - before) > 1e-6 * max(abs(before), 1))
            self._propose(result.mix, f"Fit: {moved} of {len(free)} layers moved", within)

        task.when_done(self.ui, done, poll_ms=30)

    def _judge(self):
        """``mix -> regions within tolerance``, as shown (solo and mute applied):
        a closure over the view's state now, safe to run off the UI thread."""
        match, size, reference, tolerance = self.match, self.size, self.reference, self._tolerance()
        solo, mute = set(self._solo), set(self._mute)

        def judge(mix) -> int:
            off = {n: {"weight": 0.0} for n in mix.names() if n in mute or (solo and n not in solo)}
            shown = mix.with_entries(off) if off else mix
            score = ptk.LookScore(match.predict(shown, size), reference, match.target, match.measures)
            return sum(1 for r in score.summary(tolerance) if r["within"])

        return judge

    def _propose(self, mix, text: str, within_after: int) -> None:
        within_now = sum(1 for r in self.summary if r["within"])
        self.proposal, self._proposal_label = mix, text
        self._proposal_text = f"Proposal · {text} · {within_now} → {within_after} regions within tolerance"
        self._show_proposal()
        self._update_mix_cells()

    def _show_proposal(self) -> None:
        self.ui.frm_proposal.setVisible(self.proposal is not None)
        if self.proposal is not None:
            self.ui.lbl_proposal.setText(self._proposal_text)

    def _discard_proposal(self) -> None:
        if self.proposal is not None:
            self.proposal = None
            self._show_proposal()
            self._update_mix_cells()

    def b_accept(self) -> None:
        if self.proposal is None:
            return
        proposal, label = self.proposal, self._proposal_label
        self.proposal = None
        self._show_proposal()
        self.undo.push(_MixEdit(self, self.match.mix, proposal, label))

    def b_discard(self) -> None:
        self._discard_proposal()

    def _busy(self, name: str) -> bool:
        if name in self._tasks:
            self.ui.footer.setStatusText("Still working on the last one…", level="warning")
            return True
        return False

    # ------------------------------------------------------------------ WebXR
    def _derived_dir(self, name: str) -> str:
        """Where the session's derived files of *name* go: its cache folder
        when it has an id, else beside it."""
        if self.data.get("id"):
            return ptk.LookSession.resolve(self.session, self.data, f"cache:{name}")
        return os.path.join(os.path.dirname(self.session), name)

    def _ensure_service(self) -> str:
        """The URL of this panel's capture service for the open session,
        started if it is not up (minutes, the first time: call off the UI
        thread). Callers asking together share one start; a service started
        on another session (one opened while it started) is ended first."""
        with self._service_lock:
            session = self.session
            if self.service is not None and self._service_session != session:
                self.stop_service(wait=False)
            if self.service is None or self.service[0].poll() is not None:
                self.service = ptk.LookCapture.spawn(session)
                self._service_session = session
            return self.service[1]

    def b_render(self) -> None:
        if self.match is None or self._busy("render"):
            return
        if not self.data.get("template"):
            self.ui.footer.setStatusText("This session names no template GLB to render.", level="warning")
            return
        mix = self._effective_mix()
        key = self.mix_key(mix)
        out = os.path.join(self._derived_dir("renders"), f"{key}.png")
        first = self.service is None
        progress_text = (
            "Starting the WebXR viewer (the first render loads the template: a few minutes)…"
            if first
            else "Rendering in WebXR…"
        )
        self.ui.footer.start_progress(text=progress_text)
        session = self.session

        def work() -> str:
            url = self._ensure_service()
            os.makedirs(os.path.dirname(out), exist_ok=True)
            ptk.LookCapture.client(url).invoke(
                "exact", timeout=3600, mix=mix.to_dict(), mode="lit", out=out
            )
            return out

        task = self.sb.BackgroundTask(work, "look-match-render")
        self._tasks["render"] = task

        def done() -> None:
            self._tasks.pop("render", None)
            try:
                path = task.result()
            except Exception as error:
                self.ui.footer.finish_progress("The WebXR render failed.")
                QtWidgets.QMessageBox.warning(self.ui, "Look Match", f"The WebXR render failed:\n\n{error}")
                return
            if session != self.session:  # rendered for a session no longer open
                self.ui.footer.finish_progress("")
                return
            self.frames["webxr"] = {
                "image": ptk.LookTarget.display_at(path, self.size),
                "mix": key,
                "time": time.time(),
                "path": path,
            }
            self.ui.footer.finish_progress("Rendered in WebXR.")
            shown = {self.ui.cmb_a.itemData(self.ui.cmb_a.currentIndex()), self.ui.cmb_b.itemData(self.ui.cmb_b.currentIndex())}
            if "webxr" not in shown:
                self.ui.cmb_a.setCurrentIndex(self.ui.cmb_a.findData("webxr"))
            self._show_compare()
            self._show_trust()

        task.when_done(self.ui, done)

    def stop_service(self, wait: bool = True) -> None:
        """End the WebXR viewer this panel started (never one it did not): its
        ``stop`` op closes its browser. *wait* False ends it off the UI thread
        (a session switch); the application quitting waits."""
        service, self.service = self.service, None
        if service is None:
            return
        process, url = service

        def stop() -> None:
            try:
                ptk.LookCapture.client(url).invoke("stop", timeout=10)
            except Exception:
                pass
            try:
                process.wait(15)
            except Exception:
                process.kill()  # ours, started by this panel

        if wait:
            stop()
        else:
            self.sb.BackgroundTask(stop, "look-match-stop-service")

    # ------------------------------------------------------------------ editing regions
    def _target_path(self) -> str:
        return ptk.LookSession.resolve(self.session, self.data, self.data["target"])

    def b_edit_regions(self) -> None:
        editing = self.ui.b_edit_regions.isChecked()
        self.ui.frm_region_tools.setVisible(editing)
        self.ui.tbl_regions.setColumnHidden(self.REGION_WEIGHT, not editing)
        self.ui.tbl_regions.setEditTriggers(
            QtWidgets.QAbstractItemView.DoubleClicked | QtWidgets.QAbstractItemView.EditKeyPressed
            if editing
            else QtWidgets.QAbstractItemView.NoEditTriggers
        )
        for widget in (self.ui.cmb_solve, self.ui.b_solve):
            widget.setVisible(not editing)
        if not editing:
            self.ui.cmp_view.view_a.set_tool(None)
        self.ui.footer.setStatusText(
            "Draw a region on the picture, or double-click a name or a weight to change it."
            if editing
            else None
        )

    def _arm(self, tool: str, button) -> None:
        """Draw with *tool* on the (first) picture; *button*'s tip says how."""
        if self.match is not None:
            self.ui.cmp_view.view_a.set_tool(tool)
            self.ui.footer.setStatusText(button.toolTip())

    def b_draw_rect(self) -> None:
        self._arm("rect", self.ui.b_draw_rect)

    def b_draw_ellipse(self) -> None:
        self._arm("ellipse", self.ui.b_draw_ellipse)

    def b_draw_poly(self) -> None:
        self._arm("polygon", self.ui.b_draw_poly)

    def b_draw_line(self) -> None:
        self._arm("line", self.ui.b_draw_line)

    def _on_shape_drawn(self, tool: str, points) -> None:
        """A shape drawn on the picture becomes a region (named by the user)."""
        key = self.DRAW_TOOLS.get(tool)
        if self.match is None or key is None:
            return
        try:
            spec = ptk.LookRegion.spec_from_points(key, points, self.size)
        except ValueError as error:
            self.ui.footer.setStatusText(f"Not a region: {error}", level="warning")
            return
        names = {r.name for r in self.match.target.regions}
        default = next(f"region {i}" for i in range(1, len(names) + 2) if f"region {i}" not in names)
        name, ok = QtWidgets.QInputDialog.getText(self.ui, "New Region", "Region name:", text=default)
        name = name.strip() if ok and name else ""
        if not name:
            return
        kind = ptk.LookRegion.SHAPES[key].kind
        try:
            self.match.target.add(ptk.LookRegion(name, kind, spec))
        except ValueError as error:
            self.ui.footer.setStatusText(str(error), level="warning")
            return
        self._regions_changed(f"Added region {name}.")

    def _on_region_cell_changed(self, row: int, column: int) -> None:
        if self.match is None or column not in (self.REGION_NAME, self.REGION_WEIGHT):
            return
        item = self.ui.tbl_regions.item(row, column)
        name_item = self.ui.tbl_regions.item(row, self.REGION_NAME)
        old = name_item.data(self.NAME_ROLE) if name_item is not None else None
        if item is None or old is None:
            return
        if column == self.REGION_NAME:
            new = item.text().strip()
            if not new or new == old:
                return
            try:
                self.match.target.rename(old, new)
            except ValueError as error:
                self.ui.footer.setStatusText(str(error), level="warning")
                item.setText(old)
                return
            self._owners.pop(old, None)
            if self.region == old:
                self.region = new
            name_item.setData(self.NAME_ROLE, new)
            self._regions_changed(f"Renamed {old} to {new}.")
            return
        try:
            weight = max(0.0, float(item.data(QtCore.Qt.EditRole)))
        except (TypeError, ValueError):
            return
        self.match.target.region(old).weight = weight
        self._regions_changed(f"{old} weighs {weight:g}.")

    def b_region_delete(self) -> None:
        if self.match is None or not self.region:
            self.ui.footer.setStatusText("Pick the region to delete.", level="warning")
            return
        name = self.region
        if not self._confirm(f"Delete region {name}?"):
            return
        self.match.target.remove(name)
        self._owners.pop(name, None)
        self.region = None
        self._regions_changed(f"Deleted region {name}.")

    def b_paint(self) -> None:
        if self.match is None:
            return
        folder = os.path.dirname(self._target_path())
        if not self._confirm(
            "Paint the reference's area regions in an image editor?\n\n"
            "Each becomes a colour on a marker layer (ref_markers.png, with a guide): "
            "repaint the layer, save it (transparent), then Reload. Lines and quads keep their shapes."
        ):
            return
        try:
            self.match.target.paint_template(folder, side="ref")
        except ValueError as error:  # overlapping regions on one layer
            self.ui.footer.setStatusText(str(error), level="warning")
            return
        self._regions_changed("Painted: repaint ref_markers.png, save it, then Reload.")
        self._reveal(folder)

    def b_reload(self) -> None:
        if self.match is None:
            return
        try:
            target = ptk.LookTarget.load(self._target_path())
        except Exception as error:
            self.ui.footer.setStatusText(f"Could not read the regions: {error}", level="error")
            return
        self.match.target = target
        if self.region and self.region not in {r.name for r in target.regions}:
            self.region = None
        self._owners, self._windows = {}, {}
        self.reference = self.match.reference(self.size)  # a target names its reference
        self._schedule_refresh()
        self.ui.footer.setStatusText(f"Read {len(target.regions)} regions.")

    def _regions_changed(self, text: str) -> None:
        """A region edit is saved at once (the session's target) and scored."""
        try:
            self.match.target.save(self._target_path())
        except OSError as error:
            self.ui.footer.setStatusText(f"Could not save the regions: {error}", level="error")
            return
        self._windows = {k: v for k, v in self._windows.items() if k in {r.name for r in self.match.target.regions}}
        self.ui.cmp_view.set_overlays(self._overlays())
        self._fill_solve_combo()
        self._schedule_refresh()
        self.ui.footer.setStatusText(text)

    # ------------------------------------------------------------------ updating layers
    def _sync_update_button(self) -> None:
        """Shown when the session names a bake worker; says how many layers an
        older save of the scene made."""
        loop = self.loop
        shown = bool(loop is not None and loop.queue is not None and loop.scene)
        self.ui.b_update.setVisible(shown)
        if not shown:
            return
        stale = loop.stale_layers() if os.path.isfile(loop.scene) else []
        busy = "update" in self._tasks
        self.ui.b_update.setText("Updating layers…" if busy else f"Update layers ({len(stale)})")
        self.ui.b_update.setEnabled(bool(stale) and not busy)

    def b_update(self) -> None:
        loop = self.loop
        if loop is None or loop.queue is None or self._busy("update"):
            return
        names = loop.stale_layers()
        if not names:
            return
        worker = (self.data.get("loop") or {}).get("worker") or {}
        if not loop.queue.alive() and not self._confirm(
            f"Bake {len(names)} layers again from the scene as saved?\n\n"
            f"A Maya opens minimized to bake them (about 45 s a layer) and closes "
            f"{int(self.LEASE_S // 60)} minutes after the last."
        ):
            return
        session, module, scene = self.session, worker.get("module"), loop.scene
        folder = os.path.join(self._derived_dir("rebake"), time.strftime("%Y%m%d_%H%M%S"))
        self.ui.footer.start_progress(text=f"Baking {len(names)} layers in Maya…")

        def work():
            queue = loop.queue
            queue.lease(self.LEASE_S)
            if not queue.alive():
                args, env = ptk.AppLauncher.python_args_via_env(
                    ["-m", module, "launch", "--queue", queue.root, "--scene", scene]
                )
                started = ptk.AppLauncher.run(
                    ptk.AppLauncher.companion_python(), args, env=env, timeout=300, hide_window=True
                )
                if started.returncode:
                    raise RuntimeError(
                        "The bake worker did not start:\n" + (started.stdout or started.stderr or "")
                    )
                self._worker_queues.append(queue)
            loop.client = ptk.LookCapture.client(self._ensure_service())
            return loop.rebake(names, folder)

        task = self.sb.BackgroundTask(work, "look-match-update")
        self._tasks["update"] = task
        self._leased_queue = loop.queue
        self._lease_timer.start()
        self._sync_update_button()

        def done() -> None:
            self._tasks.pop("update", None)
            self._lease_timer.stop()
            self._leased_queue = None
            try:
                task.result()
            except Exception as error:
                self.ui.footer.finish_progress("Updating the layers failed.")
                QtWidgets.QMessageBox.warning(self.ui, "Look Match", f"Updating the layers failed:\n\n{error}")
                self._sync_update_button()
                return
            if session != self.session:  # another session since: its button is free again
                self._sync_update_button()
                return
            fresh = loop.match  # the store re-read after the capture
            fresh.mix = self.match.mix  # the mix stays the panel's
            fresh.target = self.match.target  # regions unchanged: their masks stay built
            self.match = fresh
            self._saved_mixes = {}
            self.ui.footer.finish_progress(f"Updated {len(names)} layers.")
            self._sync_update_button()
            self._schedule_refresh()

        task.when_done(self.ui, done)

    def _renew_lease(self) -> None:
        """Renew the worker an Update is baking in -- its own session's, even
        after another session opened."""
        if self._leased_queue is not None:
            self._leased_queue.lease(self.LEASE_S)

    def stop_worker(self) -> None:
        """End the bake workers this panel launched (never one it did not),
        each once its current job is done."""
        queues, self._worker_queues = self._worker_queues, []
        for queue in queues:
            queue.stop()

    # ------------------------------------------------------------------ the rig library
    def b_save_rig(self) -> None:
        if self.match is None:
            return
        default = self.ui.cmb_mix.currentText() or "look_match"
        name, ok = QtWidgets.QInputDialog.getText(self.ui, "Save to Rig Library", "Rig name:", text=default)
        name = ptk.StrUtils.to_legal_filename(name.strip()) if ok and name and name.strip() else ""
        if not name:
            return
        try:
            rig = self.match.to_rig(self.match.mix)
        except ValueError as error:
            self.ui.footer.setStatusText(f"Could not build a rig from this mix: {error}", level="error")
            return
        store = ptk.LightRigPayload.library()
        if name in store.list() and not self._confirm(f"The library has a rig named {name}. Replace it?"):
            return
        try:
            store.save(name, rig)
        except PermissionError:
            self.ui.footer.setStatusText(f"{name} is locked in the library: pick another name.", level="warning")
            return
        except (OSError, ValueError) as error:
            self.ui.footer.setStatusText(f"Could not save {name} to the library: {error}", level="error")
            return
        self.ui.footer.setStatusText(
            f"Saved rig {name} ({len(rig.get('lights') or [])} lights) to the library: apply it in Maya's Light Rigs panel.",
            level="success",
        )

    # ------------------------------------------------------------------ misc
    @staticmethod
    def _reveal(folder: str) -> None:
        ptk.FileUtils.open_explorer(folder)  # a missing folder opens nothing
