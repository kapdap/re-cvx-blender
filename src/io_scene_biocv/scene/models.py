import bpy
from mathutils import Matrix, Vector

from ..rdx import mask, mlb, nj, skin
from .armature import build_armature
from .common import convert_pos, convert_scale, create_collection
from .mesh import build_mesh
from .placements import model_placements
from .rotation import set_rotation

MORPH_PAIRS = {
    1: ((0, 1),),
    2: ((5, 6),),
    9: ((0, 1),),
    12: ((0, 1),),
    14: ((0, 1),),
    26: ((0, 1),),
    30: ((0, 1),),
}


def _morph_models(mlb_data):
    out = {}
    for o in mlb_data.objects:
        if 0 <= o.model_index < len(mlb_data.models):
            m = mlb_data.models[o.model_index]
            if m is not None and m.faces:
                out[o.index] = len(m.verts)
    return out


def _morph_verified(src, tgt):
    if not _skeleton_compatible(src, tgt):
        return False
    counts = _morph_models(src)
    return bool(counts) and counts == _morph_models(tgt)


def _skeleton_compatible(src, tgt):
    if src is None or tgt is None or len(src.objects) != len(tgt.objects):
        return False
    return all(
        a.index == b.index
        and src.object_index_of(a.child) == tgt.object_index_of(b.child)
        and src.object_index_of(a.sibling) == tgt.object_index_of(b.sibling)
        and tuple(a.pos) == tuple(b.pos)
        and tuple(a.ang) == tuple(b.ang)
        and a.evalflags == b.evalflags
        for a, b in zip(src.objects, tgt.objects)
    )


def _apply_morph_key(created, tgt_mlb, worlds, name):
    if not created or tgt_mlb is None:
        return
    tgt_models = {}
    for o in tgt_mlb.objects:
        if 0 <= o.model_index < len(tgt_mlb.models):
            m = tgt_mlb.models[o.model_index]
            if m is not None and m.faces:
                tgt_models[o.index] = m
    for idx, mobj in created.items():
        tm = tgt_models.get(idx)
        if tm is None:
            continue
        me = mobj.data
        if len(me.vertices) != len(tm.verts):
            continue
        if me.shape_keys is None:
            mobj.shape_key_add(name="Basis", from_mix=False)
        kb = me.shape_keys.key_blocks.get(name)
        if kb is None:
            kb = mobj.shape_key_add(name=name, from_mix=False)
        bind = worlds.get(idx)
        for v, (x, y, z) in zip(me.vertices, tm.verts):
            kb.data[v.index].co = _skin_point(Vector(convert_pos((x, y, z))), bind)
        kb.value = 0.0


def _load_masks(table, rdx):
    masks = []
    for mo, ms in table.masks:
        try:
            masks.append(mask.parse_mask(rdx.data, mo, ms, rdx.endian))
        except mask.MaskError as exc:
            print(f"RDX: MASK decode failed @{mo:#x}: {exc}")
    return masks


def _read_mlb(rdx, bo, bs):
    try:
        return mlb.read_mlb(rdx.data, bo, bs, rdx.endian)
    except nj.NjError as exc:
        print(f"RDX: MLB decode failed @{bo:#x}: {exc}")
        return None


def _skin_entries(table):
    for entry in table.skins:
        if len(entry) == 3:
            yield entry
        elif len(entry) == 2:
            so, ss = entry
            yield (0, so, ss)


def _parse_table_skins(rdx, table, mlb_list):
    per = [{} for _ in mlb_list]
    for mdl_idx, so, ss in _skin_entries(table):
        if mdl_idx < 0 or mdl_idx >= len(mlb_list):
            continue
        mlb_data = mlb_list[mdl_idx]
        if mlb_data is None or not mlb_data.objects:
            continue
        try:
            parsed = skin.parse_skin(
                rdx.data, so, ss, len(mlb_data.objects), rdx.endian
            )
        except skin.SkinError as exc:
            print(f"RDX: SKIN decode failed @{so:#x}: {exc}")
            continue
        for node, weights in parsed:
            if node < len(mlb_data.objects):
                mi = mlb_data.objects[node].model_index
                if mi >= 0:
                    per[mdl_idx].setdefault(mi, weights)
    return per


def _stiff_set(weights_dict):
    out = set()
    for weights in weights_dict.values():
        for bone, w in weights:
            if w < 1.0:
                out.add(bone)
    return out


def _display_score(mlb_data):
    if mlb_data is None:
        return (-1, -1, -1)
    faces = 0
    meshable = 0
    for o in mlb_data.objects:
        if 0 <= o.model_index < len(mlb_data.models):
            m = mlb_data.models[o.model_index]
            if m is not None and m.faces:
                faces += len(m.faces)
                meshable += 1
    return (faces, meshable, len(mlb_data.objects))


def _face_target(masks, mlb_data, arm_obj, lip_pool, apply_motions):
    if not apply_motions:
        return None, -1
    for mk in masks:
        hit = mask.search_object(mlb_data, mk.face_id)
        if hit is not None:
            for li, blob in enumerate(lip_pool):
                arm_obj[f"lip_{li:02d}"] = list(blob)
            return mk, hit.index
    return None, -1


def _tex_table(tex_assign, ti, bi):
    return tex_assign.get((ti, bi), tex_assign.get((ti, 0)))


def _iter_meshable(mlb_data):
    for obj in mlb_data.objects:
        if obj.model_index < 0 or obj.model_index >= len(mlb_data.models):
            continue
        model = mlb_data.models[obj.model_index]
        if model is None or not model.faces:
            continue
        yield obj, model


def _resolve_weights(skin_weights, model_index, nverts):
    weights = skin_weights.get(model_index)
    if weights is None and len(skin_weights) == 1:
        weights = next(iter(skin_weights.values()))
    if weights is not None and len(weights) == nverts:
        return weights
    return None


def _skin_point(co, bind):
    if bind is not None:
        co = bind @ co
    return co


def _get_mesh(cache, key, mesh_name, model, tex_repo, tex_table, tex_names, bind=None):
    mesh = cache.get(key)
    if mesh is None:
        mesh = build_mesh(mesh_name, model, tex_repo, tex_table, tex_names)
        if mesh is not None and bind is not None:
            for v in mesh.vertices:
                v.co = _skin_point(v.co, bind)
            mesh.update()
        cache[key] = mesh
    return mesh


def _new_mesh_object(name, mesh, tcoll, parent, hidden):
    mobj = bpy.data.objects.new(name, mesh)
    tcoll.objects.link(mobj)
    mobj.parent = parent
    if hidden:
        mobj.hide_viewport = True
        mobj.hide_render = True
    return mobj


def _assign_vertex_groups(mobj, weights, bone_names):
    groups = {}

    def _group(name):
        g = groups.get(name)
        if g is None:
            g = mobj.vertex_groups.get(name)
            if g is None:
                g = mobj.vertex_groups.new(name=name)
            groups[name] = g
        return g

    def _stiff_name(bn):
        if bn.startswith("NODE_"):
            return bn.replace("NODE_", "STIFF_", 1)
        return f"STIFF_{bn}"

    batched = {}
    for vi, (bone, w) in enumerate(weights):
        bn = bone_names.get(bone)
        if bn is None:
            continue
        if w >= 0.999:
            batched.setdefault((bn, 1.0), []).append(vi)
        else:
            batched.setdefault((bn, w), []).append(vi)
            batched.setdefault((_stiff_name(bn), 1.0 - w), []).append(vi)
    for (name, w), idxs in batched.items():
        try:
            _group(name).add(idxs, w, "REPLACE")
        except RuntimeError:
            pass


def _add_face_shapes(mobj, model, face_mask, bind):
    try:
        if mobj.data.shape_keys is None:
            mobj.shape_key_add(name="Basis", from_mix=False)
        for pi, par in enumerate(face_mask.face):
            disp = mask.apply_muscle(model.verts, face_mask, par[0])
            kb = mobj.shape_key_add(name=f"FM_{pi:02d}", from_mix=False)
            kb.value = 0.0
            for vi, ((x, y, z), kd) in enumerate(zip(disp, kb.data)):
                kd.co = _skin_point(Vector((x, -z, y)), bind)
    except (RuntimeError, ValueError, IndexError):
        pass


def _build_empties(node_prefix, ti, bi, mlb_data, is_room, xform, tcoll):
    empties = {}
    for obj in mlb_data.objects:
        emp = bpy.data.objects.new(
            f"{node_prefix}_{ti:03d}_{bi}_NODE_{obj.index:03d}", None
        )
        emp.empty_display_type = "PLAIN_AXES"
        emp.empty_display_size = 2.5
        evalf = obj.evalflags
        if is_room:
            if evalf & 0x1:
                emp.location = (0.0, 0.0, 0.0)
            else:
                emp.location = convert_pos(obj.pos)
            ax, ay, az = obj.ang
            if evalf & 0x2:
                ax = ay = az = 0
            set_rotation(emp, ax, ay, az, False, bool(evalf & 0x20))
            scl = obj.scl if not (evalf & 0x4) else (1.0, 1.0, 1.0)
            emp.scale = convert_scale(scl)
        else:
            emp.location = convert_pos(obj.pos)
            set_rotation(emp, obj.ang[0], obj.ang[1], obj.ang[2])
            emp.scale = (1.0, 1.0, 1.0)
        if obj.hidden:
            emp.hide_viewport = True
        empties[obj.index] = emp
        tcoll.objects.link(emp)

    for obj in mlb_data.objects:
        seen = {obj.index}
        cur = mlb_data.object_index_of(obj.child)
        while cur != -1 and cur not in seen:
            seen.add(cur)
            empties[cur].parent = empties[obj.index]
            cur = mlb_data.object_index_of(mlb_data.objects[cur].sibling)

    if xform is not None:
        for emp in empties.values():
            if emp.parent is not None:
                continue
            local = (
                Matrix.Translation(emp.location)
                @ emp.rotation_euler.to_matrix().to_4x4()
            )
            baked = xform @ local
            emp.location = baked.to_translation()
            emp.rotation_euler = baked.to_euler("XYZ")
    return empties


def _import_skinned(
    stem,
    ti,
    bi,
    mlb_data,
    masks,
    lip_pool,
    apply_motions,
    arm_obj,
    bone_names,
    bone_worlds,
    skin_weights,
    tex_repo,
    tex_assign,
    node_prefix,
    tcoll,
    mesh_cache,
):
    face_mask, face_idx = _face_target(
        masks, mlb_data, arm_obj, lip_pool, apply_motions
    )
    tex_table = _tex_table(tex_assign, ti, bi)
    tex_names = mlb_data.texlist.names
    created = {}
    for obj, model in _iter_meshable(mlb_data):
        weights = _resolve_weights(skin_weights, obj.model_index, len(model.verts))
        if weights is None and obj.index in bone_names:
            weights = [(obj.index, 1.0)] * len(model.verts)
        key = f"{stem}{ti:03d}_{bi}_{obj.index:03d}_{obj.model_index}"
        mesh_name = f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}"
        mesh = _get_mesh(
            mesh_cache,
            key,
            mesh_name,
            model,
            tex_repo,
            tex_table,
            tex_names,
            bone_worlds.get(obj.index),
        )
        if mesh is None:
            continue
        mobj = _new_mesh_object(
            mesh_name,
            mesh,
            tcoll,
            arm_obj,
            obj.hidden,
        )
        created[obj.index] = mobj
        mod = mobj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = arm_obj
        if weights is not None:
            _assign_vertex_groups(mobj, weights, bone_names)
        if len(mobj.vertex_groups) == 0 and bone_names:
            fallback = next(iter(bone_names.values()))
            g = mobj.vertex_groups.new(name=fallback)
            try:
                g.add(list(range(len(model.verts))), 1.0, "REPLACE")
            except RuntimeError:
                pass
        if face_mask is not None and obj.index == face_idx:
            _add_face_shapes(
                mobj,
                model,
                face_mask,
                bone_worlds.get(obj.index),
            )
    return created


def _import_static(
    stem,
    ti,
    bi,
    mlb_data,
    is_room,
    xform,
    tex_repo,
    tex_assign,
    node_prefix,
    tcoll,
    mesh_cache,
):
    empties = _build_empties(node_prefix, ti, bi, mlb_data, is_room, xform, tcoll)
    tex_table = _tex_table(tex_assign, ti, bi)
    tex_names = mlb_data.texlist.names
    for obj, model in _iter_meshable(mlb_data):
        key = f"{stem}{ti:03d}_{bi}_{obj.model_index}"
        mesh = _get_mesh(
            mesh_cache,
            key,
            f"{node_prefix}_{ti:03d}_{bi}_{obj.model_index}",
            model,
            tex_repo,
            tex_table,
            tex_names,
        )
        if mesh is None:
            continue
        _new_mesh_object(
            f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}",
            mesh,
            tcoll,
            empties[obj.index],
            obj.hidden,
        )


def import_models(stem, rdx, root, tex_repo, kinds, apply_motions, rom_mtn):
    allowed = {"room", "actor", "obj", "item"} if kinds is None else set(kinds)
    coll = create_collection("MDL", root)
    mesh_cache = {}
    node_prefix = f"{stem}MDL"

    table_types, model_xforms = model_placements(rdx, rom_mtn)
    tbl_map = rdx.model_table_map()
    arms = {}
    tex_assign = rdx.texture_assignment() if tex_repo is not None else {}
    for ti, table in enumerate(rdx.models):
        kind = table_types.get(ti, "room")
        if kind not in allowed:
            continue
        actor_id = None
        entry = tbl_map.get(ti)
        if (
            entry is not None
            and entry[0] == "actor"
            and entry[1] is not None
            and 0 <= entry[1] < len(rdx.actor)
        ):
            actor_id = rdx.actor[entry[1]].id
        tcoll = create_collection(f"MDL_{ti:03d}", coll)
        is_room = kind == "room"
        masks = _load_masks(table, rdx)
        xform = model_xforms.get(ti)
        mlb_list = []
        for bo, bs in table.blobs:
            mlb_list.append(_read_mlb(rdx, bo, bs))
        if is_room or not mlb_list or all(m is None for m in mlb_list):
            for bi, mlb_data in enumerate(mlb_list):
                if mlb_data is None:
                    continue
                _import_static(
                    stem,
                    ti,
                    bi,
                    mlb_data,
                    is_room,
                    xform,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
            continue
        per = _parse_table_skins(rdx, table, mlb_list)
        rig_bi = -1
        best = (-1, -1, -1)
        for bi, mlb_data in enumerate(mlb_list):
            key = _display_score(mlb_data) if mlb_data is not None else (-1, -1, -1)
            if key > best:
                best = key
                rig_bi = bi
        if rig_bi < 0 or mlb_list[rig_bi] is None or not mlb_list[rig_bi].objects:
            for bi, mlb_data in enumerate(mlb_list):
                if mlb_data is None:
                    continue
                _import_static(
                    stem,
                    ti,
                    bi,
                    mlb_data,
                    is_room,
                    xform,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
            continue
        rig_weights = per[rig_bi] if rig_bi < len(per) else {}
        arm_obj = None
        bone_names = {}
        bone_worlds = {}
        if rig_weights or kind == "actor":
            try:
                arm_obj, bone_names, bone_worlds, arm_parent = build_armature(
                    f"{node_prefix}_{ti:03d}",
                    mlb_list[rig_bi],
                    is_room,
                    xform,
                    tcoll,
                    _stiff_set(rig_weights),
                )
                arms[ti] = (arm_obj, bone_names, arm_parent, mlb_list[rig_bi].objects)
            except (ValueError, RuntimeError) as exc:
                print(f"RDX: armature build failed @{table.blobs[rig_bi][0]:#x}: {exc}")
                arm_obj = None
        pairs = []
        for s, t in MORPH_PAIRS.get(actor_id, ()):
            if (
                0 <= s < len(mlb_list)
                and 0 <= t < len(mlb_list)
                and _morph_verified(mlb_list[s], mlb_list[t])
            ):
                pairs.append((s, t))
        morph_src_map = dict(pairs)
        morph_tgt_set = {t for _, t in pairs}
        for bi, mlb_data in enumerate(mlb_list):
            if mlb_data is None:
                continue
            worlds = None
            if bi == rig_bi and arm_obj is not None:
                created = _import_skinned(
                    stem,
                    ti,
                    bi,
                    mlb_data,
                    masks,
                    rdx.lip_pool,
                    apply_motions,
                    arm_obj,
                    bone_names,
                    bone_worlds,
                    rig_weights,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
                worlds = bone_worlds
            elif arm_obj is not None:
                if _skeleton_compatible(mlb_list[rig_bi], mlb_data):
                    own_w = per[bi] if bi < len(per) and per[bi] else rig_weights
                    arm, names, arm_worlds = arm_obj, bone_names, bone_worlds
                    hide = False
                else:
                    if not [*_iter_meshable(mlb_data)]:
                        continue
                    own_w = per[bi] if bi < len(per) else {}
                    try:
                        var_arm, var_names, var_worlds, _ = build_armature(
                            f"{node_prefix}_{ti:03d}_{bi}",
                            mlb_data,
                            is_room,
                            xform,
                            tcoll,
                            _stiff_set(own_w),
                        )
                    except (ValueError, RuntimeError) as exc:
                        print(
                            f"RDX: variant armature build failed @{table.blobs[bi][0]:#x}: {exc}"
                        )
                        continue
                    arm, names, arm_worlds = var_arm, var_names, var_worlds
                    hide = True
                created = _import_skinned(
                    stem,
                    ti,
                    bi,
                    mlb_data,
                    masks,
                    rdx.lip_pool,
                    apply_motions,
                    arm,
                    names,
                    arm_worlds,
                    own_w,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
                if hide:
                    for mobj in (arm, *created.values()):
                        mobj.hide_viewport = True
                        mobj.hide_render = True
                    continue
                worlds = arm_worlds
            else:
                _import_static(
                    stem,
                    ti,
                    bi,
                    mlb_data,
                    is_room,
                    xform,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
                continue
            tgt = morph_src_map.get(bi)
            if tgt is not None and worlds is not None:
                _apply_morph_key(created, mlb_list[tgt], worlds, f"MORPH_{tgt}")
            if bi in morph_tgt_set:
                for mobj in created.values():
                    mobj.hide_viewport = True
                    mobj.hide_render = True
    return arms
