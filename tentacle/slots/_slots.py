# !/usr/bin/python
# coding=utf-8
import inspect

from qtpy import QtCore
from uitk import AttributeSpec, BridgeSlotsBase, Cancelable, ParamRegistry, Signals


class Slots(QtCore.QObject):
    """Provides methods that can be triggered by widgets in the ui.
    Parent to the 'Init' slot class, which is in turn, inherited by every other slot class.

    If you need to create a invokable method that returns some value, declare it as a slot, e.g.:
    @Slot(result=int, float)
    ex. def getFloatReturnInt(self, f):
                    return int(f)
    """

    #: uitk slot decorators, re-exposed on the base so concrete slot modules never
    #: import uitk themselves: ``@Slots.Signals("on_item_interacted")``,
    #: ``@Slots.Cancelable(120)``. ``BridgeSlotsBase`` rides along for the same
    #: reason: the app-bridge panels' shared base (``slots/tools/_app_bridge``)
    #: subclasses it, ``class HostBridge(Slots.BridgeSlotsBase)``.
    #:
    #: ``self.sb`` is the single uitk gateway for the slots layer, and it reaches
    #: the whole of uitk: any public symbol resolves off it directly
    #: (``self.sb.IconManager``, ``self.sb.RecentValuesStore`` — see
    #: ``uitk.switchboard.namespace``), the short names cover the rest
    #: (``self.sb.registered_widgets.X``, ``self.sb.style``), and its children carry
    #: their own APIs (``self.ui.footer.status_controller(...)``).
    #:
    #: These are the sole outliers: two class-body decorators, one base class and
    #: the two parameter-declaration types a standalone panel's registry is built
    #: from at import (``slots/tools/_<tool>/parameters.py``: ``Slots.AttributeSpec``
    #: rows in a ``Slots.ParamRegistry`` subclass), all evaluated while a module or
    #: a slot class is still being built, so no instance — and therefore no
    #: ``self.sb`` — exists yet. Hanging them off the base the module already
    #: imports is the only way to keep the gateway rule without a bare
    #: ``from uitk import`` in every slot file. The import is eager for that reason
    #: (a base class is needed at definition time): it loads ``uitk.bridge.slots``
    #: with the first Slots module.
    Signals = Signals
    Cancelable = Cancelable
    BridgeSlotsBase = BridgeSlotsBase
    AttributeSpec = AttributeSpec
    ParamRegistry = ParamRegistry

    #: One-shot guard so the legacy repeat-last migration runs once per process,
    #: not on every slot instantiation (the base ``__init__`` runs for every
    #: slot class).
    _legacy_repeat_last_migrated = False

    #: Default body for the empty-selection message box (see :meth:`require_selection`).
    NOTHING_SELECTED = (
        "<b>Nothing selected.</b><br>"
        "The operation requires at least one selected object."
    )

    @property
    def tk(self):
        """The host toolkit (``mtk`` / ``btk``) the entry point set on the
        switchboard: what a Slots class shared by both hosts calls for host
        behavior, never the host itself (CODE_STANDARD section 3). ``None``
        outside a host entry point."""
        return getattr(self.sb, "tk", None)

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

    def requires(self, widget, host) -> bool:
        """Tag a code-built *widget* as served only by *host* -- the ``requires``
        property a ``.ui`` widget carries -- and apply uitk's visibility policy,
        which hides it on any other host (CODE_STANDARD section 15: hidden, never
        a stub) and records why on ``widget.hidden_by_policy``.

        Parameters:
            widget (QWidget): The widget (a menu item, an option, a list row).
            host (str): The host tag(s) that serve it (``"maya"``,
                ``"maya|blender"``). Empty or None tags nothing: every host
                serves it.

        Returns:
            bool: True when this host serves it.
        """
        if not host:
            return True
        widget.setProperty("requires", host)
        return not self.sb.apply_visibility_policy(widget)

    def hide_unless(self, widget, available) -> bool:
        """Hide *widget* when this host cannot serve it: its engine lacks the
        operation the widget runs (CODE_STANDARD section 15: hidden, never a
        stub). The capability twin of :meth:`requires`, for a control both hosts
        build but only one host's engine backs.

        Hidden as a ``requires`` exclusion is (``hidden_by_policy``), so an app
        gate never shows it again, and as a field
        (``FieldVisibility.set_widget_visible``), so a ``CollapsableGroup`` that
        re-shows its contents on expand leaves it hidden. The gap itself is the
        engine's to close (BACKLOG); the panel never says "not available".

        Parameters:
            widget (QWidget): The control.
            available (bool): Whether this host's engine backs it.

        Returns:
            bool: *available*, so a caller can skip wiring a hidden control.
        """
        if available:
            return True
        self.sb.FieldVisibility.set_widget_visible(widget, False)
        widget.hidden_by_policy = "requires"
        return False

    def host_key(self, base: str) -> str:
        """*base* namespaced by host (uitk's ``host_namespace_suffix`` of the
        switchboard's ``context_tags``): a settings key each host keeps its own
        value under, as Maya and Blender share one settings store."""
        suffix = self.sb.ShortcutManager.host_namespace_suffix(
            getattr(self.sb, "context_tags", None)
        )
        return base + suffix

    def require_selection(self, message=None):
        """The selection, or ``None`` -- after a message box -- when it is empty.

        The guard a slot runs before work that cannot answer an empty selection
        itself. An operation that takes ``None`` for the selection returns ``[]``
        on an empty one instead: report from its result, as ``normals.py`` does.
        Read through the host toolkit (``self.tk.CoreUtils.selected_objects``),
        so a Slots class shared by both hosts gets Maya's selection as
        ``cmds.ls`` names it (components included) and Blender's selected objects.

        Parameters:
            message (str, optional): HTML shown when nothing is selected.
                Defaults to :attr:`NOTHING_SELECTED`.

        Returns:
            list | None: The selection, or ``None`` when it is empty.
        """
        selection = self.tk.CoreUtils.selected_objects()
        if not selection:
            self.sb.message_box(message or self.NOTHING_SELECTED)
            return None
        return selection

    def activate_tool(self, tool) -> bool:
        """Activate a viewport tool through the host toolkit and confirm it, or say
        why not.

        *tool* is a name both hosts register (``self.tk.UiUtils.get_tool_types``:
        ``"Multi-Cut"``, ``"Quad Draw"``, ``"Lasso Select"`` ...). The confirmation
        matters from the marking menu, which closes on the click: the tool change
        is otherwise easy to miss. A refusal -- no 3D view, no object of the type
        the tool edits, the host's own error -- reaches the user as the host
        words it (``set_tool`` raises ``ValueError`` / ``RuntimeError``).

        Returns:
            bool: True when the tool was set.
        """
        try:
            self.tk.UiUtils.set_tool(tool)
        except (RuntimeError, ValueError) as error:
            self.sb.message_box(str(error))
            return False
        self.sb.message_box(f"<hl>{tool}</hl> tool active.")
        return True

    def run_operation(self, call, *args, empty=None, **kwargs):
        """Call a host operation and report it: a refusal (``ValueError`` for a
        state the user can fix, ``RuntimeError`` for the host's own) as the host
        words it, and *empty* when the operation found nothing to act on -- the
        ``[]`` an operation given ``None`` for the selection returns (see
        :meth:`require_selection`).

        Parameters:
            call (callable): The operation (``self.tk.Components.poke_faces``).
            *args, **kwargs: Its arguments.
            empty (str, optional): HTML shown when it returns ``[]``.

        Returns:
            The operation's result, or None after a refusal.
        """
        try:
            result = call(*args, **kwargs)
        except (ValueError, RuntimeError) as error:
            self.sb.message_box(str(error))
            return None
        if empty and isinstance(result, list) and not result:
            self.sb.message_box(empty)
        return result

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

    def _dispatch_tools_row(self, item):
        """Dispatch a Tools-list leaf to the slot its ``_TOOLS_ITEMS`` row names.

        The body the Tools-list handlers share (animation ``list000``, materials
        ``list001``). The handlers themselves stay on the forks: their
        ``@Signals`` decorator is evaluated in the class body. ``_TOOLS_ITEMS``
        is ``{category: [(label, slot_name, *tooltip), ...]}``; category rows
        are navigation only, and slots vary -- some take the invoking widget,
        some take none.
        """
        if getattr(item, "sublist", None) and item.sublist.get_items():
            return
        text = item.item_text()
        parent = item.parent_item_text() or ""
        for label, slot_name, *_ in self._TOOLS_ITEMS.get(parent, ()):
            if label == text:
                slot = getattr(self, slot_name, None)
                if callable(slot):
                    self._call_slot(slot, item)
                return

    @staticmethod
    def _call_slot(slot, widget=None):
        """Call *slot* with *widget* when it takes an argument, else bare.

        Decided from the signature: calling it with one and retrying bare on a
        ``TypeError`` re-ran a slot whose own body raised one, hiding the error.
        """
        try:
            params = inspect.signature(slot).parameters.values()
        except (TypeError, ValueError):  # a builtin: nothing to read
            return slot()
        positional = (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
            inspect.Parameter.VAR_POSITIONAL,
        )
        if any(p.kind in positional for p in params):
            return slot(widget)
        return slot()

    def gate_on_app(self, widget, resolve_spec) -> bool:
        """Gate *widget* on the :class:`pythontk.AppSpec` *resolve_spec* returns.

        The panel-side half of ``sb.gate``: uitk owns the presentation policy
        (hide / disable / show, per the user's Preferences), this owns the two
        things every DCC panel would otherwise repeat -- pulling ``available`` and
        ``not_found_message`` off the spec, and surviving an engine that will not
        import.

        *resolve_spec* is a zero-arg callable (``lambda: mtk.RizomUVBridge.APP``),
        not the spec itself, because reaching a bridge's ``APP`` IMPORTS its engine
        module. Passing the spec would perform that import at the call site, where
        a failure propagates into the panel build; deferring it into here means a
        broken or missing engine costs its own entry a gate, not the whole panel.
        An unresolvable spec leaves the widget ungated and usable -- the bridge
        still reports its own missing app when actually used.

        Parameters:
            widget: The widget to gate. ``None`` is tolerated (``sb.gate``'s rule).
            resolve_spec (callable): Returns the ``AppSpec`` to gate on.

        Returns:
            bool: True when the app is available (or could not be determined), so
            a caller can ``if not self.gate_on_app(...): return``.
        """
        try:
            spec = resolve_spec()
        except Exception as error:  # noqa: BLE001 - an unimportable engine isn't gated
            self.sb.logger.debug(f"[gate_on_app] spec unresolved, not gating: {error}")
            return True
        self._app_gate_specs.add(spec)
        # Registered as a CALLABLE, not as the bool it evaluates to right now, so
        # `recheck_app_gates` can ask the spec again after invalidating its cache --
        # which is the whole point of a re-check (the app appeared mid-session).
        return self.sb.gate(widget, lambda s=spec: s.available, spec.not_found_message)

    #: Every :class:`pythontk.AppSpec` any Slots object has gated on. CLASS level,
    #: not per instance: gates are registered by the panel that OWNS the widget
    #: (Materials, UV) while the re-check is triggered from Preferences, so a
    #: per-instance set would leave that trigger refreshing nothing. It also matches
    #: the scope of its partner ``sb.recheck_gates()``, which re-applies EVERY live
    #: gate — refreshing one panel's specs while re-applying all of them was already
    #: asymmetric. Specs are module-level singletons hung off their bridge class, so
    #: this holds a handful of long-lived objects for the life of the process.
    _app_gate_specs = set()

    def recheck_app_gates(self) -> int:
        """Re-probe every gated app and re-present its widgets. Returns widgets updated.

        The answer to "I just installed it, why is the button still missing?" —
        reachable from ``Preferences`` > header > **Re-check Installed Tools**.
        ``AppSpec.path`` memoizes on purpose -- an availability gate re-runs on
        every panel show and must not re-scan Program Files each time -- so a
        mid-session install is invisible until the cache is dropped. This drops
        it (``AppSpec.refresh``) and then re-applies the gates, which is the pair
        that has to happen together: refreshing alone leaves the widgets as they
        were, and re-gating alone re-reads the same cached miss.

        Returns:
            int: Widgets re-presented by the sweep.
        """
        for spec in self._app_gate_specs:
            try:
                spec.refresh()
            except Exception as error:  # noqa: BLE001 - one bad spec, not the sweep
                self.sb.logger.debug(f"[recheck_app_gates] {spec}: {error}")
        return self.sb.recheck_gates()

    def toggle_camera_view(self):
        """Toggle between the last two viewport-camera views in slot history.

        DCC-agnostic switchboard logic shared by the Maya and Blender ``CamerasSlots``
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
