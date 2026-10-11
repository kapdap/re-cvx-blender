import bpy

from .common import EMPTY_SIZE, convert_pos, create_collection
from .rotation import set_rotation


def import_players(entries, root):
    coll = create_collection("PLY", root)
    for i, e in enumerate(entries):
        obj = bpy.data.objects.new(f"PLY_{i:03d}", None)
        obj.empty_display_type = "ARROWS"
        obj.empty_display_size = EMPTY_SIZE * 2.0
        obj.location = convert_pos(e.pos)
        set_rotation(obj, 0, e.ay, 0)
        coll.objects.link(obj)
    bpy.context.view_layer.update()
