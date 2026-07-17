# !/usr/bin/python
# coding=utf-8
from tentacle.slots.blender._slots_blender import SlotsBlender


class Blender(SlotsBlender):
    """Base-name anchor for the Blender both-button chord menu (``blender#startmenu``).

    The chord menu is a thin launcher for Blender's OWN native menus — the exact mirror of
    ``ui/maya_menus``. Every node is a ``MenuButton`` with a **bare** target (``"mesh"``,
    ``"select"``, ``"vertex"`` …): hovering it opens ``<target>#submenu.ui``, and releasing shows
    the harvested Qt clone of the real Blender menu in a Switchboard window (pin header, hides
    with ``key_show`` — Maya parity). Both the resolution and the wrap live in **blendertk** —
    :class:`blendertk.ui_utils.blender_native_menus.BlenderNativeMenus` maps each bare name to a
    ``*_MT_*`` menu id and harvests its ``draw`` into a ``QMenu`` (``menu_harvest``), and
    :class:`blendertk.ui_utils.blender_ui_handler.BlenderUiHandler` resolves it (``can_resolve``)
    and hosts it (``show`` -> ``_wrap_native_menu``). This mirrors Maya, where
    ``MayaNativeMenus`` / ``MayaUiHandler`` (mayatk) do the same and the maya_menus
    ``MenuButton``s carry **no** slots.

    So this class holds no slot methods — the chord menu's ``MenuButton``s own navigation, not
    slots. It exists only so the startmenu's base name (``blender``) resolves to a slot class.
    """
