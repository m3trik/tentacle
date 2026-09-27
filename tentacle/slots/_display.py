# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``display`` panels.

The Display expandable list (header row, tree build, leaf dispatch body).
"""


class DisplayMixin:
    """Shared ``display`` panel behavior. Mixed in ahead of the DCC Slots base."""

    def _dispatch_display_item(self, item):
        """The Display list's ``list000`` body: run a leaf's handler (named in the
        fork's ``_LIST000_ITEMS``) and report the state it returns. Category rows
        are navigation only. The forks keep the handler itself: its ``@Signals``
        decorator is evaluated in the class body."""
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, handler_name in self._LIST000_ITEMS.get(parent, ()):
            if label == text:
                handler = getattr(self, handler_name, None)
                if callable(handler):
                    msg = handler()
                    if msg:
                        self.sb.message_box(msg)
                return

    def header_init(self, widget):
        """Header menu: the submenu's Display expandable list — hover a row to
        fan its flyout right (the shared list000_init applies the hover_menu
        preset here)."""
        # List leaves are one-shot actions — dismiss the menu once one is
        # triggered (category rows only navigate).
        widget.menu.hide_on_trigger = True
        widget.menu.add(
            self.sb.registered_widgets.ExpandableList, setObjectName="list000"
        )

    def list000_init(self, widget):
        """Initialize Display expandable list (categories → actions)."""
        widget.fixed_item_height = 18
        widget.apply_preset(
            "expand_overlay_left" if widget.ui.has_tags("submenu") else "hover_menu"
        )

        root = widget.add("Display")

        for category, items in self._LIST000_ITEMS.items():
            cat = root.sublist.add(category)
            cat.sublist.add([label for label, _ in items])
