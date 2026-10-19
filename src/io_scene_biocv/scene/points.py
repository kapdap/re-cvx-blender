from .common import convert_pos, create_collection, create_empty
from .rotation import set_rotation


def import_points(name, entries, root, display="PLAIN_AXES", zero_ax_az=False):
    coll = create_collection(name, root)
    created = []
    for i, e in enumerate(entries):
        obj = create_empty(f"{name}_{i:03d}", display, coll, convert_pos(e.pos))
        if zero_ax_az:
            set_rotation(obj, 0, e.ang[1], 0)
        else:
            set_rotation(obj, e.ang[0], e.ang[1], e.ang[2])
        created.append(obj)
    return created
