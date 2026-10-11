import bpy

from .common import EMPTY_SIZE, convert_pos, create_collection
from .rotation import set_rotation


def import_points(name, entries, root, display="PLAIN_AXES", zero_ax_az=False):
    coll = create_collection(name, root)
    created = []
    for i, e in enumerate(entries):
        obj = bpy.data.objects.new(f"{name}_{i:03d}", None)
        obj.empty_display_type = display
        obj.empty_display_size = EMPTY_SIZE
        obj.location = convert_pos(e.pos)
        if zero_ax_az:
            set_rotation(obj, 0, e.ang[1], 0)
        else:
            set_rotation(obj, e.ang[0], e.ang[1], e.ang[2])
        coll.objects.link(obj)
        created.append(obj)
    bpy.context.view_layer.update()
    return created
