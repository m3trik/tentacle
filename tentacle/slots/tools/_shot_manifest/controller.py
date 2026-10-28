# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest panel's controller: its state, the steps the table shows,
and the panel's two actions -- Assess and Build.

Composed of one mixin per job, each its own module: the table's rows
(:mod:`.table_presenter`), the Start / End column (:mod:`.range_column`),
following the scene's store (:mod:`.store_follow`), where the steps come from
(:mod:`.manifest_source`), the mapping template (:mod:`.mapping_picker`), the
rows' context menus (:mod:`.row_menus`), the header menu
(:mod:`.header_menu`), the view row above the table (:mod:`.view_combos`)
and the Export button's preview
(:mod:`.export_preview`).  Local Edits are a collaborator
(:class:`~.manifest_editor.ManifestEditor`).

One copy for both hosts: every host call goes through :attr:`manifest_host`,
the host library's ``ManifestHost`` (from ``Slots.tk``), and the behaviors
through :attr:`behaviors`, that host's ``Behaviors``.
"""

from contextlib import contextmanager
from typing import Dict, List, Optional, Tuple

import pythontk as ptk
from pythontk import BuilderStep, ColumnMap, ShotPairing, StepStatus

from .export_preview import ExportPreviewMixin
from .header_menu import HeaderMenuMixin
from .manifest_data import ERROR_COLOR, SETTINGS_NS
from .manifest_editor import ManifestEditor
from .manifest_source import ManifestSourceMixin
from .mapping_picker import MappingPickerMixin
from .range_column import RangeColumnMixin
from .row_menus import RowMenusMixin
from .store_follow import StoreFollowMixin
from .table_presenter import ManifestTableMixin
from .view_combos import ViewCombosMixin


class ShotManifestController(
    ManifestTableMixin,
    RangeColumnMixin,
    StoreFollowMixin,
    ManifestSourceMixin,
    MappingPickerMixin,
    RowMenusMixin,
    HeaderMenuMixin,
    ViewCombosMixin,
    ExportPreviewMixin,
    ptk.LoggingMixin,
):
    """Business logic for the Shot Manifest UI (see the module docstring)."""

    def __init__(self, slots_instance, log_level="WARNING"):
        super().__init__()
        self.set_log_level(log_level)
        self.sb = slots_instance.sb
        self.ui = slots_instance.ui
        #: The host library's manifest seam (store and engine classes, the
        #: playhead, the Outliner, names and icons) and its behaviors.
        self.manifest_host = slots_instance.tk.ManifestHost
        self.behaviors = self.manifest_host.behaviors_cls()
        self._steps: List[BuilderStep] = []
        self._csv_path: str = ""
        # Where the loaded steps came from: "csv" (a manifest), "scene" (the
        # store's own shots) or "detect" (animation regions, nothing built yet).
        self._source: str = ""
        self._store = None  # the store the last build used
        self._last_results: list = []  # Last assessment results

        from uitk.managers.settings_manager import SettingsManager

        self._settings = SettingsManager(namespace=SETTINGS_NS)
        # The loaded source's steps as the source has them; ``_steps`` is
        # what the table shows and Build takes -- these with the Local Edits.
        self._sheet_steps: List[BuilderStep] = []
        # One-shot migration: fit_mode and initial_shot_length now live on
        # ShotStore.  Purge the old manifest-namespaced keys so they don't
        # linger indefinitely in QSettings.
        _qs = self._settings.settings
        for _legacy in (
            f"{SETTINGS_NS}/fit_mode",
            f"{SETTINGS_NS}/initial_shot_length",
            # Local Edits' on/off: the edits always apply now (2026-10-10).
            f"{SETTINGS_NS}/{ManifestEditor.RETIRED_SETTING}",
        ):
            if _qs.contains(_legacy):
                _qs.remove(_legacy)

        self._user_ranges: Dict[str, Tuple[Optional[float], Optional[float]]] = {}
        # The entries of _user_ranges a load seeded from the steps' shots: a
        # shot's bounds, not a place the user typed (_typed_ranges).
        self._seeded_ranges: Dict[str, Tuple[float, float]] = {}

        tree = self.ui.tbl_steps
        tree.enable_column_config()
        # Colour tags: this panel's palette per user, the tags per sheet on the
        # scene's store (ManifestTags), a strip down each step row.
        self._row_tags = tree.enable_row_tags(
            settings=self._settings, settings_key="row_tags"
        )
        self._row_tags.assigned.connect(self._on_rows_tagged)

        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QAbstractItemView

        tree.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tree.setExpandsOnDoubleClick(False)
        tree.setContextMenuPolicy(Qt.CustomContextMenu)
        tree.customContextMenuRequested.connect(self._show_item_menu)
        tree.itemDoubleClicked.connect(self._on_range_double_clicked)
        tree.itemChanged.connect(self._on_item_changed)
        tree.elided_tooltips = True  # a long description reads in full
        self._editor = ManifestEditor(self)

        self._building = False
        self._first_shown = False
        self._shown_record = None  # the scene's shots as the table last read them
        self._shown_pairing = None  # a sheet's pairing as the table last drew it
        self._reassess_timer = None  # _reassess_soon's, made on first use
        self._reassess_on_show = False  # owed while the panel was hidden
        self._reassess_note = ""  # the edit a pending re-assessment follows
        self._behavior_sets = {}  # _behavior_set's lists, read once
        self._store_listener_bound = False
        self._cached_gaps: Optional[List[float]] = None
        self._cached_gap_ends: Optional[Dict[float, float]] = None
        self._last_resolved: List[Tuple[str, float, Optional[float], bool]] = []
        # {step_id: where}: the steps whose resolved range is where Build
        # would insert their shot on a built timeline (_projected_inserts).
        self._projected: Dict[str, str] = {}
        # {step_id: frames}: the unbuilt steps whose typed range Build's
        # inserts move, and how far (_resolve_ranges).
        self._typed_shift: Dict[str, float] = {}
        # The inserts the shown preview was resolved with (_resolve_ranges).
        self._inserts: list = []
        # The last Build's typed ranges before and after it, and the shots it
        # made: put back when that Build is undone (_on_native_step_followed).
        self._build_undo: Optional[dict] = None
        # {step_id: [(status, text)]}: the steps whose range overlaps a
        # neighbour's (_validate_range_collisions); their rows say so.
        self._range_issues: Dict[str, list] = {}
        self._detection_snapshot: tuple = ()  # _detection_inputs, last seen
        self._bind_store_listener()
        # A swapped store -- scene new / open, a referenced file's shots
        # merged or discarded -- through the store's own invalidation
        # registry, as the Shot Sequencer and blendertk's twin follow it: the
        # scriptJobs this used to hang on missed a merge, leaving the panel on
        # the dead store, and relied on running after the store's own.
        self._store_cls().add_invalidation_listener(self._on_store_invalidated)
        # The DCC's own undo / redo, once the store followed it: a Build undone
        # takes its typed-range bookkeeping with it.
        self._store_cls().add_native_step_listener(self._on_native_step_followed)
        # Tear down on panel close: the ShotStore listener needs remove_callbacks,
        # or it keeps the dead controller alive and firing after the panel closes.
        self.ui.destroyed.connect(lambda *_: self.remove_callbacks())
        self._column_map = ColumnMap()
        self._active_mapping = None  # effective template (options applied)
        self._mapping_template = None  # the template as loaded, options block and all
        self._mapping_name = None
        self._user_template = None  # the user's pick (_apply_mapping)
        # The option values the scene keeps for the sheet loaded; None: the
        # user's own (MappingPickerMixin._adopt_sheet_options).
        self._sheet_values = None
        # (key, values) of the last _inferred_sheet_options read: one sheet.
        self._inferred_options: Optional[tuple] = None
        self._option_rows: list = []  # the mapping popup's rows of its options
        self._mapping_menu = None  # that popup (_mapping_popup)
        self._mapping_dir = None  # custom directory override
        self._setup_recent_csv()
        self._setup_csv_path_editing()
        self._setup_header_menu()
        self._setup_mapping_combo()
        self._setup_view_combos()
        self._restore_color_overrides()
        self._move_action_buttons_to_footer()
        self._setup_export_button()
        self.ui.on_first_show.connect(self._on_first_show)
        self.ui.on_show.connect(self._on_show)

    def _move_action_buttons_to_footer(self) -> None:
        """Reparent the Export/Assess/Build buttons into the footer's right side.

        The UI file still lays them out in ``action_layout`` above the
        footer so Designer remains usable; at runtime we relocate them
        onto the footer itself to consolidate the action row.  Sizes
        declared in the .ui file are preserved.
        """
        footer = getattr(self.ui, "footer", None)
        add_widget = getattr(footer, "add_widget", None) if footer else None
        if not callable(add_widget):
            return
        for name in ("b004", "b002", "b003"):
            btn = getattr(self.ui, name, None)
            if btn is None:
                continue
            add_widget(btn, side="right", background=True)

    def _on_first_show(self) -> None:
        """Auto-populate the table the first time the window is shown."""
        self._first_shown = True
        self._open_scene_source()

    @property
    def _is_built(self) -> bool:
        """True if any loaded step has a shot (``_pairing``)."""
        try:
            return bool(self._pairing().shots)
        except Exception:
            return False

    def _step_is_built(self, step_id: str) -> bool:
        """True if step *step_id* has a shot (``_pairing``)."""
        try:
            return step_id in self._pairing().shots
        except Exception:
            return False

    def _store_cls(self):
        """This host's store class (``ManifestHost.store_cls``)."""
        return self.manifest_host.store_cls()

    def _manifest_cls(self):
        """This host's manifest engine class (``ManifestHost.manifest_cls``)."""
        return self.manifest_host.manifest_cls()

    @property
    def _match(self) -> str:
        """How the selected template pairs steps with shots (``match``)."""
        return (self._active_mapping or {}).get("match", "name")

    def _manifest(self, store=None):
        """This host's manifest engine over *store* (default: the active one),
        pairing steps with shots the way the selected template says."""
        store = store if store is not None else self._active_store()
        return self._manifest_cls()(
            store,
            match=self._match,
            rebuild_edited=self._rebuild_edited,
            disabled_behaviors=self._disabled_behaviors(),
            marked_behaviors=self._marked_behaviors(),
        )

    def _pairing(self, steps=None, store=None) -> ShotPairing:
        """Which shot each step (default: the loaded ones) is -- the pure
        ``ShotManifest.pair``, the one place a step finds its shot (binding,
        name, then order); it reads only the store, so no host engine."""
        store = store if store is not None else self._active_store()
        steps = self._steps if steps is None else steps
        if store is None or not steps:
            return ShotPairing()
        return ptk.ShotManifest(store, match=self._match).pair(steps)

    def _orphan_shots(self, pairing: Optional[ShotPairing] = None) -> list:
        """Shots no step of the loaded sheet pairs with ("not in doc" rows);
        only a sheet can leave a shot out, so none in the other modes."""
        if self._source != "csv":
            return []
        return (pairing if pairing is not None else self._pairing()).orphans

    @property
    def _hide_missing(self) -> bool:
        """Hide > Steps Without a Shot (kept per user): leave out the steps
        that have no shot -- the table, Assess and Build alike."""
        return bool(self._settings.value("hide_missing", False))

    def _rows(self, pairing: Optional[ShotPairing] = None) -> list:
        """The table's ``(step, shot)`` rows (``ShotPairing.rows``): the
        steps, less those with no shot while they are hidden and some
        step has one (a step Local Edits added stays: the user just asked for
        it), and the shots no step pairs with where the timeline has them."""
        pairing = pairing if pairing is not None else self._pairing()
        edits = self._editor.edits if self._editor.enabled else None
        keep = [s.step_id for s in self._steps if edits and edits.is_added(s.step_id)]
        return pairing.rows(
            self._steps,
            # Once a step has a shot: before, every step is still to build.
            hide_missing=self._hide_missing and bool(pairing.shots),
            orphans=self._source == "csv",
            keep=keep,
        )

    def _shown_steps(self) -> List[BuilderStep]:
        """The steps the table shows -- what Assess judges and Build builds:
        a step hidden as a missing shot is not built behind the user's back."""
        if not self._hide_missing:
            return self._steps
        return [step for step, _shot in self._rows() if step is not None]

    def _locked_step_ids(self, pairing: Optional[ShotPairing] = None) -> set:
        """The IDs of the steps whose shot is locked -- final: Build leaves
        it (``ShotBlock.locked``) and its row takes no Local Edits."""
        try:
            pairing = pairing if pairing is not None else self._pairing()
        except Exception:
            return set()
        return {sid for sid, shot in pairing.shots.items() if shot.locked}

    def _step_is_locked(self, step_id: str) -> bool:
        """True if step *step_id*'s shot is locked (:meth:`_locked_step_ids`)."""
        return step_id in self._locked_step_ids()

    @contextmanager
    def _edit_store(self, label: str):
        """One undoable store edit made from this panel (``scene_edit``),
        yielding the store: the events it raises are not followed -- the
        caller redraws once it is done (:meth:`_redraw`)."""
        store = self._active_store()
        if store is None:
            raise RuntimeError("No shot store in this scene.")
        self._building = True
        try:
            with store.scene_edit(label):
                yield store
        finally:
            self._building = False

    def _redraw(self, reassess: bool = False) -> None:
        """Draw the table again, keeping its expansion and scroll, with the
        showing assessment over it -- run again once edits settle when
        *reassess* (the scene changed, not only the view).

        On a built timeline the unbuilt rows' frames are worked out again --
        the shots' bounds and the insert preview, no animation scan
        (:meth:`_resolve_ranges`) -- so a Build, a shot edited elsewhere or
        the steps shown again never leave a preview of the timeline before.
        """
        state = self._save_tree_state()
        self._populate_table()
        assessed = bool(self._last_results)
        if self._is_built and not self._use_selected_keys:
            self._refresh_ranges(mark=not assessed)
        elif self._last_resolved:  # the unbuilt rows' frames, as last resolved
            self._auto_fill_ranges(self._last_resolved)
            self._validate_range_collisions(self._last_resolved, mark=not assessed)
        if assessed:
            self._apply_assessment(self._last_results)  # marks every row
            if reassess:
                self._reassess_soon()
        self._restore_tree_state(state)
        self._update_build_button()

    def _active_store(self):
        """Return the cached store, or the host's active one."""
        if self._store is not None:
            return self._store
        try:
            return self._store_cls().active()
        except Exception:
            return None

    def _set_footer(self, text: str, *, color: str = "") -> None:
        """Set footer text with an optional foreground color."""
        label = self.ui.footer._status_label
        if color:
            label.setStyleSheet(
                f"background: transparent; border: none; color: {color};"
            )
        else:
            label.setStyleSheet("background: transparent; border: none;")
        self.ui.footer.setText(text)

    @property
    def _initial_shot_length(self) -> float:
        """Read the shot-construction default from the active store."""
        store = self._store_cls().active()
        if store is not None:
            return float(store.initial_shot_length)
        return self._store_cls().DEFAULT_INITIAL_SHOT_LENGTH

    @property
    def _fit_mode(self) -> str:
        """Read the fit-mode policy from the active store."""
        store = self._store_cls().active()
        if store is not None:
            return store.fit_mode
        return self._store_cls().DEFAULT_FIT_MODE

    def _ensure_steps(self) -> bool:
        """Ensure steps are available, auto-detecting from scene if needed.

        Priority order:
        1. If steps are already loaded, return True immediately.
        2. Load the source: the CSV in the field, else the scene's shots.
        3. Otherwise, run scene detection -- unless the field names a sheet:
           guessed regions would stand in for the sheet that failed to load.

        Returns True if steps are now available.
        """
        if self._steps:
            return True

        self._populate_from_source()
        if self._steps:
            return True
        if self.ui.txt_csv_path.text().strip():
            if self._source != "csv":
                reason = (
                    "The sheet in the field did not load (see the field) and "
                    "the scene has no shots -- nothing to assess."
                )
            elif self._sheet_steps:  # Local Edits hide what the sheet has
                reason = (
                    "Every step of the sheet is hidden (Local Edits: Show "
                    "Hidden) -- nothing to assess."
                )
            else:
                reason = "Every step of the sheet is excluded -- nothing to assess."
            self._set_footer(reason, color=ERROR_COLOR)
            return False

        # Fall back to scene detection
        try:
            self.detect()
        except Exception as exc:
            self.logger.error("Auto-detect failed: %s", exc)
            self._set_footer(f"Detection error: {exc}", color=ERROR_COLOR)

        if not self._steps:
            self._set_footer("No animation detected in scene.")
            return False
        return True

    def _update_build_button(self) -> None:
        """Enable Build once Assess has run and a build would change something.

        Build always starts disabled. It is warranted while a step is unbuilt,
        an object is one a build fixes -- not in its shot, its behavior keys
        missing or made under an older effect recipe -- a shot holds keys of
        behaviors the doc dropped, or a shot's name, description or objects
        are not the step's (``StepStatus.needs_build``).  A Local Edit is
        judged by the Assess it runs again (:meth:`_reassess_soon`).
        """
        btn = getattr(self.ui, "b003", None)
        if btn is None:
            return
        if self._editor.viewing_original:
            btn.setEnabled(False)  # a view of the sheet, never built
            return
        btn.setEnabled(any(r.needs_build for r in self._last_results))

    def _confirm_inserts(self, inserts: list, store) -> bool:
        """Ask before *inserts* (``ShotManifest.plan_insertions``) move shots
        already built: how many new shots, how many existing ones move later
        with their keys, how many of those are locked.  Appending after the
        last shot moves nothing and asks nothing."""
        shots = store.sorted_shots()
        index = {shot.shot_id: i for i, shot in enumerate(shots)}
        # Every shot after the earliest existing shot an insert goes after
        # moves (PlannedInsert.after_shot_id).
        first = min(
            0 if p.after_shot_id is None else index[p.after_shot_id] + 1
            for p in inserts
        )
        moving = shots[first:]
        if not moving:
            return True
        locked = sum(1 for shot in moving if shot.locked)
        note = f" ({locked} of them locked)" if locked else ""
        answer = self.sb.message_box(
            f"<b>Insert {len(inserts)} new shot(s)?</b><br>"
            "Each goes in sheet order, after its previous step's shot.<br>"
            f"{len(moving)} existing shot(s){note} move later to make room, "
            "their keys with them.",
            "Insert",
            "Cancel",
        )
        return answer == "Insert"

    def build(self) -> None:
        """Build or update shots in the store from loaded steps."""
        if self._editor.refuse_viewing("build"):  # a view, never built
            return
        if not self._ensure_steps():
            return

        if not self.manifest_host.available():
            self._set_footer(
                f"{self.manifest_host.APP} is required to build shots.", color=ERROR_COLOR
            )
            return

        try:
            store = self._store_cls().active()
            builder = self._manifest(store)

            # When selected-keys mode is active, verify keys exist
            # before proceeding -- even if user ranges are complete.
            use_sel = self._use_selected_keys
            if use_sel and not self._selected_keys_found(store):
                return

            # Incremental mode (shots exist, no selected keys): a new step's
            # shot is inserted in sheet order, the later shots rippling out
            # of its way; the ranges are read once the inserts are in.
            incremental = self._is_built and not use_sel
            go, range_map = self._build_ranges(incremental)
            if not go:
                return
            build_steps = self._steps_to_build(use_sel, range_map)
            if not build_steps:
                return

            inserts, typed = [], self._typed_ranges()
            if incremental:  # a typed step goes there, the next follows it
                inserts = builder.plan_insertions(
                    build_steps,
                    typed=typed,
                    fit_mode=self._fit_mode,
                    initial_shot_length=self._initial_shot_length,
                )
                if inserts and not self._confirm_inserts(inserts, store):
                    self._set_footer("Build cancelled -- no shot moved.")
                    return

            ranges_before = (dict(self._user_ranges), dict(self._seeded_ranges))
            ids_before = {shot.shot_id for shot in store.shots}
            actions, beh, assessment, ridden = self._sync_build(
                builder, store, build_steps, inserts, typed, range_map, incremental, use_sel
            )

            # Store the store for later handoff to Shot Sequencer UI
            self._store = store
            self._rebase_typed_ranges(store, typed, ridden, ranges_before, ids_before)

            report, failed = self._build_report(actions, beh)
            self._set_footer(report, color=ERROR_COLOR if failed else "")
            self._sync_store_gap(store)

            # Refresh tree with post-build assessment
            self._apply_post_build(assessment, store)
            self._update_build_button()
        except Exception as exc:
            self.logger.error("Build failed: %s", exc)
            self.sb.message_box(
                f"<b>Build failed.</b><br>{exc}",
            )
            self._set_footer(f"Build error: {exc}", color=ERROR_COLOR)

    def _selected_keys_found(self, store) -> bool:
        """Whether selected keys give a selected-keys Build regions to build
        on; when none do, the user is told so."""
        self._cached_gaps = None
        regions = self._detect_regions(store.detection_threshold if store else 5.0)
        if regions:
            return True
        self.sb.message_box(
            "<b>No keys selected.</b><br>"
            "Select keyframes in the Graph Editor before building.",
        )
        self._set_footer(
            "No selected keys found \u2014 select keyframes first.",
            color=ERROR_COLOR,
        )
        return False

    def _build_ranges(self, incremental: bool) -> Tuple[bool, Optional[dict]]:
        """``(go, range_map)`` for a Build: no map in incremental mode (the
        inserts place the new steps), the typed ranges when every step has
        one (detection mode provides full ranges), else the resolved ones;
        ``go`` is ``False`` when the user cancelled."""
        if incremental:
            return True, None
        if self._all_ranges_complete():
            return True, dict(self._user_ranges)
        resolved = self._resolve_ranges()
        placement = self._placement_on_regions()
        if placement is None:
            self._set_footer("Build cancelled -- set the steps' ranges first.")
            return False, None
        if not placement:
            resolved = self._resolve_ranges(regions=False)
        return True, {sid: (s, e) for sid, s, e, _ in resolved if e is not None} or None

    def _steps_to_build(self, use_sel: bool, range_map: Optional[dict]) -> list:
        """The steps a Build makes shots for: the shown ones (one hidden as a
        missing shot gets none; never empty, a built step shows) -- in
        selected-keys mode only those the detected regions gave a range, so
        ``sync`` never places the rest by its own sequential cursor. Empty,
        and said, when the selected keys map to no step."""
        build_steps = self._shown_steps()
        if not (use_sel and range_map):
            return build_steps
        build_steps = [s for s in build_steps if s.step_id in range_map]
        if not build_steps:
            self.sb.message_box(
                "<b>No matching steps.</b><br>"
                "Selected keys don't map to any CSV steps.",
            )
            self._set_footer(
                "Selected keys don't map to any CSV steps.",
                color=ERROR_COLOR,
            )
        return build_steps

    def _sync_build(
        self, builder, store, build_steps, inserts, typed, range_map, incremental, use_sel
    ):
        """Make the Build's shots, one scene edit: the planned inserts, then
        ``sync`` over *build_steps*. Returns ``(actions, behaviors,
        assessment, ridden)``, *ridden* the typed ranges moved with the
        shots the inserts moved."""
        ridden = typed
        self._building = True
        try:
            with store.scene_edit("manifest_build"), store.batch_update():
                inserted = builder.insert_planned(inserts, typed=typed) if inserts else {}
                if incremental:
                    # A typed range is in the timeline's frames as they
                    # were: it moves with the shots the inserts moved (a
                    # refused one moved nothing).
                    made = [p for p in inserts if inserted.get(p.step.step_id) == "created"]
                    ridden = ptk.ShotManifest.ride_inserts(typed, made)
                    # Grow-only: a step with a shot keeps its bounds, a
                    # typed range places the rest (RangeResolver).
                    range_map = ptk.RangeResolver.incremental_ranges(
                        self._steps,
                        {
                            sid: (shot.start, shot.end)
                            for sid, shot in self._pairing(store=store).shots.items()
                        },
                        user_ranges=ridden,
                    )
                actions, beh, assessment = builder.sync(
                    build_steps,
                    ranges=range_map,
                    # A build never removes a shot: one no step pairs with
                    # is listed ("not in doc") for the user to remove.
                    remove_missing=False,
                    zero_duration_fallback=incremental,
                    fit_mode=self._fit_mode,
                    initial_shot_length=self._initial_shot_length,
                    skip_scene_discovery=use_sel,
                )
                # Sync patched what an insert made; a refused insert
                # stays refused unless sync made its shot after all.
                actions.update(
                    {
                        sid: action
                        for sid, action in inserted.items()
                        if action != "refused" or actions.get(sid) != "created"
                    }
                )
                # Record the source CSV for provenance on reopen -- only
                # the one these steps came from: a path still in the field
                # after a failed load was never used.
                csv_path = self._csv_path
                if csv_path and store.source_csv != csv_path:
                    store.source_csv = csv_path
                    store.mark_dirty()
                # And how it was read: the scene reopens on it this way,
                # whatever the user's own options are by then.
                self._record_sheet_options(store)
        finally:
            self._building = False
        return actions, beh, assessment, ridden

    #: A Build's shot actions and behavior outcomes, in the order its footer
    #: reports them: ``(source, key, words)``.
    BUILD_REPORT = (
        ("shots", "created", "created"),
        ("shots", "patched", "patched"),
        ("shots", "skipped", "unchanged"),
        ("shots", "refused", "not built (name taken, see log)"),
        (
            "shots",
            "kept",
            "edited by hand, kept (Edits: Rebuild Hand-Edited Shots rebuilds them)",
        ),
        ("shots", "locked", "locked, left as they are"),
        ("behaviors", "applied", "behaviors applied"),
        ("behaviors", "skipped", "behaviors kept (animator keys)"),
        ("behaviors", "marked", "behaviors marked (Shot Sequencer)"),
        ("behaviors", "failed", "behaviors failed (see log)"),
    )

    @classmethod
    def _build_report(cls, actions: dict, beh: dict) -> Tuple[str, bool]:
        """The Build's footer line from its shot *actions* and behavior
        outcomes *beh*, and whether anything failed (a behavior, or a shot
        not built)."""
        counts = {
            "shots": lambda key: sum(1 for a in actions.values() if a == key),
            "behaviors": lambda key: len(beh.get(key, [])),
        }
        parts, failed = [], False
        for source, key, words in cls.BUILD_REPORT:
            n = counts[source](key)
            if n:
                parts.append(f"{n} {words}")
                failed = failed or key in ("refused", "failed")
        return f"Build complete: {', '.join(parts)}.", failed

    @staticmethod
    def _sync_store_gap(store) -> None:
        """Sync ``store.gap`` from the actual shot positions so the spinbox
        reflects the gap the manifest produced."""
        actual_gap = store.compute_gap()
        if abs(actual_gap - store.gap) > 0.5:
            store.gap = actual_gap
            store.mark_dirty()
            store.notify_settings_changed()

    def _rebase_typed_ranges(
        self, store, typed: dict, ridden: dict, before: tuple, ids_before: set
    ) -> None:
        """The typed ranges after a Build: a step it gave a shot is placed by
        its shot now (its range goes -- left, it would place the step where it
        was once the shot is gone); the rest move with the inserts it made
        (*ridden*), as the shots after them did.  What they were is kept for
        an undo of the Build (:meth:`_on_native_step_followed`), with the
        shots it made -- the sign it was undone."""
        shots = self._pairing(store=store).shots
        for sid in typed:
            if sid in shots:
                self._user_ranges.pop(sid, None)
            elif ridden.get(sid) is not None:
                self._user_ranges[sid] = ridden[sid]
        made = {shot.shot_id for shot in store.shots} - ids_before
        self._build_undo = (
            {
                "store": store,
                "made": made,
                "before": before,
                "after": (dict(self._user_ranges), dict(self._seeded_ranges)),
            }
            if made
            else None
        )

    def _apply_post_build(self, results: list, store) -> None:
        """Refresh tree with timing from the store and assessment results."""
        self._last_results = results
        self._redraw()
        self._sync_detection_widgets()

    def _sync_detection_widgets(self) -> None:
        """Refresh the Shots UI widget states via its centralized method."""
        instances = getattr(self.sb, "slot_instances", None) or {}
        shots_slots = instances.get("shots") if isinstance(instances, dict) else None
        if shots_slots is not None:
            ctrl = getattr(shots_slots, "controller", None)
            if ctrl is not None and hasattr(ctrl, "refresh_state"):
                ctrl.refresh_state()
                return
        # Fallback: direct widget manipulation if controller not available
        try:
            shots_ui = self.sb.loaded_ui.shots
        except Exception:
            return
        store = self._active_store()
        enabled = store.is_detection_relevant if store is not None else True
        for attr in ("cmb_detection_mode", "spn_detection"):
            widget = getattr(shots_ui, attr, None)
            if widget is not None:
                widget.setEnabled(enabled)

    def assess(self, skip_key_check: bool = False, note: str = "") -> None:
        """Compare the steps against the scene's shots and colour the tree.

        Parameters:
            skip_key_check: When ``True``, bypass the selected-keys guard.
                Used by internal callers (e.g. re-apply behavior) that
                already know the scene state and just need a status refresh.
            note: What the footer says before the assessment's summary --
                the edit a re-assessment follows (:meth:`_reassess_soon`).
        """
        if not self._ensure_steps():
            return

        if not self.manifest_host.available():
            self._set_footer(
                f"{self.manifest_host.APP} is required to assess shots.", color=ERROR_COLOR
            )
            return

        store = self._store_cls().active()
        builder = self._manifest(store)
        use_sel = self._use_selected_keys

        # In selected-keys mode, verify keys exist before proceeding —
        # but only when shots haven't been built yet (key selection is for
        # initial range discovery, not for re-assessment of existing shots).
        if use_sel and not skip_key_check and not self._is_built:
            self._cached_gaps = None
            regions = self._detect_regions(store.detection_threshold if store else 5.0)
            if not regions:
                self.sb.message_box(
                    "<b>No keys selected.</b><br>"
                    "Select keyframes in the Graph Editor before assessing.",
                )
                self._set_footer(
                    "No selected keys found \u2014 select keyframes first.",
                    color=ERROR_COLOR,
                )
                return

        # Invalidate cached gaps so _resolve_ranges rescans the scene
        self._cached_gaps = None
        self._cached_gap_ends = None

        results = builder.assess(self._shown_steps(), skip_scene_discovery=use_sel)

        # Write per-object statuses back to shot metadata so that
        # both the manifest and sequencer share the same classification.
        built_map = self._pairing(store=store).shots
        status_changed = False
        for r in results:
            shot = built_map.get(r.step_id)
            if shot is None:
                continue
            obj_status = {o.name: o.status for o in r.objects}
            for extra in r.additional_objects:
                obj_status.setdefault(extra, "additional")
            if shot.metadata.get("object_status") != obj_status:
                shot.metadata["object_status"] = obj_status
                status_changed = True
        if status_changed:
            store.mark_dirty()

        # Rebuild tree and enrich with timing from store + status: the rows
        # are marked once, by this assessment (_apply_assessment).
        state = self._save_tree_state()
        self._last_results = results
        self._populate_table()
        self._refresh_ranges(mark=False)  # built: no scan -- the insert preview
        self._apply_assessment(results)
        self._restore_tree_state(state)

        # Summary counts
        n_built = sum(1 for r in results if r.built)
        missing_obj_names = {
            o.name for r in results for o in r.objects if o.status == "missing_object"
        }
        missing_beh_names = {
            o.name for r in results for o in r.objects if o.status == "missing_behavior"
        }
        stale_names = {
            o.name for r in results for o in r.objects if o.status == "stale_behavior"
        }
        n_dropped = sum(len(r.dropped_behaviors) for r in results)
        n_additional = sum(len(r.additional_objects) for r in results)
        n_shrinkable = sum(1 for r in results if r.shrinkable_frames > 0)
        n_updates = sum(1 for r in results if r.updates)
        pending = [
            u for u in StepStatus.UPDATES if any(u in r.updates for r in results)
        ]
        sorted_shots = store.sorted_shots()
        total_frames = (
            (sorted_shots[-1].end - sorted_shots[0].start) if sorted_shots else 0
        )
        parts = [f"{n_built}/{len(results)} steps built, {total_frames:.0f} frames"]
        hidden = len(self._steps) - len(results)
        if hidden:
            parts.append(f"{hidden} without a shot hidden")
        if missing_obj_names:
            parts.append(f"{len(missing_obj_names)} missing objects")
        if missing_beh_names:
            parts.append(f"{len(missing_beh_names)} missing behaviors")
        if stale_names:
            parts.append(f"{len(stale_names)} to re-key (older recipe)")
        if n_dropped:
            parts.append(f"{n_dropped} dropped behavior(s) to remove")
        if n_additional:
            parts.append(f"{n_additional} scene objects")
        if n_shrinkable:
            parts.append(f"{n_shrinkable} shrinkable")
        if n_updates:
            parts.append(f"{n_updates} shot(s) to update ({', '.join(pending)})")
        self._set_footer(f"{note} Assessment: {', '.join(parts)}".strip())
        self._update_build_button()
