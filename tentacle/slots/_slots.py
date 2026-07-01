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
