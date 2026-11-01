# !/usr/bin/python
# coding=utf-8
"""Light Rigs: save the scene's lights as named rigs, swap between them and
restore any one.

A thin driver over the host toolkit's ``LightRig`` (``self.tk``). The dropdown
is the library: picking a rig only shows it; **Apply** puts it in the scene and
**Swap Back** returns to the rig it replaced. The verbs on a rig live on the
dropdown (＋ saves the scene's rig; ☰ renames, duplicates, locks, compares with
the scene and deletes; a double-click renames).

A Maya tool for now (``tentacle.slots.tools.HOSTS``): blendertk has no
``LightRig`` yet (BACKLOG, "Light Rigs has no blendertk twin"). The panel calls
only the engine, so the port is the engine alone, plus its host added there.
"""

from typing import Optional

import pythontk as ptk

from tentacle import Slots


class LightRigSlots(Slots, ptk.LoggingMixin):
    HELP_URL = "https://github.com/m3trik/mayatk/blob/main/docs/light_rig.md"

    #: How many Compare With Scene lines the message box shows; the rest go to
    #: the log.
    COMPARE_SHOWN = 25

    def __init__(self, switchboard):
        super().__init__(switchboard)
        self.logger.setLevel("WARNING")
        self.ui = self.sb.loaded_ui.light_rig
        self.engine = self.tk.LightRig()
        # A scene open or new swaps the scene's rig: re-read it. Each subscribe
        # is guarded: an event a host lacks must not block the panel open.
        jobs = self.tk.ScriptJobManager.instance()
        for event in ("SceneOpened", "NewSceneOpened"):
            try:
                jobs.subscribe(event, self.refresh, owner=self)
            except Exception as e:
                self.logger.debug("Light Rigs: event %r unavailable (%s)", event, e)
        jobs.connect_cleanup(self.ui, owner=self)
        # The switchboard builds this instance mid-load: widgets are wired after __init__.
        self.sb.QtCore.QTimer.singleShot(0, self.refresh)

    # ------------------------------------------------------------- state
    def _picked(self) -> Optional[str]:
        return self.ui.cmb000.currentData() or None

    def _scene_group(self) -> str:
        """The group a save captures: the scene's rig group, else the engine's default."""
        rigs = self.engine.scene_rigs()
        return rigs[0][0] if rigs else self.engine.group

    def _user_info(self, name: str) -> dict:
        """The library entry's info (description, lights, lock), ``{}`` for a
        rig the user did not save (a shipped one)."""
        store = self.engine.store
        return store.info(name) if store.source(name) == "user" else {}

    def _notify(
        self, message: str, level: str = "info", detail: Optional[str] = None
    ) -> None:
        self.ui.footer.setText(message, level=level)
        {"error": self.logger.error, "warning": self.logger.warning}.get(
            level, self.logger.info
        )(detail or message)

    def refresh(self) -> None:
        """Re-read the library, select the scene's rig, and report the scene."""
        cmb = self.ui.cmb000
        picked = self._picked()
        names = self.engine.names()
        scene = self.engine.scene_rigs()
        applied = {name for _, name in scene if name}
        cmb.blockSignals(True)
        try:
            cmb.clear()
            for name in names:
                info = self._user_info(name)
                note = "locked" if info.get("read_only") else (info.get("status") or "")
                index = cmb.add_cells(
                    {"name": name, "lights": str(info.get("lights", "")), "note": note},
                    name,
                )
                tip = [name + ("  (in the scene)" if name in applied else "")]
                if info.get("description"):
                    tip.append(info["description"])
                if info.get("parent"):
                    tip.append(f"from {info['parent']}")
                cmb.setItemData(index, "\n".join(tip), self.sb.QtCore.Qt.ToolTipRole)
            target = picked if picked in names else next(iter(applied & set(names)), None)
            index = cmb.findData(target) if target else -1
            cmb.setCurrentIndex(max(index, 0) if cmb.count() else -1)
            cmb.restore_state = False
        finally:
            cmb.blockSignals(False)
        self.ui.b001.setEnabled(self.engine.can_swap_back())
        if not scene:
            self._notify("No rig in the scene: ＋ saves the lights under a group as one.")
            return
        group, name = scene[0]
        _, edited = self.engine.applied(group)
        self._notify(
            f"Scene: {name or 'an unsaved rig'}{' (edited)' if edited else ''} in {group}",
            level="warning" if edited else "info",
        )

    # ------------------------------------------------------------- widgets
    def header_init(self, widget) -> None:
        widget.config_buttons("refresh", "menu", "collapse", "hide")
        widget.refresh_requested.connect(self.refresh)
        widget.menu.add(
            "QPushButton",
            setText="Open Rig Folder",
            setObjectName="open_rig_folder",
            setToolTip="Open the folder the rig library lives in.",
        )
        widget.set_help_text(
            self.sb.tooltip.fmt(
                title="Light Rigs",
                body="Save the scene's lights as named rigs, swap between them, and restore any one.",
                steps=[
                    "<b>＋</b> on the dropdown saves the lights under the rig group (and the plugs its rig overrides).",
                    "Pick a rig and press <b>Apply</b>: it replaces the lights in its group. Lights outside the "
                    "group are never deleted; an override on a driven plug takes it over (Swap Back reconnects it), "
                    "and a locked plug is left alone -- both reported.",
                    "<b>Swap Back</b> returns to the rig Apply replaced; press it again to toggle.",
                    "<b>☰</b> renames, duplicates, locks, compares with the scene and deletes; a double-click renames.",
                ],
                notes=[
                    "Rigs are shared JSON presets (light_rigs): every scene, and the look-match tool, see the same library."
                ],
            ),
            url=self.HELP_URL,
        )

    def cmb000_init(self, widget) -> None:
        widget.set_cells(
            [
                {"key": "name", "label": "Rig"},
                {"key": "lights", "label": "Lights", "editable": False},
                {"key": "note", "label": "", "editable": False},
            ],
            cell_format="{name}",
        )
        widget.option_box.add_action(
            callback=self.prompt_save,
            icon="add",
            tooltip="Save the scene's rig… (the lights under its group)",
        )
        widget.option_box.add_action(
            callback=self._show_rig_menu,
            icon="menu",
            tooltip="Rename, duplicate, lock, compare with the scene or delete the rig shown.",
        )
        widget.setPlaceholderText("No saved rigs: ＋ saves the scene's rig")
        widget.rename_on_double_click = True
        widget.on_cells_edited.connect(self._on_cells_edited)
        widget.before_popup_shown.connect(self.refresh)
        widget.setContextMenuPolicy(self.sb.QtCore.Qt.CustomContextMenu)
        widget.customContextMenuRequested.connect(
            lambda pos: self._show_rig_menu(widget.mapToGlobal(pos))
        )

    def cmb000(self, index, widget) -> None:
        """Show the picked rig (picking never changes the scene)."""
        name = widget.currentData()
        if not name:
            return
        info = self._user_info(name)
        desc = f" — {info['description']}" if info.get("description") else ""
        self.ui.footer.setText(
            f"{name}: {info.get('lights', '?')} lights in {info.get('group', '?')}{desc}"
        )

    def b000(self) -> None:
        """Apply the picked rig: it replaces the scene's rig (Swap Back returns)."""
        name = self._picked()
        if not name:
            self._notify("Pick a rig to apply.", "warning")
            return
        try:
            report = self.engine.apply(name)
        except (KeyError, ValueError) as e:
            self._notify(f"Could not apply {name}: {e}", "error")
            return
        self.refresh()
        notes = report["disconnected"] + report["skipped"]
        if notes:
            self._notify(
                f"Applied {name}; {len(report['disconnected'])} driven plug(s) taken over "
                f"(Swap Back reconnects), {len(report['skipped'])} override(s) left alone.",
                "warning",
                detail="\n".join(notes),
            )
        else:
            self._notify(
                f"Applied {name}: {len(report['lights'])} lights in {report['group']}.",
                "success",
            )

    def b001(self) -> None:
        """Swap Back: return to the rig the last Apply replaced."""
        try:
            report = self.engine.swap_back()
        except LookupError as e:
            self._notify(str(e), "warning")
            return
        self.refresh()
        self._notify(f"Swapped back to {report['name'] or 'the unsaved rig'}.", "success")

    def open_rig_folder(self) -> None:
        """Header menu: the folder the rig library lives in."""
        ptk.FileUtils.open_explorer(
            str(self.engine.store.user_dir), create_dir=True, logger=self.logger
        )

    # ------------------------------------------------------------- verbs
    def _form(
        self,
        title: str,
        ok: str,
        name: str = "",
        description: str = "",
        group: Optional[str] = None,
    ):
        fields = [
            {"name": "name", "label": "Name", "value": name, "placeholder": "e.g. moody_v3"},
            {
                "name": "description",
                "label": "Description",
                "value": description,
                "placeholder": "Optional",
            },
        ]
        if group is not None:
            fields.append(
                {
                    "name": "group",
                    "label": "Group",
                    "value": group,
                    "hint": "The scene group whose lights are the rig.",
                }
            )

        def validate(values) -> str:
            return "" if values["name"].strip() else "Name the rig."

        return self.sb.FormPanel(
            fields,
            title=title,
            parent=self.ui,
            ok_text=ok,
            validate=validate,
            output=False,
        )

    def _ask(self, title: str, text: str) -> bool:
        Q = self.sb.QtWidgets.QMessageBox
        return Q.question(self.ui, title, text, Q.Yes | Q.No, Q.No) == Q.Yes

    def _filled(self, form) -> Optional[dict]:
        """*form*'s values once accepted, ``None`` when dismissed; the form goes either way."""
        try:
            return form.values() if form.exec_panel() else None
        finally:
            form.deleteLater()

    def prompt_save(self) -> None:
        """＋: save the scene's rig under a new (or existing) name."""
        values = self._filled(
            self._form("Save rig", "Save", name=self._picked() or "", group=self._scene_group())
        )
        if values is None:
            return
        name = values["name"].strip()
        group = values["group"].strip() or self.engine.group
        if self.engine.store.exists(name) and not self._ask(
            "Replace rig?", f"Replace the saved rig {name}?"
        ):
            return
        try:
            self.engine.save(
                name,
                description=values["description"].strip() or None,
                group=group,
                force=False,
            )
        except PermissionError:
            self._notify(f"{name} is locked: unlock it (☰) or save under another name.", "error")
            return
        self.refresh()
        self.ui.cmb000.setCurrentIndex(max(self.ui.cmb000.findData(name), 0))
        self._notify(f"Saved {name}.", "success")

    def _show_rig_menu(self, pos=None) -> None:
        cmb, name = self.ui.cmb000, self._picked()
        menu = self.sb.ContextMenu(parent=cmb)
        if not name:
            menu.add("Save a rig first (＋)", setEnabled=False)
        else:
            store = self.engine.store
            user = store.source(name) == "user"
            locked = user and bool(store.info(name).get("read_only"))
            menu.add_separator(name)
            menu.add("Rename…", callback=cmb.begin_rename, setEnabled=user and not locked)
            menu.add("Duplicate…", callback=lambda: self._duplicate(name))
            menu.add(
                "Edit Description…",
                callback=lambda: self._describe(name),
                setEnabled=user,
            )
            menu.add(
                "Unlock" if locked else "Lock",
                callback=lambda: self._lock(name, not locked),
                setEnabled=user,
                setToolTip="A locked rig cannot be saved over, renamed or deleted.",
            )
            menu.add(
                "Compare With Scene",
                callback=lambda: self._compare(name),
                setToolTip="What applying it would change in the scene's rig.",
            )
            menu.add_separator()
            menu.add(
                "Delete",
                callback=lambda: self._delete(name),
                setEnabled=user and not locked,
            )
        if pos is None:
            pos = cmb.mapToGlobal(self.sb.QtCore.QPoint(0, cmb.height()))
        menu.exec_(pos)

    def _on_cells_edited(self, index: int, cells: dict) -> None:
        old = self.ui.cmb000.itemData(index)
        new = (cells.get("name") or "").strip()
        outcome = None
        if old and new and new != old:
            if self.engine.rename(old, new):
                outcome = (f"Renamed {old} to {new}.", "success")
            else:
                outcome = (
                    f"Could not rename {old}: {new} is taken, or {old} is locked.",
                    "error",
                )
        self.refresh()  # before the message: refresh reports the scene in the footer
        if outcome:
            self._notify(*outcome)

    def _duplicate(self, name: str) -> None:
        values = self._filled(self._form(f"Duplicate {name}", "Duplicate", name=f"{name}_copy"))
        if values is None:
            return
        new = values["name"].strip()
        if self.engine.store.exists(new):
            self._notify(f"{new} already exists.", "error")
            return
        self.engine.store.save(new, self.engine.load(name))
        info = self._user_info(name)
        self.engine.store.set_info(
            new,
            parent=name,
            description=values["description"].strip() or info.get("description"),
            lights=info.get("lights"),
            group=info.get("group"),
        )
        self.refresh()

    def _describe(self, name: str) -> None:
        values = self._filled(
            self._form(
                f"Describe {name}",
                "Save",
                name=name,
                description=self.engine.store.info(name).get("description") or "",
            )
        )
        if values is None:
            return
        self.engine.store.set_info(name, description=values["description"].strip() or None)
        self.refresh()

    def _lock(self, name: str, state: bool) -> None:
        self.engine.store.set_info(name, read_only=True if state else None)
        self.refresh()

    def _compare(self, name: str) -> None:
        group = self.engine.normalize(self.engine.load(name)).get("group") or self._scene_group()
        changes = self.engine.compare(name, group)
        if not changes:
            self._notify(f"{name} matches the scene's rig in {group}.", "success")
            return
        shown = changes[: self.COMPARE_SHOWN]
        if len(changes) > self.COMPARE_SHOWN:
            shown.append(f"(+{len(changes) - self.COMPARE_SHOWN} more in the log)")
        self.logger.warning("Scene -> %s:\n%s", name, "\n".join(changes))
        self.sb.message_box(
            f"Applying {name} would change {len(changes)} thing(s):\n" + "\n".join(shown),
            "Ok",
        )

    def _delete(self, name: str) -> None:
        if not self._ask("Delete rig?", f"Delete the saved rig {name}? The scene is not changed."):
            return
        deleted = self.engine.delete(name)
        self.refresh()  # before the message: refresh reports the scene in the footer
        self._notify(
            f"Deleted {name}." if deleted else f"{name} is locked.",
            "success" if deleted else "error",
        )
