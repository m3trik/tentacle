# !/usr/bin/python
# coding=utf-8
import sys, os.path

sys.path.append(os.path.dirname(os.path.abspath(__file__))) #append this dir to the system path.

if __name__=='__main__':
	import tentacle.ui
	globals()['__package__'] = 'tentacle.ui'


from .animation_ui import Animation_ui
from .cameras_ui import Cameras_ui
from .convert_ui import Convert_ui
from .crease_ui import Crease_ui
from .create_ui import Create_ui
from .deformation_ui import Deformation_ui
from .display_ui import Display_ui
from .duplicate_ui import Duplicate_ui
from .dynLayout_ui import DynLayout_ui
from .edit_ui import Edit_ui
from .editors_ui import Editors_ui
from .file_ui import File_ui
from .init_ui import Init_ui
from .lighting_ui import Lighting_ui
from .main_ui import Main_ui
from .materials_ui import Materials_ui
from .mirror_ui import Mirror_ui
from .normals_ui import Normals_ui
from .nurbs_ui import Nurbs_ui
from .pivot_ui import Pivot_ui
from .polygons_ui import Polygons_ui
from .preferences_ui import Preferences_ui
from .rendering_ui import Rendering_ui
from .rigging_ui import Rigging_ui
from .scene_ui import Scene_ui
from .scripting_ui import Scripting_ui
from .selection_ui import Selection_ui
from .subdivision_ui import Subdivision_ui
from .symmetry_ui import Symmetry_ui
from .transform_ui import Transform_ui
from .utilities_ui import Utilities_ui
from .uv_ui import Uv_ui
from .vfx_ui import Vfx_ui

# print ('tentacle.ui:', __name__, __package__, __file__)






# -----------------------------------------------
# Notes
# -----------------------------------------------


# -----------------------------------------------
# deprecated:
# -----------------------------------------------


# import sys, os
# this_module_dir = os.path.abspath(os.path.dirname(__file__))
# sys.path.append(this_module_dir)
# import sys; for p in sys.path: print (p)