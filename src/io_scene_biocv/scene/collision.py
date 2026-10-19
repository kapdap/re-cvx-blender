import bpy

from .common import convert_pos, create_collection


def _ensure_material(name, color):
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = color
    nodes = mat.node_tree.nodes
    bsdf = next((n for n in nodes if n.type == "BSDF_PRINCIPLED"), None)
    alpha = color[3] if len(color) > 3 else 1.0
    if bsdf is not None:
        base_sock = bsdf.inputs.get("Base Color")
        if base_sock is None:
            try:
                base_sock = bsdf.inputs[0]
            except IndexError:
                base_sock = None
        if base_sock is not None:
            base_sock.default_value = (color[0], color[1], color[2], color[3])
        alpha_sock = bsdf.inputs.get("Alpha")
        if alpha_sock is not None:
            alpha_sock.default_value = alpha
    if alpha < 1.0:
        mat.surface_render_method = "BLENDED"
    return mat


def import_boxes(name, entries, root, color):
    coll = create_collection(name, root)
    mat = _ensure_material(f"{root.name}_{name}", color)
    box_faces = [
        (0, 1, 2, 3),
        (0, 4, 5, 1),
        (0, 3, 7, 4),
        (2, 3, 7, 6),
        (4, 5, 6, 7),
        (1, 2, 6, 5),
    ]
    quad_faces = [(0, 1, 2, 3)]
    for i, e in enumerate(entries):
        lo, hi = e.bounds()
        lx, ly, lz = lo
        hx, hy, hz = hi
        x0, y0, z0 = convert_pos((lx, ly, lz))
        x1, y1, z1 = convert_pos((hx, hy, hz))

        bx0, bx1 = (x0, x1)
        by0, by1 = (min(y0, y1), max(y0, y1))
        bz0, bz1 = (z0, z1)
        if bz0 == bz1:
            verts = [
                (bx0, by0, bz0),
                (bx1, by0, bz0),
                (bx1, by1, bz0),
                (bx0, by1, bz0),
            ]
            faces = quad_faces
        else:
            verts = [
                (bx0, by0, bz0),
                (bx1, by0, bz0),
                (bx1, by1, bz0),
                (bx0, by1, bz0),
                (bx0, by0, bz1),
                (bx1, by0, bz1),
                (bx1, by1, bz1),
                (bx0, by1, bz1),
            ]
            faces = box_faces
        mesh = bpy.data.meshes.new(f"{name}_{i:03d}")
        mesh.from_pydata(verts, [], faces)
        mesh.materials.append(mat)
        mesh.update()
        obj = bpy.data.objects.new(f"{name}_{i:03d}", mesh)
        obj.display_type = "SOLID"
        obj.show_wire = True
        obj.show_all_edges = True
        obj.color = (color[0], color[1], color[2], color[3])
        coll.objects.link(obj)
