# !/usr/bin/python
# coding=utf-8
from qtpy import QtCore


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    #: One-shot guard so the legacy repeat-last migration runs once per process,
    #: not on every slot instantiation (the base ``__init__`` runs for every
    #: slot class).
    _legacy_repeat_last_migrated = False

    def __init__(self, switchboard):
        super().__init__()
        self.sb = switchboard

        # Repeat-last is the unified uitk ``repeat_last_command`` command now —
        # registered by the Switchboard and bound ONCE to an always-visible host.
        # The old path created an application-scoped QShortcut here in every slot
        # instance's __init__, so N loaded UIs stacked N identical Ctrl+Shift+R
        # shortcuts on the (normally hidden) marking menu; Qt saw an ambiguous
        # overload and fired none. Fold any customized legacy key into the command
        # once, then never again.
        if not Slots._legacy_repeat_last_migrated:
            Slots._legacy_repeat_last_migrated = True
            try:
                self._migrate_legacy_repeat_last(switchboard)
            except Exception:
                pass  # best-effort; a migration hiccup must never block slot init

    @staticmethod
    def mirror_app_state(widget, seed=None) -> None:
        """Declare that *widget*'s value mirrors live DCC state, optionally seeding it.

        For a widget whose value **is** app state — the active tool, symmetry flags, snap
        settings, working units — the DCC owns the truth, not QSettings. Restoring a stored
        value over the live one is wrong twice: the widget misreports the app, and the
        restore *re-fires the slot* (``StateManager.apply`` unblocks signals per
        ``block_signals_on_restore``, which defaults False), so the command runs — and pops
        its confirmation ``message_box`` — on nothing more than the panel opening.

        ``seed`` runs with signals blocked for the same reason: reading state out of the DCC
        is not the user editing it. ``init_slot`` blocks only the widget it is initializing,
        so a ``*_init`` that seeds its *siblings* (a radio group) fires their slots without
        this. It is a callable rather than a value because only the caller knows what its
        value means for its widget — an int is an index to a combo but a level to a spinbox,
        a distinction ``ValueManager.set_value`` resolves text-first and so gets wrong.

        Call from the widget's ``*_init``: slot init (phase 1) runs before state restore
        (phase 2), which skips the widget entirely once ``restore_state`` is False. Each
        widget must be marked by its OWN ``*_init``, never by a sibling's — the deferred
        path batches all of phase 1 before phase 2 and would forgive it, but ``init_slot``
        runs the two phases per widget, so a sibling's mark can land after this widget has
        already restored.

        Parameters:
            widget (QWidget): The widget to mark. Never persisted or restored afterwards.
            seed (callable, optional): Zero-arg callable applying the live DCC value.
                Omit for state with no readable analogue — the .ui default stays put.
        """
        if seed is not None:
            was_blocked = widget.blockSignals(True)
            try:
                seed()
            finally:
                widget.blockSignals(was_blocked)
        # Marked AFTER the seed, never before: a seed that *populates* re-arms the flag —
        # ``ComboBox.add`` ends with ``restore_state = not self.has_header``, so a headerless
        # combo seeded by its own ``add`` would silently opt itself back IN to persistence.
        widget.restore_state = False

    def add_slot_widget(self, sublist, widget_class=None, **kwargs):
        """Add a slot-wired widget as an ExpandableList sublist entry.

        ``ExpandableList.add`` accepts real widgets but leaves them inert — nothing
        wires the objectName to its slot, runs its ``*_init``, or binds ``ui.<name>``.
        This adds the widget and then registers it with the list's MainWindow (the
        same path ``Menu.add`` uses for dynamic items), which does all three.

        The add-then-register ORDER is load-bearing, not stylistic: adding reparents
        the widget into the sublist's layout, and uitk only wraps an option box
        synchronously while ``parent()`` is set (the
        ``OptionBoxManager._schedule_wrap_if_needed`` fast path). Registered while
        unparented, an ``*_init`` that configures an option box would defer its wrap
        to a retry timer and the gear would be missing from the first paint. With the
        order kept, the wrap completes inside the ``*_init`` and the entry is fully
        built by the time this returns — no post-hoc ``option_box.container`` nudge
        needed (that access is a no-op by then).

        The wrap has a second consequence worth knowing: it replaces the widget with
        its container in the list's layout, so the widget leaves ``get_items()`` and
        the list stops consuming its mouse releases — its own ``clicked`` drives its
        slot, and it never reaches the list's ``on_item_interacted`` handler. A widget
        with NO option box stays in the item set, where the list consumes the release
        and ``clicked`` never fires; dispatch those from the list's handler instead.

        Parameters:
            sublist (ExpandableList): The sublist to add the widget to.
            widget_class (type, optional): Widget class to instantiate. Defaults to
                the registered uitk PushButton (menu / option-box capable).
            **kwargs: Widget attributes (``setObjectName`` names the slot and is
                required for registration; ``setText``, ``setToolTip``, ...).

        Returns:
            QWidget: The added, registered widget.
        """
        widget_class = widget_class or self.sb.registered_widgets.PushButton
        widget = widget_class()
        sublist.add(widget, **kwargs)
        # The root list is the .ui-declared widget carrying the MainWindow binding;
        # sublists are reparented to the window and never registered themselves.
        root_list = getattr(sublist, "root_list", sublist)
        root_list.ui.register_widget(widget)
        return widget

    def toggle_camera_view(self):
        """Toggle between the last two viewport-camera views in slot history.

        DCC-agnostic switchboard logic shared by the Maya and Blender ``Cameras``
        slots (the only slots that define the ``b000``-``b007`` viewport-camera
        methods it drives): if the last view was perspective (``b004``) it
        restores the previous non-perspective view, otherwise it switches to
        perspective — reading and re-appending the switchboard's ``slot_history``
        so repeated triggers alternate. A no-op until a camera view has been used
        (empty history). Lives on the shared base so both DCC cameras slots
        inherit ONE implementation; wired to its triggers by
        :meth:`register_camera_view_toggle`.
        """
        slots = self.sb.get_methods_by_string_pattern(self, "b000-7")
        # The last two camera-view slots in history (most recent last).
        history = self.sb.slot_history(slice(-2, None), inc=slots)
        if not history:
            return

        # If the last view was perspective (b004), restore the prior non-persp
        # view; otherwise switch to perspective.
        if history[-1].__name__ == self.b004.__name__:
            if len(history) < 2:
                return
            last_non_persp_cam = history[-2]
            last_non_persp_cam()
            self.sb.slot_history(add=last_non_persp_cam)
        else:
            self.b004()
            self.sb.slot_history(add=self.b004)

    def register_camera_view_toggle(self):
        """Wire :meth:`toggle_camera_view` to its triggers. Call once from a
        cameras slot's ``__init__`` (the only slots defining ``b000``-``b007``).

        Two independent trigger paths, by design:

        * the **double-click gesture** inside the marking menu (the historical
          default) — connected to the menu's ``left_mouse_double_click`` signal
          (the marking menu registers itself as ``sb.handlers.marking_menu`` in
          its ``_setup_registry``); and
        * a **keyable command** (``toggle_camera_view``) surfaced in the shortcut
          editor alongside the other marking-menu actions (``marking_menu_show``,
          ``repeat_last_command``), shipped **unbound** so the double-click stays
          the default while the user can also assign a key.

        Idempotent per process: the command-presence guard makes a slot rebuild
        (or a second cameras instance) a no-op, so neither the command nor the
        double-click connection is duplicated. Degrades to a no-op on a
        switchboard predating ``register_command`` (older uitk / a test double).
        """
        sb = self.sb
        # Already wired this process (slot rebuild / a second cameras instance).
        if "toggle_camera_view" in getattr(sb, "_commands", {}):
            return

        # 1. Double-click gesture — the historical default trigger.
        marking_menu = getattr(getattr(sb, "handlers", None), "marking_menu", None)
        if marking_menu is not None:
            marking_menu.left_mouse_double_click.connect(self.toggle_camera_view)

        # 2. Keyable command — listed and user-bindable in the shortcut editor.
        register_command = getattr(sb, "register_command", None)
        if register_command is not None:
            register_command(
                "toggle_camera_view",
                callback=self.toggle_camera_view,
                label="Toggle Camera View",
                doc="Toggle between the perspective and last orthographic "
                "viewport view. Default trigger: double-click inside the "
                "marking menu.",
                sequence="",  # unbound: the double-click is the default trigger
                scope="application",
            )

    @staticmethod
    def _migrate_legacy_repeat_last(sb) -> None:
        """Fold the retired ``configurable.repeat_last_shortcut`` into the unified
        ``repeat_last_command`` command, then delete the legacy key.

        The command ships **unbound** (no default key), so:

        - Key absent (the common case — user never customized it): no-op;
          repeat-last stays unbound until assigned in the editor.
        - Key present and different from the command default (``""``): preserve
          the user's choice as a command override — including a user who carried
          the *old* ``Ctrl+Shift+R`` default, so the "no default" change never
          yanks a working shortcut out from under them.
        - Key present and equal to the default (``""`` — explicitly disabled):
          retire it without writing a redundant override; the unbound default
          already yields the same result.

        Idempotent: the legacy key is cleared afterward, so a later session finds
        nothing to migrate.
        """
        legacy = sb.configurable.repeat_last_shortcut.get(None)
        if legacy is None:
            return  # never customized — repeat-last stays unbound
        reg = {e["method"]: e for e in sb.get_command_registry()}
        entry = reg.get("repeat_last_command")
        if entry is None:
            # The migration target isn't registered (shouldn't happen — it's a
            # built-in). Keep the legacy key rather than clearing it into the
            # void, so the user's value isn't silently lost.
            return
        if legacy != entry.get("default"):
            sb.set_command_shortcut("repeat_last_command", legacy, "application")
        sb.configurable.clear("repeat_last_shortcut")


# --------------------------------------------------------------------------------------------

# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
