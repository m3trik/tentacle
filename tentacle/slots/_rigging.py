# !/usr/bin/python
# coding=utf-8
"""Behavior shared by the Maya and Blender ``rigging`` panels."""


class RiggingMixin:
    """Shared ``rigging`` panel behavior. Mixed in ahead of the DCC Slots base."""

    #: Euler orders, Maya-spelled and in its ``rotateOrder`` enum order; both
    #: hosts' ``create_locator_at_object`` take these names.
    ROTATE_ORDERS = ("xyz", "yzx", "zxy", "xzy", "yxz", "zyx")

    # ------------------------------------------------------------- DCC hooks
    def _selected_rotate_orders(self):
        """Return ``(node, label, rotate order)`` per selected transform, the
        order Maya-spelled (:attr:`ROTATE_ORDERS`)."""
        raise NotImplementedError

    def _set_rotate_orders(self, nodes, order):
        """Run the host's pose-keeping ``XformUtils.set_rotate_order`` on *nodes*
        (one undo step)."""
        raise NotImplementedError

    def _add_rotate_order_combo(self, menu):
        """Add Create Locator's ``cmb011`` rotate-order picker to *menu*, with
        its Fix Rotate Order action (:meth:`_fix_rotate_order`)."""
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb011",
            setToolTip=(
                "The locator's rotate order. Its FIRST letter is the axis the\n"
                "prop can spin about (in Object mode) through ONE channel at\n"
                "any pose. In xyz, once X is keyed (a prop lifted and tilted),\n"
                "a spin about the locator's own Z writes X, Y and Z.\n"
                "Pick the order whose first letter is the spin axis\n"
                "(zyx for a Z spin, yzx for Y, xyz for X), and whose middle\n"
                "letter is the axis it turns least: the order locks (gimbal)\n"
                "when the middle channel reaches 90.\n"
                "Not sure yet? Animate first, then press the sync button."
            ),
        )
        for order in self.ROTATE_ORDERS:
            cmb.addItem(f"Rotate Order: {order}", order)
        cmb.option_box.set_action(
            callback=self._fix_rotate_order,
            icon="sync",
            tooltip=self.sb.tooltip.fmt(
                title="Fix Rotate Order",
                body="Give each selected locator the rotate order its own keys "
                "turn in: the one that puts every keyed turn on a single "
                "channel. That is also what takes the wobble out of a keyed "
                "turn.",
                notes=[
                    "Every key keeps its pose; the curves are re-solved.",
                    "Unkeyed locators, and hinges every order serves alike, "
                    "are left alone.",
                ],
            ),
        )
        return cmb

    def _fix_rotate_order(self):
        """cmb011's action: re-solve each selected locator's rotate order from
        its keys (the host engine's ``set_rotate_order(order="auto")``)."""
        before = self._selected_rotate_orders()
        if not before:
            self.sb.message_box("Select the locator(s) whose rotate order to fix.")
            return
        self._set_rotate_orders([node for node, _label, _order in before], "auto")
        # Keyed by node, not label: two selected nodes can share a short name.
        after = {node: order for node, _label, order in self._selected_rotate_orders()}
        fixed = [
            f"{label}: {order} → {after[node]}"
            for node, label, order in before
            if after.get(node, order) != order
        ]
        kept = [label for node, label, order in before if after.get(node) == order]
        lines = (["<hl>Rotate order fixed:</hl>"] + fixed) if fixed else []
        if kept:
            lines.append(
                f"Unchanged ({', '.join(kept)}): no rotation keys, or every "
                "keyed turn is already one channel."
            )
        self.sb.message_box("<br>".join(lines))

    @staticmethod
    def _affix_arg(field):
        """``(text, mode)`` for an affix field, as the engine wants them.

        Scene mode reports ``(None, "auto")``: ``None`` is how the host's
        ``RigUtils.create_locator_at_object`` is told to take the shared
        convention's entry for that node type -- spelling AND placement -- so
        the mode argument beside it is moot. Every other state is the user's
        literal text placed as the picker says.
        """
        mode = field.option_box.affix_mode
        return (None, "auto") if mode == "convention" else (field.text(), mode)
