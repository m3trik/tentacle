# !/usr/bin/python
# coding=utf-8
"""Shared, DCC-agnostic behavior for the ``materials`` panel.

The per-panel home for logic the Maya and Blender ``MaterialsSlots`` forks share (mixed in
ahead of their ``SlotsMaya`` / ``SlotsBlender`` base). Grow this class rather than adding a
new module per feature — see the convention in ``tentacle/CLAUDE.md``.

Currently: the prefix/suffix affix option box on the materials-combo "Rename" label.
The "Rename" label (``lbl005``) in the materials combo's (``cmb002``) right-click context
menu carries an **option box** (gear) whose dropdown — built with no apply button, so the
field's Enter key is the commit — holds two controls:

- ``cmb_rename_mode``: how the affix text joins the material name —
  **Auto** (the underscore edge picks the side: ``_lod0`` -> ``mat_lod0``,
  ``metal_`` -> ``metal_mat``), **Prefix** (prepend: ``metal`` -> ``metal_mat``),
  or **Suffix** (append: ``lod0`` -> ``mat_lod0``).
- ``txt000``: the affix text; press Enter to apply.

The option-box build, the join/validation (:meth:`_join_affix`), and the ``lbl005`` handler
are identical across DCCs. Only the rename itself forks, delegated to each slot's
``_rename_current(text)`` hook (Maya ``cmds.rename`` / Blender datablock assignment), which
must return the resulting name on success or a falsy value on failure so the field is
cleared only when the rename actually happened.

Also: the submenu's ``b003`` "Get + Select" one-shot — get the material off the current
selection, then select every object using it. It carries no options of its own; it calls
each slot's ``select_by_mat(shell, in_selection, get_first, add, unassigned)`` hook (the
parameterized primitive that also backs the main panel's option-box-driven ``tb000``) with
fixed values,
so the two entry points share one implementation without either reading — or temporarily
overwriting — the other's persisted option-box state.

And the "get the material off the selection" half of that, :meth:`_adopt_selection_mat` —
shared by "Get Material" (``b002``) and ``select_by_mat``'s ``get_first``, which differ
only in their message when the selection can't yield exactly one material. Its DCC hook is
``_selection_mats()``: the material NAMES on the selection, or ``None`` when nothing is
selected (Maya ``mtk.MatUtils.get_mats`` / Blender ``btk.get_mats``). An empty list means
"selected, but nothing assigned" — the case ``b003`` turns into an unassigned search
(``select_by_mat(unassigned=True)``, which bypasses ``cmb002``: "no material" is not a
material and must never become the current one, since ~24 call sites feed
``cmb002.currentData()`` straight to delete / assign / graph / rename).

Plus :meth:`_refresh_assign_lists`, the "current material changed" fan-out both forks
wire ``cmb002``'s ``currentIndexChanged`` / ``on_editing_finished`` to, and
:meth:`_assign_root_text`, the root row those lists are built from. The Assign list
(``list000``) exists on BOTH the panel and the submenu, so a refresh that reached only
one surface left the other advertising — and appearing to offer — a stale material. The
root row itself is worded per surface: the submenu, which floats free of the panel,
names the current material ("Assign: <mat>"); the panel's own list sits directly under
``cmb002`` and so states the action alone ("Assign Current").

A material the combo can't represent is NOT assumed to be filtered: the adopt
path asks ``_list_filter_names()`` which list filters are actually enabled, and
when none are, adds the found material to the combo and adopts it — the list not
carrying a material assigned to the selection is the list's limitation, not a
reason for "Get Material" to fail.

Hooks each ``<Panel>Slots`` fork must supply: ``_rename_current(text)``,
``select_by_mat(...)``, ``_selection_mats()``. Optional:
``_list_filter_names()`` (defaults to no filters).
"""
import pythontk as ptk


class MaterialsMixin:
    """DCC-agnostic ``materials`` slot behavior.

    ``cmb002`` "Rename" label (``lbl005``) + its prefix/suffix affix option box,
    the submenu's ``b003`` "Get + Select" one-shot, and the shared
    adopt-the-selection's-material path behind ``b003`` / ``b002``.
    """

    #: Affix modes offered by ``cmb_rename_mode`` (index 0 is the default).
    _RENAME_MODES = ("Auto", "Prefix", "Suffix")

    def _assign_root_text(self, widget):
        """Root-row label for the Assign list (``list000``) hosted by *widget*.

        The two surfaces need different labels because they carry different
        context. The submenu floats free of the panel, so its root row is the
        only thing there naming what a release will assign: "Assign: <material>".
        The panel's own list sits directly under ``cmb002``, which already shows
        that name — repeating it made the row a second, redundant statement of
        the same fact (and a wider one, since the row grows with the name), so
        there it reads simply "Assign Current" and the combo stays the single
        place the material is named.

        Both forks build their root from this, so the panel/submenu split lives
        in one place rather than being re-decided per DCC.

        The submenu names the material by its LEAF, matching what ``cmb002``
        displays (its item text is the leaf, its data the full name — see
        :meth:`_adopt_selection_mat`): the row mirrors the combo, so it must not
        spell the same material differently.
        """
        if not widget.ui.has_tags("submenu"):
            return "Assign Current"
        current = self.ui.cmb002.currentData()
        return f"Assign: {ptk.HierarchyPath.leaf(str(current))}" if current else "Assign"

    def _refresh_assign_lists(self, *_):
        """Re-init the Assign list (``list000``) on every surface that carries one.

        BOTH the main panel and the submenu host a ``list000``, while ``cmb002``
        lives only on the panel — so a refresh must reach both. The submenu's
        root row names the current material (see :meth:`_assign_root_text`) and
        goes stale the moment the combo changes; the panel's rows are the scene's
        materials, which change under :meth:`_refresh_material_lists`. Refreshing
        one surface only (the original wiring, submenu-first) left the other
        built against a material set / current material that had moved on.

        Connected straight to ``currentIndexChanged(int)`` /
        ``on_editing_finished(str)``, hence the swallowed signal args. A surface
        without a ``list000`` is skipped rather than assumed.
        """
        for ui in (self.ui, self.submenu):
            widget = getattr(ui, "list000", None)
            if widget is not None:
                widget.init_slot()

    def _refresh_material_lists(self):
        """Re-populate every surface that mirrors the scene's material set.

        The panel's "the materials changed" signal — call it instead of a bare
        ``cmb002.init_slot()`` from anything that creates, deletes or renames a
        material. ``cmb002`` is not the only widget listing them: each Assign
        list (``list000``) carries a row per scene material, so a combo-only
        refresh left rows naming materials that no longer exist. Clicking one
        then failed at the far end of the assign — loudly in Maya ("Assign
        failed": ``assign_mat`` raises on a missing node) and silently in
        Blender (``_resolve_material`` returns None and the handler just
        returns) — which reads as a dead menu row rather than a stale one.

        Combo first: the lists' root row is built from ``cmb002.currentData()``,
        so it must be re-resolved against the new material set before the lists
        rebuild off it. ``init_slot`` blocks the combo's own signals while it
        re-populates, so this does not double up with the
        ``currentIndexChanged`` -> :meth:`_refresh_assign_lists` connection.
        """
        self.ui.cmb002.init_slot()
        self._refresh_assign_lists()

    def _add_rename_control(self, menu):
        """Add the "Rename" label with its affix option box to *menu*.

        The label (``lbl005``) auto-wires to the slot method of the same name; its
        option-box dropdown carries the affix field (on top) + a mode combo below.
        No apply button — the affix commits when the field's Enter is pressed or
        the "Rename" label is clicked while the field holds text (:meth:`lbl005`).
        """
        lbl005 = menu.add(
            self.sb.registered_widgets.Label,
            setText="Rename",
            setObjectName="lbl005",
            setToolTip=(
                "Rename the current material. Type an affix in the option box (gear) "
                "to prefix/suffix instead — press Enter or click Rename to apply."
            ),
        )

        # No apply / restore-defaults buttons — commit is Enter / the label click.
        lbl005.option_box.enable_menu(add_apply_button=False, add_defaults_button=False)
        obox = lbl005.option_box.menu
        obox.setTitle("Rename Affix")
        # Affix field on top (primary), the mode selector below it.
        obox.add(
            "QLineEdit",
            setObjectName="txt000",
            setPlaceholderText="affix (Enter to apply)",
            setToolTip=(
                "Type an affix and press Enter (or click Rename) to prefix/suffix the "
                "current material name. In Auto mode the underscore edge picks the side."
            ),
        )
        obox.add(
            "QComboBox",
            setObjectName="cmb_rename_mode",
            setToolTip=(
                "How the affix text joins the material name:\n"
                "  Auto   — the underscore edge picks the side "
                "(_lod0 → mat_lod0, metal_ → metal_mat)\n"
                "  Prefix — prepend the text  (metal → metal_mat)\n"
                "  Suffix — append the text   (lod0 → mat_lod0)"
            ),
        )
        obox.cmb_rename_mode.addItems(list(self._RENAME_MODES))
        # Transient input — don't persist the typed affix across sessions
        # (registration defaults new widgets to restore_state=True).
        obox.txt000.restore_state = False
        obox.txt000.returnPressed.connect(self._apply_rename_affix)

        self._rename_affix = obox.txt000
        self._rename_mode_combo = obox.cmb_rename_mode

    @staticmethod
    def _join_affix(name, affix, mode):
        """Join *affix* onto *name* per *mode*, via ``ptk.StrUtils.apply_affix``.

        Returns the new name, or ``None`` when the input can't yield one: an Auto
        affix with an underscore on both edges or neither (no side to infer), or a
        Prefix/Suffix affix that is only underscores.

        Auto resolves the side from the underscore edge (leading ``_`` → suffix,
        trailing ``_`` → prefix). The actual join — a single ``_`` separator,
        idempotent, no dangling underscores — is pythontk's ``apply_affix``
        primitive; this method is only the UI's mode + rejection policy over it
        (edge underscores are stripped from the token, so ``metal`` and ``metal_``
        both give ``metal_<name>``).
        """
        if mode == "Auto":
            leading, trailing = affix.startswith("_"), affix.endswith("_")
            if leading == trailing:  # both edges or neither → can't infer a side
                return None
            mode = "Suffix" if leading else "Prefix"
        token = affix.strip("_")
        if not token:
            return None
        if mode == "Prefix":
            return ptk.StrUtils.apply_affix(name, prefix=f"{token}_")
        return ptk.StrUtils.apply_affix(name, suffix=f"_{token}")

    def _apply_rename_affix(self):
        """Apply the affix field to the current material using the selected mode.

        Reads the mode from ``cmb_rename_mode`` and the text from ``txt000``,
        joins them via :meth:`_join_affix`, and commits through the DCC slot's
        ``_rename_current`` hook. The field is cleared only on a successful
        rename (a failed/ rejected commit keeps the typed affix).
        """
        affix = self._rename_affix.text().strip()
        if not affix:
            return
        mat = self.ui.cmb002.currentData()
        if not mat:
            return

        name = ptk.HierarchyPath.leaf(str(mat))
        mode = self._rename_mode_combo.currentText()
        new_name = self._join_affix(name, affix, mode)
        if new_name is None:
            if mode == "Auto":
                self.sb.message_box(
                    "<hl>Ambiguous affix</hl><br>"
                    "In Auto mode, put one underscore on the joining edge: "
                    "leading '_' for a suffix (_lod0), trailing '_' for a prefix "
                    "(metal_). Or pick Prefix / Suffix from the option box."
                )
            else:
                self.sb.message_box(
                    f"<hl>Empty affix</hl><br>Enter some text to use as the {mode.lower()}."
                )
            return

        if self._rename_current(new_name):
            self._rename_affix.clear()

    def lbl005(self):
        """Rename the current material.

        With an affix typed in the option box, apply the prefix/suffix; otherwise
        make the combo editable for a full free-form rename. Clicking the label is
        the reliable commit for the affix (reading option-box values on the main
        widget's action is the established pattern) — the field's Enter key is a
        shortcut for the same. The context menu dismisses itself via
        ``hide_on_trigger`` (the label's option-box wrap is recognized as the
        triggered item), so no explicit hide is needed.
        """
        if self._rename_affix.text().strip():
            self._apply_rename_affix()
        else:
            self.ui.cmb002.setEditable(True)

    #: Why the selection can't yield one material -> (title, body) for the message box.
    _GET_MAT_FAILURES = {
        "empty": (
            "Nothing selected",
            "Select mesh object(s) or face(s) to get the material from.",
        ),
        "none": (
            "No material found",
            "The selected object has no material assigned.",
        ),
        "multiple": (
            "Multiple materials found",
            "The selected object has multiple materials assigned, so a single "
            "current material can't be determined.",
        ),
        "filtered": (
            "Material hidden by a list filter",
            "'{mat}' isn't in the materials list — it's hidden by the cmb002 "
            "option-box filter: {filters}. Turn that off to make it current.",
        ),
        "unlisted": (
            "Material not in the list",
            "'{mat}' is assigned to the selection but couldn't be made the "
            "current material — the materials list doesn't carry it.",
        ),
    }

    def _list_filter_names(self):
        """Names of the cmb002 list filters currently ENABLED (DCC hook).

        Only a filter that is actually on can be the reason a found material is
        missing from the list — reporting "a filter is hiding it" without
        checking sent the user to an option box whose boxes were already
        unchecked, while the real cause (a material the DCC's own material query
        doesn't report) went unnamed. Returning nothing means nothing is being
        filtered, which is what :meth:`_adopt_selection_mat` treats as license to
        adopt the material anyway.

        Default: no filters (Blender's combo has none). Maya overrides it.
        """
        return ()

    def _adopt_selection_mat(self, on_failure=""):
        """Set ``cmb002`` to the single material assigned to the current selection.

        Shared by "Get Material" (``b002``) and ``select_by_mat``'s ``get_first``,
        which differ only in what happens when the selection can't yield exactly
        one material: b002 stops there, get_first carries on with whatever material
        is current — hence ``on_failure``, appended to the reported reason.

        Only the lookup forks, via each slot's ``_selection_mats()`` hook: the
        material NAMES on the selection, or ``None`` when nothing is selected.

        Parameters:
            on_failure (str): Text appended to the failure message (e.g. what the
                caller does next).

        Returns:
            str | None: The adopted material name, or None (a message was shown).
        """
        mats = self._selection_mats()
        found = mats[0] if mats and len(mats) == 1 else ""

        filters = ()
        if found:
            previous = self.ui.cmb002.currentData()
            self.ui.cmb002.init_slot()  # refresh the list so the found material is in it
            if self._make_current(found):
                return found
            # ``ComboBox.setAsCurrent`` silently falls back to INDEX 0 for a
            # missing item, which would leave an unrelated material current and
            # select by it — so a miss is handled here rather than trusted.
            filters = tuple(self._list_filter_names())
            if not filters:
                # Nothing is filtering the list, so the material is simply one it
                # doesn't carry. It IS assigned to the selection and every
                # consumer of cmb002 works on the name, so add it and adopt it
                # rather than failing on a list that can't represent it.
                self.ui.cmb002.addItem(ptk.HierarchyPath.leaf(str(found)), found)
                if self._make_current(found):
                    return found
            # Put the previous material back, then report like any other failure.
            # Only an enabled filter may be blamed — otherwise the list simply
            # can't represent the material and the adopt-anyway above didn't take.
            if previous is not None:
                self.ui.cmb002.setAsCurrent(str(previous))
            reason = "filtered" if filters else "unlisted"
        else:
            reason = "empty" if mats is None else "none" if not mats else "multiple"

        # One report path, so ``on_failure`` (what the caller does next) is always
        # part of the message — a reason without it would misdescribe the outcome.
        title, body = self._GET_MAT_FAILURES[reason]
        self.sb.message_box(
            f"<hl>{title}</hl><br>"
            f"{body.format(mat=found, filters=' / '.join(filters))}{on_failure}"
        )
        return None

    def _make_current(self, mat):
        """Select *mat* in ``cmb002``; True only when it actually landed there.

        ``setAsCurrent`` falls back to index 0 for an item it can't find, so its
        return tells you nothing — the combo has to be read back.
        """
        mat = str(mat)
        self.ui.cmb002.setAsCurrent(mat)
        return str(self.ui.cmb002.currentData() or "") == mat

    def b003(self, widget=None):
        """Get + Select (submenu): adopt the selection's material, then select its users.

        A fixed one-shot — whole objects, whole scene, replacing the selection —
        so the submenu button does the same thing every time. The configurable
        form is the main panel's ``tb000`` with its option box; both run the same
        ``select_by_mat`` implementation.

        A selection with NO material takes the analogous branch rather than
        failing: "everything that matches this selection, material-wise" becomes
        every object that also has no material. Only a genuinely materialless
        selection routes there — an empty or multi-material selection still
        reports through the normal adopt path.

        Returns:
            list: whatever ``select_by_mat`` selected (see the DCC slot's hook).
        """
        if self._selection_mats() == []:  # selected, but nothing assigned
            self.sb.message_box(
                "<hl>No material on the selection</hl><br>"
                "Selecting the objects that have no material assigned."
            )
            return self.select_by_mat(shell=True, unassigned=True)
        return self.select_by_mat(shell=True, get_first=True)
