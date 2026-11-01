# !/usr/bin/python
# coding=utf-8
"""The Shot Manifest rows' context menus and what they do: a step row's (colour
tags, open its shot, Lock / Unlock it or its section, Pair with Shot), an
object row's (reveal, copy, re-apply its behaviors, its Render Effects pages,
its audio clip), and a "not in doc" shot's (open, reveal its members, Add to
the Manifest, Pair with Step, Remove Shot).  Local Edits add their own.

One copy for both hosts: every host call goes through the controller's
``manifest_host``, the host library's ``ManifestHost`` (from ``Slots.tk``).
"""

from typing import Dict, List, Tuple

import pythontk as ptk
from pythontk import BuilderObject, BuilderStep

from .manifest_data import COL_END, COL_START, ERROR_COLOR, ManifestData


class RowMenusMixin:
    """The rows' context menus, mixed into ``ShotManifestController``.

    Uses the controller's ``ui.tbl_steps``, ``sb``, ``_editor``, ``_row_tags``,
    ``_steps``, ``_user_ranges``, ``_source``, ``_store_cls()``,
    ``_active_store()``, ``_manifest()``, ``_pairing()``, ``_orphan_shots()``,
    ``_is_built``, ``_step_items()``, ``_step_index()``, ``_cascade_from()``,
    ``_refresh_ranges()``, ``_set_range_to_current_frame()``,
    ``_reapply_behavior()``, ``_edit_store()``, ``_redraw()`` and
    ``_set_footer()``.
    """

    def _remove_orphan(self, shot) -> None:
        """Remove one shot no doc step pairs with -- the only way a shot leaves
        the store from this panel: explicit, one at a time, undoable.  The
        table redraws once, keeping its expansion and assessment, like every
        other store edit made from a row's menu (:meth:`_edit_store`)."""
        if self._active_store() is None:
            return
        with self._edit_store("manifest_remove_shot") as store:
            store.remove_shot(shot.shot_id)
        self._redraw(reassess=True)
        self._set_footer(f"Removed shot '{shot.name}'; its keys stay in the scene.")

    def _on_rows_tagged(self, rows, slot) -> None:
        """The user picked a colour (or none) for step rows: keep it on the
        scene's store, under the loaded sheet (``ManifestTags``)."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        step_ids = [
            step.step_id
            for step in (tree.itemFromIndex(i).data(0, Qt.UserRole) for i in rows)
            if isinstance(step, BuilderStep)
        ]
        store = self._active_store()
        if store is not None and step_ids:
            ptk.ManifestTags.assign(store, self._editor.source_key, step_ids, slot)

    def _show_item_menu(self, pos) -> None:
        """Show a context menu for the clicked tree item; each entry carries
        its own callback."""
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QMenu
        StyleSheet = self.sb.StyleSheet

        tree = self.ui.tbl_steps
        item = tree.itemAt(pos)

        # Right-click on empty space -- Local Edits' Add Step / Show Hidden
        if item is None:
            menu = QMenu(tree)
            StyleSheet.cast_shadow(menu)
            self._editor.add_menu_actions(menu, None)
            if any(not a.isSeparator() for a in menu.actions()):
                menu.exec_(tree.viewport().mapToGlobal(pos))
            menu.deleteLater()  # parented to the tree: else kept per right-click
            return

        # Resolve to parent step row
        is_child = item.parent() is not None
        step_item = item.parent() if is_child else item
        step_data = step_item.data(0, Qt.UserRole)
        if not isinstance(step_data, BuilderStep):
            if getattr(step_data, "shot_id", None) is not None:  # "not in doc" row
                self._show_shot_menu(item, step_data, pos)
            return

        selected_step_ids = self._selected_step_ids()
        # Pre-compute the pairing once for all guards in this menu.
        try:
            built_names = set(self._pairing().shots)
        except Exception:
            built_names = set()

        menu = QMenu(tree)
        StyleSheet.cast_shadow(menu)
        menu.setToolTipsVisible(True)
        if not is_child:
            # Colour swatches: every selected step when the clicked one is
            # among them, else the clicked one.
            tag_ids = (
                selected_step_ids
                if step_data.step_id in selected_step_ids
                else [step_data.step_id]
            )
            self._row_tags.add_to_menu(menu, self._step_items(tag_ids))
            menu.addSeparator()
        self._add_open_actions(menu, step_data, bool(built_names))
        if not is_child:
            self._add_step_shot_actions(menu, step_data, selected_step_ids)
            # Range column actions (parent rows, pre-build only)
            column = tree.columnAt(pos.x())
            if step_data.step_id not in built_names and column in (COL_START, COL_END):
                self._add_range_actions(menu, step_item, step_data.step_id)
        else:
            self._add_object_actions(menu, item, step_data.step_id)

        # Local Edits: rename / hide / move / add.
        self._editor.add_menu_actions(menu, item, selected_step_ids)

        menu.exec_(tree.viewport().mapToGlobal(pos))
        menu.deleteLater()  # the actions stay valid until the event loop runs

    def _selected_step_ids(self) -> List[str]:
        """The selected rows' step IDs, each once in selection order (an
        object row counts as its step)."""
        from qtpy.QtCore import Qt

        step_ids = []
        for sel_item in self.ui.tbl_steps.selectedItems():
            parent_item = sel_item.parent() if sel_item.parent() is not None else sel_item
            data = parent_item.data(0, Qt.UserRole)
            if isinstance(data, BuilderStep) and data.step_id not in step_ids:
                step_ids.append(data.step_id)
        return step_ids

    def _add_open_actions(self, menu, step, any_built: bool) -> None:
        """Open *step*'s shot in the Shot Sequencer or the Shots panel --
        disabled until shots are built."""
        step_id = step.step_id
        actions = (
            menu.addAction(
                f"Open '{step.shot_name}' in Shot Sequencer",
                lambda: self._open_in_shot_sequencer(step_id),
            ),
            menu.addAction(
                f"Open '{step.shot_name}' in Shots",
                lambda: self._open_in_shots(step_id),
            ),
        )
        if not any_built:
            for action in actions:
                action.setEnabled(False)
                action.setToolTip("Build shots first")

    def _add_range_actions(self, menu, step_item, step_id: str) -> None:
        """The Start / End column's entries for a step not yet built."""
        menu.addSeparator()
        menu.addAction(
            "Set Start to Current Frame",
            lambda: self._set_range_to_current_frame(step_item, step_id),
        )
        menu.addAction("Auto-fill from Gaps", lambda: self._auto_fill_from(step_id))
        if step_id in self._user_ranges:
            menu.addAction("Clear Range", lambda: self._clear_range(step_id))

    def _auto_fill_from(self, step_id: str) -> None:
        """Clear the typed ranges from *step_id* onward so they re-resolve."""
        step_idx = self._step_index(step_id)
        self._user_ranges.pop(step_id, None)
        self._cascade_from(step_idx)
        self._refresh_ranges(from_step_idx=step_idx)

    def _clear_range(self, step_id: str) -> None:
        """Drop *step_id*'s typed range."""
        self._user_ranges.pop(step_id, None)
        self._refresh_ranges()

    def _add_object_actions(self, menu, item, step_id: str) -> None:
        """An object row's entries: reveal or copy it -- every selected object
        row when the clicked one is among them (a name several nodes share is
        fixed in the scene) -- apply its behaviors, open the pages that say
        how they are keyed, and an audio row's clip."""
        from qtpy.QtCore import Qt

        obj_data = item.data(0, Qt.UserRole)
        obj_name = (
            getattr(obj_data, "name", None) if isinstance(obj_data, BuilderObject) else None
        )
        if not obj_name:
            return
        obj_names = [obj_name]
        if item.isSelected():
            obj_names = list(
                dict.fromkeys(
                    o.name
                    for o in (
                        s.data(0, Qt.UserRole) for s in self.ui.tbl_steps.selectedItems()
                    )
                    if isinstance(o, BuilderObject) and o.name
                )
            )
        many = len(obj_names) > 1
        menu.addSeparator()
        menu.addAction(
            f"Show {len(obj_names)} Objects in Outliner"
            if many
            else f"Show '{obj_name}' in Outliner",
            lambda: self._show_in_outliner(obj_names),
        )
        menu.addAction(
            f"Copy {len(obj_names)} Names to Clipboard"
            if many
            else f"Copy '{obj_name}' to Clipboard",
            lambda: self._copy_names(obj_names),
        )
        if self._is_built and obj_data.behaviors:
            names = ", ".join(ManifestData.fmt_behavior(b) for b in obj_data.behaviors)
            menu.addAction(
                f"Apply [{names}]", lambda: self._reapply_behavior(step_id, obj_data)
            )

        # The panels that say HOW its behaviors are keyed, opened on this
        # object alone (the recipe there is the build's). A closure per page:
        # a default argument would take the action's ``checked``.
        def open_page(channel):
            return lambda: self._open_effect(step_id, obj_data, channel)

        for channel, verb in self._effect_pages(obj_data):
            menu.addAction(f"{verb} '{obj_name}'\u2026", open_page(channel))
        if obj_data.kind == "audio":
            menu.addAction(
                f"Open '{obj_name}' in Audio Clips",
                lambda: self._open_audio_clip(obj_name),
            )

    def _show_shot_menu(self, item, shot, pos) -> None:
        """The context menu of a "not in doc" row (*item* the row or one of
        its member rows): open the shot, reveal or copy its members, take it
        into the manifest -- a step of its own, or the shot of a step that has
        none -- or remove it."""
        from qtpy.QtCore import Qt
        from qtpy.QtWidgets import QMenu
        StyleSheet = self.sb.StyleSheet

        tree = self.ui.tbl_steps
        after = self._row_above(item)  # now: a redraw may delete the row
        menu = QMenu(tree)
        StyleSheet.cast_shadow(menu)
        menu.setToolTipsVisible(True)
        name = shot.name
        menu.addAction(
            f"Open '{name}' in Shot Sequencer",
            lambda: self._open_shot_in_sequencer(shot),
        )
        menu.addAction(
            f"Open '{name}' in Shots", lambda: self._open_shot_in_shots(shot)
        )
        obj = item.data(0, Qt.UserRole) if item.parent() is not None else None
        names = [obj.name] if isinstance(obj, BuilderObject) else list(shot.objects)
        if names:
            menu.addSeparator()
            leaf = str(names[0]).split("|")[-1]
            many = len(names) > 1
            menu.addAction(
                f"Show {len(names)} Members in Outliner"
                if many
                else f"Show '{leaf}' in Outliner",
                lambda: self._show_in_outliner(names),
            )
            menu.addAction(
                f"Copy {len(names)} Names to Clipboard"
                if many
                else f"Copy '{leaf}' to Clipboard",
                lambda: self._copy_names(names),
            )
        menu.addSeparator()
        act_add = menu.addAction(
            f"Add '{name}' to the Manifest",
            lambda: self._editor.add_shot(shot, after),
        )
        if self._editor.enabled:
            act_add.setToolTip(
                "A step of its own, named after the shot and bound to it, right\n"
                "where the table lists it -- a Local Edit, never written to the\n"
                "sheet. Its members stay."
            )
        else:
            act_add.setEnabled(False)
            act_add.setToolTip(
                "Comparing to the original sheet: pick another Edits mode "
                "(header menu) to add it."
            )
        built = self._pairing().shots
        self._add_pair_menu(
            menu,
            f"Pair '{name}' with Step",
            [s for s in self._steps if s.step_id not in built],
            lambda step: self._pair_shot(shot, step),
            "Every step has a shot.",
        )
        menu.addSeparator()
        act_remove = menu.addAction(
            f"Remove Shot '{name}'", lambda: self._remove_orphan(shot)
        )
        act_remove.setToolTip(
            "No doc step pairs with this shot. Removes its record; "
            "its keys stay in the scene."
        )
        menu.exec_(tree.viewport().mapToGlobal(pos))
        menu.deleteLater()  # parented to the tree: else kept per right-click

    def _add_step_shot_actions(self, menu, step, selected: List[str]) -> None:
        """A step row's shot actions: Lock / Unlock it (the selection when the
        step is in it) and its section, or -- a step with no shot -- Pair it
        with a shot no step pairs with."""
        pairing = self._pairing()
        shot = pairing.shots.get(step.step_id)
        if shot is None and self._source != "csv":
            return  # only a sheet leaves a shot unpaired
        menu.addSeparator()
        if shot is None:
            self._add_pair_menu(
                menu,
                f"Pair '{step.shot_name}' with Shot",
                self._orphan_shots(pairing),
                lambda target: self._pair_shot(target, step),
                "No shot is free: every shot pairs with a step.",
            )
            return
        chosen = list(selected) if step.step_id in selected else [step.step_id]
        built = [sid for sid in chosen if sid in pairing.shots]
        locked = shot.locked
        verb = "Unlock" if locked else "Lock"
        label = f"'{step.shot_name}'" if len(built) == 1 else f"{len(built)} Steps"
        act = menu.addAction(
            f"{verb} {label}", lambda: self._set_locked(built, not locked)
        )
        act.setToolTip(
            "Locked: final -- Build never changes its shot, and its row takes no\n"
            "Local Edits. Unlock to revise it, then lock it again."
        )
        if step.section:
            section = [s.step_id for s in self._steps if s.section == step.section]
            for verb, value in (("Lock", True), ("Unlock", False)):
                menu.addAction(
                    f"{verb} Section '{step.section}'",
                    lambda v=value: self._set_locked(section, v),
                )

    def _add_pair_menu(self, menu, title, candidates, pair, empty_tip) -> None:
        """A *title* submenu with an entry per candidate (steps or shots),
        calling ``pair(candidate)``; steps go under their sections once they
        are many.  Disabled with *empty_tip* when there are none."""
        sub = menu.addMenu(title)
        sub.setToolTipsVisible(True)
        if not candidates:
            sub.setEnabled(False)
            sub.menuAction().setToolTip(empty_tip)
            return
        sub.menuAction().setToolTip(
            "Make that the step's shot: Build then updates the shot from the step\n"
            "and keeps its name."
        )
        sections: Dict[str, list] = {}
        for c in candidates:
            sections.setdefault(getattr(c, "section", "") or "", []).append(c)
        grouped = len(candidates) > 15 and len(sections) > 1
        for section, items in sections.items():
            target = sub.addMenu(f"Section {section}") if grouped else sub
            for c in items:
                label = getattr(c, "shot_name", None) or c.name
                desc = (getattr(c, "description", "") or "").strip()
                if len(desc) > 48:
                    desc = desc[:47] + "…"
                if desc:
                    label += "  —  " + desc
                target.addAction(label, lambda c=c: pair(c))

    def _row_above(self, item) -> str:
        """The ID of the step row nearest above *item*'s top-level row, ``""``
        when none is -- where a step added from that row goes."""
        from qtpy.QtCore import Qt

        tree = self.ui.tbl_steps
        top = item.parent() or item
        for i in range(tree.indexOfTopLevelItem(top) - 1, -1, -1):
            data = tree.topLevelItem(i).data(0, Qt.UserRole)
            if isinstance(data, BuilderStep):
                return data.step_id
        return ""

    def _pair_shot(self, shot, step) -> None:
        """Make *shot* *step*'s shot (``ShotManifest.bind``): one undo step;
        Build then updates it from the step and keeps its name."""
        with self._edit_store("manifest_pair_shot") as store:
            self._manifest(store).bind(shot, step.step_id)
        self._redraw(reassess=True)
        self._set_footer(
            f"'{shot.name}' is now the shot of step '{step.shot_name}' -- Build "
            "updates it from the step."
        )

    def _set_locked(self, step_ids, locked: bool) -> None:
        """Lock (or unlock) the shots of *step_ids* -- final: Build leaves a
        locked shot as it is and its row takes no Local Edits.  One undo step;
        a step with no shot has nothing to lock."""
        pairing = self._pairing()
        shots = [pairing.shots[sid] for sid in step_ids if sid in pairing.shots]
        changed = [shot for shot in shots if bool(shot.locked) != locked]
        if changed:
            with self._edit_store("manifest_lock") as store:
                for shot in changed:
                    store.update_shot(shot.shot_id, locked=locked)
            self._redraw(reassess=True)
        verb = "lock" if locked else "unlock"
        footer = f"{verb.title()}ed {len(changed)} shot(s)."
        unbuilt = len(step_ids) - len(shots)
        if unbuilt:
            footer += f" {unbuilt} step(s) have no shot to {verb}."
        self._set_footer(footer)

    @staticmethod
    def _copy_names(names) -> None:
        """Put *names* on the clipboard, one per line."""
        from qtpy.QtWidgets import QApplication

        QApplication.clipboard().setText("\n".join(names))

    @staticmethod
    def _reveal_targets(obj_names, find) -> Tuple[List[str], List[str]]:
        """``(nodes, notes)``: every scene node *obj_names* answer to (*find*:
        name -> nodes), in order, and a footer note for each name answering to
        several (all selected, so the duplicates can be found and renamed) or
        to none."""
        nodes, missing, shared = [], [], []
        for name in obj_names:
            hits = find(name)
            if not hits:
                missing.append(f"'{name}'")
            elif len(hits) > 1:
                shared.append(f"'{name}' ({len(hits)})")
            nodes.extend(h for h in hits if h not in nodes)
        notes = []
        if shared:
            notes.append(f"Several nodes share {', '.join(shared)}: all selected.")
        if missing:
            notes.append(f"{', '.join(missing)} not found in scene.")
        return nodes, notes

    def _show_in_outliner(self, obj_names) -> None:
        """Select every node *obj_names* answer to and reveal them in the
        host's Outliner (``ManifestHost.find_nodes`` / ``reveal``); what could
        not be (missing, shared, unrevealable) is said on the footer
        (:meth:`_reveal_targets`)."""
        if not self.manifest_host.available():
            return
        store = self._active_store()
        nodes, notes = self._reveal_targets(
            obj_names, lambda name: self.manifest_host.find_nodes(name, store)
        )
        if nodes:
            notes += self.manifest_host.reveal(nodes)
        if notes:
            self._set_footer(" ".join(notes), color=ERROR_COLOR)

    def _open_in_shot_sequencer(self, step_id: str) -> None:
        """Open the Shot Sequencer UI and navigate to the shot matching *step_id*.

        The sequencer controller lazily wraps ``ShotStore.active()`` via
        its ``sequencer`` property — no manual wiring needed here.
        """
        store = self._store_cls().active()
        if not store.shots:
            self._set_footer("Build shots first before opening the sequencer.")
            return
        self._open_shot_in_sequencer(self._pairing().shots.get(step_id))

    def _open_shot_in_sequencer(self, target) -> None:
        """Open the Shot Sequencer on shot *target* (``None``: as it is)."""
        self.sb.handlers.marking_menu.show("shot_sequencer")

        seq_slots = self.sb.get_slots_instance("shot_sequencer")
        if seq_slots is None:
            return

        controller = getattr(seq_slots, "controller", None)
        if controller is None:
            return

        # Clear stale session state so prior shifted-out keys
        # and cached segments don't suppress the new display.
        controller._shifted_out_keys.clear()
        controller._segment_cache.clear()
        controller._sync_combobox()

        cmb = getattr(seq_slots.ui, "cmb_shot", None)
        if cmb is not None and target is not None:
            for i in range(cmb.count()):
                shot_id = cmb.itemData(i)
                if shot_id == target.shot_id:
                    cmb.blockSignals(True)
                    cmb.setCurrentIndex(i)
                    cmb.blockSignals(False)
                    controller._sync_to_widget(shot_id, frame=True)
                    controller._update_shot_nav_state()
                    break

    #: The Render Effects page each recipe effect is keyed from, and the verb
    #: its row entry reads with.
    EFFECT_PAGES = {
        "fade_in": ("opacity", "Fade"),
        "fade_out": ("opacity", "Fade"),
        "pulse": ("highlight", "Highlight"),
    }

    def _effect_pages(self, obj) -> list:
        """``[(channel, verb)]`` -- the Render Effects pages *obj*'s behaviors
        are keyed from, each once, in behavior order."""
        pages = []
        for behavior in obj.behaviors or ():
            page = self.EFFECT_PAGES.get(self.behaviors.effect_of(behavior))
            if page is not None and page not in pages:
                pages.append(page)
        return pages

    def _open_effect(self, step_id: str, obj, channel: str) -> None:
        """Open Render Effects focused on *obj*'s *channel* effect.

        The picker hides and the header names the object and its step; the
        object is selected. Once its step is built, the panel's Key re-applies
        the object's behaviors where the build places them
        (:meth:`_reapply_behavior`) -- the recipe the page edits is the one
        that keys them.
        """
        store = self._active_store()
        node = store.resolve_member(obj.name)[0] if store is not None else obj.name
        leaf = str(node).split("|")[-1].split(":")[-1]
        self.sb.handlers.marking_menu.show("render_effects")
        slots = self.sb.get_slots_instance("render_effects")
        if slots is None or not hasattr(slots, "focus"):
            return
        apply = None
        if self._pairing().shots.get(step_id) is not None:

            def apply():
                # Raises why not: Render Effects reports it, not "Re-applied".
                self._reapply_behavior(step_id, obj, raise_errors=True)
                return f"Re-applied {leaf}'s behaviors in {step_id}."

        slots.focus(
            channel,
            [node],
            title=f"{leaf} \u00b7 {step_id}",
            apply=apply,
            apply_text=f"Apply to '{leaf}' in {step_id}" if apply else "",
        )

    def _open_audio_clip(self, name: str) -> None:
        """Open Audio Clips on *name*'s track."""
        self.sb.handlers.marking_menu.show("audio_clips")
        slots = self.sb.get_slots_instance("audio_clips")
        if slots is not None and hasattr(slots, "select_track"):
            slots.select_track(name)

    def _open_in_shots(self, step_id: str) -> None:
        """Open the Shots editor UI and navigate to the shot matching *step_id*."""
        store = self._store_cls().active()
        if not store.shots:
            self._set_footer("Build shots first before opening the shots editor.")
            return

        shot = self._pairing().shots.get(step_id)
        if shot is None:
            self._set_footer(f"No shot pairs with '{step_id}' yet.")
            return
        self._open_shot_in_shots(shot)

    def _open_shot_in_shots(self, shot) -> None:
        """Open the Shots editor on *shot*."""
        store = self._store_cls().active()
        self.sb.handlers.marking_menu.show("shots")

        # set_active_shot fires ActiveShotChanged which the ShotsController
        # listener handles — it syncs the combobox and editor fields.
        store.set_active_shot(shot.shot_id)
