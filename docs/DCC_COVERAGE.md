# tentacle — DCC Slot Coverage

> ⚠️ **Measures button presence only — superseded by `PARITY_AUDIT.md` for true parity.** A deferred-message stub and a faithful port both count as 'handled' here, so this reaches ~100%/100% regardless of real depth. For true depth/panel/helper parity see [`PARITY_AUDIT.md`](PARITY_AUDIT.md).

_Auto-generated (BLENDER_PORT_PLAN M5). Do not edit by hand. Refresh via `m3trik/scripts/generate_dcc_coverage.py`._

A widget counts as **handled** when the DCC's slot class defines the widget method (deferred-message stubs count) or a `<name>_init` (hidden-until-ported). The denominator is the interactive widget surface of the shared `ui/*.ui` files — `ui/maya_menus/` overlays are Maya-only whole menus and are out of scope by design.

| Domain | Widgets | Maya | Blender |
|:---|--:|--:|--:|
| animation | 19 | 100% | 100% |
| cameras | 13 | 100% | 100% |
| crease | 2 | 100% | 100% |
| deformation | 1 | 100% | 100% |
| display | 3 | 100% | 100% |
| duplicate | 7 | 100% | 100% |
| edit | 11 | 100% | 100% |
| editors | 15 | 100% | 100% |
| lighting | 2 | 100% | 100% |
| main | 1 | 100% | 100% |
| materials | 9 | 100% | 100% |
| normals | 8 | 100% | 100% |
| nurbs | 6 | 100% | 100% |
| pivot | 8 | 100% | 100% |
| polygons | 27 | 100% | 100% |
| preferences | 8 | 100% | 100% |
| rendering | 7 | 100% | 100% |
| rigging | 8 | 100% | 100% |
| scene | 10 | 100% | 100% |
| selection | 13 | 100% | 100% |
| settings | 3 | 100% | 100% |
| subdivision | 9 | 100% | 100% |
| symmetry | 5 | 100% | 100% |
| transform | 12 | 100% | 100% |
| utilities | 4 | 100% | 100% |
| uv | 26 | 100% | 100% |
| **TOTAL** | **237** | **100%** | **100%** |
