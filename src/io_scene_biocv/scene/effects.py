import bpy

from .common import EMPTY_SIZE, create_collection, convert_pos, convert_scale
from .rotation import set_rotation


def import_effects(entries, root):
    coll = create_collection("EFF", root)
    created = []
    for i, e in enumerate(entries):
        obj = bpy.data.objects.new("EFF_%03d" % i, None)
        obj.empty_display_type = "SPHERE"
        obj.empty_display_size = EMPTY_SIZE
        obj.location = convert_pos(e.pos)
        set_rotation(obj, e.ax, e.ay, 0)
        obj.scale = convert_scale(e.scale)
        coll.objects.link(obj)
        created.append(obj)
    bpy.context.view_layer.update()
    return created
