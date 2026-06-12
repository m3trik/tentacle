# tentacle — DCC Slot Coverage

_Auto-generated (BLENDER_PORT_PLAN M5). Do not edit by hand. Refresh via `m3trik/scripts/generate_dcc_coverage.py`._

A widget counts as **handled** when the DCC's slot class defines the widget method (deferred-message stubs count) or a `<name>_init` (hidden-until-ported). The denominator is the interactive widget surface of the shared `ui/*.ui` files — `ui/maya_menus/` overlays are Maya-only whole menus and are out of scope by design.

| Domain | Widgets | Maya | Blender |
|:---|--:|--:|--:|
| animation | 19 | 100% | — |
| cameras | 13 | 100% | 100% |
| crease | 2 | 100% | 100% |
| deformation | 1 | 100% | — |
| display | 3 | 100% | 100% |
| duplicate | 7 | 100% | 100% |
| edit | 11 | 100% | 100% |
| editors | 15 | 100% | — |
| lighting | 2 | 100% | — |
| main | 1 | 100% | 100% |
| materials | 9 | 100% | — |
| normals | 8 | 100% | 100% |
| nurbs | 6 | 100% | — |
| pivot | 8 | 100% | 100% |
| polygons | 27 | 100% | — |
| preferences | 8 | 100% | 100% |
| rendering | 7 | 100% | — |
| rigging | 8 | 100% | — |
| scene | 11 | 100% | — |
| selection | 13 | 100% | 100% |
| settings | 3 | 100% | 100% |
| subdivision | 9 | 100% | 100% |
| symmetry | 5 | 80% | 80% |
| transform | 12 | 100% | 100% |
| utilities | 4 | 100% | — |
| uv | 26 | 92% | 100% |
| **TOTAL** | **238** | **99%** | **54%** |

## maya — unhandled widgets

- **symmetry**: chk004
- **uv**: cmb003, s003

## blender — unhandled widgets

- **animation** *(no slot file)*: b000, b004, b005, tb000, tb001, tb002, tb003, tb004, tb005, tb006, tb007, tb008, tb009, tb010, tb012, tb013, tb014, tb017, tb018
- **deformation** *(no slot file)*: tb001
- **editors** *(no slot file)*: b000, b001, b002, b003, b004, b005, b006, b007, b008, b009, b010, b011, b012, b013, list000
- **lighting** *(no slot file)*: b000, b001
- **materials** *(no slot file)*: b002, b004, b005, b006, b013, cmb002, list000, list001, tb000
- **nurbs** *(no slot file)*: b030, b056, b058, list000, tb000, tb001
- **polygons** *(no slot file)*: b000, b001, b003, b006, b007, b008, b009, b011, b012, b022, b032, b034, b038, b043, b047, b049, b051, b053, tb000, tb002, tb003, tb004, tb005, tb006, tb007, tb008, tb009
- **rendering** *(no slot file)*: b000, b001, b002, b003, b004, cmb001, tb000
- **rigging** *(no slot file)*: b003, b004, cmb001, cmb002, tb000, tb001, tb003, tb004
- **scene** *(no slot file)*: b001, b002, b004, b005, b007, cmb002, cmb003, cmb004, list000, tb000, tb003
- **symmetry**: chk004
- **utilities** *(no slot file)*: b000, b001, b002, b003
