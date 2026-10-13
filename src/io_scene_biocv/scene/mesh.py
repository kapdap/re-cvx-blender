import bpy

from .common import convert_normal, convert_pos


def _tex_alpha_kind(tex_repo, tex_table, texid):
    try:
        pics = tex_repo.table_pics(tex_table)
        if 0 <= texid < len(pics):
            bi, pi, variant = pics[texid]
            return tex_repo.alpha_kind(tex_table, bi, pi, variant) != "OPAQUE"
    except (AttributeError, IndexError, TypeError):
        pass
    return False


def _face_material_alpha(model, mat_idx):
    materials = model.materials
    entry = materials[mat_idx] if 0 <= mat_idx < len(materials) else None
    if entry is None:
        return 1.0
    return entry["alpha"]


def _face_slot_key(model, tex_repo, tex_table, texid, blend, mat_idx, nat=False):
    a = _face_material_alpha(model, mat_idx) if blend else 1.0
    if not blend:
        return (texid, False, 1.0, nat)
    if a < 0.999:
        return (texid, True, round(a, 3), nat)
    if _tex_alpha_kind(tex_repo, tex_table, texid):
        return (texid, True, 1.0, nat)
    return (texid, False, 1.0, nat)


def build_mesh(mesh_key, model, tex_repo, tex_table, tex_names):
    mesh_name = f"MDL_{mesh_key}_MESH"
    mesh = bpy.data.meshes.get(mesh_name)
    if mesh is not None:
        return mesh
    verts = [convert_pos(v) for v in model.verts]
    mesh = bpy.data.meshes.new(mesh_name)
    try:
        mesh.from_pydata(verts, [], model.faces)
    except (ValueError, RuntimeError) as exc:
        print(f"RDX: from_pydata failed for {mesh_key}: {exc}")
        return None
    mesh.update()

    flats = list(model.face_flat)
    if len(flats) == len(model.faces) and len(mesh.polygons) == len(model.faces):
        if "sharp_face" in mesh.attributes:
            sharp = mesh.attributes["sharp_face"]
            for poly, flat in zip(mesh.polygons, flats):
                try:
                    sharp.data[poly.index].value = bool(flat)
                except (AttributeError, IndexError, TypeError):
                    pass
        else:
            for poly, flat in zip(mesh.polygons, flats):
                try:
                    poly.use_smooth = not flat
                except AttributeError:
                    pass

    normals = model.normals
    if len(normals) == len(model.verts) and model.faces:
        loop_normals = []
        has_source = False
        for face in model.faces:
            for vi in face:
                if 0 <= vi < len(normals):
                    n = convert_normal(normals[vi])
                    if n != (0.0, 0.0, 0.0):
                        has_source = True
                    loop_normals.append(n)
                else:
                    loop_normals.append((0.0, 0.0, 0.0))
        if has_source and len(loop_normals) == len(mesh.loops):
            try:
                mesh.normals_split_custom_set(loop_normals)
            except (RuntimeError, ValueError, TypeError) as exc:
                print(f"RDX: normals assign failed for {mesh_key}: {exc}")

    if model.uvs and len(model.uvs) == len(model.faces):
        try:
            uv_layer = mesh.uv_layers.new(name="UVMap")
            for poly, uvs in zip(mesh.polygons, model.uvs):
                for loop_idx, (u, v) in zip(poly.loop_indices, uvs):
                    uv_layer.data[loop_idx].uv = (u, 1.0 - v)
        except (RuntimeError, AttributeError) as exc:
            print(f"RDX: UV assign failed for {mesh_key}: {exc}")

    if tex_repo is not None and tex_table is not None and model.faces:
        blends = list(model.face_blend)
        if len(blends) != len(model.faces):
            blends = [False] * len(model.faces)
        nats = list(model.face_nat)
        if len(nats) != len(model.faces):
            nats = [False] * len(model.faces)
        mats_list = list(model.mats)
        if len(mats_list) != len(model.faces):
            mats_list = [-1] * len(model.faces)
        keys = [
            _face_slot_key(model, tex_repo, tex_table, tid, blend, mi, nat)
            for tid, blend, mi, nat in zip(model.texids, blends, mats_list, nats)
        ]
        slot_of = {}
        for key in sorted(set(keys)):
            tid, transparent, a, nat = key
            mat = tex_repo.material(
                tex_table,
                tid,
                transparent,
                (a if transparent else 1.0),
                nat,
                tex_names,
            )
            if mat is not None:
                mesh.materials.append(mat)
                slot_of[key] = len(mesh.materials) - 1
        for poly, key in zip(mesh.polygons, keys):
            if key in slot_of:
                poly.material_index = slot_of[key]
    return mesh
