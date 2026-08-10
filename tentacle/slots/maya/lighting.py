# !/usr/bin/python
# coding=utf-8
import mayatk as mtk

# From this Package:
from tentacle import LightingMixin, SlotsMaya


class Lighting(LightingMixin, SlotsMaya):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.sb = kwargs.get("switchboard")
        self.ui = self.sb.loaded_ui.lighting
        self.submenu = self.sb.loaded_ui.lighting_submenu

    def b000(self):
        """Launch the HDR Manager."""
        self.sb.handlers.marking_menu.show("hdr_manager")

    def b001(self):
        """Launch the Lightmap Baker."""
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
                "<b>Colour temperature</b> used when the fixture's material carries no"
                " constant emission colour — the material's own emission always wins.",
                "Off leaves the fallback white.",
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Intensity: ",
            setObjectName="d000",
            set_limits=[0, 100000, 1.0, 2],
            setValue=100.0,
            setToolTip=(
                "Maya light intensity for every created light (unitless).\n"
                "Created lights emit PER-AREA (Arnold Normalize off): a "
                "fixture-sized plate at the same intensity otherwise bakes "
                "~100× dimmer than the number suggests.\n"
                "The Blender bridge converts it for a bake (1.0 ≈ 1000 W) and its "
                "bake summary reports each light's final wattage — adjust the "
                "light's intensity attribute (or the bake's Scene Light Strength) "
                "from that number rather than re-creating the lights."
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setObjectName="d001",
            set_limits=[0, 10000, 0.5, 2],
            setValue=1.0,
            setToolTip="Scene units of clearance between the fixture's surface and its light.",
        )
        cmb = menu.add(
            "QComboBox",
            setObjectName="cmb000",
            setToolTip=(
                "How a face selection becomes emitters.\n"
                "Shell: connected face islands each get their own light — right for a\n"
                "merged environment mesh with many fixtures.\n"
                "Object: one light per shape. Face: one light per face."
            ),
        )
        for text, data in [
            ("Cluster: Shell", "shell"),
            ("Cluster: Object", "object"),
            ("Cluster: Face", "face"),
        ]:
            cmb.addItem(text, data)

    def tb000(self, widget):
        """Create real area lights from the selected fixture geometry."""
        menu = widget.option_box.menu
        cluster = menu.cmb000.itemData(menu.cmb000.currentIndex())
        created = mtk.LightUtils.lights_from_geometry(
            intensity=menu.d000.value(),
            kelvin=menu.s000.value() or None,
            offset=menu.d001.value(),
            cluster=cluster,
        )
        if not created:
            self.sb.message_box(
                "Select the fixture geometry first — whole meshes, or just their lens faces."
            )
            return
        self.sb.message_box(f"Created {len(created)} light(s) from the selection.")


# --------------------------------------------------------------------------------------------

# module name
# print(__name__)
# --------------------------------------------------------------------------------------------
# Notes
# --------------------------------------------------------------------------------------------
