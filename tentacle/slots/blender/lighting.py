# !/usr/bin/python
# coding=utf-8
import blendertk as btk

from tentacle import LightingMixin, SlotsBlender


class Lighting(LightingMixin, SlotsBlender):
    """Blender port of the shared ``lighting`` menu.

    HDR Manager opens the world-environment panel; the Lightmap Baker opens the
    Cycles-bake panel (``btk.LightmapBaker`` engine + co-located ``LightmapBakerSlots``,
    discovered by ``BlenderUiHandler``). Both panels live in blendertk.
    """

    def __init__(self, switchboard):
        super().__init__(switchboard)

    def b000(self):
        """Launch the HDR Manager (world-environment HDRI panel)."""
        self.sb.handlers.marking_menu.show("hdr_manager")

    def b001(self):
        """Launch the Lightmap Baker (Cycles-bake → game-engine lightmaps)."""
        self.sb.handlers.marking_menu.show("lightmap_baker")

    def tb000_init(self, widget):
        """Lights From Geometry Init"""
        menu = widget.option_box.menu
        menu.setTitle("Lights From Geometry")
        menu.add(
            self.sb.registered_widgets.SpinBox,
            setPrefix="Kelvin: ",
            setObjectName="s000",
            set_limits=[0, 12000],
            setValue=self.DEFAULT_KELVIN,
            setCustomDisplayValues={0: "Off"},
            setToolTip=self.kelvin_tooltip(
                "<b>Colour temperature</b> of the created lights (Blender's own"
                " blackbody conversion).",
                "Off leaves them white.",
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Power: ",
            setObjectName="d000",
            set_limits=[0, 1000000, 10.0, 1],
            setValue=100.0,
            setToolTip=(
                "Wattage of every created light (Blender's native light energy).\n"
                "Maya's fork exposes the same dial in Maya's unitless intensity."
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="d001",
            set_limits=[0, 100, 0.01, 3],
            setValue=0.01,
            setToolTip="Metres of clearance between the fixture's surface and its light.",
        )

    def tb000(self, widget):
        """Create real area lights from the selected fixture meshes."""
        import bpy

        objects = self.selected_objects()
        if not objects:
            self.sb.message_box("Select the fixture meshes first.")
            return
        menu = widget.option_box.menu
        # Aim reference = the centre of the scene's geometry, not of the selection:
        # a ceiling grid's own centre lies in the fixtures' plane, and the up/down
        # decision there would ride on modelling noise.
        room = [o for o in bpy.data.objects if o.type == "MESH"]
        created = btk.LightUtils.lights_from_geometry(
            objects,
            power=menu.d000.value(),
            kelvin=menu.s000.value() or None,
            offset=menu.d001.value(),
            toward=btk.XformUtils.get_center_point(room),
            # Not a control: a baked specular highlight is locked to the baking
            # viewpoint and reads as a smudge from every other angle, and the
            # light is an ordinary Blender light the artist can switch it back
            # on. Passed rather than left to the engine default so both DCCs
            # create the same light (mayatk's emit_specular already defaults off).
            diffuse_only=True,
        )
        if not created:
            self.sb.message_box("No lights created — the selection holds no meshes.")
            return
        self.sb.message_box(f"Created {len(created)} light(s) from the selection.")


# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
