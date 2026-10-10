import bpy

from .common import convert_pos


def _face_material_alpha(model, mat_idx):
    try:
        materials = getattr(model, "materials", None)
        if materials is None:
            return 1.0
        entry = materials[mat_idx] if 0 <= mat_idx < len(materials) else None
    except (TypeError, IndexError):
        return 1.0
    if not isinstance(entry, dict):
        return 1.0
    try:
        return float(entry.get("alpha", 1.0))
    except (TypeError, ValueError):
        return 1.0


def _tex_has_real_alpha(tex_repo, tex_table, texid):
    try:
        pics = tex_repo.table_pics(tex_table)
        if 0 <= texid < len(pics):
            bi, pi, variant = pics[texid]
            return tex_repo.alpha_kind(tex_table, bi, pi, variant) != "OPAQUE"
    except (AttributeError, IndexError, TypeError):
        pass
    return False


def _face_slot_key(model, tex_repo, tex_table, texid, blend, mat_idx):

    a = _face_material_alpha(model, mat_idx) if blend else 1.0
    if not blend:
        return (texid, False, 1.0)
    if a < 0.999:
        return (texid, True, round(a, 3))
    if _tex_has_real_alpha(tex_repo, tex_table, texid):
        return (texid, True, 1.0)
    return (texid, False, 1.0)


def build_mesh(mesh_key, model, tex_repo, tex_table):
    mesh_name = "MDL_%s_MESH" % mesh_key
    mesh = bpy.data.meshes.get(mesh_name)
    if mesh is not None:
        return mesh
    verts = [convert_pos(v) for v in model.verts]
    mesh = bpy.data.meshes.new(mesh_name)
    try:
        mesh.from_pydata(verts, [], model.faces)
    except (ValueError, RuntimeError) as exc:
        print("RDX: from_pydata failed for %s: %s" % (mesh_key, exc))
        return None
    mesh.update()

    if model.uvs and len(model.uvs) == len(model.faces):
        try:
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly, uvs in zip(mesh.polygons, model.uvs):
                for loop_idx, (u, v) in zip(poly.loop_indices, uvs):
                    uv_layer.data[loop_idx].uv = (u, 1.0 - v)
        except (RuntimeError, AttributeError) as exc:
            print("RDX: UV assign failed for %s: %s" % (mesh_key, exc))

    if tex_repo is not None and tex_table is not None and model.faces:
        blends = list(getattr(model, "face_blend", []))
        if len(blends) != len(model.faces):
            blends = [False] * len(model.faces)
        mats_list = list(getattr(model, "mats", []))
        if len(mats_list) != len(model.faces):
            mats_list = [-1] * len(model.faces)
        keys = [
            _face_slot_key(model, tex_repo, tex_table, tid, blend, mi)
            for tid, blend, mi in zip(model.texids, blends, mats_list)
        ]
        slot_of = {}
        for key in sorted(set(keys)):
            tid, transparent, a = key
            mat = tex_repo.material(
                tex_table,
                tid,
                transparent=transparent,
                alpha=(a if transparent else 1.0),
            )
            if mat is not None:
                mesh.materials.append(mat)
                slot_of[key] = len(mesh.materials) - 1
        for poly, key in zip(mesh.polygons, keys):
            if key in slot_of:
                poly.material_index = slot_of[key]
    return mesh
