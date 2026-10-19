from .common import convert_pos, create_collection, create_empty
from .rotation import set_rotation


def import_players(entries, root):
    coll = create_collection("PLY", root)
    for i, e in enumerate(entries):
        obj = create_empty(f"PLY_{i:03d}", "ARROWS", coll, convert_pos(e.pos), 10.0)
        set_rotation(obj, 0, e.ay, 0)
