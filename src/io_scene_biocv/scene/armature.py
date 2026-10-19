import bpy
from mathutils import Matrix, Vector

from .common import convert_pos, convert_scale
from .rotation import ninja_euler


def _local_matrix(obj, is_room):
    evalf = obj.evalflags
    if is_room:
        if evalf & 0x1:
            loc = (0.0, 0.0, 0.0)
        else:
            loc = convert_pos(obj.pos)
        ax, ay, az = obj.ang
        if evalf & 0x2:
            ax = ay = az = 0
        eul = ninja_euler(ax, ay, az, bool(evalf & 0x20))
        if evalf & 0x4:
            scl = (1.0, 1.0, 1.0)
        else:
            scl = convert_scale(obj.scl)
        sx, sy, sz = scl
        return (
            Matrix.Translation(Vector(loc))
            @ eul.to_matrix().to_4x4()
            @ Matrix(
                (
                    (sx, 0.0, 0.0, 0.0),
                    (0.0, sy, 0.0, 0.0),
                    (0.0, 0.0, sz, 0.0),
                    (0.0, 0.0, 0.0, 1.0),
                )
            )
        )
    loc = convert_pos(obj.pos)
    eul = ninja_euler(obj.ang[0], obj.ang[1], obj.ang[2])
    return Matrix.Translation(Vector(loc)) @ eul.to_matrix().to_4x4()


def build_armature(
    name, mlb_data, is_room, placement, collection, stiff_bones, prefix="NODE"
):
    arm = bpy.data.armatures.new(name)
    arm_obj = bpy.data.objects.new(name, arm)
    arm_obj.show_in_front = True
    collection.objects.link(arm_obj)
    locals = [_local_matrix(o, is_room) for o in mlb_data.objects]
    parent = {}
    children = {}
    for obj in mlb_data.objects:
        cur = mlb_data.object_index_of(obj.child)
        seen = set()
        while cur != -1 and cur not in seen:
            seen.add(cur)
            parent[cur] = obj.index
            children.setdefault(obj.index, []).append(cur)
            cur = mlb_data.object_index_of(mlb_data.objects[cur].sibling)
    worlds = {}

    def world_of(i):
        if i in worlds:
            return worlds[i]
        if i not in parent:
            worlds[i] = locals[i]
        else:
            worlds[i] = world_of(parent[i]) @ locals[i]
        return worlds[i]

    for obj in mlb_data.objects:
        world_of(obj.index)
    heads = {i: worlds[i].to_translation() for i in worlds}
    prev_active = bpy.context.view_layer.objects.active
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode="EDIT")
    if prefix == "NODE":
        stiff_prefix = "STIFF"
    else:
        stiff_prefix = f"{prefix}STIFF"
    stiff_set = set(stiff_bones) if stiff_bones else set()
    ang_of = {o.index: o.ang for o in mlb_data.objects}
    try:
        for obj in mlb_data.objects:
            b = arm.edit_bones.new(f"{prefix}_{obj.index:03d}")
            b.head = heads[obj.index]
            rot = worlds[obj.index].to_3x3()
            d = rot @ Vector((0.0, 1.0, 0.0))
            if d.length < 1e-6:
                d = Vector((0.0, 0.0, 1.0))
            else:
                d = d.normalized()
            length = 1.0
            ch = children.get(obj.index, [])
            if len(ch) == 1 and ch[0] in heads:
                dist = (heads[ch[0]] - heads[obj.index]).length
                if dist > 1e-6:
                    length = max(min(1.0, dist), 0.01)
            b.tail = heads[obj.index] + d * length
            if obj.hidden:
                b.hide = True
        for obj in mlb_data.objects:
            if obj.index in parent:
                child_bone = arm.edit_bones.get(f"{prefix}_{obj.index:03d}")
                parent_bone = arm.edit_bones.get(f"{prefix}_{parent[obj.index]:03d}")
                if child_bone is not None and parent_bone is not None:
                    child_bone.parent = parent_bone
                    if (child_bone.head - parent_bone.tail).length < 1e-4:
                        child_bone.use_connect = True
        for idx in stiff_set:
            pname = f"{prefix}_{idx:03d}"
            sname = f"{stiff_prefix}_{idx:03d}"
            pbone = arm.edit_bones.get(pname)
            if pbone is None or sname in arm.edit_bones:
                continue
            if idx not in heads:
                continue
            sb = arm.edit_bones.new(sname)
            sb.head = pbone.head
            sb.tail = pbone.tail
            sb.parent = pbone
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
        bpy.context.view_layer.objects.active = prev_active
    for idx in stiff_set:
        sname = f"{stiff_prefix}_{idx:03d}"
        pb = arm_obj.pose.bones.get(sname)
        if pb is None:
            continue
        pb.rotation_mode = "XYZ"
        pb.location = (0.0, 0.0, 0.0)
        ang = ang_of.get(idx, (0, 0, 0))
        pb.rotation_euler = ninja_euler(-ang[0], -ang[1], -ang[2])
    if placement is not None:
        arm_obj.matrix_world = placement
    bone_names = {o.index: f"{prefix}_{o.index:03d}" for o in mlb_data.objects}
    return arm_obj, bone_names, worlds, parent
