# !/usr/bin/python
# coding=utf-8
"""The Emissive Groups tool in the running host."""

import importlib


class EmissiveGroupsApi:
    """Reaches the host half a toolkit names, without importing a host here."""

    #: Toolkit package -> its half (whose ``EmissiveGroups`` is the tool there).
    HALVES = {
        "mayatk": "tentacle.tools.emissive_groups.maya",
        "blendertk": "tentacle.tools.emissive_groups.blender",
    }

    @classmethod
    def for_toolkit(cls, tk):
        """The tool over *tk*'s host: what a panel calls with its ``Slots.tk``.

        Raises:
            ValueError: *tk* is no toolkit Emissive Groups has a half for.
        """
        module = cls.HALVES.get(getattr(tk, "__name__", None))
        if module is None:
            raise ValueError(f"Emissive Groups has no half for {tk!r}.")
        return importlib.import_module(module).EmissiveGroups
