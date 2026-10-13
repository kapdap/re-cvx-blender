import bpy
from mathutils import Matrix, Vector

from .common import convert_pos
from .rotation import ninja_euler


def _local_matrix(pos, ang):
    return (
        Matrix.Translation(Vector(convert_pos(pos)))
        @ ninja_euler(ang[0], ang[1], ang[2]).to_matrix().to_4x4()
    )


def build_motion(arm_obj, bone_names, parent, objects, parsed, name):
    obj_num, frm_num, tracks = parsed
    bpos = {}
    for o in objects:
        bpos[o.index] = o.pos
    rest_inv = {}
    for i in bone_names:
        r = arm_obj.data.bones[bone_names[i]].matrix_local.copy()
        if i in parent:
            rp = arm_obj.data.bones[bone_names[parent[i]]].matrix_local.copy()
            rest_inv[i] = (rp.inverted() @ r).inverted()
        else:
            rest_inv[i] = r.inverted()
    action = bpy.data.actions.new(name)
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    for f in range(frm_num):
        for i in bone_names:
            if i < obj_num:
                pos, ang = tracks[i]
            else:
                pos, ang = (None, None)
            p = pos[f] if pos is not None else bpos[i]
            a = ang[f] if ang is not None else (0, 0, 0)
            d = rest_inv[i] @ _local_matrix(p, a)
            pb = arm_obj.pose.bones[bone_names[i]]
            pb.location = d.to_translation()
            pb.rotation_euler = d.to_euler("XYZ")
            pb.keyframe_insert(data_path="location", frame=f + 1)
            pb.keyframe_insert(data_path="rotation_euler", frame=f + 1)
    return action
