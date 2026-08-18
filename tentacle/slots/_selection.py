# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``selection`` panels.

Two subsystems live here:

* the **Convert To** list (``list001``): a root row whose flyout is one row per
  component category (Verts, Edges, Faces, UV's, Shell), each of which both
  converts on click AND fans out its related conversions on hover (Verts →
  Vertex Faces / Vertex Perimeter, …). Same on the panel (a hover-menu row
  under the header) and the submenu (an ``expand_overlay`` flyout). The grouping
  is one table here (``_CONVERT_TO_GROUPS``); the ops are the fork's flat
  ``_CONVERT_TO_OPS`` table, which is what the leaves dispatch back into. Only
  that table differs per DCC (Maya has two component types Blender lacks —
  ledgered in ``docs/parity_map.py``); the list plumbing is identical.
* the **selection-constraint icon row** (``b002``–``b007``): six icon-only
  buttons replacing the one-at-a-time ``cmb005`` combo, so more than one
  constraint can be enabled together. The row's identity — which button is
  which constraint, its glyph, its label — is one table here so the two forks
  can't drift; what a press *does* is the fork's (Maya toggles a persistent
  ``polySelectConstraint`` flag, Blender expands the current selection once —
  it has no drag-select constraint to leave on).
"""


class SelectionMixin:
    """Shared ``selection`` panel behavior. Mixed in ahead of the DCC Slots base."""

    # ------------------------------------------------------------------ hooks
    #: Convert To: ``{label: callable}`` in display order. The fork defines it;
    #: keys are the list rows, so the table IS the menu — no separate item
    #: list to keep in step with the dispatch. How an entry is invoked is the
    #: fork's :meth:`_run_convert_to`.
    _CONVERT_TO_OPS = {}

    #: Convert To menu shape: ``{category: (member, ...)}`` in display order.
    #: A category is itself a table key (clicking "Verts" converts to verts);
    #: hovering it fans out its members. Shared by both forks — the shape is
    #: DCC-neutral; a member a fork's table lacks is simply not shown, and a
    #: category a fork's table lacks (Blender has no "UV's" component) is a
    #: navigation-only header for the members it does have.
    _CONVERT_TO_GROUPS = {
        "Verts": ("Vertex Faces", "Vertex Perimeter"),
        "Edges": (
            "Edge Loop",
            "Edge Ring",
            "Contained Edges",
            "Edge Perimeter",
            "Border Edges",
        ),
        "Faces": ("Face Path", "Contained Faces", "Face Perimeter"),
        "UV's": ("UV Shell", "UV Shell Border", "UV Perimeter", "UV Edge Loop"),
        "Shell": ("Shell Border",),
    }

    def _run_convert_to(self, label, op):
        """Invoke Convert To entry *op* (from ``_CONVERT_TO_OPS``) for *label*.

        Default: ``op(self)`` — the entry receives the slot instance. A fork
        whose entries need more (Blender resolves the edit-mode mesh first and
        hands it in) overrides this; the table's call convention and its
        runner then live side by side in that fork.
        """
        op(self)

    # ---------------------------------------------------- selection constraints
    #: The constraint row, in .ui order: ``objectName -> (icon, label)``.
    #: objectNames are persisted / parity keys — never renumber them. Both
    #: forks read this for the glyph and the human name; each fork's
    #: ``b00X_init`` / ``b00X`` bodies decide the DCC behavior.
    _CONSTRAINT_BUTTONS = {
        "b002": ("angle", "Angle"),
        "b003": ("border", "Border"),
        "b004": ("edge_loop", "Edge Loop"),
        "b005": ("edge_ring", "Edge Ring"),
        "b006": ("shell", "Shell"),
        "b007": ("uv_edge_loop", "UV Edge Loop"),
    }

    #: What a press does in this DCC — the one line the fork appends to every
    #: constraint tooltip. Override in the fork.
    _CONSTRAINT_ACTION_HINT = ""

    #: Glyph extent for the row: a 16px icon in the 19px-high buttons the .ui
    #: declares (the header's own 3px-margin rule). A constant rather than a
    #: ``fit_icon`` read of the button's height, which is Qt's 16777215 default
    #: on any button not yet capped by a .ui — a gigantic rasterization.
    _CONSTRAINT_ICON_SIZE = 16

    def _constraint_label(self, widget):
        """The human name of the constraint *widget* stands for (``"Angle"``, …)."""
        return self._CONSTRAINT_BUTTONS[widget.objectName()][1]

    def _init_constraint_button(self, widget):
        """Dress a constraint row button: themed glyph, empty text, tooltip.

        Icon-only by design — six buttons share a 200px panel row, so the label
        lives in the tooltip. Called from each fork's ``b00X_init``.
        """
        icon, label = self._CONSTRAINT_BUTTONS[widget.objectName()]
        widget.setText("")
        self.sb.IconManager.set_icon(widget, icon, size=self._CONSTRAINT_ICON_SIZE)
        hint = f"\n{self._CONSTRAINT_ACTION_HINT}" if self._CONSTRAINT_ACTION_HINT else ""
        widget.setToolTip(f"Selection constraint: {label}.{hint}")

    # ------------------------------------------------------------- Convert To
    def list001_init(self, widget):
        """Convert To: category rows that convert on click and expand on hover.

        ``expand_overlay`` in the submenu: the category flyout covers the
        "Convert To" row itself (top row aligned to it, at least as wide as
        it) and grows downward — the row sits below the radial center — with
        each category's members fanning right; ``hover_menu`` in the panel,
        where the row is a layout-managed header menu that fans right on
        hover. Shape from :attr:`_CONVERT_TO_GROUPS`, filtered to what the
        fork's :attr:`_CONVERT_TO_OPS` actually provides.
        """
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay" if widget.ui.has_tags("submenu") else "hover_menu"
        )
        root = widget.add(
            "Convert To",
            setToolTip="Convert the component selection to another component type.",
        )
        ops = self._CONVERT_TO_OPS
        for category, members in self._CONVERT_TO_GROUPS.items():
            members = [m for m in members if m in ops]
            if category not in ops and not members:
                continue
            if category in ops:
                tip = f"Click: convert to {category}."
                if members:
                    tip += " Hover: related conversions."
            else:
                tip = f"{category} conversions."
            row = root.sublist.add(category, setToolTip=tip)
            if members:
                row.sublist.add(members)

    def _dispatch_convert_to(self, item):
        """Run the conversion a Convert To row names (the forks' ``list001`` body).

        Any row whose label is a table key runs — a category row ("Verts") as
        much as a leaf ("Vertex Faces"); the root ("Convert To") and a
        category the fork's table lacks are navigation only because they have
        no entry, not because they carry a sublist. The forks keep the ``list001`` method
        itself: its ``@Signals`` decorator is evaluated in the class body, and
        the decorator is re-exposed on the DCC ``Slots`` base precisely so the
        slots layer never imports uitk directly (see ``slots/_slots.py``).
        """
        label = item.item_text()
        op = self._CONVERT_TO_OPS.get(label)
        if op is not None:
            self._run_convert_to(label, op)
