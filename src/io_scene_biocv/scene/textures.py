import bpy

from ..rdx import tex

_FWD = ((-1, 0, 1), (0, -1, 1), (-1, -1, 2), (1, -1, 2))
_BWD = ((1, 0, 1), (0, 1, 1), (1, 1, 2), (-1, 1, 2))
_MATTE = (
    ("Metallic", 6, 0.0),
    ("Roughness", 7, 0.9),
    ("Specular IOR Level", None, 0.0),
    ("Specular", None, 0.0),
)


def _get(coll, name=None, index=None):
    if coll is None:
        return None
    if name is not None:
        sock = coll.get(name)
        if sock is not None:
            return sock
    if index is not None:
        try:
            return coll[index]
        except (IndexError, KeyError):
            return None
    return None


def _bsdf(nodes):
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return nodes.get("Principled BSDF")


def _safe_link(links, out_sock, in_sock):
    if out_sock is None or in_sock is None:
        return
    try:
        links.new(out_sock, in_sock)
    except RuntimeError:
        pass


def _make_matte(bsdf):
    if bsdf is None:
        return
    for name, idx, val in _MATTE:
        sock = _get(bsdf.inputs, name, idx)
        if sock is not None:
            sock.default_value = val


def _set_blend(mat, transparent, cutout=False):
    if not transparent:
        mat.surface_render_method = "DITHERED"
        mat.use_transparency_overlap = False
        mat.alpha_threshold = 0.5
    elif cutout:
        mat.surface_render_method = "DITHERED"
        mat.use_transparency_overlap = True
        mat.alpha_threshold = 0.5
    else:
        mat.surface_render_method = "BLENDED"
        mat.use_transparency_overlap = True


def _unlink_alpha(mat, bsdf):
    if bsdf is None:
        return None
    if mat.node_tree is None:
        return None
    alpha_in = _get(bsdf.inputs, "Alpha")
    if alpha_in is None:
        return None
    for link in list(alpha_in.links):
        mat.node_tree.links.remove(link)
    alpha_in.default_value = 1.0
    return alpha_in


def _flat_alpha(mat, bsdf, alpha):
    _set_blend(mat, True, False)
    sock = _get(bsdf.inputs, "Alpha") if bsdf is not None else None
    if sock is not None:
        sock.default_value = alpha


def _bleed_transparent_rgb(raw, w, h):
    if not raw or w <= 0 or h <= 0:
        return raw
    n = w * h
    if len(raw) < n * 4:
        return raw
    if 0 not in raw[3::4]:
        return raw
    INF = 1 << 30
    dist = [0] * n
    sr = [0] * n
    sg = [0] * n
    sb = [0] * n
    for idx in range(n):
        o = idx * 4
        if raw[o + 3]:
            sr[idx] = raw[o]
            sg[idx] = raw[o + 1]
            sb[idx] = raw[o + 2]
        else:
            dist[idx] = INF

    def sweep(xs, ys, neigh):
        for y in ys:
            base = y * w
            for x in xs:
                i = base + x
                if dist[i] == 0:
                    continue
                best = dist[i]
                bi = -1
                for dx, dy, cost in neigh:
                    nx, ny = x + dx, y + dy
                    if 0 <= nx < w and 0 <= ny < h:
                        j = ny * w + nx
                        nd = dist[j] + cost
                        if nd < best:
                            best = nd
                            bi = j
                if bi >= 0:
                    dist[i] = best
                    sr[i] = sr[bi]
                    sg[i] = sg[bi]
                    sb[i] = sb[bi]

    sweep(range(w), range(h), _FWD)
    sweep(range(w - 1, -1, -1), range(h - 1, -1, -1), _BWD)
    out = bytearray(raw)
    for idx in range(n):
        if raw[idx * 4 + 3] == 0 and dist[idx] != INF:
            out[idx * 4] = sr[idx]
            out[idx * 4 + 1] = sg[idx]
            out[idx * 4 + 2] = sb[idx]
    return bytes(out)


def _push_pixels(img, raw, w, h):
    if len(img.pixels) != w * h * 4:
        return
    rowlen = w * 4
    flat = [0.0] * (w * h * 4)
    for row in range(h):
        src = (h - 1 - row) * rowlen
        dst = row * rowlen
        flat[dst : dst + rowlen] = [b / 255.0 for b in raw[src : src + rowlen]]
    img.pixels = flat
    img.pack()


class TextureRepo:
    def __init__(self, rdx, prefix=""):
        self.rdx = rdx
        self.prefix = prefix
        self.images = {}
        self.materials = {}
        self._docs = {}
        self._pic_index = {}
        self._alpha_kind = {}

    def doc(self, table_idx, block_idx):
        key = (table_idx, block_idx)
        if key not in self._docs:
            blk = self.rdx.textures[table_idx].blocks[block_idx]
            try:
                pal = None
                if blk.kind in ("PVR", "GVR"):
                    _palnum, pli_entries = self.rdx.pli_state_at(table_idx, block_idx)
                    pal = pli_entries if _palnum > 0 else None
                self._docs[key] = tex.decode(self.rdx.data, blk.data_offset, pal)
            except (tex.TexError, ValueError):
                self._docs[key] = None
        return self._docs[key]

    def table_pics(self, table_idx):
        if table_idx not in self._pic_index:
            pics = []
            table = self.rdx.textures[table_idx]
            for bi, blk in enumerate(table.blocks):
                if blk.kind not in ("TIM2", "PVR", "GVR"):
                    continue
                doc = self.doc(table_idx, bi)
                if doc is None:
                    continue
                palnum, pli_entries = self.rdx.pli_state_at(table_idx, bi)
                for pi in range(len(doc.pictures)):
                    pic = doc.pictures[pi]
                    variants = (
                        [
                            lop
                            for lop, (_c, tf, _b, _e) in enumerate(pli_entries)
                            if tf == 0
                        ]
                        if not tex.is_vq_path(pic.pic_format) and palnum > 0
                        else []
                    )
                    if variants:
                        pics.extend((bi, pi, lop) for lop in variants)
                    else:
                        pics.append((bi, pi, None))
            self._pic_index[table_idx] = pics
        return self._pic_index[table_idx]

    def _variant_pixels(self, table_idx, block_idx, pic_idx, variant):
        doc = self.doc(table_idx, block_idx)
        if doc is None or pic_idx >= len(doc.pictures):
            return None, None
        pic = doc.pictures[pic_idx]
        if variant is None:
            return pic, pic.pixels
        _palnum, pli_entries = self.rdx.pli_state_at(table_idx, block_idx)
        pal_colors = [c for (c, _tf, _b, _e) in pli_entries]
        return pic, tex.apply_pal_sub(
            pic.image_type, pic.image_data, pic.pixels, pal_colors
        )

    def alpha_kind(self, table_idx, block_idx, pic_idx, variant=None):
        key = (table_idx, block_idx, pic_idx, variant)
        if key not in self._alpha_kind:
            kind = "OPAQUE"
            try:
                _pic, pixels = self._variant_pixels(
                    table_idx, block_idx, pic_idx, variant
                )
                if pixels is not None:
                    kind = tex.classify_alpha(pixels)
            except (AttributeError, IndexError, TypeError):
                kind = "OPAQUE"
            self._alpha_kind[key] = kind
        return self._alpha_kind[key]

    def _aliased_name(self, alias, table_idx, texid, suffix, used, pool, fallback):
        if not alias:
            return fallback
        name = f"{self.prefix}{alias}{suffix}"
        existing = pool.get(name)
        if existing is not None and any(m is existing for m in used.values()):
            name = f"{self.prefix}{alias}_T{table_idx}_{texid}{suffix}"
        return name

    def image(self, table_idx, block_idx, pic_idx, variant=None, alias=None):
        key = (table_idx, block_idx, pic_idx, variant)
        img = self.images.get(key)
        if img is not None:
            return img
        doc = self.doc(table_idx, block_idx)
        if doc is None or pic_idx >= len(doc.pictures):
            return None
        pic = doc.pictures[pic_idx]
        if pic.width <= 0 or pic.height <= 0 or not pic.pixels:
            return None
        kind = self.alpha_kind(table_idx, block_idx, pic_idx, variant)
        _pic, pixels = self._variant_pixels(table_idx, block_idx, pic_idx, variant)
        raw = pixels if pixels is not None else pic.pixels

        if kind == "OPAQUE" and not any(raw[3::4]):
            buf = bytearray(raw)
            for i in range(3, len(buf), 4):
                buf[i] = 255
            raw = bytes(buf)
        if kind != "OPAQUE":
            raw = _bleed_transparent_rgb(raw, pic.width, pic.height)
        vsuffix = f"_v{variant}" if variant is not None else ""
        try:
            texid = self.table_pics(table_idx).index((block_idx, pic_idx, variant))
        except ValueError:
            texid = alias = None
        name = self._aliased_name(
            alias,
            table_idx,
            texid,
            vsuffix,
            self.images,
            bpy.data.images,
            f"{self.prefix}TEX_{table_idx}_{block_idx}_{pic_idx}{vsuffix}",
        )
        img = bpy.data.images.get(name)
        if img is None:
            img = bpy.data.images.new(
                name, pic.width, pic.height, alpha=(kind != "OPAQUE")
            )
        _push_pixels(img, raw, pic.width, pic.height)
        img.alpha_mode = "STRAIGHT" if kind != "OPAQUE" else "NONE"
        img.colorspace_settings.name = "sRGB"
        self.images[key] = img
        return img

    def _fetch_image(self, table_idx, texid, alias):
        if table_idx < len(self.rdx.textures):
            pics = self.table_pics(table_idx)
            if 0 <= texid < len(pics):
                bi, pi, variant = pics[texid]
                return self.image(table_idx, bi, pi, variant, alias), self.alpha_kind(
                    table_idx, bi, pi, variant
                )
            print(f"RDX: texid {texid} out of range", flush=True)
        return None, "OPAQUE"

    def _wire_alpha(self, mat, bsdf, tex_node, alpha):
        if bsdf is None or tex_node is None or mat.node_tree is None:
            return
        alpha_in = _get(bsdf.inputs, "Alpha")
        alpha_out = _get(tex_node.outputs, "Alpha", 1)
        if alpha_in is not None and alpha_out is not None:
            if alpha < 1.0:
                math_node = mat.node_tree.nodes.new("ShaderNodeMath")
                math_node.operation = "MULTIPLY"
                math_node.inputs[1].default_value = alpha
                _safe_link(mat.node_tree.links, alpha_out, math_node.inputs[0])
                _safe_link(mat.node_tree.links, math_node.outputs[0], alpha_in)
            else:
                _safe_link(mat.node_tree.links, alpha_out, alpha_in)
        if alpha < 1.0 and alpha_in is not None and not list(alpha_in.links):
            alpha_in.default_value = alpha

    def material(
        self,
        table_idx,
        texid,
        transparent=False,
        alpha=1.0,
        nat=False,
        tex_names=None,
    ):
        alias = None
        if tex_names is not None and texid is not None and 0 <= texid < len(tex_names):
            alias = tex_names[texid] or None
        key = (table_idx, texid, transparent, alpha, nat, alias)
        mat = self.materials.get(key)
        if mat is not None:
            return mat
        img, kind = self._fetch_image(table_idx, texid, alias)
        suffix = ("_TN" if nat else "_T") if transparent else ("_N" if nat else "")
        name = self._aliased_name(
            alias,
            table_idx,
            texid,
            suffix,
            self.materials,
            bpy.data.materials,
            f"{self.prefix}RDX_{table_idx}_{texid}{suffix}",
        )
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        if not mat.use_nodes:
            mat.use_nodes = True
        tree = mat.node_tree
        bsdf = _bsdf(tree.nodes) if tree is not None else None
        _make_matte(bsdf)
        tex_node = None
        if img is not None and bsdf is not None and tree is not None:
            tex_node = tree.nodes.new("ShaderNodeTexImage")
            tex_node.image = img
            _safe_link(
                tree.links,
                _get(tex_node.outputs, "Color", 0),
                _get(bsdf.inputs, "Base Color", 0),
            )
        if tex_node is not None:
            if transparent and kind != "OPAQUE":
                _set_blend(mat, True, kind == "CUTOUT" and not nat)
                self._wire_alpha(mat, bsdf, tex_node, alpha)
            else:
                _set_blend(mat, False)
                _unlink_alpha(mat, bsdf)
                if transparent and alpha < 1.0:
                    _flat_alpha(mat, bsdf, alpha)
        else:
            mat.diffuse_color = (0.8, 0.8, 0.8, 1.0)
            if transparent and alpha < 1.0:
                _flat_alpha(mat, bsdf, alpha)
            else:
                _set_blend(mat, False)
                _unlink_alpha(mat, bsdf)
        self.materials[key] = mat
        return mat
