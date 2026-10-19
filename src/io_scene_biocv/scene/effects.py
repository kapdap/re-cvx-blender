from .common import convert_pos, convert_scale, create_collection, create_empty
from .rotation import set_rotation


def import_effects(entries, root):
    coll = create_collection("EFF", root)
    created = []
    for i, e in enumerate(entries):
        obj = create_empty(f"EFF_{i:03d}", "SPHERE", coll, convert_pos(e.pos))
        set_rotation(obj, e.ax, e.ay, 0)
        obj.scale = convert_scale(e.scale)
        created.append(obj)
    return created
