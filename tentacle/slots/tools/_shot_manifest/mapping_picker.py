# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest's mapping template: its own popup on the build sheet
field (a columns button) holding the picker (built-in and user templates,
Refresh and Open Folder on its option box) and the template's options as rows
under it, and applying them to the loaded sheet.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import Dict, Optional

import pythontk as ptk

from .manifest_data import ERROR_COLOR


class MappingPickerMixin:
    """The mapping template, mixed into ``ShotManifestController``.

    Uses the controller's ``ui.txt_csv_path`` (``ui.header.menu`` standing
    in for its popup on a mocked UI),
    ``_settings``, ``_csv_path``, ``_mapping_*`` / ``_active_mapping`` /
    ``_option_rows`` state, ``logger``, ``_load_csv()`` and ``_set_footer()``.
    """

    def _setup_mapping_combo(self) -> None:
        """Put the mapping selector in its popup (:meth:`_mapping_popup`).

        A :class:`~uitk.widgets.comboBox.ComboBox` whose ``option_box``
        carries two icon buttons to its right — *Refresh* (rescan the folder)
        and *Open folder* -- with the template's options as rows below it
        (:meth:`_build_option_rows`).  Mapping files aren't edited in-place
        from the UI; the workflow is to open the folder, manage the files
        externally, then refresh.
        """
        ComboBox = self.sb.ComboBox

        menu = self._mapping_menu = self._mapping_popup()
        cmb = menu.add(
            ComboBox,
            setObjectName="cmb_csv_mapping",
            setToolTip=(
                "Select a CSV mapping. Built-in mappings ship with the tool;\n"
                "your own live in the mappings folder — open it to add or edit\n"
                "files, then click Refresh."
            ),
        )
        self._cmb_mapping = cmb
        self._refresh_mapping_list()
        cmb.currentIndexChanged.connect(self._on_mapping_changed)
        # Pin the combo (and thus its square icon buttons) to the menu's row
        # height so the template row lines up with the option rows.
        self._wire_mapping_option_box(
            cmb, target_h=getattr(menu, "fixed_item_height", None)
        )

    def _mapping_popup(self):
        """The CSV mapping's popup: a menu on the build sheet field's option
        box, opened by its columns button -- how the sheet's columns are read
        is the field's business, not the panel's.  A mocked field (logic
        tests) has no option box: the header menu stands in."""
        from qtpy import QtWidgets
        OptionMenuOption = self.sb.OptionMenuOption

        txt = self.ui.txt_csv_path
        if not isinstance(txt, QtWidgets.QWidget):
            return self.ui.header.menu
        option = OptionMenuOption(
            wrapped_widget=txt,
            icon="columns",
            tooltip=(
                "CSV Mapping: the template that says how the sheet's columns are\n"
                "read, and its options."
            ),
            add_apply_button=False,
            match_parent_width=False,  # its content's width, not the field's
        )
        txt.option_box.add_option(option)
        menu = option.menu
        menu.setTitle("CSV Mapping:")
        return menu

    def _wire_mapping_option_box(self, cmb, target_h=None) -> None:
        """Attach the option-box toolbar to *cmb*: *Refresh* then *Open folder*.

        Factored out so the construction is unit-testable on a real ComboBox.
        A no-op when *cmb* isn't a real widget — the controller's logic tests
        run against a mocked UI where the toolbar is irrelevant.

        *target_h* pins the combo to the header row height; the option-box sizes
        its square icon buttons to the combo's height, so both end up matching
        the sibling buttons.  Falls back to the combo's natural height hint.
        """
        from qtpy import QtWidgets

        if not isinstance(cmb, QtWidgets.QWidget):
            return

        cmb.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
        h = (
            target_h
            if isinstance(target_h, int) and target_h > 0
            else cmb.sizeHint().height()
        )
        cmb.setFixedHeight(h)
        # Give the combo its row height *now*, before the synchronous option-box
        # wrap below: the option-box sizes its icon buttons from the wrapped
        # widget's current height, which is otherwise 0 until the still-hidden
        # header menu is first laid out.
        cmb.resize(cmb.width() or cmb.sizeHint().width(), h)

        cmb.option_box.add_action(
            callback=self._refresh_mapping_list,
            icon="refresh",
            tooltip="Rescan the mappings folder for files you've added, removed, or edited.",
        )
        cmb.option_box.add_action(
            callback=self._open_mappings_folder,
            icon="folder",
            tooltip="Open the mappings folder to add or edit files (manage them here, then Refresh).",
        )

    def _refresh_mapping_list(self, select: Optional[str] = None) -> None:
        """Rebuild the mapping combo, tagging each item by source.

        The item *text* carries a built-in/user tag for the user; the real
        mapping name is stored as item *data* so selection stays robust.
        Selection priority: *select* arg > last-used > ``default`` > ``(none)``.
        """
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        cmb = self._cmb_mapping
        cmb.blockSignals(True)
        cmb.clear()
        cmb.addItem("(none)", None)
        if self._mapping_dir:
            names = list(Mapping.discover(self._mapping_dir))
            for name in names:
                cmb.addItem(name, name)
        else:
            ts = Mapping.templates()
            names = ts.names()
            for name in names:
                tag = "user" if ts.source(name) == "user" else "built-in"
                cmb.addItem(f"{name}  ·  {tag}", name)

        target = select
        if target is None and not self._mapping_dir:
            target = Mapping.templates().active
        idx = self._combo_data_index(target) if target else -1
        if idx < 0 and "default" in names:
            idx = self._combo_data_index("default")
        cmb.setCurrentIndex(idx if idx >= 0 else 0)
        cmb.blockSignals(False)
        # Programmatic refresh: apply but don't persist — rebuilding the list
        # must not overwrite the user's last-used pointer.
        self._apply_mapping(cmb.currentData(), persist=False)

    def _combo_data_index(self, name) -> int:
        """Index of the combo item whose data == *name*, or -1."""
        cmb = self._cmb_mapping
        for i in range(cmb.count()):
            if cmb.itemData(i) == name:
                return i
        return -1

    def _on_mapping_changed(self, arg=None) -> None:
        """Handle a mapping selection.

        Connected to ``currentIndexChanged`` (passes an int) — the real mapping
        name is read from the current item's data. A ``str`` *arg* is also
        accepted (legacy/tests) and used directly as the name.
        """
        if isinstance(arg, str):
            name = None if (not arg or arg == "(none)") else arg
        else:
            name = self._cmb_mapping.currentData()
        path, store = self._loaded_sheet(), self._active_store()
        if path and store is not None:
            # The user's pick for the sheet loaded is the scene's from now on
            # (its options seeded from theirs); else the reload below would
            # read it with the template the scene kept.
            self._sheet_values = None
            ptk.ManifestEdits.set_sheet_options(
                store, path, name, self._user_option_values(name) if name else {}
            )
        self._apply_mapping(name, persist=True)

    def _apply_mapping(self, name, persist: bool) -> None:
        """Load *name* into ``_active_mapping`` and re-parse the current CSV.

        *persist* records the choice as last-used (skipped in directory-override
        mode, whose pointer belongs to a different store).
        """
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        self._mapping_name = name or None
        # The user's own pick: what a sheet the scene never read is read with
        # (_adopt_sheet_options), whichever template a record switched in.
        self._user_template = self._mapping_name
        self._mapping_template = None
        if name:
            try:
                self._mapping_template = Mapping.load_mapping(
                    name, self._mapping_dir or None
                )
            except Exception as exc:
                self.logger.error("Failed to load mapping '%s': %s", name, exc)
                self._set_footer(f"Mapping error: {exc}", color=ERROR_COLOR)
                self._active_mapping = None
                self._build_option_rows()
                return
            if persist and not self._mapping_dir:
                try:
                    Mapping.templates().active = (
                        name  # remember last-used across sessions
                    )
                except Exception:
                    pass
        self._build_option_rows()
        self._reapply_mapping()

    def _option_values(self, name: Optional[str] = None) -> Dict[str, object]:
        """The option values template *name* (the current one by default)
        reads with: the scene's for the sheet loaded (``_sheet_values``,
        :meth:`_adopt_sheet_options`), else the user's own (``{}`` if none)."""
        name = name or self._mapping_name
        sheet = getattr(self, "_sheet_values", None)
        if name and sheet is not None and name == self._mapping_name:
            return dict(sheet)
        return self._user_option_values(name)

    def _user_option_values(self, name: Optional[str] = None) -> Dict[str, object]:
        """The user's saved option values of template *name* (the current one
        by default; ``{}`` if none) -- what seeds a sheet the scene has never
        read (maintainer 2026-10-12)."""
        import json

        name = name or self._mapping_name
        if not name:
            return {}
        raw = self._settings.value(f"mapping_options/{name}", "")
        try:
            values = json.loads(raw) if raw else {}
        except (TypeError, ValueError):
            return {}
        return values if isinstance(values, dict) else {}

    def _reapply_mapping(self) -> None:
        """Rebuild the effective template from its options, then re-load the sheet."""
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        self._active_mapping = (
            Mapping.apply_options(self._mapping_template, self._option_values())
            if self._mapping_template is not None
            else None
        )
        # The sheet in the field: one that just failed to load is the one an
        # option is set for (its field says to set its Step IDs), not the
        # sheet still shown.
        path = self.ui.txt_csv_path.text().strip() or self._csv_path
        if path:
            self._load_csv(path)

    def _on_option_changed(self, key: str, value) -> None:
        """Save one option of the current template and re-apply it: on the
        scene for the sheet loaded (how the scene reads it,
        :meth:`_record_sheet_options`), and as the user's own, which seed the
        next sheet the scene has never read.  A sheet in the field that did
        not load is read again with it (:meth:`_reapply_mapping`), and the
        sheet still shown keeps its record."""
        import json

        user = self._user_option_values()
        user[key] = value
        self._settings.setValue(
            f"mapping_options/{self._mapping_name}", json.dumps(user)
        )
        field = self.ui.txt_csv_path.text().strip()
        if self._loaded_sheet() and field in ("", self._loaded_sheet()):
            values = self._option_values()
            values[key] = value
            self._sheet_values = values
            self._record_sheet_options()
        self._reapply_mapping()

    # ---- the scene's options for its sheet (maintainer 2026-10-12) ---------------

    def _loaded_sheet(self) -> str:
        """The sheet the table shows, or ``""`` (the scene's own shots)."""
        return (self._csv_path or "") if self._source == "csv" else ""

    def _record_sheet_options(self, store=None) -> bool:
        """Keep the template and options the loaded sheet is read with on the
        scene, beside its Local Edits (``ManifestEdits.set_sheet_options``):
        what a Build, an option change and a saved edit record, so a reopen
        reads the sheet the way it was built whatever the user's own options
        are by then.  ``False`` with no sheet loaded or nothing changed."""
        path = self._loaded_sheet()
        store = store if store is not None else self._active_store()
        if not path or store is None:
            return False
        values = self._option_values() if self._mapping_name else {}
        self._sheet_values = dict(values)
        return ptk.ManifestEdits.set_sheet_options(
            store, path, self._mapping_name, values
        )

    def _adopt_sheet_options(self, path: str) -> None:
        """Read sheet *path* the way the scene reads it, before it is parsed:
        the template and options the scene keeps for it
        (``ManifestEdits.sheet_options``); else -- a scene built from it before
        they were kept -- the options its build reads back as
        (:meth:`_inferred_sheet_options`); else the user's own: a sheet the
        scene has never read.  Nothing is written: a record is made by a
        Build, an option change or a saved edit."""
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        store = self._active_store()
        record = ptk.ManifestEdits.sheet_options(store, path)
        if record is None:
            record = self._inferred_sheet_options(store, path)
        if record is None:
            user = getattr(self, "_user_template", self._mapping_name)
            if user != self._mapping_name:
                self._switch_template(user)  # a record's, switched in before
            elif getattr(self, "_sheet_values", None) is None:
                return  # already the user's own
            self._sheet_values = None
        else:
            values = dict(record.get("values") or {})
            if (record.get("template"), values) == (
                self._mapping_name,
                getattr(self, "_sheet_values", None),
            ):
                # Read this way already (an option just changed for it): the
                # option rows -- the changed one's among them -- stay.
                return
            if record.get("template") != self._mapping_name:
                self._switch_template(record.get("template"))
            self._sheet_values = values
        self._active_mapping = (
            Mapping.apply_options(self._mapping_template, self._option_values())
            if self._mapping_template is not None
            else None
        )
        self._build_option_rows()

    def _switch_template(self, name: Optional[str]) -> bool:
        """Read with template *name* (``None``: no template) for the sheet
        loaded -- shown on the picker, never saved as the user's last-used.
        ``False`` (the current one kept) when this machine has no such
        template; the footer says so."""
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        template = None
        if name:
            try:
                template = Mapping.load_mapping(name, self._mapping_dir or None)
            except Exception as exc:
                self.logger.warning("Sheet template %r not loaded: %s", name, exc)
                self._set_footer(
                    f"This scene reads its sheet with template '{name}', which "
                    "is not installed here: read with the current one.",
                    color=ERROR_COLOR,
                )
                return False
        self._show_template(name, template)
        return True

    def _show_template(self, name: Optional[str], template) -> None:
        """Make *name* (its loaded *template*) the current template and show
        it on the picker, without its change signal."""
        self._mapping_name, self._mapping_template = name or None, template
        cmb = getattr(self, "_cmb_mapping", None)
        if cmb is not None:
            idx = self._combo_data_index(name) if name else 0
            cmb.blockSignals(True)
            cmb.setCurrentIndex(max(idx, 0))
            cmb.blockSignals(False)

    def _sheet_read_state(self) -> tuple:
        """What :meth:`_adopt_sheet_options` changes -- the template, the
        sheet's option values and the effective mapping -- for
        :meth:`_restore_sheet_read_state`."""
        return (
            self._mapping_name,
            self._mapping_template,
            getattr(self, "_sheet_values", None),
            self._active_mapping,
        )

    def _restore_sheet_read_state(self, state: tuple) -> None:
        """Read the sheet shown as it was read before another sheet failed to
        load (:meth:`_load_csv`): a Build and an option change record on the
        sheet shown, so the failed sheet's template and options must not
        stay current."""
        if state == self._sheet_read_state():
            return
        name, template, values, active = state
        self._show_template(name, template)
        self._sheet_values, self._active_mapping = values, active
        self._build_option_rows()

    def _inferred_sheet_options(self, store, path: str) -> Optional[dict]:
        """``{"template", "values"}`` for a scene built from sheet *path*
        before its options were kept with it: the values its shots' recorded
        objects read back as (``Mapping.infer_options``, from the user's own),
        with the current template.  ``None`` when the scene was not built
        from *path*, records no objects, or the sheet is a URL (each trial
        would fetch it).  The last read is kept, keyed by its sheet,
        template and build record."""
        import os
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        if (
            store is None
            or self._mapping_template is None
            or ptk.RemoteFile.is_url(path)
            or not ptk.ManifestEdits.same_sheet(store.source_csv, path)
        ):
            return None
        built = {}
        for shot in store.shots:
            meta = shot.metadata or {}
            names = [
                o.get("name")
                for o in meta.get("csv_objects") or ()
                if isinstance(o, dict) and o.get("name")
            ]
            if meta.get("step") and names:
                built[str(meta["step"])] = names
        if not built:
            return None
        user = self._user_option_values()
        try:
            stamp = os.path.getmtime(path)
        except OSError:
            stamp = None
        key = (
            path,
            stamp,
            self._mapping_name,
            repr(sorted(built.items())),
            repr(sorted(user.items())),
        )
        cached = getattr(self, "_inferred_options", None)
        if cached is None or cached[0] != key:
            values = Mapping.infer_options(path, self._mapping_template, built, user)
            cached = self._inferred_options = (key, values)
        return {"template": self._mapping_name, "values": dict(cached[1])}

    def _build_option_rows(self) -> None:
        """Show the current template's options under its picker (:meth:`_mapping_popup`).

        One form (uitk's ``FormRows``): a caption per option in one column,
        its control in the next, so the values line up -- under a titled
        divider per section the template names (``Mapping.option_sections``).
        Each control is built by uitk's widget factory from an
        ``AttributeSpec`` -- the template declares its own settings and how
        they group, so a new option needs no code here.  Values persist per
        template; the template, not the widget state, owns them.
        """
        from qtpy import QtWidgets
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping
        AttributeSpec, KindFactory = self.sb.AttributeSpec, self.sb.KindFactory
        Tooltip = self.sb.Tooltip
        FormRows = self.sb.FormRows

        menu = self._mapping_menu
        for row in self._option_rows:
            menu.remove_widget(row)
            row.hide()  # gone now, not when the deferred delete runs
            row.deleteLater()
        self._option_rows = []
        if not isinstance(menu, QtWidgets.QWidget):
            return  # mocked UI (logic tests)
        values = self._option_values()
        form = FormRows()
        for title, specs in Mapping.option_sections(self._mapping_template):
            if title:
                form.add("Separator", setTitle=title)
            for opt in specs:
                spec = AttributeSpec(
                    key=opt["key"],
                    label=opt["label"],
                    kind=opt["kind"],
                    default=values.get(opt["key"], opt["default"]),
                    choices=tuple(opt.get("choices", ())),
                    tooltip=opt["tooltip"],
                )
                widget = KindFactory.make_widget(spec, form)
                widget.setObjectName(f"opt_{spec.key}")
                widget.restore_state = False  # the template owns the value
                form.add(
                    widget,
                    label=spec.display_label,
                    tooltip=Tooltip.format_param_tooltip(spec),
                )
                KindFactory.connect_changed(
                    widget,
                    lambda value, key=spec.key: self._on_option_changed(key, value),
                )
        menu.add(form)
        self._option_rows.append(form)

    def _open_mappings_folder(self) -> None:
        """Open the writable folder where user mapping files live.

        Mapping files are managed externally, not edited in-place from the UI:
        the user opens this folder, adds/edits/removes files, then clicks
        *Refresh*.  On first use (empty folder) it's seeded with a documented
        example and the format reference, so there's a model to copy and a spec
        to read.
        """
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        ts = Mapping.templates()
        d = ts.user_dir
        d.mkdir(parents=True, exist_ok=True)
        self._seed_mappings_folder(ts)
        ptk.FileUtils.open_explorer(str(d), logger=self.logger)

    @staticmethod
    def _seed_mappings_folder(ts) -> None:
        """Seed *ts*'s empty user folder with an example mapping + format
        reference (``Mapping.seed_user_folder``: a no-op once it holds anything).
        """
        from pythontk.core_utils.engines.shots.manifest.mapping import Mapping

        Mapping.seed_user_folder(ts)
