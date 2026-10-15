import bpy
from mathutils import Matrix, Vector

from .common import convert_pos
from .rotation import ninja_euler


def _local_matrix(pos, ang):
    return (
        Matrix.Translation(Vector(convert_pos(pos)))
        @ ninja_euler(ang[0], ang[1], ang[2]).to_matrix().to_4x4()
    )


def build_motion(arm_obj, bone_names, parent, objects, parsed, routing, name):
    obj_num, frm_num, tracks = parsed
    bpos = {o.index: o.pos for o in objects}
    bang = {o.index: o.ang for o in objects}
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
    if not bone_names:
        return action
    values = {}
    for i in bone_names:
        t = routing.get(i)
        fb = t is None or t >= obj_num
        pos, ang = (None, None) if fb else tracks[t]
        for f in range(frm_num):
            p = pos[f] if pos is not None else bpos[i]
            a = ang[f] if ang is not None else bang[i] if fb else (0, 0, 0)
            d = rest_inv[i] @ _local_matrix(p, a)
            loc = d.to_translation()
            eul = d.to_euler("XYZ")
            for c, v in enumerate((loc.x, loc.y, loc.z)):
                values.setdefault((bone_names[i], "location", c), []).append(v)
            for c, v in enumerate((eul.x, eul.y, eul.z)):
                values.setdefault((bone_names[i], "rotation_euler", c), []).append(v)
    pb0 = arm_obj.pose.bones[bone_names[next(iter(bone_names))]]
    for path in ("location", "rotation_euler"):
        pb0.keyframe_insert(data_path=path, frame=1)
    slot = arm_obj.animation_data.action_slot
    bag = action.layers[0].strips[0].channelbag(slot, ensure=True)
    for (bn, path, ch), vals in values.items():
        dp = f'pose.bones["{bn}"].{path}'
        fc = next(
            (
                fcu
                for fcu in bag.fcurves
                if fcu.data_path == dp and fcu.array_index == ch
            ),
            None,
        )
        if fc is None:
            fc = bag.fcurves.new(dp, index=ch)
        else:
            try:
                fc.keyframe_points.clear()
            except AttributeError:
                bag.fcurves.remove(fc)
                fc = bag.fcurves.new(dp, index=ch)
        fc.keyframe_points.add(count=frm_num)
        fc.keyframe_points.foreach_set(
            "co", [x for f, v in enumerate(vals, start=1) for x in (float(f), float(v))]
        )
        fc.keyframe_points.update()
    return action
