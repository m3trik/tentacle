# !/usr/bin/python
# coding=utf-8
"""Lighting: one Slots class for both hosts.

The HDR Manager and Lightmap Baker buttons open the shared tool panels (Light
Rigs is Maya's: ``requires`` hides it in Blender). *Lights From Geometry*
builds real area lights from the selected fixture geometry through the host
toolkit's ``LightUtils.lights_from_geometry``, one undo step.
"""

from tentacle import Slots


class LightingSlots(Slots):
    #: Real-world sources at each colour temperature, for the Kelvin field's
    #: tooltip: a bare number is unguessable, so the tooltip names things the
    #: artist has seen at each level.
    #:
    #: Rich text in a ``<pre>`` block: Qt renders tooltip HTML, and only a
    #: preformatted block keeps both the newlines and the column. The font stack
    #: is explicit because Qt's generic ``monospace`` alias resolves per platform.
    KELVIN_REFERENCE = (
        "<pre style=\"font-family: Consolas, 'Courier New', monospace\">"
        "1700 K   match flame\n"
        "1900 K   candlelight\n"
        "2400 K   incandescent bulb, dimmed\n"
        "2700 K   soft-white bulb, warm halogen\n"
        "3000 K   warm-white LED, film tungsten\n"
        "3500 K   office troffer, warm end\n"
        "4100 K   cool-white fluorescent\n"
        "5000 K   horizon daylight, neutral white\n"
        "5500 K   midday sun, camera flash\n"
        "6500 K   overcast sky, monitor white\n"
        "7500 K   shade under a blue sky\n"
        "9000 K   clear blue northern sky"
        "</pre>"
    )

    #: Value the Kelvin field starts on: horizon daylight, which reads neutral
    #: rather than casting every fixture warm.
    DEFAULT_KELVIN = 5000

    def b000(self):
        """Launch the HDR Manager (the scene's world / sky-dome HDRI)."""
        self.sb.handlers.marking_menu.show("hdr_manager")

    def b001(self):
        """Launch the Lightmap Baker (bake scene lighting for game engines)."""
        self.sb.handlers.marking_menu.show("lightmap_baker")

    def b002(self):
        """Launch Light Rigs: save, swap and restore named light rigs (Maya)."""
        self.sb.handlers.marking_menu.show("light_rig")

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
            setToolTip=(
                "<b>Colour temperature</b> of the created lights. In Maya it is the"
                " fallback for a fixture whose material carries no constant emission"
                " colour: the material's own emission wins."
                f"{self.KELVIN_REFERENCE}"
                "Off leaves them white."
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Intensity: ",
            setObjectName="d000",
            set_limits=[0, 1000000, 1.0, 2],
            setValue=100.0,
            setToolTip=(
                "Intensity of every created light, in the host's own unit:\n"
                "Maya's unitless intensity, Blender's Watts.\n"
                "Maya's lights emit PER-AREA (Arnold Normalize off): a "
                "fixture-sized plate at the same intensity otherwise bakes "
                "~100x dimmer than the number suggests. The Blender bridge "
                "converts it for a bake (1.0 = about 1000 W) and reports each "
                "light's final wattage: adjust the light from that number "
                "rather than re-creating the lights."
            ),
        )
        menu.add(
            "QDoubleSpinBox",
            setPrefix="Offset: ",
            setSuffix=" cm",
            setObjectName="d001",
            set_limits=[0, 10000, 0.5, 2],
            setValue=1.0,
            setToolTip=(
                "Clearance between the fixture's surface and its light, in "
                "centimetres (converted to the scene's units)."
            ),
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
        # Face clustering is Maya's: Blender's lights come from whole meshes
        # (its engine takes the mode for parity only).
        self.requires(cmb, "maya")

    def tb000(self, widget):
        """Create real area lights from the selected fixture geometry."""
        menu = widget.option_box.menu
        created = self.tk.LightUtils.lights_from_geometry(
            None,
            intensity=menu.d000.value(),
            kelvin=menu.s000.value() or None,
            offset=self.tk.Units.convert(menu.d001.value(), "cm", "working"),
            cluster=menu.cmb000.currentData(),
        )
        if not created:
            self.sb.message_box(
                "Select the fixture geometry first: whole meshes, or (in Maya)"
                " just their lens faces."
            )
            return
        self.sb.message_box(f"Created {len(created)} light(s) from the selection.")
