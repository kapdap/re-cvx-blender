import importlib

import bpy

from . import handlers, importer, operators, scene
from .scene import anim as scene_anim
from .scene import armature as scene_armature
from .scene import cameras as scene_cameras
from .scene import collision as scene_collision
from .scene import common as scene_common
from .scene import effects as scene_effects
from .scene import lights as scene_lights
from .scene import mesh as scene_mesh
from .scene import models as scene_models
from .scene import motions as scene_motions
from .scene import placements as scene_placements
from .scene import players as scene_players
from .scene import points as scene_points
from .scene import rotation as scene_rotation
from .scene import textures as scene_textures

importlib.reload(scene_common)
importlib.reload(scene_rotation)
importlib.reload(scene_armature)
importlib.reload(scene_anim)
importlib.reload(scene_effects)
importlib.reload(scene_players)
importlib.reload(scene_points)
importlib.reload(scene_textures)
importlib.reload(scene_mesh)
importlib.reload(scene_models)
importlib.reload(scene_motions)
importlib.reload(scene_placements)
importlib.reload(scene_collision)
importlib.reload(scene_cameras)
importlib.reload(scene_lights)
importlib.reload(scene)
importlib.reload(importer)
importlib.reload(operators)
importlib.reload(handlers)

_classes = [operators.ImportOperator]
_classes.append(handlers.DragDropFileHandler)


def menu_func(self, context):
    self.layout.operator(operators.ImportOperator.bl_idname, text="RDX (.rdx/.rdt)")


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.TOPBAR_MT_file_import.append(menu_func)


def unregister():
    bpy.types.TOPBAR_MT_file_import.remove(menu_func)
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)


if __name__ == "__main__":
    register()
