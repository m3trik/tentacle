# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest's header menu: Long Names, Local Edits' Edits mode and
Reset, a Key / Marker / Off choice per behavior (Off by default), the actions
(Colors, the sibling panels) and the panel's help.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import List

import pythontk as ptk
from pythontk import SHOT_PALETTE

from .manifest_data import PASTEL_STATUS, ManifestData


class HeaderMenuMixin:
    """The header menu, mixed into ``ShotManifestController``.

    Uses the controller's ``ui`` (``header``), ``sb``, ``_settings``,
    ``_editor``, ``_steps``, ``_last_results``, ``assess()``, ``_redraw()``,
    ``_shown_steps()``, ``_update_build_button()``, ``_set_footer()`` and the
    mapping picker's ``_loaded_sheet()``.
    """

    _COLOR_SETTINGS_NS = "ShotManifest/colors"
    #: What Build does with a behavior type (the header menu's choice per
    #: type): key it, mark it on the timeline instead, or leave it alone.
    BEHAVIOR_MODES = (("Key", "key"), ("Marker", "marker"), ("Off", "off"))
    #: What each mode does, as its choice's tooltip says it (``{label}``: the behavior).
    BEHAVIOR_MODE_TIPS = {
        "key": "Build keys {label} on every row it is listed on.",
        "marker": "Build marks where {label} would go on the timeline, keying nothing.",
        "off": "Build leaves {label} out on every row.",
    }
    #: The full guide; the header's help is its short form.
    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/shot_manifest.md"

    def _setup_header_menu(self) -> None:
        """Configure the header option menu.

        Generation settings (threshold, mode) now live in the shared
        ``shots.ui`` panel, opened via the Settings button.
        """
        menu = self.ui.header.menu
        menu.setTitle("Shot Manifest:")

        chk_long = menu.add(
            "QCheckBox",
            setText="Long Names",
            setChecked=bool(self._settings.value("long_names", False)),
            setToolTip="Show full DAG paths instead of leaf node names.",
        )
        chk_long.toggled.connect(self._on_long_names_toggled)
        self._editor.add_header_options(menu)
        self._add_build_options(menu)

        menu.add("Separator", setTitle="Actions")
        menu.add(
            "QPushButton",
            setText="Colors\u2026",
            setObjectName="btn_manifest_colors",
            setToolTip="Edit manifest status colors.",
        ).released.connect(self._open_color_editor)
        menu.add(
            "QPushButton",
            setText="Audio Clips\u2026",
            setObjectName="btn_audio_clips",
            setToolTip="Open the Audio Clips editor to load, key, and\nmanage audio tracks used by this manifest.",
        ).released.connect(self._open_audio_clips)
        menu.add(
            "QPushButton",
            setText="Render Effects\u2026",
            setObjectName="btn_render_effects",
            setToolTip="Open Render Effects to key or revise the opacity and highlight\nchannels this manifest's fade and highlight behaviors key.",
        ).released.connect(self._open_render_effects)
        menu.add(
            "QPushButton",
            setText="Shots\u2026",
            setObjectName="btn_settings",
            setToolTip="Open shared shot generation, gap, and editing settings.",
        )

        self.ui.header.set_help_text(
            self.sb.tooltip.fmt(
                title="Shot Manifest",
                body="Check the scene's shots against a build sheet, or review the shots the scene already has.",
                sections=[
                    (
                        "Quick Start \u2014 Build Sheet",
                        [
                            "Browse to a CSV file, or paste a web address (a Google "
                            "Sheets share link works) and press Enter.",
                            "Review parsed steps in the table; edit ranges as needed.",
                            "Click <b>Build</b> to create shots with behaviors applied.",
                            "Click <b>Assess</b> to verify completeness.",
                            "The mapping template and its options (the field's "
                            "columns button) adapt it to the sheet: step-ID style (Auto reads "
                            "<code>A01.)</code> and <code>A01</code> / "
                            "<code>IN_01</code> sheets alike), audio, and "
                            "<b>Auto-fill Missing Assets</b> -- then <b>Export</b> "
                            "hands them, with the rest, to the sheet's owner.",
                        ],
                    ),
                    (
                        "No Build Sheet",
                        [
                            "Leave the field empty (or clear it) \u2014 the table shows the "
                            "scene's own shots with their descriptions; <b>Assess</b> checks "
                            "them for missing objects and behaviors.",
                            "A scene with no shots yet is generated from animation using "
                            "the settings in Shot Settings; refine ranges, then <b>Build</b>.",
                            "A scene built from a sheet re-opens checked against that sheet.",
                        ],
                    ),
                    (
                        "Table Columns",
                        [
                            "<b>Step</b> \u2014 Step ID (e.g. A01), or the name Local Edits gave it.",
                            "<b>Section</b> \u2014 Read-only grouping label from the sheet.",
                            "<b>Description</b> \u2014 Audio narration or step notes.",
                            "<b>Behaviors</b> \u2014 A chip per behavior of an object, in its "
                            "state's colour and glyph; click one for its menu, <b>+</b> to give "
                            "the object another.",
                            "<b>Start / End</b> \u2014 Frame range. Solid text = user-entered; dim italic = auto-filled "
                            "-- once shots exist, an unbuilt step's are where Build inserts it.",
                        ],
                    ),
                    (
                        "Editing &amp; Actions",
                        [
                            "Double-click Start or End to type a frame. Downstream steps re-flow.",
                            "Right-click a range cell: Set Start to Current Frame, Auto-fill from Gaps, Clear Range.",
                            "<b>Assess</b> \u2014 Read-only comparison. A step row's icon is its state "
                            "(a check: in order; a note: Build has work for it; a warning; an error; a "
                            "pencil: edited by hand; a padlock: locked), the Status column says its worst "
                            "issue in a few words, and its tooltip lists them all. "
                            "While it shows it stays current: a shot edit "
                            "made anywhere, a Local Edit, a hide or a sheet read again runs it again.",
                            "<b>Build</b> \u2014 Create or update shots from loaded steps: the button counts the steps it "
                            "changes, and its tooltip says the plan (to create, to update, kept, locked, waiting on you). "
                            "Locked shots are never modified, "
                            "and neither is a shot edited by hand since its last Build (renamed, resized, its members "
                            "or description changed) unless <b>Edits</b> is set to <b>Rebuild Hand-Edited "
                            "Shots</b> (header menu); Assess shows such a step as edited. Once shots exist, a step "
                            "without one is inserted in sheet order, after its previous step's shot: the shots "
                            "after it move later with their keys -- locked ones too: a lock keeps a shot's "
                            "content, not its place -- after you confirm how many. "
                            "Fades and highlights are keyed from the scene's effect recipe (Render Effects); "
                            "Build re-keys those an older recipe made and removes the keys of behaviors the "
                            "doc dropped, so it stays enabled while either is pending. A behavior type set "
                            "to <b>Marker</b> is marked on the Shot Sequencer's timeline instead.",
                            "<b>Export</b> \u2014 a live preview of the export: "
                            "the rows the table shows, or the selected ones, as CSV, "
                            "JSON or Markdown -- what the table says, Local Edits, "
                            "frames and status included. Set the format, rows, object "
                            "layout and columns beside the text and it updates as you "
                            "go; then <b>Copy</b> it or <b>Save As</b> a file. It never "
                            "writes the loaded sheet.",
                            "Right-click a step row: Open in Shot Sequencer or Shots (once built). "
                            "An object row adds Show in "
                            "Outliner, Copy, Apply its behaviors, and Fade / Highlight '...' -- Render "
                            "Effects on that object alone, where Key re-applies its behaviors; an audio "
                            "row opens its clip in Audio Clips.",
                        ],
                    ),
                    (
                        "Above the Table",
                        [
                            "<b>Select</b> \u2014 rows (with issues, unbuilt, all, none), "
                            "or the rows' objects in the scene.",
                            "<b>Expand</b> / <b>Collapse</b> \u2014 every row, the rows "
                            "with (or without) issues, those with objects not in the "
                            "manifest, or the selected rows.",
                            "<b>Hide</b> / <b>Show</b> \u2014 the selected steps or their "
                            "sections (Local Edits; a built step stays), and the steps "
                            "without a shot (a view: Assess and Build skip them).",
                            "<b>Search</b> — only the steps whose words match every "
                            "word typed show; a view alone.",
                        ],
                    ),
                    (
                        "When the Scene Moves On",
                        [
                            "Every shot lists its members: a step's shot shows those the "
                            "step does not list (marked), with no Assess needed.",
                            "A shot no step pairs with -- split off or added in the Shot "
                            "Sequencer -- is a 'not in doc' row where the timeline has it. "
                            "Right-click it: open it, reveal its members, <b>Add to the "
                            "Manifest</b> (a step of its own, a Local Edit), <b>Pair with "
                            "Step</b> (the shot of a step that has none), or Remove Shot "
                            "-- its keys stay in the scene.",
                            "<b>Lock</b> a step, a selection or a whole section "
                            "(right-click): final -- Build never changes its shot and its "
                            "row takes no Local Edits. Unlock to revise, then lock again.",
                            "<b>Hide \u25b8 Steps Without a Shot</b> leaves out the steps "
                            "with no shot once any step has one; Assess and Build skip them, "
                            "so Build only keeps the shots there are up to date.",
                        ],
                    ),
                    (
                        "Behaviors (header menu)",
                        [
                            "A Key / Marker / Off choice per "
                            "behavior type. <b>Key</b>: Build keys it. <b>Marker</b>: Build "
                            "keys nothing -- it puts a marker on the Shot Sequencer's timeline "
                            "where the keys would go, naming the objects, for keying by hand; "
                            "Assess checks the marker is there, and its chips show "
                            f"{ManifestData.MARKED_GLYPH}. <b>Off</b>: neither keyed nor "
                            "marked, and not reported by Assess; its chips show it struck "
                            "through. Marker and Off leave the keys a type already has. "
                            "A behavior the sheet asks for by its word (a row in cells: "
                            "<i>highlight</i>, <i>fade_out</i>) starts at Key, any other is Off "
                            "until you choose; the choices are kept with the scene, for its "
                            "sheet (your own seed a scene that keeps none).",
                        ],
                    ),
                    (
                        "Local Edits",
                        [
                            "Revise the manifest without touching the sheet: edits are "
                            "kept with the scene, always applied, and Build follows them. "
                            "A locked step takes none until it is unlocked.",
                            "<b>Edits</b> (header menu, kept per user): <b>Keep All "
                            "Edits</b> \u2014 Build keeps a shot edited by hand since its "
                            "last Build as it is, its behaviors not re-keyed; <b>Rebuild "
                            "Hand-Edited Shots</b> \u2014 Build rebuilds it from the "
                            "manifest like any other; <b>Compare to Original Sheet</b> "
                            "\u2014 the sheet as delivered, to compare: read-only, Build "
                            "off. Pick another mode to return; nothing is lost.",
                            "A step row leads its right-click menu with its own fix, in "
                            "bold: <b>Build</b> where a Build would change its built shot, "
                            "<b>Rebuild from Sheet</b> where a hand edited it. That shot "
                            "takes the sheet's name, description, objects and behaviors and "
                            "keeps its range; no other row is built.",
                            "A step that plays no animation has <i>no shot</i> in its Start "
                            "cell (the template's Shots option: steps with an animation clip): "
                            "Build makes none. Right-click a step: <b>Mark as No Shot</b> / "
                            "<b>Mark as a Shot</b>, a Local Edit.",
                            "Double-click a step's name or description, or an object's "
                            "name, to edit it.  An object's name says which scene object "
                            "the step means -- the object itself is never renamed.",
                            "Right-click: Add Step, Hide (a flyout: the step, the "
                            "selected steps, its section, or every step without a shot) "
                            "/ Show Hidden (a built step stays: Build never removes a "
                            "shot), Move an object to another step, Rename All of one "
                            "object, Revert.  A behavior turned off or given on its row "
                            "(its chip, its +) is an edit too.",
                            "Renaming a built step renames its shot on the next Build -- "
                            "and the clip it exports as.  Edited cells are italic; their "
                            "tooltip shows the sheet's value.  <b>Reset</b> (beside "
                            "Edits) drops them all.",
                        ],
                    ),
                ],
            ),
            url=self.HELP_URL,
        )

    @property
    def _rebuild_edited(self) -> bool:
        """Header menu > Edits is Rebuild Hand-Edited Shots (off by default,
        kept per user): whether a build rebuilds a shot edited by hand since
        its last build (``ShotManifest.edited_by_hand``) instead of keeping it."""
        return bool(self._settings.value("rebuild_edited", False))

    def _set_rebuild_edited(self, on: bool, judge: bool = True) -> None:
        """Persist the Edits mode's Keep / Rebuild choice; what Build would
        do changed (*judge*: say so now -- off for a caller that redraws and
        re-assesses next anyway)."""
        self._settings.setValue("rebuild_edited", bool(on))
        if judge:
            self._build_options_changed()

    #: The settings key of the behavior types that were Off when every other
    #: type was keyed (before 2026-10-12: behaviors default to Off now).  Read
    #: once, never written; kept, not removed: Maya and Blender share these
    #: settings, and an older release reading no list would key every type.
    RETIRED_BEHAVIOR_SETTING = "disabled_behaviors"

    def _migrate_behavior_modes(self) -> None:
        """Keep what each behavior type did when Off became the default
        (2026-10-12: "behaviors should default to off"): a user whose
        settings name the types turned Off (:attr:`RETIRED_BEHAVIOR_SETTING`)
        had every other unmarked type keyed -- those are now kept as Key
        (``keyed_behaviors``).  A user with no such settings starts with
        every type Off.

        Once only: the old list stays for an older release sharing the
        settings, so the carry-over runs while ``keyed_behaviors`` is
        absent -- which it never is again once written (an empty list is a
        choice: every type Off).
        """
        settings = self._settings
        if settings.value("keyed_behaviors", None) is not None:
            return  # carried over, or chosen since
        legacy = settings.value(self.RETIRED_BEHAVIOR_SETTING, None)
        marked = settings.value("marked_behaviors", None)
        if legacy is None and marked is None:
            return  # nothing chosen yet: every type is Off
        off = set(legacy if isinstance(legacy, list) else ())
        off |= set(marked if isinstance(marked, list) else ())
        keyed = [n for n in self.behaviors.list_behaviors() if n not in off]
        settings.setValue("keyed_behaviors", keyed)
        self._behavior_sets.clear()

    def _behavior_cache(self) -> dict:
        """What the behavior lists and modes read once (:meth:`_behavior_set`,
        :meth:`_behavior_mode`, :meth:`_family_members`) are kept in: emptied
        for another scene or sheet and a sheet read again, and kept in step by
        a choice (:meth:`_set_behavior_mode`) -- every chip asks, on every
        table rebuild."""
        store = self._active_store()
        who = (id(store) if store is not None else None, self._loaded_sheet())
        if self._behavior_sets.get("@") != who:
            self._behavior_sets.clear()
            self._behavior_sets["@"] = who
        return self._behavior_sets

    def _behavior_set(self, key: str) -> frozenset:
        """A behavior-type list in force (``keyed_behaviors``,
        ``marked_behaviors``): :meth:`_modes_in_force`'s, read once per scene
        and sheet."""
        cache = self._behavior_cache()
        if key not in cache:
            cache["keyed_behaviors"], cache["marked_behaviors"] = self._modes_in_force()
        return cache[key]

    def _modes_in_force(self):
        """``(keyed, marked)``: the behavior modes in force for the loaded
        sheet (``ManifestEdits.modes_in_force``, the rule every builder reads):
        the scene's own (maintainer 2026-11-23: "with the scene"), else those a
        scene that keeps none starts with -- Key for what the sheet's cells
        name, the user's own seeding them."""
        modes = ptk.ManifestEdits.modes_in_force(
            self._active_store(),
            self._loaded_sheet() or "",
            getattr(self, "_sheet_steps", None) or (),
            self._behavior_types(),
            self._own_behavior_set("keyed_behaviors"),
            self._own_behavior_set("marked_behaviors"),
        )
        return frozenset(modes["key"]), frozenset(modes["marker"])

    def _own_behavior_set(self, key: str) -> frozenset:
        """The user's own list *key* (kept per user): their choices alone, the
        seed of a scene that keeps no modes."""
        raw = self._settings.value(key, [])
        return frozenset(raw if isinstance(raw, list) else ())

    def _behavior_types(self) -> frozenset:
        """Every behavior type (``Behaviors.list_behaviors``, which lists the
        template folders), read once with the lists above."""
        cache = self._behavior_cache()
        types = cache.get("")
        if types is None:
            types = cache[""] = frozenset(self.behaviors.list_behaviors())
        return types

    def _keyed_behaviors(self) -> frozenset:
        """The behavior types set to Key in the header menu."""
        return self._behavior_set("keyed_behaviors")

    def _marked_behaviors(self) -> frozenset:
        """The behavior types set to Marker in the header menu: Build marks
        them on the timeline instead of keying them."""
        return self._behavior_set("marked_behaviors") - self._keyed_behaviors()

    def _disabled_behaviors(self) -> frozenset:
        """The behavior types set to Off in the header menu -- every type
        neither keyed nor marked: Off is the default."""
        return (
            self._behavior_types() - self._keyed_behaviors() - self._marked_behaviors()
        )

    def _behavior_mode(self, name: str) -> str:
        """``"key"``, ``"marker"`` or ``"off"``: what Build does with *name*
        -- a behavior or a family of them (``Behaviors.family_of``: ``fade``),
        whose members share one mode (:meth:`_set_behavior_mode`): its first's.
        Read once per name (:meth:`_behavior_cache`)."""
        modes = self._behavior_cache().setdefault("mode", {})
        mode = modes.get(name)
        if mode is None:
            first = self._family_members(name)[0]
            if first in self._keyed_behaviors():
                mode = "key"
            else:
                mode = "marker" if first in self._marked_behaviors() else "off"
            modes[name] = mode
        return mode

    def _family_members(self, name: str) -> List[str]:
        """The behavior types of *name*'s family (``fade_in`` or ``fade``:
        ``["fade_in", "fade_out"]``), else ``[name]``: one Key / Marker / Off
        choice sets them all. Every type's family is read once
        (:meth:`_behavior_cache`)."""
        cache = self._behavior_cache()
        families = cache.get("family")
        if families is None:
            families = {}
            for family, members in self.behaviors.families(sorted(self._behavior_types())).items():
                for key in [family] + members:
                    families[key] = members
            cache["family"] = families
        members = families.get(name)
        if members is None:
            members = families[name] = families.get(self.behaviors.family_of(name)) or [name]
        return members

    def _add_build_options(self, menu) -> None:
        """The header menu's Behaviors: a Key / Marker / Off choice per
        behavior template: Key for one the loaded sheet asks for by its word
        (:meth:`_modes_in_force`), else Off until the user chooses.

        Kept with the scene, per sheet (maintainer 2026-11-23: "with the
        scene"): whoever opens it builds the same, and its delivery says the
        same; the user's own choices seed a scene that keeps none, and stay
        their default for the next (2026-10-07: "ability to disable/enable
        certain behaviors"; 2026-10-11: "a third option ... of adding a marker
        in the sequencer instead of keying"; 2026-10-12: "behaviors should
        default to off").
        """
        self._migrate_behavior_modes()
        menu.add("Separator", setTitle="Behaviors")
        self._behavior_modes = {}
        # A family (fade_in and fade_out: fade) is one behavior, one choice.
        for name in self.behaviors.families(self.behaviors.list_behaviors()):
            label = ManifestData.fmt_behavior(name)
            cmb = menu.add(
                "QComboBox",
                setCurrentTextPrefix=f"{label}:  ",
                setToolTip=(
                    f"Key: Build keys {label} wherever the doc asks for it.\n"
                    "Marker: Build keys nothing -- it puts a marker on the Shot\n"
                    "Sequencer's timeline where the keys would go, naming the\n"
                    "objects, and Assess checks the marker is there.\n"
                    "Off: Build neither keys nor marks it, and Assess does not\n"
                    "report it.\n"
                    "Marker and Off leave the keys it already has."
                ),
            )
            for text, mode in self.BEHAVIOR_MODES:
                cmb.addItem(text, mode)
            cmb.currentIndexChanged.connect(
                lambda _i, n=name, c=cmb: self._set_behavior_mode(n, c.currentData())
            )
            self._behavior_modes[name] = cmb
        self._sync_behavior_modes()

    def _sync_behavior_modes(self) -> None:
        """Show each behavior's mode in force in its header-menu combo
        (:meth:`_behavior_mode`): the scene's for the loaded sheet, which a
        sheet loaded or a scene swapped changes. A display: no mode is set."""
        for name, cmb in self._behavior_modes.items():
            index = cmb.findData(self._behavior_mode(name))
            if cmb.currentIndex() != index:
                blocked = cmb.blockSignals(True)
                try:
                    cmb.setCurrentIndex(index)
                finally:
                    cmb.blockSignals(blocked)

    def _set_behavior_mode(self, name: str, mode: str) -> None:
        """Set what Build does with the behavior type *name* and the rest of
        its family (:meth:`_family_members`): ``"key"``, ``"marker"`` or
        ``"off"`` (Assess follows). The scene keeps the modes in force
        (:meth:`_record_behavior_modes`); the user's own lists take this
        choice alone, their default for the next scene -- never what a sheet
        asked for by its word."""
        family = self._family_members(name)
        cache = self._behavior_cache()
        for key, member in (
            ("keyed_behaviors", mode == "key"),
            ("marked_behaviors", mode == "marker"),
        ):
            own, now = set(self._own_behavior_set(key)), set(self._behavior_set(key))
            for names in (own, now):
                if member:
                    names.update(family)
                else:
                    names.difference_update(family)
            self._settings.setValue(key, sorted(own))
            cache[key] = frozenset(now)
        cache.pop("mode", None)
        self._record_behavior_modes()
        self._build_options_changed()

    def _record_behavior_modes(self, store=None) -> bool:
        """Keep the behavior modes in force with the scene, for the loaded
        sheet (``ManifestEdits.set_behavior_modes``): what a change of a type's
        mode and a Build record. ``False`` with no sheet or scene, or nothing
        changed."""
        path = self._loaded_sheet()
        store = store if store is not None else self._active_store()
        if not path or store is None:
            return False
        return ptk.ManifestEdits.set_behavior_modes(
            store, path, self._keyed_behaviors(), self._marked_behaviors()
        )

    def _build_options_changed(self) -> None:
        """A showing assessment is judged again under the new options (Build
        enabled with it); otherwise the table redraws its behavior labels."""
        if self._last_results:
            self.assess(skip_key_check=True)
            return
        if self._steps:
            self._redraw()
        else:
            self._update_build_button()

    def _on_long_names_toggled(self, checked: bool) -> None:
        """Persist and apply the long-names display preference."""
        self._settings.setValue("long_names", checked)
        self._redraw()

    def _set_hide_missing(self, on: bool) -> None:
        """Hide (or show) the steps without a shot -- the view row's Hide /
        Show, a step row's Hide flyout -- kept per user; a showing assessment
        is judged again over the steps now shown (Build follows them)."""
        if bool(on) == self._hide_missing:
            return
        self._settings.setValue("hide_missing", bool(on))
        if not self._steps:
            return
        if self._last_results:
            self.assess(skip_key_check=True)  # its footer counts the hidden
        else:
            self._redraw()
            self._set_footer(self._shown_note())

    def _set_issues_only(self, on: bool) -> None:
        """Show only the rows that need something (or every row again) -- the
        view row's Hide / Show -- kept per user. A view alone: nothing is
        assessed again, and Build builds what it built."""
        if bool(on) == self._issues_only:
            return
        self._settings.setValue("issues_only", bool(on))
        hidden = self._apply_issues_filter()
        if on:
            self._set_footer(
                f"{hidden} step(s) with nothing to do hidden (Show \u25b8 Steps "
                "With Nothing to Do): a view, Build still takes every step."
                if self._last_results
                else "Steps with nothing to do hide once Assess has run."
            )

    def _shown_note(self) -> str:
        """What the table leaves out: ``"37 steps without a shot hidden."``,
        or the steps and shots it shows."""
        shown = len(self._shown_steps())
        hidden = len(self._steps) - shown
        if hidden:
            return (
                f"{hidden} step(s) without a shot hidden (Show \u25b8 Steps "
                "Without a Shot): Build does not create them."
            )
        return f"{shown} steps shown."

    def _open_audio_clips(self) -> None:
        """Open the Audio Clips editor."""
        self.sb.handlers.marking_menu.show("audio_clips")

    def _open_render_effects(self) -> None:
        """Open the Render Effects panel."""
        self.sb.handlers.marking_menu.show("render_effects")

    def _open_color_editor(self) -> None:
        """Launch the status-color editor dialog."""
        ColorMappingDialog = self.sb.ColorMappingDialog
        SettingsManager = self.sb.SettingsManager

        # Keys with actual (fg, bg) colours — skip 'valid'/'csv_object' (None, None)
        editable_keys = [
            k for k, v in SHOT_PALETTE.items() if v[0] is not None or v[1] is not None
        ]

        # Build defaults dict: {key: (fg_hex, bg_hex)} -- the shipped palette,
        # whatever this panel's has been recoloured to.
        defaults = {}
        for k in editable_keys:
            fg, bg = SHOT_PALETTE[k]
            defaults[k] = (str(fg) if fg else "#808080", str(bg) if bg else "#2A2A2A")

        sections = [("Status Colors", editable_keys)]

        color_settings = SettingsManager(namespace=self._COLOR_SETTINGS_NS)
        dlg = ColorMappingDialog(
            defaults=defaults,
            sections=sections,
            settings=color_settings,
            title="Manifest Colors",
            preset_dir=self.manifest_host.COLOR_PRESET_DIR,
            parent=self.ui,
        )

        def _apply(cmap):
            # Write changed colours back into the live PASTEL_STATUS palette
            for key, val in cmap.items():
                if key in PASTEL_STATUS:
                    PASTEL_STATUS[key] = val
            self._redraw()  # in the new colours

        dlg.colors_changed.connect(_apply)
        dlg.exec_()

    #: Status colours that had their own key split off another's (2026-11-22:
    #: the step's dropped-behavior keys and its shot updates borrowed the
    #: ``missing_behavior`` and ``missing_shot`` colours): ``{new: old}``.
    COLOR_KEYS_SPLIT = {
        "dropped_behavior": "missing_behavior",
        "shot_update": "missing_shot",
    }
    #: The panel setting naming the split keys already carried over.
    _COLOR_SPLIT_SETTING = "color_keys_split"

    def _carry_split_colors(self, settings) -> None:
        """Once per key: a user's colour for the old key a split key was
        drawn in (:attr:`COLOR_KEYS_SPLIT`) becomes the new key's, saved, so
        what they recoloured stays so -- and the Colors... editor shows it --
        until they change either one."""
        done = self._settings.value(self._COLOR_SPLIT_SETTING, [])
        done = list(done) if isinstance(done, list) else []
        todo = [new for new in self.COLOR_KEYS_SPLIT if new not in done]
        for new in todo:
            if settings.value(f"{new}/fg") or settings.value(f"{new}/bg"):
                continue  # chosen already
            for role in ("fg", "bg"):
                value = settings.value(f"{self.COLOR_KEYS_SPLIT[new]}/{role}")
                if value:
                    settings.setValue(f"{new}/{role}", value)
        if todo:
            self._settings.setValue(self._COLOR_SPLIT_SETTING, done + todo)

    def _restore_color_overrides(self) -> None:
        """Apply any persisted color overrides to the live palette."""
        SettingsManager = self.sb.SettingsManager

        settings = SettingsManager(namespace=self._COLOR_SETTINGS_NS)
        self._carry_split_colors(settings)
        for key in list(PASTEL_STATUS):
            fg_val = settings.value(f"{key}/fg")
            bg_val = settings.value(f"{key}/bg")
            if fg_val or bg_val:
                orig_fg, orig_bg = PASTEL_STATUS[key]
                PASTEL_STATUS[key] = (
                    fg_val or (str(orig_fg) if orig_fg else None),
                    bg_val or (str(orig_bg) if orig_bg else None),
                )
