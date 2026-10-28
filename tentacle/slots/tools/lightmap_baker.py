# !/usr/bin/python
# coding=utf-8
"""Lightmap Baker: bake the scene's lighting into lightmaps the engine reads.

One Slots class for both hosts over the host toolkit's ``LightmapBaker``
(``self.tk``): Maya bakes with Arnold, Blender with Cycles. A thin driver,
holding no bake logic and no bake policy either: the checks a bake runs (the
renderer, the lights, the unlit verdict) live on the engine's
``LightmapBaker.bake``, so a script bakes as safely as the panel, and what a
Scope word gathers is the engine's too (``LightmapBaker.scope_meshes`` /
``scope_lights``).
"""

import functools
import os
from typing import Any, Callable, Dict, List, Optional, Tuple

import pythontk as ptk

from tentacle import Slots


class LightmapBakerSlots(Slots, ptk.LoggingMixin):
    """The Lightmap Baker panel.

    Composition over inheritance: a thin driver over the host's
    ``LightmapBaker`` (the workflow) -- no bake logic lives here, and no bake
    policy. **Bake Lightmaps** (``b000``) hands the objects in Scope and the
    dials to ``LightmapBaker.bake``, which checks the scene, bakes, and wires
    the result up so nothing is left to do afterward: the full PBR material and
    texture UVs are kept, lighting lands on the second UV set, and the engine
    metadata is stamped on the shared ``data_export`` carrier. The panel then
    reports what the bake returned. The maps survive; the engine composites.

    Nothing is reverted before a bake. An object in the scene's Exclude set
    (``LightmapExcludeSet``, edited by the Exclude row) keeps any map it has
    and still lights the rest, and so does an object the bake does not finish;
    one in its Isolate set (the Isolate row) bakes in a pass of its own, out of
    every other object's render. The **Manage** page lists the maps the scene
    reads and redoes them: what changed, the selection
    (:meth:`rebake_selected`), or undoes the wiring (:meth:`revert_selected`).

    The **Preset** combo (``cmb000``) is uitk's preset template
    (``PresetManager.wire_combo``) in semantic mode over
    ``LightmapBaker.preset_store`` -- the store ``LightmapBaker.from_preset``
    reads, so a preset saved here is also a headless bake recipe. Its keys are
    the engine's (``PRESET_INT_KEYS`` / ``PRESET_BOOL_KEYS``), each host's own:
    :meth:`_preset_fields` is the one map between them and the widgets, which
    stay the source of truth at bake time.
    """

    #: The full reference (mayatk's doc covers both hosts).
    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/lightmap_baker.md"

    # Packing labels for the Packing combobox (cmb002). Atlas by Material
    # (index 1, the default) consolidates a material group into one shared EXR
    # + a per-object scaleOffset rect; Per-Object keeps one full-resolution map
    # each; _packing() reads it back.
    _PACKING_LABELS = ("Per-Object (one map each)", "Atlas by Material (shared map)")

    # Fixed lightmap sizes (square, px) for the Resolution combobox
    # (cmb_resolution). Power-of-two atlas sizes; every Quality preset lands on
    # one of these. _resolution() reads the selection back as an int.
    _RESOLUTIONS = (256, 512, 1024, 2048, 4096)

    # Scope labels for the Scope combobox (cmb_scope): which objects b000 bakes,
    # as pythontk's HandoffScope words (LightmapBaker.scope_meshes reads them).
    # Every scope bakes fresh with the panel's settings; re-baking what changed
    # is the Manage page's. The combo persists by INDEX: a session saved on the
    # retired fourth row (Changed) reopens on Selected.
    _SCOPE_LABELS = ("Selected", "Visible", "Scene")

    #: The page picker's rows (cmb_page), in stk_pages order: what a new
    #: bake covers, and the maps the scene already reads.
    _PAGES = ("Bake", "Manage")

    #: The Manage table's columns (tbl_maps).
    _MAP_COLUMNS = ("Map", "Objects", "State")

    #: The quality dials' spin boxes, by the preset key -- and constructor
    #: keyword -- the host's engine stores each under
    #: (``LightmapBaker.PRESET_INT_KEYS``); Resolution is its combo's own
    #: (:meth:`_resolution`). Bounces answers to either engine's name: mayatk's
    #: ``gi_depth`` (Arnold's GI Diffuse Depth), blendertk's ``bounces``
    #: (Cycles' diffuse bounces) -- one dial, a saved-data key in each host's
    #: presets. ``gi_samples`` is Arnold's alone (Cycles traces every path from
    #: Samples), so its spin box hides where the engine has no such key.
    _DIALS: Dict[str, str] = {
        "samples": "spn_samples",
        "gi_samples": "spn_gi_samples",
        "gi_depth": "spn_bounces",
        "bounces": "spn_bounces",
    }

    #: The panel's switches, ``{preset key: (field, default)}``. Each rides the
    #: option box of the field it QUALIFIES rather than a checkbox row of its
    #: own: the lights that light the bake are part of what Scope gathers --
    #: every scene light or the Scope's own, the environment, the hidden ones
    #: -- adaptive sampling is how the Samples are spent, denoise is what the
    #: map ships at that Resolution, Beside Material Textures redirects the
    #: Output Directory, and the reflection probe is what the bake ships beside
    #: the maps Packing lays out. So each reads as a qualifier on a control
    #: rather than a row that happens to sit nearby. A field carrying several
    #: holds them in this order (:meth:`_toggle`).
    #:
    #: The keys are the preset store's (``LightmapBaker.PRESET_BOOL_KEYS``, the
    #: same in both hosts), so :meth:`_preset_fields` builds its entries
    #: straight from here and :meth:`_wire_toggle` derives each settings key
    #: from the same name.
    _TOGGLES: Dict[str, Tuple[str, bool]] = {
        "include_scene_lights": ("cmb_scope", True),
        "include_environment": ("cmb_scope", True),
        "include_hidden_lights": ("cmb_scope", False),
        "adaptive": ("spn_samples", True),
        "denoise": ("cmb_resolution", True),
        "beside_textures": ("txt_output_dir", False),
        "reflection_probe": ("cmb002", True),
    }

    #: The tier a panel opened for the first time shows, and the dials'
    #: factory defaults: each dial starts at its value (:meth:`_seed_dial`),
    #: so naming it costs nothing and says which tier the untouched dials are.
    _DEFAULT_PRESET = "mobile"
    #: Settings key recording that the default preset was seeded once (see
    #: :meth:`cmb000_init`).
    _PRESET_SEEDED_KEY = "lightmap_baker_preset_seeded"

    #: Bake-processor rows, label -> the value the baker takes. Auto is first
    #: (the default) because it is the fast choice on both renderers; the
    #: explicit rows exist for A/B-ing a suspect map against the other one.
    _DEVICES = (("Auto", "AUTO"), ("GPU", "GPU"), ("CPU", "CPU"))

    #: The footer's Select picks (:meth:`select_by_state`) and what each takes.
    _SELECT_KINDS: Dict[str, str] = {
        "Changed": "What a re-bake would redo: every changed object, and what "
        "its change shades.",
        "Split": "The maps of a material baked into more than one.",
        "Untracked": "Maps whose objects' changes go unseen.",
        "Missing": "Maps not on disk.",
        "All": "Every map.",
    }

    #: How long Undo/Redo steps must stop before the Manage table is re-read.
    _UNDO_SETTLE_MS = 400

    #: The panel's scene-set rows -- Exclude and Isolate -- by button: a label,
    #: one Set From Selection button, Select / Clear on its option box, and a
    #: live hover. One implementation (:meth:`_init_set_row` and the
    #: ``_*_set_row`` methods); a row is its set (the host toolkit's class of
    #: that name) and its words.
    _SET_ROWS: Dict[str, Dict[str, Any]] = {
        "set_exclusions": dict(
            scene_set="LightmapExcludeSet",
            label="lbl_exclude",
            title="Exclude",
            verb="excluded",
            effect="they still light the rest.",
            clear_tip="Clear the Exclude set: every object in Scope bakes again. "
            "The objects themselves are untouched.",
            cleared="Exclude set cleared — every object in Scope bakes.",
        ),
        "set_isolation": dict(
            scene_set="LightmapIsolateSet",
            label="lbl_isolate",
            title="Isolate",
            verb="isolated",
            effect="each bakes alone, out of every other object's render.",
            clear_tip="Clear the Isolate set: every object bakes in one pass, "
            "each in the others' render. The objects themselves are untouched.",
            cleared="Isolate set cleared — every object bakes in one pass.",
        ),
    }

    #: The Bake State window (:meth:`show_bake_state`), once shown.
    _state_view = None

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.logger.set_log_prefix("[Lightmap Baker] ")
        self.ui = self.sb.loaded_ui.lightmap_baker

        # Output dir of the most recent bake (reported in the footer).
        self._last_output_dir: Optional[str] = None
        # The Manage table's rows by map file (:meth:`_fill_maps`), and the
        # dry run they were read from (:meth:`_refresh_manage`).
        self._map_rows: Dict[str, Dict[str, Any]] = {}
        self._report = None
        # Workflow instance, rebuilt per bake from the current dials. commit /
        # revert persist their state on the object, so revert works even from
        # a fresh instance / reopened scene.
        self._baker = None
        # The Preset combo's manager, built by cmb000_init.
        self._presets = None
        # The default tier's values, read once (:meth:`_default_tier`).
        self._tier: Optional[Dict[str, Any]] = None
        # One restartable single-shot timer per key (:meth:`_later`).
        self._timers: Dict[str, Any] = {}

        # Deferred to the next tick: the switchboard builds this instance
        # mid-load, before child widgets (footer, combos) are wired onto self.ui.
        self.sb.QtCore.QTimer.singleShot(0, self._initialize_ui)

    def _initialize_ui(self) -> None:
        """Wire what reads several widgets at once, once all of them exist.

        Deferred from __init__ (QTimer) so every widget has run its ``*_init``
        and restored its session value first: the Preset combo's modified
        marker, the Adaptive Sampling gate and the Exclude / Isolate counts.
        The renderer is not checked here: a bake loads it on demand
        (``LightmapBaker.preflight``), and loading a renderer just because a
        panel opened would cost seconds for nothing.
        """
        if self._presets is not None:
            # Semantic presets leave this wiring to the owner
            # (``PresetManager.connect_value_widgets`` is a no-op there): any
            # edit to a setting a preset stores re-evaluates the " *" marker.
            def refresh(*_):
                self._presets.refresh_modified_state()

            for control, _read, _write in self._preset_fields().values():
                # A panel widget announces a change on the switchboard's
                # default signal for its type; a field's switch is an
                # option-box option, not a widget, and has ``toggled``.
                signal = getattr(control, "default_signals", lambda: "toggled")()
                if control is not None and signal:
                    getattr(control, signal).connect(refresh)
            # The widgets restored their session values with signals blocked.
            self._presets.refresh_modified_state()

        # Adaptive sampling applies on the processors the host's engine names
        # (``LightmapBaker.ADAPTIVE_DEVICES``): Arnold samples adaptively on the
        # GPU only, so a forced CPU bake in Maya ignores it; Cycles does on
        # both. The switch rides the Samples field's option box, so the rule
        # greys the TOGGLE rather than a row: the spinbox stays live, and a
        # toggle button sits out the container's enabled cascade, so this rule
        # is the only thing that moves it.
        #
        # A rule is keyed by its targets' objectNames, and an option button has
        # none -- so a SECOND rule from this trigger onto another switch would
        # collide with this one's key and be dropped in silence. Gate both from
        # one call (``targets`` takes a list) rather than wiring two.
        adaptive = self._toggle("adaptive")
        if adaptive is not None:
            devices = tuple(self.tk.LightmapBaker.ADAPTIVE_DEVICES)
            self.sb.enable_when(
                self.ui, adaptive.widget, "cmb_device", lambda device: device in devices
            )

        # The Exclude and Isolate sets live in the scene, so the count on each
        # label must follow the scene: another file opened, a Set undone. A
        # save moves the maps waiting in the session home, which the Manage
        # table shows. Each subscribe is guarded: an event a host lacks must
        # not block the panel open.
        jobs = self.tk.ScriptJobManager.instance()
        handlers = dict.fromkeys(
            ("SceneOpened", "NewSceneOpened", "SceneSaved"), self._scene_opened
        )
        handlers.update(Undo=self._scene_undone, Redo=self._scene_undone)
        for event, handler in handlers.items():
            try:
                jobs.subscribe(event, handler, owner=self)
            except Exception as error:  # noqa: BLE001 -- never block the panel
                self.logger.debug(f"scene event {event!r} unavailable ({error})")
        jobs.connect_cleanup(self.ui, owner=self)
        self._refresh_scene_sets(manage=False)  # the page refresh below reads it
        # A session saved on the retired Changed scope restores an index the
        # combo no longer has.
        if self.ui.cmb_scope.currentIndex() < 0:
            self.ui.cmb_scope.setCurrentIndex(0)
        self._manage_footer()
        # The picker restored its page with signals blocked; every later show
        # reads it again (``cmb_page_init``, refreshed on show).
        self._refresh_page()

    def _manage_footer(self) -> None:
        """The Manage page's footer controls: **Select** (maps and their
        objects by state, :meth:`select_by_state`) and **Fix All**
        (:meth:`fix_all`), shown with the page (:meth:`_refresh_page`). Built
        once per footer; a reloaded panel re-wires them to itself."""
        footer, Qt = self.ui.footer, self.sb.QtCore.Qt
        controls = getattr(footer, "_lightmap_manage", None)
        if controls is None:
            # uitk's: its list widens to its longest item (a plain one is as
            # narrow as the box, and clipped them).
            combo = self.sb.registered_widgets.ComboBox(footer)
            combo.setObjectName("cmb_select")
            combo.addItem("Select…")
            for kind, tip in self._SELECT_KINDS.items():
                combo.addItem(kind)
                combo.setItemData(combo.count() - 1, tip, Qt.ToolTipRole)
            combo.setToolTip(
                "Highlight the maps in a state and select their objects -- then "
                "right-click a highlighted row."
            )
            # Sized by its items: uitk's sizes to none by default (5 px here).
            combo.setSizeAdjustPolicy(self.sb.QtWidgets.QComboBox.AdjustToContents)
            height = max(footer.height() - 2, 1)
            combo.setFixedHeight(height)
            footer.add_widget(combo, background=True)
            # A button, styled as one: an action button is a footer icon,
            # transparent on the footer.
            fix = self.sb.QtWidgets.QPushButton("Fix All", footer)
            fix.setObjectName("btn_fix_all")
            fix.setToolTip(
                "Fix every map that needs it, once confirmed: Revert a missing "
                "map no re-bake renders, Combine each split, Start Tracking the "
                "untracked as they stand, then re-bake what changed."
            )
            fix.setFixedHeight(height)
            fix.setCursor(self.sb.QtGui.QCursor(Qt.ArrowCursor))
            footer.add_widget(fix, background=True)
            controls = footer._lightmap_manage = (combo, fix)
        combo, fix = controls
        # Re-wired on every init, its own handlers only: a reloaded panel keeps
        # the widgets, not the connections (the Manage table's rule).
        prior = getattr(footer, "_lightmap_handlers", {})
        wired = {"activated": self._on_select, "clicked": self.fix_all}
        for (name, handler), widget in zip(wired.items(), (combo, fix)):
            signal = getattr(widget, name)
            if name in prior:
                try:
                    signal.disconnect(prior[name])
                except (TypeError, RuntimeError):
                    pass
            signal.connect(handler)
        footer._lightmap_handlers = wired

    def _on_select(self, index: int) -> None:
        """The footer's Select: run the pick, then show its label again."""
        combo = self.ui.footer._lightmap_manage[0]
        kind = combo.itemText(index)
        combo.setCurrentIndex(0)
        if kind in self._SELECT_KINDS:
            self.select_by_state(kind.lower())

    # ------------------------------------------------------------------
    # Scene events
    # ------------------------------------------------------------------

    def _refresh_scene_sets(self, manage: bool = True) -> None:
        """Re-read the scene onto the panel: the Exclude and Isolate labels,
        and the Manage table while it shows."""
        for row in self._SET_ROWS:
            self._refresh_set_row(row)
        if manage and self._page() == "manage" and self.ui.isVisible():
            self._refresh_manage()

    def _scene_opened(self, *_args) -> None:
        """A scene opened, started or saved: re-read it once the events stop
        -- a host may report one load twice (Blender's ``load_post`` backs both
        an open and a new scene), and the Manage table's dry run costs about a
        second on a production scene."""
        self._later("scene", 0, self._refresh_scene_sets)

    def _scene_undone(self, *_args) -> None:
        """Undo/Redo: the set rows now, the Manage table once the steps stop
        (:attr:`_UNDO_SETTLE_MS`) -- its dry run costs about a second on a
        production scene, and a held Ctrl+Z is a step per key repeat."""
        for row in self._SET_ROWS:
            self._refresh_set_row(row)
        if self._page() != "manage" or not self.ui.isVisible():
            return
        self._later("scene", self._UNDO_SETTLE_MS, self._refresh_scene_sets)

    def _later(self, key: str, ms: int, callback: Callable[[], Any]) -> None:
        """Run *callback* *ms* after the last call under *key*, once: one
        single-shot timer per key, restarted by each call -- a read per burst
        of events, not per event."""
        timer = self._timers.get(key)
        if timer is None:
            timer = self._timers[key] = self.sb.QtCore.QTimer(self.ui)
            timer.setSingleShot(True)
            timer.timeout.connect(lambda: callback())
        timer.start(ms)

    # ------------------------------------------------------------------
    # Header
    # ------------------------------------------------------------------

    def header_init(self, widget) -> None:
        """Configure the header and its help text.

        Its menu holds what reads the whole scene: the Bake Report; a map's
        own verbs are the Manage table's (:meth:`tbl_maps_init`), and the
        output folder opens from the Output Directory field.
        """
        widget.config_buttons("menu", "collapse", "hide")
        widget.menu.add(
            "QPushButton",
            setText="Bake Report",
            setObjectName="show_bake_state",
            setToolTip="The full bake state: every map, each object a "
            "re-bake would redo and why, and the visible meshes no bake "
            "renders. Its links select objects and open folders.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Lightmap Baker",
                body="Bakes the scene's lighting into lightmaps the engine "
                "multiplies with the albedo, read on a second UV set (Maya: "
                "Arnold; Blender: Cycles). Materials and texture UVs never change.",
                sections=[
                    (
                        "Bake",
                        [
                            "<b>Scope</b>: Selected, Visible or Scene. Its icons pick "
                            "the lights: scene lights, environment, hidden lights.",
                            "<b>Exclude</b>: no map, still casts shadow and bounce. "
                            "<b>Isolate</b>: moving parts, baked alone.",
                            "Any other unbaked mesh is taken to move and left out "
                            "of the render.",
                            "A field's icons are its switches: Reflection Probe, "
                            "Denoise, Adaptive Sampling, Beside Textures.",
                        ],
                    ),
                    (
                        "Manage",
                        [
                            "Every map the scene reads and its state; hover a row "
                            "for what it means and how to fix it. Highlight rows "
                            "to select their objects.",
                            "Right-click: <b>Re-Bake</b>, <b>Combine</b>, <b>Start "
                            "Tracking</b> or <b>Revert</b> the selection, or open a "
                            "map's folder.",
                            "Footer: <b>Select</b> picks maps by state; <b>Fix "
                            "All</b> fixes every one that needs it.",
                            "A duplicate material bakes one atlas with the one it "
                            "duplicates (Maya: so does one material in two "
                            "shading groups).",
                            "<b>Bake Report</b> (header menu): every map, and why "
                            "each object re-bakes.",
                        ],
                    ),
                    (
                        "Run",
                        [
                            "<b>Preset</b> sets the Quality of every bake and re-bake.",
                            "The wiring rides the hidden <i>data_export</i> node "
                            "(Maya: export with the <b>Scene Exporter</b>, a plain "
                            "Export Selection drops it; Blender: export the FBX "
                            "with <b>Custom Properties</b> on).",
                        ],
                    ),
                ],
                notes=["Maya: needs Arnold (mtoa). Blender: Cycles ships with it."],
            ),
            url=self.HELP_URL,
        )

    # ------------------------------------------------------------------
    # Preset combobox (uitk preset template, semantic mode)
    # ------------------------------------------------------------------

    def cmb000_init(self, widget) -> None:
        """Wire the Preset combo: uitk's preset template over the shared store.

        Semantic mode (``value_provider`` / ``value_applier``): a preset is the
        store's ``{key: value}`` dict, not a widget snapshot, so the file this
        panel saves is the one ``LightmapBaker.from_preset`` reads -- and the
        shipped tiers keep working here. The combo restores only its
        SELECTION, from the store's active pointer; every dial restores its own
        session value, so nothing is re-applied at open. That pointer owns the
        selection outright: a restored index would second-guess it against a
        list that grows whenever a preset is saved.
        """
        baker = self.tk.LightmapBaker
        store = baker.preset_store()
        self._presets = self.sb.PresetManager(
            preset_dir=str(store.user_dir),
            builtin_dir=str(store.builtin_dir) if store.builtin_dir else None,
            value_provider=self._preset_values,
            value_applier=self._apply_preset_values,
        )
        # The manager's user-facing lines (a preset that fails to load) reach
        # this panel's log rather than only the console.
        self._presets.use_logger(self.logger)
        # A pointer left on a retired tier name ("quest", now "mobile") names a
        # preset the store no longer has; follow the rename rather than open
        # on no selection.
        active = self._presets.active_preset
        if active and not self._presets.exists(active):
            current = baker.preset_name(active)
            if current != active:
                self._presets.active_preset = current
        # Seeded ONCE per machine: a reset (or deleting the active user
        # preset) clears the pointer, and read as "never set" it was reseeded
        # on the next open -- the reset values then showed as that preset,
        # modified ("mobile *"), which is what ``_after_reset`` exists to stop.
        settings = getattr(self.ui, "settings", None)
        seeded = bool(settings and settings.value(self._PRESET_SEEDED_KEY, False))
        if (
            not seeded
            and self._presets.active_preset is None
            and self._presets.exists(self._DEFAULT_PRESET)
        ):
            self._presets.active_preset = self._DEFAULT_PRESET
        if settings is not None and not seeded:
            settings.setValue(self._PRESET_SEEDED_KEY, True)
        widget.restore_state = False
        self._presets.wire_combo(widget, placeholder="Preset…")

    def btn_reset_defaults_init(self, widget) -> None:
        """Wire Reset to Defaults to uitk's shared reset grammar.

        Click restores the defaults, Shift+Click makes the current values the
        defaults and Ctrl+Shift+Click forgets those -- the grammar a per-field
        reset option already teaches, so the panel-wide button adds a scope
        rather than a second idiom, and brings its own tooltip and hover
        preview with it.

        The scope is every widget the window's state manages: the quality
        dials (their factory defaults are the default tier's,
        :meth:`_seed_dial`), the Scope and Packing combos, the output fields.
        The Exclude set is scene data rather than a widget value, so a reset
        leaves it standing.
        """
        self._reset_gesture = self.sb.ResetGesture(widget, on_performed=self._after_reset)

    def _after_reset(self, action: str) -> None:
        """Let go of the active preset when a reset moved the dials off it.

        The values are the defaults now, not the preset the combo still names;
        keeping the pointer would show them as that preset, modified. Saving
        the current values as the defaults (Shift+Click) moves no dial, so it
        keeps the selection.
        """
        presets = getattr(self, "_presets", None)
        if presets is None or action == self.sb.ResetGesture.SAVE:
            return
        presets.active_preset = None
        presets.refresh_combo()

    def _dial_keys(self) -> List[str]:
        """The host engine's quality-dial keys that have a spin box
        (:attr:`_DIALS`), in the engine's order."""
        return [k for k in self.tk.LightmapBaker.PRESET_INT_KEYS if k in self._DIALS]

    def _preset_fields(self) -> Dict[str, Tuple[Any, Callable[[], Any], Callable]]:
        """``{preset key: (control, read, write)}`` -- the one map between the
        preset store's keys and this panel's controls. Save reads through it
        (:meth:`_preset_values`), a load writes through it
        (:meth:`_apply_preset_values`), a bake builds its baker from it
        (:meth:`_make_baker`) and each control's change re-evaluates the
        modified marker (:meth:`_initialize_ui`), so a key added here is
        saved, loaded, baked and marked, or none of the four. The keys are the
        host engine's ``PRESET_INT_KEYS`` / ``PRESET_BOOL_KEYS`` plus the
        panel's own ``packing``.

        The dials are widgets; every switch rides a field's option box
        (:attr:`_TOGGLES`) and is read and written through the same three-part
        shape, so neither half of the preset machinery has to know which kind
        it is holding.
        """
        ui = self.ui
        fields: Dict[str, Tuple[Any, Callable[[], Any], Callable]] = {
            "packing": (ui.cmb002, self._packing, self._set_packing),
            "resolution": (ui.cmb_resolution, self._resolution, self._set_resolution),
        }
        for key in self._dial_keys():
            spin = getattr(ui, self._DIALS[key])
            fields[key] = (
                spin,
                spin.value,
                lambda value, spin=spin: spin.setValue(int(value)),
            )
        for key in self._TOGGLES:
            fields[key] = (
                self._toggle(key),
                lambda key=key: self._toggle_state(key),
                lambda value, key=key: self._set_toggle_state(key, value),
            )
        return fields

    def _preset_values(self) -> Dict[str, Any]:
        """The panel's bake settings, keyed as the preset store keys them."""
        return {
            key: read()
            for key, (_control, read, _write) in self._preset_fields().items()
        }

    def _apply_preset_values(self, data: Dict[str, Any]) -> int:
        """Write a preset's values onto the widgets; returns how many applied.

        Overlay semantics: a key the preset lacks keeps its widget's value -- a
        shipped tier stores only the quality dials, so loading one leaves the
        switches as the user set them. Unknown keys (``description``) are
        skipped. Signals are left on, so the session state records the loaded
        values: that is what the next session restores the dials from.
        """
        fields = self._preset_fields()
        applied = 0
        for key, value in data.items():
            field = fields.get(key)
            if field is None:
                continue
            _control, _read, write = field
            try:
                write(value)
            except (TypeError, ValueError) as error:
                self.logger.warning(f"Preset value {key}={value!r} skipped: {error}")
                continue
            applied += 1
        return applied

    def _default_tier(self) -> Dict[str, Any]:
        """The default tier's values (:attr:`_DEFAULT_PRESET`), read once from
        the host engine's preset store; ``{}`` when it cannot be read."""
        if self._tier is None:
            try:
                store = self.tk.LightmapBaker.preset_store()
                self._tier = dict(store.load(self._DEFAULT_PRESET))
            except Exception as error:  # noqa: BLE001 -- a dial keeps its .ui value
                self.logger.debug(f"default tier unreadable ({error})")
                self._tier = {}
        return self._tier

    def _seed_dial(self, widget, key: str) -> None:
        """Start *widget* at the default tier's value for *key*.

        Set in its ``_init``, the value is the dial's factory default (uitk
        captures it after the ``_init``, before the session restore): a first
        open and Reset to Defaults land on the tier the Preset combo names, in
        each host's units -- Arnold's AA samples are not Cycles' paths, so the
        ``.ui``'s one number could not serve both.
        """
        value = self._default_tier().get(key)
        if value is not None:
            widget.setValue(int(value))

    # ------------------------------------------------------------------
    # Switches (option-box toggles)
    # ------------------------------------------------------------------

    def _wire_toggle(self, widget, key: str, icon: str, on: str, off: str, **kwargs):
        """Hang the *key* switch off *widget*'s option box as a toggle button.

        One shape for every entry in :attr:`_TOGGLES`. Off takes the neutral
        "locked" tint rather than a toggle's default error red: none of these
        switches stops the panel working, and red would read as a fault that
        isn't there. The settings key is explicit and panel-scoped -- the
        auto-derived one is the field's own objectName, and ``spn_samples`` /
        ``cmb_scope`` are names another panel in the same host would share.

        Parameters:
            widget: The field the switch rides.
            key: Its :attr:`_TOGGLES` entry; names the default and the key.
            icon: uitk icon name for the button.
            on: Tooltip while on -- what it is doing, then what a click does.
            off: Tooltip while off, the same way round.
            kwargs: Forwarded to ``set_toggle`` (e.g. ``on_toggled``,
                ``icon_off``). A field's first switch replaces what it carried;
                the next are added beside it, in :attr:`_TOGGLES` order.
        """
        kwargs.setdefault("replace", self._field_switches(key)[0] == key)
        widget.option_box.set_toggle(
            icon=icon,
            tooltip_on=on,
            tooltip_off=off,
            initial=self._TOGGLES[key][1],
            disabled_color=ptk.Palette.status()["locked"][0],
            settings_key=f"lightmap_baker_{key}",
            **kwargs,
        )

    def _field_switches(self, key: str) -> List[str]:
        """The :attr:`_TOGGLES` keys riding *key*'s field, in their order."""
        field = self._TOGGLES[key][0]
        return [k for k, (f, _default) in self._TOGGLES.items() if f == field]

    def _toggle(self, key: str):
        """The :attr:`_TOGGLES` switch *key*, or ``None`` before its field's
        ``_init`` has built it (the preset machinery reads this map while the
        panel is still loading). A field carrying several switches (Scope's
        three) holds them in :attr:`_TOGGLES` order, so each is read by its
        place among the field's switches -- options with an on/off state."""
        widget = getattr(self.ui, self._TOGGLES[key][0], None)
        shared = self._field_switches(key)
        try:
            if len(shared) == 1:
                return widget.option_box.find_option(self.sb.ToggleOption)
            switches = [
                option
                for option in widget.option_box.get_options()
                if hasattr(option, "is_on")
            ]
        except Exception:  # noqa: BLE001 -- no option box on a bare widget
            return None
        index = shared.index(key)
        return switches[index] if index < len(switches) else None

    def _toggle_state(self, key: str) -> bool:
        """Whether the *key* switch is on (its shipped default until wired)."""
        toggle = self._toggle(key)
        return self._TOGGLES[key][1] if toggle is None else bool(toggle.is_on)

    def _set_toggle_state(self, key: str, value: bool) -> None:
        """Set the *key* switch (a preset load)."""
        toggle = self._toggle(key)
        if toggle is not None:
            toggle.set_on(bool(value))

    # ------------------------------------------------------------------
    # Scope, Exclude, Isolate, Packing
    # ------------------------------------------------------------------

    def cmb002_init(self, widget) -> None:
        """Populate the Packing combobox (Atlas by Material is the default) and
        hang the Reflection Probe switch off it.

        One shared map per material is what an engine wants: fewer textures,
        no per-object naming collisions, the texels spent where the surface
        area is -- and a glTF material carries ONE lightmap, so per-object maps
        force a material copy per object downstream. Per-Object is the opt-out,
        for a hero asset that earns a full map of its own. Packing is what the
        bake ships, and the probe is the one file it ships beside the maps
        (``LightmapBaker.bake_probe``).
        """
        widget.clear()
        widget.addItems(self._PACKING_LABELS)
        widget.setCurrentIndex(1)  # Atlas by Material — one shared map each
        self._wire_toggle(
            widget,
            "reflection_probe",
            icon="camera",
            on="Reflection Probe: the bake also renders the room it lit as an "
            "HDR from one point and ships it beside the maps. A lightmap holds "
            "no reflections, so a baked metal shows only what it reflects, and "
            "an object the bake leaves out is lit by nothing of the room: the "
            "WebXR preview and the GLB light both from the probe. Click to "
            "ship the maps alone.",
            off="No reflection probe: baked metals reflect the viewer's stock "
            "studio rather than this room, and objects the bake leaves out are "
            "lit by it. Click to capture the room with the bake.",
        )

    def _packing(self) -> str:
        """``"atlas"`` or ``"per_object"`` from the Packing combobox (default per_object)."""
        text = (self.ui.cmb002.currentText() or "").lower()
        return "atlas" if "atlas" in text else "per_object"

    def _set_packing(self, value: str) -> None:
        """Select the Packing row for ``"atlas"`` / ``"per_object"``."""
        self.ui.cmb002.setCurrentIndex(1 if value == "atlas" else 0)

    def _reflection_probe(self) -> bool:
        """Whether the bake captures the room as a reflection probe (the
        Packing switch)."""
        return self._toggle_state("reflection_probe")

    def cmb_scope_init(self, widget) -> None:
        """Populate the Scope combobox (Selected is the default) and hang the
        three lighting switches off it.

        Scope is what the bake gathers, and what lights it is part of that
        (``LightmapBaker.scope_lights``): **Include Scene Lighting** -- every
        scene light, or only the Scope's own -- **Include Environment** -- the
        HDRI environment, by its own switch whatever the first says -- and
        **Include Hidden Lights** -- the hidden ones of that set switched on
        for the run. Each answers alone, so none greys another out.
        """
        widget.clear()
        widget.addItems(self._SCOPE_LABELS)
        widget.setCurrentIndex(0)  # Selected — the prior selection-only behavior
        self._wire_toggle(
            widget,
            "include_scene_lights",
            icon="light",
            on="Include Scene Lighting: every light in the scene lights the "
            "bake, wherever it sits. Click to bake with only the lights the "
            "Scope holds.",
            off="Scope lighting only: the lights the Scope holds -- selected or "
            "under the selection, every visible one (Visible), every one "
            "(Scene) -- light the bake; every other scene light is left out of "
            "it and handed back after. The environment has its own button. "
            "Click to bake with every scene light.",
        )
        self._wire_toggle(
            widget,
            "include_environment",
            icon="theme",
            on="Include environment: the scene's HDRI environment (Maya: the "
            "aiSkyDomeLight; Blender: the world) lights the bake along with its "
            "lights, in the Scope or not. Click to bake the room's own lights "
            "only.",
            off="Environment excluded: the HDRI environment is switched off for "
            "the bake and restored afterwards. An HDRI is often a backdrop or a "
            "look-dev convenience rather than the room's real lighting, and "
            "baking it in is a flat ambient lift that cannot be taken back out "
            "of the map. Click to bake it in.",
        )
        self._wire_toggle(
            widget,
            "include_hidden_lights",
            icon="eye",
            icon_off="eye_off",
            on="Include Hidden Lights: the hidden lights the bake uses are "
            "switched on for it -- one a hidden parent or collection hides too, "
            "without revealing anything else it hides -- and hidden again "
            "after. Click to leave hidden lights off.",
            off="Hidden lights stay off: a light hidden by its own flag, a "
            "parent's or a collection's does not light the bake. Click to "
            "switch them on for the bake.",
        )

    def _scope(self) -> str:
        """``"selected"`` (default), ``"visible"`` or ``"scene"`` from cmb_scope."""
        return (self.ui.cmb_scope.currentText() or "Selected").split()[0].lower()

    def _scene_set(self, row: str):
        """The host toolkit's scene-set class a row stands for (:attr:`_SET_ROWS`)."""
        return getattr(self.tk, self._SET_ROWS[row]["scene_set"])

    def _init_set_row(self, widget, row: str) -> None:
        """Hang Select / Clear off a scene-set row's button, and make its hover live.

        The row mirrors the Marmoset bridge's Bake Source row: Set From
        Selection is the button, Select and Clear its option-box icons. The set
        lives in the scene, so the hover lists its CURRENT members instead of
        the ones the panel opened on; it wraps each widget's own help text.
        """
        spec = self._SET_ROWS[row]
        widget.option_box.add_action(
            callback=lambda: self._select_set_row(row),
            icon="select",
            tooltip=f"Select the {spec['verb']} objects.",
            settings_key=False,
        )
        widget.option_box.add_action(
            callback=lambda: self._clear_set_row(row),
            icon="clear",
            tooltip=spec["clear_tip"],
            settings_key=False,
        )
        for target in (widget, getattr(self.ui, spec["label"])):
            help_text = target.toolTip()
            self.sb.tooltip.bind(
                target, lambda text=help_text: self._set_row_tooltip(row, text)
            )

    def _set_row_tooltip(self, row: str, help_text: str) -> str:
        """*help_text* over the meshes a row's set holds, live.

        The meshes, not the set's members: a group stored in the set reads as
        what the bake will actually act on -- the same count the label shows.
        """
        spec = self._SET_ROWS[row]
        try:
            meshes = self._scene_set(row).meshes()
        except Exception:  # noqa: BLE001 -- a tooltip must never raise into Qt
            return help_text
        return self.sb.tooltip.stored_items(
            meshes,
            body=help_text.replace("\n", "<br>"),
            formatter=self.tk.CoreUtils.leaf_name,
            noun=f"mesh(es) {spec['verb']} in this scene",
            empty_text=f"Nothing is {spec['verb']} in this scene.",
        )

    def _refresh_set_row(self, row: str) -> None:
        """Show a row's set's mesh count on its label (``Exclude (3):``).

        The count is of MESHES -- what the bake acts on -- so a group reads as
        everything under it. Runs on the panel's own edits and on scene
        open / new / undo / redo (see :meth:`_initialize_ui`).
        """
        spec = self._SET_ROWS[row]
        label = getattr(self.ui, spec["label"], None)
        if label is None:
            return
        try:
            count = len(self._scene_set(row).meshes())
        except Exception:  # noqa: BLE001 -- a label refresh must never raise
            count = 0
        title = spec["title"]
        label.setText(f"{title} ({count}):" if count else f"{title}:")

    def _define_set_row(self, row: str) -> None:
        """Make the selection a row's set; an empty selection clears it."""
        spec = self._SET_ROWS[row]
        scene_set = self._scene_set(row)
        members = scene_set.define()
        self._refresh_set_row(row)
        if not members:
            self.ui.footer.setText(
                f"Nothing selected — the {spec['title']} set is cleared."
            )
            return
        count = len(scene_set.meshes())
        self.ui.footer.setText(
            f"{count} mesh{'es' if count != 1 else ''} {spec['verb']}; {spec['effect']}"
            if count
            else f"{spec['title']} set stored, but it holds no meshes -- nothing "
            f"is {spec['verb']}.",
            None if count else "warning",
        )

    def _select_set_row(self, row: str) -> None:
        """Select a row's set's members.

        What the host cannot select (Blender: a member hidden, or outside the
        view layer) is counted rather than forced: unhiding geometry to
        satisfy a *select* would change the scene the set promises to leave
        alone.
        """
        spec = self._SET_ROWS[row]
        members = self._scene_set(row).members()
        self._refresh_set_row(row)
        if not members:
            self.ui.footer.setText(
                f"Nothing is {spec['verb']} in this scene.", level="warning"
            )
            return
        selected = self.tk.LightmapBaker.select(members)
        count, unreachable = len(selected), len(members) - len(selected)
        self.ui.footer.setText(
            f"Selected {count} {spec['verb']} object{'s' if count != 1 else ''}."
            + (
                f" {unreachable} could not be selected (hidden, or not selectable "
                f"here); they stay {spec['verb']}."
                if unreachable > 0
                else ""
            )
        )

    def _clear_set_row(self, row: str) -> None:
        """Remove a row's set; its objects are left untouched."""
        spec = self._SET_ROWS[row]
        scene_set = self._scene_set(row)
        if not scene_set.exists():
            self.ui.footer.setText(
                f"Nothing is {spec['verb']} in this scene.", level="warning"
            )
            return
        scene_set.clear()
        self._refresh_set_row(row)
        self.ui.footer.setText(spec["cleared"])

    # Exclude: no map of their own, still in the render (LightmapExcludeSet).
    def set_exclusions_init(self, widget) -> None:
        """Hang Select / Clear off the Exclude row (:meth:`_init_set_row`)."""
        self._init_set_row(widget, "set_exclusions")

    def set_exclusions(self) -> None:
        """Make the selection the Exclude set; an empty selection clears it."""
        self._define_set_row("set_exclusions")

    def select_exclusions(self) -> None:
        """Select the Exclude set's members (:meth:`_select_set_row`)."""
        self._select_set_row("set_exclusions")

    def clear_exclusions(self) -> None:
        """Remove the Exclude set; its objects are left untouched."""
        self._clear_set_row("set_exclusions")

    # Isolate: each bakes alone, out of every other's render (LightmapIsolateSet).
    def set_isolation_init(self, widget) -> None:
        """Hang Select / Clear off the Isolate row (:meth:`_init_set_row`)."""
        self._init_set_row(widget, "set_isolation")

    def set_isolation(self) -> None:
        """Make the selection the Isolate set; an empty selection clears it."""
        self._define_set_row("set_isolation")

    def select_isolation(self) -> None:
        """Select the Isolate set's members (:meth:`_select_set_row`)."""
        self._select_set_row("set_isolation")

    def clear_isolation(self) -> None:
        """Remove the Isolate set; its objects are left untouched."""
        self._clear_set_row("set_isolation")

    # ------------------------------------------------------------------
    # Quality
    # ------------------------------------------------------------------

    def cmb_resolution_init(self, widget) -> None:
        """Populate the Resolution combobox (value carried as item data,
        default the default tier's) and hang the Denoise switch off it.

        Denoise cleans the map at the size this combo sets, so the switch
        belongs to it.
        """
        widget.clear()
        for r in self._RESOLUTIONS:
            widget.addItem(f"Resolution:\t{r}", r)
        self._set_resolution(self._default_tier().get("resolution", 1024))
        self._wire_toggle(
            widget,
            "denoise",
            icon="filter",
            on="Denoise: every map is cleaned once it is baked (Maya: at the size "
            "it ships at -- the object's own map, or the atlas cell it is shrunk "
            "into -- edge-preserving, so falloff and shadow edges survive and "
            "lone fireflies are clamped; Blender: by OpenImageDenoise). Click to "
            "ship the bake as rendered.",
            off="Not denoising. Neither renderer denoises a bake by itself, so "
            "each map ships its sampling noise, which reads as grain or "
            "splotches up close. Click to denoise.",
        )

    def _resolution(self) -> int:
        """The selected lightmap resolution (px) from cmb_resolution (its item data)."""
        value = self.ui.cmb_resolution.currentData()
        return int(value) if value is not None else 1024

    def _set_resolution(self, value: int) -> None:
        """Select *value* in the Resolution combobox, snapping to the nearest fixed size."""
        nearest = min(self._RESOLUTIONS, key=lambda r: abs(r - int(value)))
        self.ui.cmb_resolution.setCurrentIndex(self._RESOLUTIONS.index(nearest))

    def spn_samples_init(self, widget) -> None:
        """Range and seed the Samples field in the host's units, and hang the
        Adaptive Sampling switch off it.

        The range is the engine's (``LightmapBaker.SAMPLES_RANGE``): Arnold's
        AA samples are squared, so a few hundred is already extreme, while
        Cycles counts paths in the thousands. Set before the seed, which a
        narrower ``.ui`` range would clamp.

        Adaptive sampling does not change how MANY samples the bake may spend
        -- it decides where the Samples this field sets are spent -- so it
        qualifies this dial. A processor that spends them the other way
        ignores it, which is what greys the button out (:meth:`_initialize_ui`).
        """
        low, high = self.tk.LightmapBaker.SAMPLES_RANGE
        widget.setRange(int(low), int(high))
        self._seed_dial(widget, "samples")
        self._wire_toggle(
            widget,
            "adaptive",
            icon="activity",
            on="Adaptive Sampling: the budget goes where the noise is -- the "
            "flat, lit texels finish early and the shadows take the rest (Maya: "
            "GPU bakes, up to Samples × GI Samples; Blender: CPU and GPU). "
            "Measured on production floors: 73s where the full budget took 381s "
            "(Maya), 33s against 72s (Blender), for slightly more residual "
            "noise. Click to give every texel the full budget.",
            off="Every texel gets the full budget: the cleanest map, and the "
            "slowest. Click to spend the budget adaptively.",
        )

    def spn_gi_samples_init(self, widget) -> None:
        """Seed GI Samples from the default tier, or hide it where the host's
        engine has no such dial (Blender: Cycles traces every path from
        Samples)."""
        if "gi_samples" not in self._dial_keys():
            widget.setVisible(False)
            return
        self._seed_dial(widget, "gi_samples")

    def spn_bounces_init(self, widget) -> None:
        """Seed Bounces from the default tier, under the host engine's key for
        it (:attr:`_DIALS`)."""
        for key in self._dial_keys():
            if self._DIALS[key] == "spn_bounces":
                self._seed_dial(widget, key)

    def cmb_device_init(self, widget) -> None:
        """Populate the Processor combobox (value carried as item data); default Auto."""
        widget.clear()
        for label, value in self._DEVICES:
            widget.addItem(f"Processor:\t{label}", value)
        widget.setCurrentIndex(0)  # Auto

    def _device(self) -> str:
        """The processor the bake renders on, from cmb_device (its item data)."""
        return self.ui.cmb_device.currentData() or self._DEVICES[0][1]

    def _adaptive(self) -> bool:
        """Whether the bake samples adaptively (the Samples field's switch)."""
        return self._toggle_state("adaptive")

    def _include_environment(self) -> bool:
        """Whether the bake keeps the scene's environment (a Scope switch)."""
        return self._toggle_state("include_environment")

    def _include_scene_lights(self) -> bool:
        """Whether every scene light lights the bake, or only the Scope's (a Scope switch)."""
        return self._toggle_state("include_scene_lights")

    def _include_hidden_lights(self) -> bool:
        """Whether the bake switches the hidden lights on (a Scope switch)."""
        return self._toggle_state("include_hidden_lights")

    def _denoise(self) -> bool:
        """Whether the maps are denoised (the Resolution switch)."""
        return self._toggle_state("denoise")

    # ------------------------------------------------------------------
    # Output
    # ------------------------------------------------------------------

    def txt_output_dir_init(self, widget) -> None:
        """Add the folder browser and the Beside Material Textures toggle.

        No clear button: the value arrives from the browse dialog as often as
        it is typed, and a mis-click would drop a path the user picked and
        can't retype -- the field's *empty* default is one keystroke away
        anyway (see :meth:`_output_dir`).

        The toggle is a switch on the field it redirects (:attr:`_TOGGLES`):
        on, each map goes to its material's texture folder
        (``LightmapBaker.beside_textures``) and this field only takes the
        objects whose material has none.
        """
        widget.option_box.browse(
            mode="directory",
            title="Lightmap output directory",
            tooltip="Browse for the lightmap output directory…",
            start_dir=self._output_dir,
            callback=self._relativize_output_dir,
        )
        self._wire_toggle(
            widget,
            "beside_textures",
            icon="image",
            on="Beside material textures: each lightmap is saved in the folder "
            "its material's texture maps are in, named after that texture set. "
            "This field only takes the objects whose material has no texture "
            "folder inside the project (a packed or embedded image has none, and "
            "another project's is never written to). Click to save every map "
            "here instead.",
            off="Saving every lightmap to this folder. Click to save each one "
            "beside its material's texture maps instead.",
            on_toggled=self._show_output_mode,
        )
        widget.option_box.add_action(
            callback=self.open_output,
            icon="open_external",
            tooltip="Open the folder the lightmaps are written to: where the "
            "last bake wrote, else this field's folder, else the project's "
            "texture folder (sourceimages).",
            settings_key=False,
        )
        self._show_output_mode(self._beside_textures())

    def _beside_textures(self) -> bool:
        """Whether each map is saved beside its material's texture maps."""
        return self._toggle_state("beside_textures")

    def _show_output_mode(self, beside: bool) -> None:
        """Say in the empty field where the maps will go."""
        self.ui.txt_output_dir.setPlaceholderText(
            "(blank: beside textures, else sourceimages/lightmaps)"
            if beside
            else "(blank: sourceimages/lightmaps)"
        )

    def _relativize_output_dir(self, path: str) -> None:
        """Store a browsed dir as the portable spelling of itself.

        The dialog can only hand back an absolute path; under the texture
        folder the relative one is what survives the project being moved (or a
        teammate's copy) -- see ``ptk.FileUtils.relativize_output_dir``, the
        exact inverse of the ``resolve_output_dir`` :meth:`_output_dir` reads
        the field with.
        """
        if not path:
            return
        self.ui.txt_output_dir.setText(
            ptk.FileUtils.relativize_output_dir(path, self._sourceimages_dir())
        )

    def _output_dir(self) -> Optional[str]:
        """The bake's output directory: the field, resolved against the
        project's texture folder (sourceimages).

        Empty field -> that folder's ``lightmaps``
        (``LightmapBaker.OUTPUT_SUBDIR``): exactly where a scripted bake
        lands on its own, in both hosts -- one default. A subdirectory entry
        is joined onto the texture folder (the conventional, portable home for
        material-referenced textures) so the setting survives a project move;
        a full path is taken as-is, with or without a project. The directory
        itself is created by the bake.

        ``None`` when a blank or subdirectory entry has no project to resolve
        against, rather than handing the workflow a *relative* directory
        (``os.makedirs`` would create that against the process CWD): the
        workflow's own default decides, and refuses.
        """
        entry = self.ui.txt_output_dir.text()
        if (entry or "").strip():
            rooted = ptk.FileUtils.resolve_output_dir(entry, None)
            if rooted:
                return rooted
        base = self._sourceimages_dir()
        if not base:
            return None
        if not (entry or "").strip():
            return os.path.normpath(
                os.path.join(base, self.tk.LightmapBaker.OUTPUT_SUBDIR)
            )
        return ptk.FileUtils.resolve_output_dir(entry, base)

    def _sourceimages_dir(self) -> Optional[str]:
        """The scene project's texture folder (sourceimages), or None (no
        project / lookup failed): the project the scene is saved in, not
        merely the active one (``DataNodes.scene_source_images_dir``).

        Returns the path even if the folder doesn't exist yet (the bake creates it).
        """
        try:
            return self.tk.DataNodes.scene_source_images_dir() or None
        except Exception:  # noqa: BLE001 -- no project reads as none
            return None

    def txt000_init(self, widget) -> None:
        """Add the Prefix / Suffix / Auto picker to the name-affix field."""
        widget.option_box.clear_option = True
        # Explicit key: ``txt000`` is generic enough that another panel in the
        # same host would share the auto-derived namespace.
        widget.option_box.set_affix(
            default="auto",
            settings_key="lightmap_baker_affix",
            # Fourth, custom state: take the lightmap affix from the shared
            # naming convention instead of this one field.
            convention_key="lightmap",
        )

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _make_baker(self):
        """A ``LightmapBaker`` built from the panel's dials and switches -- its
        preset fields, which are the engine's constructor keywords
        (:meth:`_preset_fields`), and the Processor, which no preset stores --
        the one every action builds, so the Manage page's dry run reads the
        lights, resolution and switches the bake will."""
        values = self._preset_values()
        values.pop("packing")  # a bake argument, not a constructor one
        return self.tk.LightmapBaker(device=self._device(), **values)

    def b000(self) -> None:
        """The Bake page's run button: bake the Scope minus the Exclude set
        (``LightmapBaker.bake``). What changed re-bakes from the Manage page
        (its footer's Fix All, or Select then a right-click)."""
        scope = self._scope()
        scoped = list(self.tk.LightmapBaker.scope_meshes(scope) or [])
        if not scoped:
            self.ui.footer.setText(
                "Select one or more mesh objects to bake."
                if scope == "selected"
                else f"No meshes found for scope '{scope}'.",
                level="warning",
            )
            return

        self._baker = self._make_baker()
        args = self._bake_args()
        if args is None:
            return

        def bake(progress):
            # The Scope's lights ride beside its meshes: what lights the bake
            # with Include Scene Lighting off (the bake's targets stay the
            # meshes).
            lights = self.tk.LightmapBaker.scope_lights(scope) or []
            return self._baker.bake(
                scoped + [light for light in lights if light not in scoped],
                packing=self._packing(),
                on_progress=progress,
                **args,
            )

        self._show_bake_report(self._baking(bake))

    def _bake_args(self) -> Optional[Dict[str, str]]:
        """``{"output_dir", "prefix", "suffix"}`` every bake takes from the
        panel, or ``None`` (the footer says why).

        The Output Directory field resolved against the scene project's
        texture folder (empty: its lightmaps folder; see :meth:`_output_dir`
        -- resolved HERE, so the workflow is never handed a relative
        directory). With Beside Material Textures it takes only the objects
        whose material has no texture folder. The name is ``<texture
        set><affix>`` per the field; an empty field falls back to the
        placeholder default (the .ui's single source for it), so a cleared
        field never bakes affix-less files that could collide with source
        texture names.
        """
        out_dir = self._output_dir()
        if out_dir is None:
            self.ui.footer.setText(
                "No project to bake into — save the scene or set a project.",
                level="error",
            )
            return None
        field = self.ui.txt000
        affix = field.text().strip() or field.placeholderText()
        prefix, suffix = field.option_box.resolve_affix(affix, default="suffix")
        return {"output_dir": out_dir, "prefix": prefix, "suffix": suffix}

    def _baking(
        self,
        run: Callable[[Callable[[int, int, str], bool]], Any],
        doing: str = "Baking",
        done: str = "Baked",
    ) -> Any:
        """``run(progress)`` under the footer's marquee, *progress* naming
        each object as it bakes -- or, by *doing* / *done*, as it combines.

        Indeterminate marquee + per-object text in OUR footer. Deliberately
        not a determinate 0..100% bar: a single bake is one opaque blocking
        call with no sub-progress, so a percentage would sit at 0 and jump --
        which is exactly what mtoa's own popup does. The text still reports
        object i / N, which is the part that tells the artist the run is alive
        and how far in.
        """

        def progress(count, total, name):
            return update(
                None,
                f"{doing} {name}…  ({min(count + 1, total)}/{total})"
                if count < total
                else f"{done} {total} object{'s' if total != 1 else ''}.",
            )

        with self.ui.footer.progress(text=f"{doing} lightmaps…") as update:
            return run(progress)

    def _confirm_rebake(self, report, src: str, title: str) -> Optional[bool]:
        """Ask what a re-bake must, from its dry run *report*: ``False`` keep
        each map in its folder, ``True`` relocate to *src*, ``None`` cancelled
        (the footer says so).

        Two questions, each only when it applies:

        - An Output Directory typed in -- a blank one means "where they are"
          -- that is not where the maps the re-bake rewrites live: keep them
          there, or move them, which re-packs every atlas it touches whole.
        - An atlas that re-packs whole (every member renders again --
          production: "29 to re-bake" was 97 maps and 50 minutes), or Bounces
          that differ from the bake's (every map re-bakes): the dials of a
          fresh panel, not the preset the maps were baked with, read as both.
        """
        if self.ui.txt_output_dir.text().strip():
            here = os.path.normcase(os.path.abspath(src))
            ids = list(report.targets) + list(report.joining)
            elsewhere = sorted(
                folder
                for folder in self._baker.map_folders(ids)
                if os.path.normcase(os.path.abspath(folder)) != here
            )
            if elsewhere:
                answer = self.sb.message_box(
                    f"<b>{title}</b> -- the maps it rewrites are in "
                    + ", ".join(f"<hl>{folder}</hl>" for folder in elsewhere)
                    + f", not the Output Directory (<hl>{src}</hl>).<br><br>"
                    "<b>Keep</b> writes each back where it is, changed cells in "
                    "place. <b>Move</b> writes them to the Output Directory: "
                    "every atlas it touches re-packs whole there.",
                    "Keep",
                    "Move",
                    "Cancel",
                )
                if answer == "Move":
                    return True
                if answer != "Keep":
                    self.ui.footer.setText(f"{title} cancelled.")
                    return None
        settings = ptk.BakeBaseline.SETTINGS in report.lighting
        if report.repack or settings:
            n, more = len(report.targets), len(report.joining)
            why = []
            if settings:
                why.append(
                    "The Bounces differ from the ones the maps were baked with: "
                    "every map they lit re-bakes."
                )
            if report.repack:
                atlases = len(report.repack)
                why.append(
                    f"{atlases} atlas{'es' if atlases != 1 else ''} re-pack"
                    f"{'' if atlases != 1 else 's'} whole -- every member "
                    "renders again:<br>"
                    + "<br>".join(
                        f"<hl>{atlas}</hl>: {reason}"
                        for atlas, reason in report.repack.items()
                    )
                )
            answer = self.sb.message_box(
                f"<b>{title}</b> -- {n + more} objects"
                + (f" ({n} to re-bake, {more} more with their atlases)" if more else "")
                + ".<br><br>"
                + "<br><br>".join(why)
                + "<br><br>If the panel's dials are not the ones the maps were "
                "baked with, load that preset first: only what changed re-bakes.",
                "Bake All",
                "Cancel",
            )
            if answer != "Bake All":
                self.ui.footer.setText(f"{title} cancelled.")
                return None
        return False

    def _show_bake_report(self, result) -> None:
        """Put :meth:`_bake_report` in the footer: red when nothing baked,
        gold when some objects were not or the level looks wrong."""
        text = self._bake_report(result)
        if result.refused or not result:
            level = "error"
        elif result.unbaked or result.verdict:
            level = "warning"
        else:
            level = None
        self.ui.footer.setText(text, level)

    def _bake_report(self, result) -> str:
        """The footer line for a ``LightmapBakeResult``, short: a refusal says
        why, an empty bake where to look, a bake how many objects went into
        how many maps where, what it left alone and whether its level looks
        wrong. The detail is in the log."""
        if result.refused:
            self._last_output_dir = None
            return result.refused
        if not result:
            self._last_output_dir = None
            return "Bake produced no output (see the log)."
        # Its home: where a map waiting in the session for the save lands.
        self._last_output_dir = os.path.dirname(
            ptk.PendingFiles.session().home(next(iter(result.maps.values())))
        )
        folders = result.folders
        where = (
            os.path.basename(self._last_output_dir)
            if len(folders) == 1
            else f"{len(folders)} folders"
        )
        count, files = len(result.maps), len(result.files)
        atlas = result.in_place or result.repacked or self._packing() == "atlas"
        kind = ("atlas" if files == 1 else "atlases") if atlas else (
            "map" if files == 1 else "maps"
        )
        notes = [f"Baked {count} object{'s' if count != 1 else ''} → {files} {kind} in {where}"]
        for n, what in (
            (len(result.in_place), "in place"),
            (len(result.repacked), "re-packed"),
            (len(result.excluded), "excluded"),
            (len(result.hidden), "hidden"),
            (len(result.unbaked), "not baked"),
            (len(result.retired), "old → Recycle Bin on save"),
        ):
            if n:
                notes.append(f"{n} {what}")
        text = "; ".join(notes) + "."
        return f"{text} WARNING: {result.verdict}" if result.verdict else text

    # ------------------------------------------------------------------
    # Pages: Bake (what a new bake covers) and Manage (the maps it made)
    # ------------------------------------------------------------------

    def cmb_page_init(self, widget) -> None:
        """Populate the page picker (Bake first); it restores the last page.

        Re-run on every later show (``refresh_on_show``): the scene moves on
        while the panel is away, so the page shown is read again then
        (:meth:`_refresh_page`). The first show's read is
        :meth:`_initialize_ui`'s.
        """
        if widget.is_initialized:
            self._refresh_page()
            return
        widget.clear()
        widget.addItems(self._PAGES)
        widget.setCurrentIndex(0)
        widget.refresh_on_show = True

    def cmb_page(self, index) -> None:
        """Show the picked page (:meth:`_refresh_page`)."""
        self._refresh_page()

    def _page(self) -> str:
        """``"bake"`` or ``"manage"``, from cmb_page."""
        return (self.ui.cmb_page.currentText() or self._PAGES[0]).lower()

    def _refresh_page(self):
        """Show the picked page; the Manage page reads the dry run each time
        it shows, and returns it (:meth:`_refresh_manage`).

        Each page carries its own controls: the Bake page its settings,
        Preset, Reset to Defaults and run button; the Manage page its table,
        whose right-click menu acts on the selection (:meth:`tbl_maps_init`),
        and the footer's Select and Fix All (:meth:`_manage_footer`). Neither
        shows a control that acts on the other.
        """
        manage = self._page() == "manage"
        self.ui.stk_pages.setCurrentIndex(int(manage))
        for control in getattr(self.ui.footer, "_lightmap_manage", ()):
            control.setVisible(manage)
        return self._refresh_manage() if manage else None

    def tbl_maps_init(self, widget) -> None:
        """The Manage table: one row per map the scene reads
        (:meth:`_refresh_manage`). Selecting rows selects their objects -- the
        selection its right-click **Re-Bake**, **Combine**, **Start Tracking**
        and **Revert** act on (:meth:`rebake_selected`, :meth:`combine_selected`,
        :meth:`track_selected`, :meth:`revert_selected`) -- and the menu opens a
        map's folder (:meth:`_fit_map_menu`)."""
        if not widget.is_initialized:
            widget.is_initialized = True
            QtWidgets = self.sb.QtWidgets
            widget.setColumnCount(len(self._MAP_COLUMNS))
            widget.setHorizontalHeaderLabels(list(self._MAP_COLUMNS))
            header = widget.horizontalHeader()
            header.setStretchLastSection(False)
            header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
            for col in range(1, len(self._MAP_COLUMNS)):
                header.setSectionResizeMode(col, QtWidgets.QHeaderView.ResizeToContents)
            widget.verticalHeader().setVisible(False)
            widget.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            widget.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            widget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
            widget.menu.add(
                "QPushButton",
                setText="Re-Bake",
                setObjectName="rebake_selected",
                setToolTip="Re-bake the selected objects -- the highlighted maps' "
                "objects, or what the footer's Select picked -- the way "
                "each was baked, changed or not: an atlas member back into its own "
                "cell where it fits. Uses the Bake page's Quality.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Combine…",
                setObjectName="combine_selected",
                setToolTip="Pack a split material's maps into one atlas from the "
                "lighting they hold -- no render -- and merge its duplicate "
                "materials. Asks the atlas size.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Start Tracking",
                setObjectName="track_selected",
                setToolTip="Record the selected untracked objects as baked, as they "
                "stand -- no render -- so their changes from here on are detected. "
                "For maps that match the scene; Re-Bake one that may not.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Revert…",
                setObjectName="revert_selected",
                setToolTip="Remove the selected objects' lightmap wiring, once "
                "confirmed. Materials and texture UVs were never changed, and the "
                "maps stay on disk; one Undo restores it.",
            )
            widget.menu.add(
                "QPushButton",
                setText="Open Folder",
                setObjectName="open_map_folder",
                setToolTip="Open the highlighted map's folder in the file manager.",
            )
        # Re-wired on every init: a reloaded panel keeps the widget, not the
        # connection (the Texture Combine table's rule).
        prior = getattr(widget, "_lightmap_handlers", {})
        wired = {
            "itemSelectionChanged": self._select_map_readers,
            "context_menu_about_to_show": self._fit_map_menu,
        }
        for name, handler in wired.items():
            signal = getattr(widget, name)
            if name in prior:
                try:
                    signal.disconnect(prior[name])
                except (TypeError, RuntimeError):
                    pass
            signal.connect(handler)
        widget._lightmap_handlers = wired

    def _fit_map_menu(self) -> None:
        """Fit the table menu to the highlighted rows, just before it opens:
        Open Folder needs a row whose map is on disk, Combine a split one,
        Start Tracking an untracked one."""
        rows = self._selected_maps()
        menu = self.ui.tbl_maps.menu
        QPushButton = self.sb.QtWidgets.QPushButton
        for name, enabled in (
            ("open_map_folder", any(row.get("path") for row in rows)),
            ("combine_selected", any(row.get("state") == "split" for row in rows)),
            ("track_selected", any(row.get("state") == "untracked" for row in rows)),
        ):
            item = menu.findChild(QPushButton, name)
            if item is not None:
                item.setEnabled(enabled)

    def _refresh_manage(self, footer: bool = True):
        """Read the maps and what changed onto the Manage page: the table and,
        with *footer*, the summary; returns the dry run read (``None`` when it
        could not be). Nothing is baked; nothing is read while the Bake page
        shows (a dry run is not free)."""
        if self._page() != "manage":
            return None
        try:
            baker = self._make_baker()
            # The folder Bake writes to: an atlas in another one re-packs
            # whole, and a report blind to it promised "written in place".
            report = baker.stale_report(output_dir=self._output_dir())
            rows = baker.bake_maps(report)
        except Exception as error:  # noqa: BLE001 -- a page change never raises
            self.logger.warning(f"Could not read the bake state: {error}")
            if footer:
                self.ui.footer.setText(
                    "Could not read the bake state (see the log).", level="error"
                )
            return None
        self._fill_maps(rows, report)
        self._report = report  # the dry run the table shows (Combine's names)
        if footer:
            levels = {row["level"] for row in rows}
            self.ui.footer.setText(
                ptk.StaleReport.tally(rows) if rows else "Nothing baked yet.",
                "error" if "error" in levels else "warning" if "warn" in levels else None,
            )
        return report

    def _fill_maps(self, rows: List[Dict[str, Any]], report) -> None:
        """Write *rows* (``LightmapBaker.bake_maps``) into the Manage table;
        each row's tooltip says where the map is, who wrote it, what its state
        means and how to remedy it (the row's ``hint``), and why each of its
        readers re-bakes (*report*)."""
        table = self.ui.tbl_maps
        QtGui, Qt = self.sb.QtGui, self.sb.QtCore.Qt
        colors = ptk.Palette.status()
        targets = set(report.targets)
        # A refill clears the highlight, which would select nothing in the
        # scene: the rows are written with signals blocked, and the maps
        # highlighted before are highlighted again.
        kept = {row["map"] for row in self._selected_maps()}
        blocked = table.blockSignals(True)
        self._map_rows = {}
        sorting = table.isSortingEnabled()
        table.setSortingEnabled(False)  # rows land where they are written
        table.setRowCount(len(rows))
        for r, row in enumerate(rows):
            name = str(row["map"])
            self._map_rows[name] = row
            readers = list(row.get("objects") or [])
            size = row.get("size")
            tip = [
                f"<b>{name}</b>",
                f"Folder: {row.get('folder') or '-'}",
                f"Size: {size[0]} x {size[1]}" if size else "Not on disk",
                f"Written by: {row['writer']}" if row.get("writer") else "Written by this scene",
                "",
                # The cell names the condition; what it means and the button
                # that remedies it ride the tooltip.
                f"<b>{row['state'].capitalize()}</b>: {row['hint']}",
            ]
            redo = [obj for obj in readers if obj in targets]
            if redo:
                tip.append("")
                tip += [f"{report.leaf(obj)}: {report.why(obj)}" for obj in redo]
            values = (
                name,
                "probe" if row.get("probe") else str(len(readers)),
                row["state"],
            )
            color = colors[{"ok": "valid"}.get(row["level"], row["level"])][0]
            for col, value in enumerate(values):
                item = self.sb.QtWidgets.QTableWidgetItem(value)
                item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
                item.setToolTip("<br>".join(tip))
                if col == 0:
                    item.setData(Qt.UserRole, name)
                    if row.get("saves_to"):  # waits for the save: its hint says
                        font = item.font()
                        font.setItalic(True)
                        item.setFont(font)
                elif col == 1:
                    item.setTextAlignment(Qt.AlignCenter)
                elif color:
                    item.setForeground(QtGui.QColor(color))
                table.setItem(r, col, item)
        table.setSortingEnabled(sorting)
        table.blockSignals(blocked)
        self._highlight_maps(kept)

    def _highlight_maps(self, names) -> None:
        """Highlight exactly the rows of the maps *names*, quietly: a row
        highlight otherwise selects every object its map is read by
        (:meth:`_select_map_readers`), replacing a selection set elsewhere."""
        table, Qt = self.ui.tbl_maps, self.sb.QtCore.Qt
        flags = self.sb.QtCore.QItemSelectionModel
        blocked = table.blockSignals(True)
        table.clearSelection()
        model = table.selectionModel()
        for r in range(table.rowCount()):
            if table.item(r, 0).data(Qt.UserRole) in names:
                model.select(table.model().index(r, 0), flags.Select | flags.Rows)
        table.blockSignals(blocked)

    def select_by_state(self, kind: str) -> None:
        """The footer's **Select**: highlight the maps in *kind*'s state on
        the Manage page (shown if it was not) and select their objects, so a
        right-click acts on them.

        *kind*: ``"changed"`` -- exactly what a re-bake would redo, the dry
        run's targets and what joins their atlases
        (``LightmapBaker.stale_report``), not every reader of their maps --
        ``"split"``, ``"untracked"``, ``"missing"`` or ``"all"``. Quietly: one
        dry run, the page's own refresh (:meth:`_refresh_manage`).
        """
        if self._page() != "manage":
            # Quietly: the picker's own slot would read the dry run again.
            combo = self.ui.cmb_page
            blocked = combo.blockSignals(True)
            combo.setCurrentIndex(self._PAGES.index("Manage"))
            combo.blockSignals(blocked)
        report = self._refresh_page()
        if report is None:
            return  # the footer says why
        rows = self._map_rows
        if kind == "changed":
            objects = list(dict.fromkeys(list(report.targets) + list(report.joining)))
            wanted = set(objects)
            names = {
                name for name, row in rows.items() if wanted & set(row.get("objects") or ())
            }
        else:
            names = {
                name for name, row in rows.items() if kind in ("all", row["state"])
            }
            objects = sorted({o for name in names for o in rows[name].get("objects") or ()})
        self._highlight_maps(names)
        # Replaced, not added to: a pick that finds nothing must not leave the
        # last pick standing, as if it had found that.
        chosen = self.tk.LightmapBaker.select(objects)
        if not (names or chosen):
            self.ui.footer.setText(f"No {kind} maps.")
            return
        n, m = len(chosen), len(names)
        self.ui.footer.setText(
            f"Selected {n} object{'s' if n != 1 else ''} on {m} map{'s' if m != 1 else ''}."
        )

    def _selected_maps(self) -> List[Dict[str, Any]]:
        """The Manage table's highlighted rows, as ``LightmapBaker.bake_maps`` gave them."""
        table = self.ui.tbl_maps
        rows = sorted({index.row() for index in table.selectedIndexes()})
        names = [table.item(r, 0).data(self.sb.QtCore.Qt.UserRole) for r in rows]
        return [self._map_rows[n] for n in names if n in self._map_rows]

    def _select_map_readers(self) -> None:
        """Select the objects the highlighted maps are read by (none: clear)."""
        readers = sorted(
            {obj for row in self._selected_maps() for obj in row.get("objects") or []}
        )
        self.tk.LightmapBaker.select(readers)

    def open_map_folder(self) -> None:
        """Open the highlighted map's folder in the file manager: its home,
        where a map waiting in the session for the save lands (``saves_to``)."""
        rows = self._selected_maps()
        path = rows[0].get("path") if rows else None
        if not path:
            self.ui.footer.setText(
                "That map is missing." if rows else "Highlight a map first.",
                level="error" if rows else "warning",
            )
            return
        ptk.FileUtils.open_explorer(
            os.path.dirname(rows[0].get("saves_to") or path), logger=self.logger
        )

    def combine_selected(self) -> None:
        """Pack the highlighted split maps' groups into one atlas each, no
        render (``LightmapBaker.combine``) -- the table menu's **Combine**, at
        the size the artist picks (:meth:`_combine_size`)."""
        maps = [row["map"] for row in self._selected_maps() if row["state"] == "split"]
        if not maps:
            self.ui.footer.setText("Highlight a split map first.", level="warning")
            return
        self._baker = self._make_baker()
        size = self._combine_size(maps)
        if size is None:
            return
        self._show_combined(
            self._baking(
                lambda progress: self._baker.combine(maps, size=size, on_progress=progress),
                "Combining",
                "Combined",
            )
        )

    def _combine_size(self, maps: List[str]) -> Optional[int]:
        """Ask the atlas size :meth:`combine_selected` packs *maps* into, each
        offered with the detail it keeps (``LightmapBaker.combine_sizes``);
        ``None`` cancelled (the footer says so)."""
        sizes = self._baker.combine_sizes(maps)
        if not sizes:
            self.ui.footer.setText("Nothing to combine.", level="warning")
            return None
        report = self._report
        files = sorted({f for name in maps for f in (report.split.get(name) or (name,))})
        duplicates = self._merged_materials(report, maps)
        labels: Dict[str, int] = {}
        for size, kept in sizes:
            full = kept >= self._baker.COMBINE_KEEP
            labels[f"{size} px: {'all' if full else f'{kept:.0%}'} detail"] = size
        answer = self.sb.message_box(
            "<b>Combine</b> -- "
            + ", ".join(f"<hl>{f}</hl>" for f in files)
            + " into one atlas, from the lighting they hold: no render."
            + (
                f"<br><br>Merges the duplicate materials ({', '.join(duplicates)})."
                if duplicates
                else ""
            ),
            *labels,
            "Cancel",
            default=list(labels)[-1],
        )
        if answer not in labels:
            self.ui.footer.setText("Combine cancelled.")
            return None
        return labels[answer]

    @staticmethod
    def _merged_materials(report, maps: List[str]) -> List[str]:
        """The duplicate materials a Combine of *maps* merges: each split
        group's own, where it has more than one (one material in two shading
        groups merges nothing). What every question that leads to a Combine
        names."""
        found: set = set()
        for name in maps:
            group = report.split_materials.get(name) or ()
            if len(group) > 1:
                found.update(group)
        return sorted(found)

    def _show_combined(self, result) -> None:
        """Refresh the table and say in the footer what a combine did."""
        self._refresh_manage(footer=False)
        if result.refused or not result:
            self.ui.footer.setText(result.refused or "Combined nothing.", level="error")
            return
        n = len(result.retired)
        self.ui.footer.setText(
            "Combined into " + ", ".join(os.path.basename(f) for f in result.files)
            + (f"; {n} old → Recycle Bin on save." if n else ".")
        )

    def fix_all(self) -> None:
        """The footer's **Fix All**: every map that needs it, once confirmed
        (``ptk.StaleReport.fix_plan``), the render last so a cancel keeps the rest.

        A missing map no re-bake renders (its objects hidden or excluded) comes
        off them (``LightmapBaker.revert``); each split no re-bake mends is
        combined (``LightmapBaker.combine``); the untracked rest is tracked as
        it stands (``LightmapBaker.track``) -- confirming vouches for those
        maps; then what changed re-bakes (``LightmapBaker.rebake_changed``), a
        missing map among it. The footer counts each step in one line, what it
        did not do too; detail goes to the log.
        """
        report = self._refresh_manage(footer=False)
        if report is None:
            return
        plan = report.fix_plan(self._map_rows.values())
        if not any(plan.values()):
            self.ui.footer.setText("Nothing to fix.")
            return
        self._baker = self._make_baker()
        args = self._bake_args() if plan["rebake"] else {}
        if args is None:
            return

        merged = self._merged_materials(report, plan["combine"])
        steps = (
            ("revert", "Take the lightmap off {}: hidden or excluded, map missing.", "object"),
            (
                "combine",
                "Combine {}, no render"
                + (
                    f"; merges the duplicate materials ({', '.join(merged)})."
                    if merged
                    else "."
                ),
                "split map",
            ),
            ("track", "Start tracking {} as they stand, no render.", "untracked object"),
            ("rebake", "Re-bake {}.", "changed object"),
        )
        if not self.sb.confirm(
            "<b>Fix All</b><br><br>"
            + "<br>".join(
                line.format(f"{len(plan[key])} {noun}{'s' if len(plan[key]) != 1 else ''}")
                for key, line, noun in steps
                if plan[key]
            ),
            yes="Fix All",
            no="Cancel",
        ):
            self.ui.footer.setText("Fix All cancelled.")
            return
        relocate = False
        if plan["rebake"]:
            relocate = self._confirm_rebake(report, args["output_dir"], "Fix All")
            if relocate is None:
                return
        # Each step's count, and what it planned but did not do (a cancel, a
        # refusal -- logged): "2 reverted, 3 not re-baked".
        parts: List[str] = []

        def tally(done: int, planned: int, verb: str) -> None:
            if done:
                parts.append(f"{done} {verb}")
            if planned > done:
                parts.append(f"{planned - done} not {verb}")

        # The steps that render nothing are one undo step; the re-bake, a
        # render, is its own.
        cancelled = False
        with self.tk.CoreUtils.undo_chunk("Fix All"):
            if plan["revert"]:
                # Per object: revert names every node it cleared, a legacy
                # shape marker's too.
                reverted = self._baker.revert(plan["revert"])
                tally(
                    len(plan["revert"]) if reverted else 0, len(plan["revert"]), "reverted"
                )
            if plan["combine"]:
                combined = self._baking(
                    lambda progress: self._baker.combine(
                        plan["combine"], on_progress=progress
                    ),
                    "Combining",
                    "Combined",
                )
                cancelled = combined.cancelled
                if combined.refused and not cancelled:
                    self.logger.warning(f"Fix All: {combined.refused}")
                n = len(plan["combine"])
                tally(0 if combined.refused else n, n, "combined")
            if plan["track"] and not cancelled:
                tally(len(self._baker.track(plan["track"])), len(plan["track"]), "tracked")
        if cancelled:  # the artist said stop: nothing after it runs
            self._refresh_manage(footer=False)
            self.ui.footer.setText(f"Fix All cancelled: {', '.join(parts)}.")
            return
        if plan["rebake"]:
            result = self._baking(
                lambda progress: self._baker.rebake_changed(
                    relocate=relocate, on_progress=progress, **args
                )
            )
            self.logger.info(f"Fix All: {self._bake_report(result)}")
            tally(len(result.maps), len(plan["rebake"]), "re-baked")
        self._refresh_manage(footer=False)
        short = any(" not " in part for part in parts)
        self.ui.footer.setText(
            f"Fix All: {', '.join(parts)}" + (" (see the log)." if short else "."),
            "warning" if short else None,
        )

    def _selected_meshes(self) -> Optional[List[Any]]:
        """The meshes the selection names, by the bake's own rule
        (``TextureBaker.resolve_meshes``: faces or a shape name their mesh, a
        group the meshes under it); ``None`` when nothing is selected -- an
        empty selection is not every baked object."""
        raw = self.tk.CoreUtils.selected_objects()
        if not raw:
            return None
        return list(self.tk.TextureBaker.resolve_meshes(raw, descendants=True) or [])

    def track_selected(self) -> None:
        """Start tracking the selected untracked objects as they stand
        (``LightmapBaker.track``) -- the table menu's **Start Tracking**.
        No render: for maps known to match the scene; one that may not wants
        **Re-Bake**."""
        meshes = self._selected_meshes()
        if meshes is None:
            self.ui.footer.setText(
                "Highlight the untracked maps first.",
                level="warning",
            )
            return
        tracked = self._make_baker().track(meshes)
        self._refresh_manage(footer=False)
        if not tracked:
            self.ui.footer.setText(
                "None of the selected objects is untracked.", level="warning"
            )
            return
        count = len(tracked)
        self.ui.footer.setText(
            f"Tracking {count} object{'s' if count != 1 else ''}."
        )

    def revert_selected(self) -> None:
        """Take the lightmaps off the selected objects, once confirmed.

        The selection only: an empty one is not every baked object (a
        whole-scene revert is every Manage row highlighted). What it removes
        is only the wiring -- the materials and texture UVs were never
        changed, and the EXR files stay on disk.
        """
        if self._baker is None:
            self._baker = self.tk.LightmapBaker()
        # Faces or a shape name their mesh (the bake's own rule): read as
        # objects only, a face selection became "nothing selected", and the
        # dialog offered to revert EVERY baked object.
        selection = self._selected_meshes()
        if selection is None:
            self.ui.footer.setText(
                "Highlight the maps to revert (or select their objects).",
                level="warning",
            )
            return
        targets = self._baker.baked_objects(selection) if selection else []
        if not targets:
            self.ui.footer.setText(
                "None of the selected objects has a lightmap.", level="warning"
            )
            return
        count = len(targets)
        confirmed = self.sb.confirm(
            f"<b>Revert</b> &mdash; {count} selected "
            f"object{'s' if count != 1 else ''}"
            + "<br><br>Removes their lightmap wiring: each object's lightmap "
            "record and its entry in the scene's lightmap export data. Their "
            "materials and texture UVs were never changed, and the baked EXR "
            "files stay on disk.<br><br>An export will carry no lightmap for "
            "them until they are baked again. One Undo restores the wiring.",
            yes="Ok",
            no="Cancel",
        )
        if not confirmed:
            self.ui.footer.setText("Revert cancelled.")
            return
        reverted = self._baker.revert(selection)
        self._refresh_manage(footer=False)
        if reverted:
            self.ui.footer.setText(
                f"Reverted {count} object{'s' if count != 1 else ''} (maps kept on disk)."
            )
        else:
            self.ui.footer.setText("No baked objects to revert.", level="warning")

    def rebake_selected(self) -> None:
        """Re-bake the selected baked objects the way each was baked, changed
        or not (``LightmapBaker.rebake``) -- the table menu's **Re-Bake**.
        After Select: Changed (:meth:`select_by_state`), exactly what changed
        and what it shades; on a highlighted map, also what the baseline
        cannot see (an albedo or emissive edit, a noisy render). Asks first
        what :meth:`_confirm_rebake` must."""
        selection = list(self.tk.CoreUtils.selected_objects() or [])
        if not selection:
            self.ui.footer.setText(
                "Highlight the maps to re-bake (or select their objects).",
                level="warning",
            )
            return
        self._baker = self._make_baker()
        args = self._bake_args()
        if args is None:
            return
        report = self._baker.rebake_report(selection, output_dir=args["output_dir"])
        if not report.targets:
            self.ui.footer.setText(
                "None of the selection is baked yet.",
                level="warning",
            )
            return
        relocate = self._confirm_rebake(report, args["output_dir"], "Re-Bake")
        if relocate is None:
            return
        result = self._baking(
            lambda progress: self._baker.rebake(
                selection, relocate=relocate, on_progress=progress, **args
            )
        )
        self._refresh_manage(footer=False)
        self._show_bake_report(result)

    def show_bake_state(self) -> None:
        """Show the scene's bake state, map by map, in a viewer
        (``LightmapBaker.bake_breakdown``, read with the panel's dials and
        Output Directory): each map's folder, readers, size, writer and state,
        what a Changed bake would redo and why, and the visible meshes no bake
        renders. Read-only; its links select and open
        (``UiUtils.dispatch_log_link``).

        One window: asked again while it is open, it is read again. It reads
        itself again on its header's refresh button, and on every save, open
        and new scene while it is open (:meth:`_refresh_bake_state`, once per
        burst): a save is when a map waiting in the session reaches its folder.
        """
        html = self._bake_state_html()
        if html is None:
            return
        view = self._state_view
        if view is not None and view.isVisible():
            view.setText(html)
            view.present()
            return
        jobs = self.tk.ScriptJobManager.instance()
        if view is not None:  # a closed one stops listening
            jobs.unsubscribe_all(view)
        view = self._state_view = self.sb.text_view_dialog(
            html,
            "Ok",
            title="Lightmap Bake State",
            size=(980, 640),
            link_handler=functools.partial(
                self.tk.UiUtils.dispatch_log_link, logger=self.logger
            ),
            on_refresh=self._refresh_bake_state,
        )

        def changed():
            # A host may report one load as two events (see _scene_opened).
            self._later("state", 0, self._refresh_bake_state)

        for event in ("SceneSaved", "SceneOpened", "NewSceneOpened"):
            try:
                jobs.subscribe(event, changed, owner=view)
            except Exception as error:  # noqa: BLE001 -- never block the window
                self.logger.debug(f"scene event {event!r} unavailable ({error})")
        # And with the panel: a window left open would read its gone widgets.
        jobs.connect_cleanup(self.ui, owner=view)

    def _bake_state_html(self) -> Optional[str]:
        """The Bake State as HTML (``LightmapBaker.bake_breakdown``, with the
        panel's Output Directory), or ``None`` -- said in the footer."""
        try:
            doc = self._make_baker().bake_breakdown(output_dir=self._output_dir())
        except Exception as error:  # noqa: BLE001 -- a menu item never raises
            self.logger.warning(f"Could not read the bake state: {error}")
            self.ui.footer.setText(
                "Could not read the bake state (see the log).", level="error"
            )
            return None
        return doc.to_html()

    def _refresh_bake_state(self) -> None:
        """Read the open Bake State window again; a closed one stops listening."""
        view = self._state_view
        if view is None:
            return
        if not view.isVisible():
            self.tk.ScriptJobManager.instance().unsubscribe_all(view)
            return
        html = self._bake_state_html()
        if html is not None:
            view.setText(html)

    def open_output(self) -> None:
        """Open the bake's output folder in the file manager.

        The folder the last bake wrote to when there is one -- Beside Material
        Textures sends maps away from the Output Directory, which then showed
        nothing new -- else the Output Directory field's resolved target when
        it points somewhere that exists, else the project's texture folder it
        resolves against: an action labelled "where the bakes go" that opened
        the *base* of a custom relative path would be one click short of the
        truth.
        """
        src = self._last_output_dir
        if not (src and os.path.isdir(src)):
            src = self._output_dir()
        if src and not os.path.isdir(src):  # not baked into yet
            src = self._sourceimages_dir()
        # The shared opener, not os.startfile: that exists on Windows only.
        if not (src and ptk.FileUtils.open_explorer(src, logger=self.logger)):
            self.ui.footer.setText(
                "No folder to open yet — set a project, or bake first.",
                level="warning",
            )
