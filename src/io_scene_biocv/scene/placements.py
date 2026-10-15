from mathutils import Matrix, Vector

from .common import convert_pos
from .rotation import ninja_euler


def _xform(entry, yaw_only=False):
    ang = (0, entry.ang[1], 0) if yaw_only else entry.ang
    eul = ninja_euler(ang[0], ang[1], ang[2])
    return Matrix.Translation(Vector(convert_pos(entry.pos))) @ eul.to_matrix().to_4x4()


def _work_xform(pos, ang):
    eul = ninja_euler(ang[0], ang[1], ang[2])
    return Matrix.Translation(Vector(convert_pos(pos))) @ eul.to_matrix().to_4x4()


def model_placements(rdx, apply_motions=False):
    tables = {"actor": rdx.actor, "obj": rdx.obj, "item": rdx.item}
    types = {}
    xforms = {}
    work = rdx.work_xforms
    for ti, (kind, idx) in rdx.model_table_map().items():
        types[ti] = kind
        if idx is None:
            continue
        if apply_motions and rdx.models[ti].motions and (kind, idx) in work:
            p, a = work[(kind, idx)]
            xforms[ti] = _work_xform(p, a)
        else:
            xforms[ti] = _xform(tables[kind][idx], yaw_only=kind == "actor")
    return types, xforms
