from ..rdx import motion
from .anim import build_combined, build_motion
from .rig import motion_targets


def _parse_bins(bins, rdx):
    parsed = {}
    failed = 0
    for true_no, mo, ms in bins:
        try:
            parsed[true_no] = motion.parse_mnb(rdx.data, mo, ms, rdx.endian)
        except motion.MotionError as exc:
            print(f"RDX: motion decode failed @{mo:#x}: {exc}")
            failed += 1
    return parsed, failed


def _link_pairs(parsed):
    pairs = {}
    for t, p in parsed.items():
        if p.obj_num != 8:
            continue
        q = parsed.get(t + 200)
        if q is None or q.obj_num != 10:
            continue
        if q.frm_num != p.frm_num or q.flg != p.flg:
            continue
        pairs[t] = t + 200
    return pairs


def _new_track(arm_obj, action, slot):
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    track = arm_obj.animation_data.nla_tracks.new()
    track.name = action.name
    track.mute = True
    strip = track.strips.new(action.name, 1, action)
    try:
        if slot is not None:
            strip.action_slot = slot
    except (AttributeError, TypeError):
        pass
    return track


def _actor_segments(parsed, pairs, linked):
    out = []
    for t in sorted(parsed):
        if t in linked:
            continue
        if t in pairs:
            segments = [(parsed[t], 0), (parsed[pairs[t]], 8)]
        else:
            segments = [(parsed[t], 0)]
        out.append((t, segments))
    return out


def _wanted_room_takes(rparsed, wanted):
    out = []
    skipped = 0
    for t in sorted(rparsed):
        if t not in wanted:
            skipped += 1
            continue
        out.append(t)
    return out, skipped


def _action_slot(arm_obj):
    try:
        return arm_obj.animation_data.action_slot
    except AttributeError:
        return None


def _import_strips(
    stem,
    arm_obj,
    bone_names,
    parent,
    objects,
    idx,
    aid,
    rig_n,
    targets,
    stiff_of,
    stiff_key,
    parsed,
    pairs,
    linked,
    rparsed,
    wanted,
    actions,
    arm_tracks,
):
    failed = 0
    for t, segments in _actor_segments(parsed, pairs, linked):
        key = (aid, rig_n, len(targets), len(segments), stiff_key, t)
        cached = actions.get(key)
        if cached is None:
            action = build_motion(
                arm_obj,
                bone_names,
                parent,
                objects,
                segments,
                f"{stem}ACT_{idx:03d}_{t:03d}",
                targets,
                stiff_of,
            )
            if action is None:
                failed += 1
                continue
            slot = _action_slot(arm_obj)
            actions[key] = (action, slot)
            action, slot = actions[key]
        else:
            action, slot = cached
        arm_tracks.append(_new_track(arm_obj, action, slot))
    room, skipped = _wanted_room_takes(rparsed, wanted)
    for t in room:
        key = (aid, rig_n, len(targets), stiff_key, "room", t)
        cached = actions.get(key)
        if cached is None:
            action = build_motion(
                arm_obj,
                bone_names,
                parent,
                objects,
                [(rparsed[t], 0)],
                f"{stem}ACT_{idx:03d}_room_{t:03d}",
                targets,
                stiff_of,
            )
            if action is None:
                failed += 1
                continue
            slot = _action_slot(arm_obj)
            actions[key] = (action, slot)
            action, slot = actions[key]
        else:
            action, slot = cached
        arm_tracks.append(_new_track(arm_obj, action, slot))
    return failed, skipped


def _import_single(
    stem,
    arm_obj,
    bone_names,
    parent,
    objects,
    idx,
    aid,
    rig_n,
    targets,
    stiff_of,
    stiff_key,
    parsed,
    pairs,
    linked,
    rparsed,
    wanted,
    actions,
    arm_tracks,
):
    segs = []
    ids = []
    for t, segments in _actor_segments(parsed, pairs, linked):
        segs.append(segments)
        ids.append(("a", t, len(segments)))
    room, skipped = _wanted_room_takes(rparsed, wanted)
    for t in room:
        segs.append([(rparsed[t], 0)])
        ids.append(("r", t))
    failed = 0
    if segs:
        key = (aid, rig_n, len(targets), stiff_key, tuple(ids))
        cached = actions.get(key)
        if cached is None:
            action, resolved = build_combined(
                arm_obj,
                bone_names,
                parent,
                objects,
                segs,
                f"{stem}ACT_{idx:03d}",
                targets,
                stiff_of,
            )
            failed = len(segs) - resolved
            if action is not None:
                slot = _action_slot(arm_obj)
                actions[key] = (action, slot)
                action, slot = actions[key]
            else:
                action = None
        else:
            action, slot = cached
        if action is not None:
            tr = _new_track(arm_obj, action, slot)
            tr.mute = False
            arm_tracks.append(tr)
    return failed, skipped


def import_motions(stem, rdx, table_arms, ene_mtn, rom_mtn, mtn_layout):
    actions = {}
    for ti, (kind, idx) in rdx.model_table_map().items():
        if kind != "actor" or idx is None:
            continue
        arm = table_arms.get(ti)
        if arm is None:
            continue
        arm_obj, bone_names, parent, objects = arm[0], arm[1], arm[2], arm[3]
        actor_bins = list(rdx.models[ti].motions) if ene_mtn else []
        room_pool = list(rdx.room_motions) if rom_mtn else []
        if not actor_bins and not room_pool:
            continue
        for pb in arm_obj.pose.bones:
            pb.rotation_mode = "XYZ"
        aid = rdx.actor[idx].id
        rig_n = len(bone_names)
        has_mask = bool(rdx.models[ti].masks)
        targets = motion_targets(rig_n, aid, has_mask)
        stiff_of = {}
        for bi2 in bone_names:
            sname = f"STIFF_{bi2:03d}"
            if arm_obj.pose.bones.get(sname) is not None:
                stiff_of[bi2] = sname
        stiff_key = tuple(sorted(stiff_of.items()))
        parsed, dropped = _parse_bins(actor_bins, rdx)
        total = len(actor_bins) + len(room_pool)
        pairs = _link_pairs(parsed) if aid == 1 else {}
        linked = set(pairs.values())
        rparsed, rfailed = _parse_bins(room_pool, rdx)
        dropped += rfailed
        wanted = rdx.room_refs.get(("actor", idx), set())
        arm_tracks = []
        path_args = (
            stem,
            arm_obj,
            bone_names,
            parent,
            objects,
            idx,
            aid,
            rig_n,
            targets,
            stiff_of,
            stiff_key,
            parsed,
            pairs,
            linked,
            rparsed,
            wanted,
            actions,
            arm_tracks,
        )
        if mtn_layout == "SINGLE":
            failed, skipped = _import_single(*path_args)
        else:
            failed, skipped = _import_strips(*path_args)
        dropped += failed
        if arm_tracks:
            arm_tracks[0].mute = False
            try:
                arm_obj.animation_data.action = None
            except AttributeError:
                pass
        print(
            f"RDX: table {ti:03d} rig {rig_n} targets {len(targets)}"
            f" dropped {dropped}/{total} skipped {skipped}"
        )
