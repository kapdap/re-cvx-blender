import bpy
from mathutils import Matrix, Vector

from ..rdx import mask, mlb, nj, skin
from .armature import build_armature
from .common import EMPTY_SIZE, convert_pos, convert_scale, create_collection
from .mesh import build_mesh
from .placements import model_placements
from .rotation import ninja_euler, set_rotation


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


def _ensure_armature(
    ti,
    table,
    mlb_data,
    is_room,
    xform,
    tcoll,
    rdx,
    bo,
    node_prefix,
    skin_weights,
    arms,
    arm_obj,
    bone_names,
    bone_worlds,
):
    if is_room or arm_obj is not None:
        return arm_obj, bone_names, bone_worlds
    if not table.skins or not mlb_data.objects:
        return arm_obj, bone_names, bone_worlds
    try:
        parsed = None
        for so, ss in table.skins:
            try:
                parsed = skin.parse_skin(
                    rdx.data, so, ss, len(mlb_data.objects), rdx.endian
                )
                break
            except skin.SkinError as exc:
                print(f"RDX: SKIN decode failed @{so:#x}: {exc}")
                continue
        if parsed:
            for node, weights in parsed:
                if node < len(mlb_data.objects):
                    mi = mlb_data.objects[node].model_index
                    if mi >= 0:
                        skin_weights.setdefault(mi, weights)
        if skin_weights:
            arm_obj, bone_names, bone_worlds, arm_parent = build_armature(
                f"{node_prefix}_{ti:03d}_ARM",
                mlb_data,
                is_room,
                xform,
                tcoll,
            )
            arms[ti] = (arm_obj, bone_names, arm_parent, mlb_data.objects)
    except (ValueError, RuntimeError) as exc:
        print(f"RDX: armature build failed @{bo:#x}: {exc}")
        arm_obj = None
    return arm_obj, bone_names, bone_worlds


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


def _rigid_indices(masks, mlb_data):
    rigid = set()
    for mk in masks:
        for oid in list(mk.eye_ids) + [mk.tang_id, mk.tooth_id]:
            hit = mask.search_object(mlb_data, oid)
            if hit is not None:
                rigid.add(hit.index)
    return rigid


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


def _stiffness_map(mlb_data):
    return {
        n.index: ninja_euler(-n.ang[0], -n.ang[1], -n.ang[2]).to_matrix()
        for n in mlb_data.objects
    }


def _skin_point(co, bind, entry, stiffness):
    if bind is not None:
        co = bind @ co
    if entry is not None:
        bone, w = entry
        if w < 1.0:
            c = stiffness.get(bone)
            if c is not None:
                co = (1.0 - w) * (c @ co) + w * co
    return co


def _cached_mesh(cache, key, model, tex_repo, tex_table, tex_names):
    mesh = cache.get(key)
    if mesh is None:
        mesh = build_mesh(key, model, tex_repo, tex_table, tex_names)
        cache[key] = mesh
    return mesh


def _skinned_mesh(
    cache, key, model, tex_repo, tex_table, bind, weights, stiffness, tex_names
):
    mesh = cache.get(key)
    if mesh is None:
        mesh = build_mesh(key, model, tex_repo, tex_table, tex_names)
        if mesh is not None:
            for vi, v in enumerate(mesh.vertices):
                entry = weights[vi] if weights is not None else None
                v.co = _skin_point(v.co, bind, entry, stiffness)
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
    for vi, (bone, _w) in enumerate(weights):
        bn = bone_names.get(bone)
        if bn is None:
            continue
        g = groups.get(bn)
        if g is None:
            g = mobj.vertex_groups.get(bn)
            if g is None:
                g = mobj.vertex_groups.new(name=bn)
            groups[bn] = g
        try:
            g.add([vi], 1.0, "REPLACE")
        except RuntimeError:
            pass


def _add_face_shapes(mobj, model, weights, face_mask, bind, stiffness):
    try:
        if mobj.data.shape_keys is None:
            mobj.shape_key_add(name="Basis", from_mix=False)
        for pi, par in enumerate(face_mask.face):
            disp = mask.apply_muscle(model.verts, face_mask, par[0])
            kb = mobj.shape_key_add(name=f"FM_{pi:02d}", from_mix=False)
            kb.value = 0.0
            for vi, ((x, y, z), kd) in enumerate(zip(disp, kb.data)):
                entry = weights[vi] if weights is not None else None
                kd.co = _skin_point(Vector((x, -z, y)), bind, entry, stiffness)
    except (RuntimeError, ValueError, IndexError):
        pass


def _build_empties(node_prefix, ti, bi, mlb_data, is_room, xform, tcoll):
    empties = {}
    for obj in mlb_data.objects:
        emp = bpy.data.objects.new(
            f"{node_prefix}_{ti:03d}_{bi}_NODE_{obj.index:03d}", None
        )
        emp.empty_display_type = "PLAIN_AXES"
        emp.empty_display_size = EMPTY_SIZE * 0.5
        evalf = obj.evalflags
        if is_room:
            if evalf & 0x1:
                emp.location = (0.0, 0.0, 0.0)
            else:
                emp.location = convert_pos(obj.pos)
            ax, ay, az = obj.ang
            if evalf & 0x2:
                ax = ay = az = 0
            set_rotation(emp, ax, ay, az, zxy=bool(evalf & 0x20))
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
    stiffness = _stiffness_map(mlb_data)
    face_mask, face_idx = _face_target(
        masks, mlb_data, arm_obj, lip_pool, apply_motions
    )
    rigid = _rigid_indices(masks, mlb_data)
    tex_table = _tex_table(tex_assign, ti, bi)
    tex_names = mlb_data.texlist.names
    for obj, model in _iter_meshable(mlb_data):
        weights = _resolve_weights(skin_weights, obj.model_index, len(model.verts))
        if weights is None and obj.index in rigid:
            weights = [(obj.index, 1.0)] * len(model.verts)
        key = f"{stem}{ti:03d}_{bi}_{obj.index:03d}_{obj.model_index}"
        mesh = _skinned_mesh(
            mesh_cache,
            key,
            model,
            tex_repo,
            tex_table,
            bone_worlds.get(obj.index),
            weights,
            stiffness,
            tex_names,
        )
        if mesh is None:
            continue
        mobj = _new_mesh_object(
            f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}",
            mesh,
            tcoll,
            arm_obj,
            obj.hidden,
        )
        mod = mobj.modifiers.new(name="Armature", type="ARMATURE")
        mod.object = arm_obj
        if weights is not None:
            _assign_vertex_groups(mobj, weights, bone_names)
        if face_mask is not None and obj.index == face_idx:
            _add_face_shapes(
                mobj,
                model,
                weights,
                face_mask,
                bone_worlds.get(obj.index),
                stiffness,
            )


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
        mesh = _cached_mesh(mesh_cache, key, model, tex_repo, tex_table, tex_names)
        if mesh is None:
            continue
        _new_mesh_object(
            f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}",
            mesh,
            tcoll,
            empties[obj.index],
            obj.hidden,
        )


def import_models(stem, rdx, root, tex_repo, kinds, apply_motions):
    allowed = {"room", "actor", "obj", "item"} if kinds is None else set(kinds)
    coll = create_collection("MDL", root)
    mesh_cache = {}
    node_prefix = f"{stem}MDL"

    table_types, model_xforms = model_placements(rdx)
    arms = {}
    tex_assign = rdx.texture_assignment() if tex_repo is not None else {}
    for ti, table in enumerate(rdx.models):
        kind = table_types.get(ti, "room")
        if kind not in allowed:
            continue
        tcoll = create_collection(f"MDL_{ti:03d}", coll)
        is_room = kind == "room"
        arm_obj = None
        bone_names = {}
        bone_worlds = {}
        skin_weights = {}
        masks = _load_masks(table, rdx)
        for bi, (bo, bs) in enumerate(table.blobs):
            mlb_data = _read_mlb(rdx, bo, bs)
            if mlb_data is None:
                continue

            arm_obj, bone_names, bone_worlds = _ensure_armature(
                ti,
                table,
                mlb_data,
                is_room,
                model_xforms.get(ti),
                tcoll,
                rdx,
                bo,
                node_prefix,
                skin_weights,
                arms,
                arm_obj,
                bone_names,
                bone_worlds,
            )

            if arm_obj is not None:
                _import_skinned(
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
                    skin_weights,
                    tex_repo,
                    tex_assign,
                    node_prefix,
                    tcoll,
                    mesh_cache,
                )
                continue

            _import_static(
                stem,
                ti,
                bi,
                mlb_data,
                is_room,
                model_xforms.get(ti),
                tex_repo,
                tex_assign,
                node_prefix,
                tcoll,
                mesh_cache,
            )
    bpy.context.view_layer.update()
    return arms
