from mathutils import Matrix, Vector

from .common import convert_pos
from .rotation import ninja_euler


def _xform(entry, yaw_only=False):
    ang = (0, entry.ang[1], 0) if yaw_only else entry.ang
    eul = ninja_euler(ang[0], ang[1], ang[2])
    return Matrix.Translation(Vector(convert_pos(entry.pos))) @ eul.to_matrix().to_4x4()


def model_placements(rdx):
    tables = {"actor": rdx.actor, "obj": rdx.obj, "item": rdx.item}
    types = {}
    xforms = {}
    for ti, (kind, idx) in rdx.model_table_map().items():
        types[ti] = kind
        if idx is None:
            continue
        xforms[ti] = _xform(tables[kind][idx], yaw_only=kind == "actor")
    return types, xforms
