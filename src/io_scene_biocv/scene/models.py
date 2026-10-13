import bpy
from mathutils import Matrix

from ..rdx import mlb, nj, skin
from .armature import build_armature
from .common import EMPTY_SIZE, convert_pos, convert_scale, create_collection
from .mesh import build_mesh
from .placements import model_placements
from .rotation import ninja_euler, set_rotation


def import_models(stem, rdx, root, tex_repo, tex_assign, kinds=None):
    allowed = {"room", "actor", "obj", "item"} if kinds is None else set(kinds)
    coll = create_collection("MDL", root)
    mesh_cache = {}
    node_prefix = f"{stem}MDL"

    table_types, model_xforms = model_placements(rdx)
    arms = {}
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
        for bi, (bo, bs) in enumerate(table.blobs):
            try:
                mlb_data = mlb.read_mlb(rdx.data, bo, bs, rdx.endian)
            except nj.NjError as exc:
                print(f"RDX: MLB decode failed @{bo:#x}: {exc}")
                continue

            if not is_room and arm_obj is None and table.skins and mlb_data.objects:
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
                        for mno, weights in parsed:
                            skin_weights.setdefault(mno, weights)
                    if skin_weights:
                        arm_obj, bone_names, bone_worlds, arm_parent = build_armature(
                            f"{node_prefix}_{ti:03d}_ARM",
                            mlb_data,
                            is_room,
                            model_xforms.get(ti),
                            tcoll,
                        )
                        arms[ti] = (arm_obj, bone_names, arm_parent, mlb_data.objects)
                except (ValueError, RuntimeError) as exc:
                    print(f"RDX: armature build failed @{bo:#x}: {exc}")
                    arm_obj = None

            if arm_obj is not None:
                stiffness = {}
                for n in mlb_data.objects:
                    stiffness[n.index] = ninja_euler(
                        -n.ang[0], -n.ang[1], -n.ang[2]
                    ).to_matrix()
                for obj in mlb_data.objects:
                    if obj.model_index < 0 or obj.model_index >= len(mlb_data.models):
                        continue
                    model = mlb_data.models[obj.model_index]
                    if model is None or not model.faces:
                        continue
                    weights = skin_weights.get(obj.model_index)
                    if weights is None and len(skin_weights) == 1:
                        weights = next(iter(skin_weights.values()))
                    key = f"{stem}{ti:03d}_{bi}_{obj.index:03d}_{obj.model_index}"
                    tex_table = tex_assign.get((ti, bi), tex_assign.get((ti, 0)))
                    mesh = mesh_cache.get(key)
                    if mesh is None:
                        mesh = build_mesh(key, model, tex_repo, tex_table)
                        if mesh is not None:
                            bind = bone_worlds.get(obj.index)
                            if bind is not None:
                                for v in mesh.vertices:
                                    v.co = bind @ v.co
                            if weights is not None and len(weights) == len(model.verts):
                                for vi, v in enumerate(mesh.vertices):
                                    bone, w = weights[vi]
                                    if w < 1.0:
                                        c = stiffness.get(bone)
                                        if c is not None:
                                            v.co = (1.0 - w) * (c @ v.co) + w * v.co
                            mesh.update()
                        mesh_cache[key] = mesh
                    if mesh is None:
                        continue
                    mobj = bpy.data.objects.new(
                        f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}", mesh
                    )
                    tcoll.objects.link(mobj)
                    mobj.parent = arm_obj
                    mod = mobj.modifiers.new(name="Armature", type="ARMATURE")
                    mod.object = arm_obj
                    if weights is not None and len(weights) == len(model.verts):
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
                    if obj.hidden:
                        mobj.hide_viewport = True
                        mobj.hide_render = True
                continue

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

            xform = model_xforms.get(ti)
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

            for obj in mlb_data.objects:
                if obj.model_index < 0 or obj.model_index >= len(mlb_data.models):
                    continue
                model = mlb_data.models[obj.model_index]
                if model is None or not model.faces:
                    continue
                key = f"{stem}{ti:03d}_{bi}_{obj.model_index}"
                tex_table = tex_assign.get((ti, bi), tex_assign.get((ti, 0)))
                mesh = mesh_cache.get(key)
                if mesh is None:
                    mesh = build_mesh(key, model, tex_repo, tex_table)
                    mesh_cache[key] = mesh
                if mesh is None:
                    continue
                mobj = bpy.data.objects.new(
                    f"{node_prefix}_{ti:03d}_{bi}_{obj.index:03d}", mesh
                )
                tcoll.objects.link(mobj)
                mobj.parent = empties[obj.index]
                if obj.hidden:
                    mobj.hide_viewport = True
                    mobj.hide_render = True
    bpy.context.view_layer.update()
    return arms
