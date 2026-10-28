# !/usr/bin/python
# coding=utf-8
"""Where the Shot Manifest's steps come from: a build sheet (a CSV path or link,
with its recent-paths list and live validation), the scene's own shots, or the
animation detected in the scene -- and the one place a source becomes the
table (:meth:`ManifestSourceMixin._load_data`).  Also the sheet's asset column:
filling it from the scene.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import Dict, List, Optional, Tuple

import pythontk as ptk
from pythontk import BuilderStep, ManifestModel

from .manifest_data import ERROR_COLOR


class ManifestSourceMixin:
    """The panel's sources, mixed into ``ShotManifestController``.

    Uses the controller's ``ui`` (``txt_csv_path``, ``tbl_steps``), ``sb``,
    ``_editor``, ``_column_map``, ``_active_mapping``, ``_active_store()``,
    ``_manifest()``, ``_pairing()``, ``_shown_steps()``, ``_populate_table()``,
    ``_refresh_ranges()``, ``_update_build_button()``, ``_set_footer()`` and
    ``MappingPickerMixin._adopt_sheet_options()``.
    """

    def _detect_regions(self, gap_threshold: float) -> list:
        """Return detected shot regions, respecting the detection mode.

        Returns an empty list when a selected-keys mode is active and
        no keys are selected.  Callers are responsible for showing
        appropriate user feedback (message box, footer, etc.).

        The store's detection_mode is always respected regardless of
        whether a CSV is loaded — CSV defines steps, detection_mode
        controls how timing boundaries are discovered.
        """
        store = self._active_store()
        mode = store.detection_mode if store is not None else "auto"
        detection = self.manifest_host.detection()
        if mode != "auto":
            return detection.regions_from_selected_keys(
                gap_threshold=gap_threshold, key_filter=mode
            )
        return detection.detect_shot_regions(gap_threshold=gap_threshold)

    def detect(self, gap: Optional[float] = None) -> None:
        """Detect animation regions in the scene and populate the table.

        Replaces any loaded CSV data.  Ranges are pre-filled from
        detection results (user-editable).  Section and Behaviors
        columns are minimal since detection doesn't provide that
        metadata.

        Parameters:
            gap: Minimum gap (frames) between shots.  When ``None``,
                reads from the active ShotStore's detection_threshold,
                falling back to 5.0.
        """
        store = self._active_store()
        if gap is None:
            gap = store.detection_threshold if store is not None else 5.0

        use_sel = self._use_selected_keys
        regions = self._detect_regions(gap)
        if not regions:
            if use_sel:
                self.sb.message_box(
                    "<b>No keys selected.</b><br>"
                    "Select keyframes in the Graph Editor first.",
                )
            footer = (
                "No selected keys found (select keys in the Graph Editor)."
                if use_sel
                else "No animation found in scene."
            )
            self._load_data([], footer=footer)
            return

        steps, ranges = BuilderStep.from_detection(regions)
        n_obj = sum(len(s.objects) for s in steps)
        source = "selected keys" if use_sel else "scene"
        self._load_data(
            steps,
            ranges=dict(ranges),
            footer=f"Found {len(steps)} shots, {n_obj} objects from {source}.",
        )

    def _open_scene_source(self) -> None:
        """Point the source field at this scene's manifest, then populate.

        The scene remembers the CSV it was built from (``store.source_csv``,
        recorded at build), so a scene built from a sheet re-opens checked
        against that sheet and one built any other way opens on its own shots.
        Shared by ``_on_first_show`` and ``_on_scene_changed``.
        """
        store = self._active_store()
        self.ui.txt_csv_path.setText(store.source_csv if store is not None else "")
        self._populate_from_source()

    def _populate_from_source(self) -> None:
        """Load the manifest named in the source field, else the scene's shots.

        No mode switch: a path or link checks the scene against that file; an
        empty field (or one that fails to load) shows the scene's own shots,
        and a scene with none yet falls through to animation detection.
        """
        path = self.ui.txt_csv_path.text().strip()
        if path and self._load_csv(path):
            return
        self._load_scene_shots(manifest_failed=bool(path))

    def _load_scene_shots(
        self, manifest_failed: bool = False, detect_when_empty: bool = True
    ) -> None:
        """Show the store's shots as the steps; detect when there are none.

        The steps carry each shot's description, section, members and (for a
        manifest-built shot) its behaviors (``BuilderStep.from_shots``), so
        Assess checks the scene against itself: missing objects, broken
        behaviors, unlisted animated objects.  A build from this source only
        patches -- it never removes a shot (``_is_detection_mode``).

        Parameters:
            manifest_failed: The source field named a manifest that did not
                load; its reason stays on the field and the footer says so.
            detect_when_empty: Fall through to :meth:`detect` when the store
                has no shots.  ``False`` on a store event: another panel
                removed them and asked for no detection -- which may stop to
                ask for selected keys -- so the table empties and keeps
                following the store.
        """
        store = self._active_store()
        shots = store.sorted_shots() if store is not None else []
        if not shots:
            if manifest_failed:
                self._load_data([])  # never leave a previous scene's rows up
            elif detect_when_empty:
                self.detect()
            else:
                self._load_data(
                    [],
                    source="scene",
                    footer="No shots in the scene -- Assess or Build detects "
                    "its animation.",
                )
            return
        steps, ranges = BuilderStep.from_shots(shots)
        steps = self._drop_excluded(steps)
        n_obj = sum(len(s.objects) for s in steps)
        footer = f"{len(steps)} shots, {n_obj} objects from the scene."
        self._load_data(steps, ranges=ranges, source="scene", footer=footer)
        if manifest_failed:
            self._set_footer(
                f"Manifest not loaded (see the field) \u2014 showing {footer}",
                color=ERROR_COLOR,
            )

    def _drop_excluded(self, steps: List[BuilderStep]) -> List[BuilderStep]:
        """*steps* less the column map's ``exclude_steps`` (case-insensitive)."""
        if not self._column_map.exclude_steps:
            return steps
        excluded = {e.upper() for e in self._column_map.exclude_steps}
        return [s for s in steps if s.step_id.upper() not in excluded]

    def _setup_recent_csv(self) -> None:
        """Attach a RecentValuesOption and BrowseOption to the CSV path widget."""
        RecentValuesOption = self.sb.RecentValuesOption
        BrowseOption = self.sb.BrowseOption

        txt = self.ui.txt_csv_path
        self._recent_csv_option = RecentValuesOption(
            wrapped_widget=txt,
            settings_key="shot_manifest_csv_paths",
            max_recent=10,
        )
        txt.option_box.add_option(self._recent_csv_option)
        # Picking a recent path should load it (parity with Browse).  The
        # signal fires only on an explicit user selection, never on record,
        # so this can't loop with _load_csv's record() call.
        self._recent_csv_option.value_selected.connect(self._on_csv_recent_selected)

        self._browse_csv_option = BrowseOption(
            wrapped_widget=txt,
            file_types="CSV Files (*.csv);;All Files (*)",
            title="Open Sequence CSV",
            callback=lambda path: self._on_csv_browsed(path),
        )
        txt.option_box.add_option(self._browse_csv_option)

    def _setup_csv_path_editing(self) -> None:
        """Make the CSV path field typeable/pasteable with live validation.

        The field ships read-only (browse-only) in the .ui.  Here we allow
        direct entry, attach uitk's ``"file_or_url"`` validator (an existing
        file, or a URL probed off the UI thread; red + reason otherwise), and load
        the CSV on commit (Enter / focus-out) via :meth:`_on_csv_path_edited`.
        """
        txt = self.ui.txt_csv_path
        txt.setReadOnly(False)
        # The scene owns its source (ShotStore.source_csv); a path restored
        # from the last session would check this scene against another's sheet.
        # Past paths stay one click away in the recent-values list.
        txt.restore_state = False
        # uitk's "file_or_url" preset: an existing file passes synchronously; a
        # URL passes on shape, then uitk's deferred probe (off the UI thread)
        # settles reachability and hands its reason to the callable tooltip.
        txt.set_validator(
            "file_or_url",
            invalid_tooltip=lambda problem: self._csv_source_tooltip(
                problem or "CSV file not found."
            ),
            valid_tooltip=self._csv_source_tooltip(),
            empty_tooltip=self._csv_source_tooltip(),
            pending_tooltip=self._csv_source_tooltip("Checking the link\u2026"),
            empty_is_valid=True,
        )
        txt.editingFinished.connect(self._on_csv_path_edited)

    def _csv_source_tooltip(self, problem: Optional[str] = None) -> str:
        """The CSV field's tooltip; *problem* (when given) leads as the body."""
        tt = self.sb.tooltip
        return tt.fmt(
            title="CSV Source",
            body=problem
            or "A local CSV file, or a web address that serves one.  Leave it "
            "empty to review the scene's own shots.",
            sections=[
                (
                    "Local file",
                    ["Browse from the option box, or paste a path."],
                ),
                (
                    "Web address",
                    [
                        "Paste an <b>http(s)</b> link to a CSV and press "
                        f"{tt.kbd('Enter')}.",
                        "A <b>Google Sheets</b> share link works as-is: File > "
                        "Share > <b>Anyone with the link</b> (Viewer), then copy "
                        "the link.  The tab named in the link is the one used.",
                        "Reload re-fetches, so edits made in the sheet arrive on "
                        "the next load.",
                    ],
                ),
            ],
            notes=[
                "A link is checked in the background and turns red when it "
                "can't be fetched; the reason shows here and in the footer.",
                "Sheets that require sign-in are not supported.",
            ],
        )

    def _mark_csv_invalid(self, reason: str) -> None:
        """Red field, tooltip and footer all carrying the same *reason*."""
        self.ui.txt_csv_path.set_action_color("invalid")
        self.ui.txt_csv_path.setToolTip(self._csv_source_tooltip(reason))
        self._set_footer(reason, color=ERROR_COLOR)

    def _on_csv_path_edited(self) -> None:
        """Load the CSV when a typed/pasted path is committed (Enter / focus-out).

        Skips an unchanged path (a bare re-commit on focus-out); a cleared
        field returns to the scene's own shots.  Any other changed path is
        handed to _load_csv -- the
        single authority on validity -- which strips it, reports a missing
        file, surfaces an unreadable cloud placeholder, and keeps the field
        editable on failure.
        """
        path = self.ui.txt_csv_path.text().strip()
        if path == self._csv_path:
            return
        if not path:
            self._load_scene_shots()
            return
        self._load_csv(path)

    def _on_csv_recent_selected(self, _value=None) -> None:
        """Load the CSV when a path is chosen from the recent-values list."""
        path = self.ui.txt_csv_path.text().strip()
        if path:
            self._on_csv_browsed(path)

    def _fill_missing_assets(self) -> None:
        """Give the loaded sheet's asset-less steps the scene's objects.

        ``ShotManifest.fill_missing_assets``: what each step's paired shot
        holds (its members and what animates in its range) -- a step with no
        shot stays empty (nothing links it to scene time).  The added objects
        are marked in the table (``origin``), built like any other, and
        exported with the rest (Export).  The sheet's steps are filled, then
        the Local Edits applied over them: a step the edits emptied stays
        empty.
        """
        store = self._active_store()
        mapping = self._active_mapping or {}
        if not (
            mapping.get("fill_missing_assets")
            and self._sheet_steps
            and store is not None
        ):
            return
        filled = self._manifest(store).fill_missing_assets(self._sheet_steps)
        if filled:
            self._steps = self._editor.apply(self._sheet_steps)
        unfilled = [
            s.step_id
            for s in self._steps
            if not any(o.kind != "audio" for o in s.objects)
        ]
        if filled:
            self._populate_table()
            self._refresh_ranges()
        n_obj = sum(len(names) for names in filled.values())
        footer = f"{len(self._steps)} steps loaded; auto-filled {len(filled)} ({n_obj} objects)"
        if unfilled:
            footer += (
                f"; {len(unfilled)} have no shot to take objects from -- "
                "build or match shots first"
            )
        self._set_footer(footer + ".")

    def _load_data(
        self,
        steps: List[BuilderStep],
        *,
        ranges: Optional[Dict[str, Tuple[Optional[float], Optional[float]]]] = None,
        csv_path: str = "",
        source: str = "",
        footer: str = "",
    ) -> None:
        """Single source of truth for mode switching.

        Every code path that changes table contents (detect, CSV load, the
        scene's shots) funnels through here so that state and the table are
        always consistent.  *source* defaults to ``"csv"`` with a
        *csv_path*, else ``"detect"``.  *steps* are the source's own; the
        table shows them with this source's Local Edits applied.  A showing
        assessment stays showing: it is run again over the new steps
        (:meth:`_reassess_soon`) -- a template option or a sheet read again
        never leaves it to another click.
        """
        assessed = bool(self._last_results)
        self._csv_path = csv_path
        self._source = source or ("csv" if csv_path else "detect")
        self._sheet_steps = steps
        self._shown_record = None  # _follow_store reads the shots again
        self._editor.load()
        self._steps = self._editor.apply(steps)
        self._user_ranges = dict(ranges) if ranges else {}
        self._seeded_ranges = dict(self._user_ranges)  # the shots', not typed
        self._last_results = []
        self._last_resolved = []
        self._projected = {}
        self._typed_shift = {}
        self._range_issues = {}
        self._inserts = []
        self._build_undo = None  # another sheet: no Build of it to undo
        self._cached_gaps = None
        self._cached_gap_ends = None

        self._populate_table()
        self._update_build_button()

        stale = self._editor.stale() if self._editor.enabled else []
        if stale:
            footer = f"{footer} {len(stale)} local edit(s) match nothing here.".strip()
        hidden = len(self._steps) - len(self._shown_steps())
        if hidden:
            footer = f"{footer} {hidden} without a shot hidden.".strip()
        if footer:
            self._set_footer(footer)
        if assessed and self._steps:
            self._reassess_soon(note=footer)

    def _on_csv_browsed(self, path: str) -> None:
        """Handle a CSV path selected via browse or BrowseOption."""
        self.ui.txt_csv_path.setText(path)
        self._load_csv(path)

    def _load_csv(self, path: str) -> bool:
        """Parse the CSV (a path or URL) and load it via :meth:`_load_data`.

        Returns ``True`` once loaded; a failure marks the field invalid with
        its reason and returns ``False``.

        When an active mapping is selected, delegates to the
        :mod:`mapping` resolver.  Otherwise falls back to
        :func:`parse_csv` with the current :attr:`_column_map`.
        """
        import os

        # Settle the path field's live validator now (sync check only) so
        # neither its debounce nor an in-flight URL probe can re-color the
        # field after the load below sets the authoritative result (e.g.
        # flip an unreadable cloud file back to "valid" 300ms later).
        self.ui.txt_csv_path.validate_now(run_deferred=False)

        # A URL is a source too (RemoteFile fetches it inside parse_csv).  It
        # can't be probed without a round trip, so only a local path is gated.
        if not ptk.RemoteFile.is_url(path) and not os.path.isfile(path):
            self._mark_csv_invalid(f"File not found: {path}")
            return False

        # Read it the way the scene reads it: the template and options the
        # scene keeps for this sheet, not the user's (MappingPickerMixin).  A
        # sheet that does not load leaves the sheet shown read as it was: a
        # Build or an option change records on THAT sheet.
        shown = self._sheet_read_state()
        self._adopt_sheet_options(path)

        def refuse(reason: str) -> bool:
            self._restore_sheet_read_state(shown)
            self._mark_csv_invalid(reason)
            return False

        try:
            if self._active_mapping is not None:
                from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

                steps = Mapping.resolve(path, mapping=self._active_mapping)
            else:
                steps = ManifestModel.parse_csv(path, columns=self._column_map)
        except ptk.RemoteFile.Error as exc:
            # A URL that didn't yield a CSV: no network, an HTTP error, or a
            # sign-in page where a file was expected.  RemoteFile's message
            # already names the remedy (share the sheet, check the link); the
            # disk/sync diagnosis below would be wrong for a URL, and Error
            # subclasses OSError, so this branch must come first.
            self.logger.error("Failed to fetch CSV %r: %s", path, exc)
            return refuse(str(exc))
        except OSError as exc:
            # isfile() passed but the bytes can't be read.  Don't assume a
            # single cause -- _describe_read_failure enumerates the likely
            # culprits (full disk / stopped sync client / locked / disconnected),
            # always surfaces the raw error, and appends the free space if low.
            self.logger.error("Failed to read CSV %r: %s", path, exc)
            return refuse(self._describe_read_failure(path, exc))
        except Exception as exc:
            self.logger.error("Failed to parse CSV: %s", exc)
            return refuse(f"Error: {exc}")

        if not steps:
            # A sheet the template reads nothing of is not a manifest to
            # check the scene against; an empty table would read as one.
            # (Steps the user excluded below are theirs, not a misread.)
            return refuse(
                "No steps read: no step-ID cell matches the mapping template. "
                "Set its Step IDs (the field's columns button) to the way the sheet writes "
                "them, or Auto."
            )
        # Honor context-menu exclusions on BOTH branches.  parse_csv already
        # applies them on the no-mapping branch (idempotent here); resolve()
        # builds a fresh ColumnMap from the mapping JSON and never sees
        # self._column_map, so without this a reload while a mapping is active
        # resurrects every context-menu-excluded step.
        steps = self._drop_excluded(steps)

        self.ui.txt_csv_path.reset_action_color()
        self._recent_csv_option.record(path)
        n_obj = sum(len(s.objects) for s in steps)

        self._load_data(
            steps,
            csv_path=path,
            footer=f"{len(steps)} steps, {n_obj} objects loaded.",
        )

        # Seed _user_ranges with the paired shots' store positions so the
        # table shows built steps' Start/End at once -- the steps as shown, a
        # step Local Edits added included -- and populate _last_resolved so
        # edit validation has correct bounds for steps between built ones.
        try:
            store_ranges = {
                sid: (shot.start, shot.end)
                for sid, shot in self._pairing().shots.items()
            }
        except Exception:
            store_ranges = {}
        if store_ranges:
            self._user_ranges.update(store_ranges)
            self._seeded_ranges.update(store_ranges)
            self._refresh_ranges()
        self._fill_missing_assets()
        return True

    @staticmethod
    def _describe_read_failure(path: str, exc: OSError) -> str:
        """Explain an unreadable CSV by its likely causes, never one asserted
        (``ManifestModel.describe_read_failure``)."""
        return ptk.ManifestModel.describe_read_failure(path, exc)
