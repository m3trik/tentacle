# !/usr/bin/python
# coding=utf-8
"""The app-bridge panels' one base, shared by both hosts.

:class:`HostBridge` is uitk's :class:`BridgeSlotsBase` (the parameter rows, the
presets, the log pane, the Output Dir row, the header) with the host behavior every
bridge panel shares, reached through ``self.tk`` like any tentacle Slots class:

* **The engine**: a panel names its host's engine class (:attr:`bridge_class`,
  ``self.tk.<X>Bridge``); the base builds it and reads its parameter registry
  (``<X>Bridge.params_registry()``), template folder (``<X>Bridge.TEMPLATE_DIR``)
  and ``(template, mode)`` list (``<X>Bridge.list_template_modes()``) off it.
* **Presets** stay where each host has always kept them,
  ``<host library>/<UI_NAME>`` (``mayatk/unity_bridge``, ``blendertk/unity_bridge``).
* **Scope**: ``self.tk.BridgeHost`` resolves a ``SCOPE`` word to the host's objects
  and closes them over what a send ships; it also installs an optional package
  where this session imports it from.
* **The Bake Source row** (Set From Selection / Select / Clear, and its live
  member list) over ``self.tk.BakeSourceSet``, for the bridges that declare the
  ``BAKE_SOURCE_SET`` row.

A panel subclasses this, names ``UI_NAME`` and :attr:`bridge_class`, and writes
its ``b000``; everything else is a hook to override only where the bridge differs.

Not a :class:`tentacle.Slots` itself: ``BridgeSlotsBase`` is a plain class whose
``__init__`` never calls ``super()``, and ``Slots`` is a ``QObject`` (a Shiboken
metaclass, and a ``QObject.__init__`` that must run before any Qt call). Mixed in,
in either order, the two ``__init__``s would have to be called by hand. None of
``Slots``' behavior is a bridge's (camera toggles, Tools-list dispatch, app-state
mirrors), so the base takes the one thing it needs -- the ``tk`` property, the
same object, not a copy -- and stays the plain class every bridge panel has always
been under the Switchboard. ``Slots.Cancelable`` / ``Slots.Signals`` stay reachable
for a bridge's ``b000`` decorators.
"""

from pathlib import Path

import pythontk as ptk

from tentacle import Slots


class HostBridge(Slots.BridgeSlotsBase):
    """uitk's ``BridgeSlotsBase`` over the host toolkit (``self.tk``).

    Subclasses set ``UI_NAME`` and :attr:`bridge_class`, and implement ``b000``.
    """

    #: The host toolkit (``mtk`` / ``btk``) the entry point set on the switchboard.
    tk = Slots.tk

    # ------------------------------------------------------------------ engine
    @property
    def bridge_class(self):
        """The host's engine class for this panel: ``self.tk.<X>Bridge``."""
        raise NotImplementedError(f"{type(self).__name__} must name its bridge_class")

    def make_bridge(self):
        """A fresh engine; override to return ``None`` while an optional package
        it needs is missing (the panel still opens, to offer the install)."""
        return self.bridge_class()

    @property
    def params_module(self):
        """The engine's parameter registry (a ``uitk.bridge.ParamRegistry``)."""
        return self.bridge_class.params_registry()

    @property
    def template_dir(self):
        """The engine's template folder."""
        return self.bridge_class.TEMPLATE_DIR

    def list_template_modes(self):
        """The engine's ``[(template, mode), ...]`` for the template combo."""
        return self.bridge_class.list_template_modes()

    @property
    def PRESETS_ROOT(self):  # noqa: N802 - the uitk hook's name
        """``<host library>/<UI_NAME>``: each host's presets stay where they were."""
        return Path(self.tk.__name__.split(".")[0]) / self.UI_NAME

    # ------------------------------------------------------------------- scope
    def resolve_scope_objects(self, scope: str):
        """The host's objects for a ``SCOPE`` word; Entire Scene asks the engine's
        whole-scene hook first (``BridgeHost.resolve_scope``)."""
        return self.tk.BridgeHost.resolve_scope(scope, self.peek_bridge())

    def scoped_objects(self, params, warn: bool = True):
        """The Scope's objects closed over what a send of them ships.

        Maya's export-selection writes a group's subtree, Blender's FBX only the
        objects it is handed, so the host closes the scope
        (``BridgeHost.scope_closure``): a scoped group ships its group in both.
        """
        objects = super().scoped_objects(params, warn=warn)
        if not objects:
            return objects
        return self.tk.BridgeHost.scope_closure(objects, params)

    def _install_optional_package(self, spec: str) -> None:
        """Install *spec* where this session imports from (``BridgeHost.install_package``:
        Blender's interpreter keeps the user site off ``sys.path``)."""
        self.tk.BridgeHost.install_package(spec)

    # ------------------------------------------------------------- bake source
    #: The row a bake bridge declares for the scene's Bake Source set; its three
    #: buttons call the same-named methods below.
    BAKE_SOURCE_KEY = "BAKE_SOURCE_SET"
    #: What defining the set changes for THIS bridge's sends, appended to the Set
    #: From Selection log line (a bridge that reads the set differently says so).
    BAKE_SOURCE_DEFINED_NOTE = "Sends now ship it as the companion bake source."
    #: What clearing the set falls back to for this bridge ("" = nothing to say).
    BAKE_SOURCE_CLEARED_NOTE = ""

    def live_param_tooltip_blocks(self):
        """Append the Bake Source set's CURRENT members to its row's tooltips.

        The set lives in the scene, so it changes under an open panel; the block
        reads it on each hover. Only for a bridge that declares the row; extends
        the base's mapping, so a subclass's own live rows keep theirs.
        """
        tips = dict(super().live_param_tooltip_blocks() or {})
        params = getattr(self.params_module, "PARAMS", {}) or {}
        if self.BAKE_SOURCE_KEY in params:
            tips[self.BAKE_SOURCE_KEY] = self._bake_source_tooltip
        return tips

    def _bake_source_tooltip(self) -> str:
        """The Bake Source set's live member list (appended to each hover target)."""
        try:
            names = self.tk.BakeSourceSet.member_names()
        except Exception:  # noqa: BLE001 - a tooltip must never raise into Qt
            return ""
        return ptk.TooltipFormat.stored_items(
            names,
            noun="object(s) in the bake-source set",
            empty_text="No bake source is defined.",
        )

    def set_bake_source_from_selection(self) -> None:
        """Store the selection as the scene's bake source.

        Defining the set IS the opt-in: there is no checkbox beside it to tick,
        which could be left half-on (a set defined, the box clear).
        """
        bake_set = self.tk.BakeSourceSet
        members = bake_set.define()
        # Rows that key off the set (Marmoset's suffix fallback) re-grey now.
        self._refresh_param_enablement()
        if not members:
            self.bridge.logger.warning(
                "Nothing selected; the bake-source set was cleared."
            )
            return
        self.bridge.logger.info(
            f"Bake Source set: {len(members)} object(s) -> {bake_set.SET_NAME}. "
            f"{self.BAKE_SOURCE_DEFINED_NOTE}"
        )

    def select_bake_source(self) -> None:
        """Select the bake-source set's members.

        What the host cannot select (Blender: a member outside the view layer, or
        one locked from selection) is counted, never forced: unhiding geometry to
        satisfy a select would change the scene. The export ships it either way.
        """
        bake_set = self.tk.BakeSourceSet
        members = bake_set.members()
        # Also resyncs the rows keyed off the set if it went outside the panel.
        self._refresh_param_enablement()
        if not members:
            self.bridge.logger.warning("No bake-source set is defined.")
            return
        selected = bake_set.select()
        unreachable = len(members) - len(selected)
        self.bridge.logger.info(
            f"Selected {len(selected)} bake-source object(s)."
            + (
                f" {unreachable} could not be selected (hidden, or not selectable "
                "here); they still export."
                if unreachable > 0
                else ""
            )
        )

    def clear_bake_source(self) -> None:
        """Remove the bake-source set; its objects are left alone."""
        bake_set = self.tk.BakeSourceSet
        if not bake_set.exists():
            self.bridge.logger.warning("No bake-source set is defined.")
            return
        bake_set.clear()
        self._refresh_param_enablement()
        self.bridge.logger.info(
            " ".join(
                s
                for s in ("Bake-source set cleared.", self.BAKE_SOURCE_CLEARED_NOTE)
                if s
            )
        )
