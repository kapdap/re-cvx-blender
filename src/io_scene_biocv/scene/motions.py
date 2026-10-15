import bpy

from ..rdx import motion
from .anim import build_motion


def import_motions(stem, rdx, table_arms):
    actions = {}
    for ti, (kind, idx) in rdx.model_table_map().items():
        if kind not in ("actor", "obj", "item") or idx is None:
            continue
        arm = table_arms.get(ti)
        if arm is None:
            continue
        arm_obj, bone_names, parent, objects = arm
        if not rdx.models[ti].motions:
            continue
        for pb in arm_obj.pose.bones:
            pb.rotation_mode = "XYZ"
        if kind == "actor":
            eid = rdx.actor[idx].id
            prefix = "ACT"
        elif kind == "obj":
            eid = rdx.obj[idx].id
            prefix = "OBJ"
        else:
            eid = rdx.item[idx].id
            prefix = "ITM"
        skipped = set(range(6, 11)) if kind == "actor" and eid > 90 else set()
        targets = [i for i in bone_names if i not in skipped]
        arm_strips = []
        for mi, (mo, ms) in enumerate(rdx.models[ti].motions):
            key = (kind, eid, mi)
            entry = actions.get(key)
            if entry is None:
                try:
                    parsed = motion.parse_mnb(rdx.data, mo, ms, rdx.endian)
                except motion.MotionError as exc:
                    print(f"RDX: motion decode failed @{mo:#x}: {exc}")
                    continue
                if parsed[0] > len(targets):
                    continue
                routing = {bone: t for t, bone in enumerate(targets[: parsed[0]])}
                entry = (
                    build_motion(
                        arm_obj,
                        bone_names,
                        parent,
                        objects,
                        parsed,
                        routing,
                        f"{stem}{prefix}_{idx:03d}_{mi:02d}",
                    ),
                    arm_obj.animation_data.action_slot,
                )
                actions[key] = entry
            action, slot = entry
            if arm_obj.animation_data is None:
                arm_obj.animation_data_create()
            track = arm_obj.animation_data.nla_tracks.new()
            track.name = action.name
            strip = track.strips.new(action.name, 1, action)
            strip.action_slot = slot
            strip.mute = True
            arm_strips.append(strip)
        if arm_strips:
            arm_strips[0].mute = False
            arm_obj.animation_data.action = None
    bpy.context.view_layer.update()
