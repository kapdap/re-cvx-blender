import bpy
from mathutils import Matrix, Vector

from .rotation import ninja_euler


def _mnb_fields(parsed):
    return (parsed.obj_num, parsed.frm_num, parsed.tracks, parsed.flg)


def _resolve_segments(segments, targets):
    covered = {}
    frm_num = 0
    flg = 0
    for parsed, off in segments:
        obj_num, fnum, tracks, sflg = _mnb_fields(parsed)
        if off < 0 or off + obj_num > len(targets):
            return None
        frm_num = max(frm_num, fnum)
        flg |= sflg
        for t in range(obj_num):
            covered[targets[off + t]] = tracks[t]
    return covered, frm_num, flg


def _rig_data(arm_obj, bone_names, parent, objects, stiff_of):
    bpos = {}
    if objects:
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
    live_stiff = {}
    for idx, sname in (stiff_of or {}).items():
        if arm_obj.pose.bones.get(sname) is not None:
            live_stiff[idx] = sname
    return bpos, rest_inv, live_stiff


def _take_values(bone_names, bpos, rest_inv, live_stiff, covered, frm_num, slow):
    out = {}
    count = frm_num + (1 if slow else 0)
    ne = ninja_euler
    zero3 = (0.0, 0.0, 0.0)
    zero6 = [0.0] * count

    def emit(bone_name, path, ch, vals):
        out[(bone_name, path, ch)] = vals

    for i in bone_names:
        bn = bone_names[i]
        ri = rest_inv[i]
        sname = live_stiff.get(i)
        entry = covered.get(i)
        if entry is None:
            bp = bpos.get(i, zero3)
            d = ri @ (
                Matrix.Translation(Vector((bp[0], -bp[2], bp[1])))
                @ ne(0, 0, 0).to_matrix().to_4x4()
            )
            t = d.to_translation()
            e = d.to_euler("XYZ")
            for c, v in enumerate((t.x, t.y, t.z)):
                emit(bn, "location", c, [v] * count)
            for c, v in enumerate((e.x, e.y, e.z)):
                emit(bn, "rotation_euler", c, [v] * count)
            if sname is not None:
                s = ne(0, 0, 0)
                for c in range(3):
                    emit(sname, "location", c, zero6)
                for c, v in enumerate((s.x, s.y, s.z)):
                    emit(sname, "rotation_euler", c, [v] * count)
            continue
        pos, ang = entry
        bp = bpos.get(i, zero3)
        if pos is None:
            pos = [bp] * frm_num
        elif len(pos) < frm_num:
            pos = list(pos) + [bp] * (frm_num - len(pos))
        if ang is None:
            ang = [zero3] * frm_num
        elif len(ang) < frm_num:
            ang = list(ang) + [zero3] * (frm_num - len(ang))
        lx = []
        ly = []
        lz = []
        ex = []
        ey = []
        ez = []
        if sname is None:
            sxs = sys = sez = None
        else:
            sxs = []
            sys = []
            sez = []
        for f in range(frm_num):
            p = pos[f]
            a = ang[f]
            d = ri @ (
                Matrix.Translation(Vector((p[0], -p[2], p[1])))
                @ ne(a[0], a[1], a[2]).to_matrix().to_4x4()
            )
            t = d.to_translation()
            e = d.to_euler("XYZ")
            lx.append(t.x)
            ly.append(t.y)
            lz.append(t.z)
            ex.append(e.x)
            ey.append(e.y)
            ez.append(e.z)
            if sxs is not None:
                s = ne(-a[0], -a[1], -a[2])
                sxs.append(s.x)
                sys.append(s.y)
                sez.append(s.z)
        if slow:
            lx.append(lx[0])
            ly.append(ly[0])
            lz.append(lz[0])
            ex.append(ex[0])
            ey.append(ey[0])
            ez.append(ez[0])
        emit(bn, "location", 0, lx)
        emit(bn, "location", 1, ly)
        emit(bn, "location", 2, lz)
        emit(bn, "rotation_euler", 0, ex)
        emit(bn, "rotation_euler", 1, ey)
        emit(bn, "rotation_euler", 2, ez)
        if sname is not None:
            for c in range(3):
                emit(sname, "location", c, zero6)
            emit(sname, "rotation_euler", 0, sxs + [sxs[0]] if slow else sxs)
            emit(sname, "rotation_euler", 1, sys + [sys[0]] if slow else sys)
            emit(sname, "rotation_euler", 2, sez + [sez[0]] if slow else sez)
    return out, count


def _write_action(arm_obj, bone_names, name, curves):
    action = bpy.data.actions.new(name)
    if arm_obj.animation_data is None:
        arm_obj.animation_data_create()
    arm_obj.animation_data.action = action
    first = arm_obj.pose.bones[bone_names[next(iter(bone_names))]]
    for path in ("location", "rotation_euler"):
        first.keyframe_insert(data_path=path, frame=1)
    if hasattr(action, "layers"):
        slot = arm_obj.animation_data.action_slot
        bag = action.layers[0].strips[0].channelbag(slot, ensure=True)
        fcurves = bag.fcurves
    else:
        fcurves = action.fcurves
    have = {(fc.data_path, fc.array_index): fc for fc in fcurves}
    for (bone_name, path, ch), (frames, vals) in curves.items():
        dp = f'pose.bones["{bone_name}"].{path}'
        fc = have.get((dp, ch))
        if fc is None:
            fc = fcurves.new(dp, index=ch)
            have[(dp, ch)] = fc
        else:
            fc.keyframe_points.clear()
        total = len(vals)
        co = [0.0] * (2 * total)
        co[0::2] = frames
        co[1::2] = vals
        fc.keyframe_points.add(count=total)
        fc.keyframe_points.foreach_set("co", co)
        fc.keyframe_points.update()
        try:
            fc.keyframe_points.foreach_set("interpolation", [1] * total)
        except (AttributeError, TypeError, ValueError):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
        try:
            fc.extrapolation = "HOLD"
        except (AttributeError, TypeError):
            try:
                fc.extrapolation = "CONSTANT"
            except (AttributeError, TypeError):
                pass
    return action


def build_combined(
    arm_obj, bone_names, parent, objects, takes, name, targets, stiff_of
):
    if targets is None:
        targets = sorted(bone_names.keys())
    if not takes:
        return None, 0
    bpos, rest_inv, live_stiff = _rig_data(
        arm_obj, bone_names, parent, objects, stiff_of
    )
    curves = {}
    offset = 0
    resolved = 0
    for segments in takes:
        taken = _resolve_segments(segments, targets)
        if taken is None:
            continue
        covered, frm_num, flg = taken
        vals, count = _take_values(
            bone_names, bpos, rest_inv, live_stiff, covered, frm_num, bool(flg & 0x20)
        )
        for key, v in vals.items():
            fr, vv = curves.get(key, ([], []))
            fr.extend(offset + x for x in range(1, count + 1))
            vv.extend(v)
            curves[key] = (fr, vv)
        offset += count
        resolved += 1
    if not resolved:
        return None, 0
    return _write_action(arm_obj, bone_names, name, curves), resolved


def build_motion(
    arm_obj, bone_names, parent, objects, segments, name, targets, stiff_of
):
    if targets is None:
        targets = sorted(bone_names.keys())
    resolved = _resolve_segments(segments, targets)
    if resolved is None:
        return None
    covered, frm_num, flg = resolved
    bpos, rest_inv, live_stiff = _rig_data(
        arm_obj, bone_names, parent, objects, stiff_of
    )
    vals, count = _take_values(
        bone_names, bpos, rest_inv, live_stiff, covered, frm_num, bool(flg & 0x20)
    )
    frames = [float(x) for x in range(1, count + 1)]
    curves = {}
    for key, v in vals.items():
        curves[key] = (frames, v)
    return _write_action(arm_obj, bone_names, name, curves)
