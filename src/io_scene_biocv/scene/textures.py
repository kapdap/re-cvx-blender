import bpy

from ..rdx import tex

try:
    import numpy as np
except ImportError:
    np = None

_FWD = ((-1, 0, 1), (0, -1, 1), (-1, -1, 2), (1, -1, 2))
_BWD = ((1, 0, 1), (0, 1, 1), (1, 1, 2), (-1, 1, 2))
_MATTE = (
    ("Metallic", 0.0),
    ("Roughness", 0.9),
    ("Specular IOR Level", 0.0),
)


def _bsdf(nodes):
    for node in nodes:
        if node.type == "BSDF_PRINCIPLED":
            return node
    return None


def _safe_link(links, out_sock, in_sock):
    try:
        links.new(out_sock, in_sock)
    except RuntimeError:
        pass


def _bleed_rgb(raw, w, h):
    if 0 not in raw[3::4]:
        return raw
    n = w * h
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
    if np is not None and len(raw) >= h * rowlen:
        rows = np.frombuffer(raw, dtype=np.uint8, count=h * rowlen)
        img.pixels.foreach_set(
            rows.reshape(h, w, 4)[::-1].reshape(-1).astype(np.float32) / 255.0
        )
    else:
        flat = [0.0] * (w * h * 4)
        for row in range(h):
            src = (h - 1 - row) * rowlen
            dst = row * rowlen
            flat[dst : dst + rowlen] = [b / 255.0 for b in raw[src : src + rowlen]]
        img.pixels.foreach_set(flat)
    img.pack()


def _set_matte(bsdf):
    for name, val in _MATTE:
        bsdf.inputs.get(name).default_value = val


def _set_render(mat, transparent):
    if transparent:
        mat.surface_render_method = "BLENDED"
    else:
        mat.surface_render_method = "DITHERED"
        mat.alpha_threshold = 0.5 / 255
    mat.use_transparency_overlap = transparent


def _unlink_alpha(mat, bsdf):
    alpha_in = bsdf.inputs.get("Alpha")
    for link in list(alpha_in.links):
        mat.node_tree.links.remove(link)
    alpha_in.default_value = 1.0


def _set_alpha(mat, bsdf, tex_node, alpha):
    alpha_in = bsdf.inputs.get("Alpha")
    alpha_out = tex_node.outputs.get("Alpha")
    if alpha < 1.0:
        math_node = mat.node_tree.nodes.new("ShaderNodeMath")
        math_node.operation = "MULTIPLY"
        math_node.inputs[1].default_value = alpha
        _safe_link(mat.node_tree.links, alpha_out, math_node.inputs[0])
        _safe_link(mat.node_tree.links, math_node.outputs[0], alpha_in)
    else:
        _safe_link(mat.node_tree.links, alpha_out, alpha_in)


def _reset_alpha(mat, bsdf, transparent, alpha):
    flat = transparent and alpha < 1.0
    _set_render(mat, flat)
    _unlink_alpha(mat, bsdf)
    if flat:
        bsdf.inputs.get("Alpha").default_value = alpha


class TextureRepo:
    def __init__(self, rdx, prefix, alpha_mode):
        self.rdx = rdx
        self.prefix = prefix
        self.alpha_mode = alpha_mode
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
                    palnum, pli_entries = self.rdx.pli_state_at(table_idx, block_idx)
                    pal = pli_entries if palnum > 0 else None
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
                for pi, pic in enumerate(doc.pictures):
                    variants = (
                        [lop for lop, entry in enumerate(pli_entries) if entry[1] == 0]
                        if not tex.is_vq_path(pic.pic_format) and palnum > 0
                        else []
                    )
                    if variants:
                        pics.extend((bi, pi, lop) for lop in variants)
                    else:
                        pics.append((bi, pi, None))
            self._pic_index[table_idx] = pics
        return self._pic_index[table_idx]

    def alpha_kind(self, table_idx, block_idx, pic_idx, variant):
        key = (table_idx, block_idx, pic_idx, variant)
        if key not in self._alpha_kind:
            pixels = self._variant_pixels(table_idx, block_idx, pic_idx, variant)[1]
            self._alpha_kind[key] = tex.classify_alpha(pixels)
        return self._alpha_kind[key]

    def image(self, table_idx, block_idx, pic_idx, variant, alias):
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
        raw = self._variant_pixels(table_idx, block_idx, pic_idx, variant)[1]

        if kind == "OPAQUE" and not any(raw[3::4]):
            buf = bytearray(raw)
            for i in range(3, len(buf), 4):
                buf[i] = 255
            raw = bytes(buf)
        if kind != "OPAQUE":
            raw = _bleed_rgb(raw, pic.width, pic.height)
        if alias:
            name = f"{self.prefix}{alias}"
        else:
            name = f"{self.prefix}TEX_{table_idx}_{block_idx}_{pic_idx}"
        img = bpy.data.images.get(name) or bpy.data.images.new(
            name, pic.width, pic.height, alpha=(kind != "OPAQUE")
        )
        _push_pixels(img, raw, pic.width, pic.height)
        img.alpha_mode = "STRAIGHT" if kind != "OPAQUE" else "NONE"
        img.colorspace_settings.name = "sRGB"
        img.filepath_raw = f"//{name}.png"
        self.images[key] = img
        return img

    def material(
        self,
        table_idx,
        tex_names,
        texid,
        transparent,
        alpha,
        nat,
    ):
        alias = None
        if 0 <= texid < len(tex_names):
            alias = tex_names[texid] or None
        key = (table_idx, texid, transparent, alpha, nat, alias)
        mat = self.materials.get(key)
        if mat is not None:
            return mat
        img, kind = self._fetch_image(table_idx, texid, alias)
        if img is None:
            return None
        suffix = ("_TN" if nat else "_T") if transparent else ("_N" if nat else "")
        if alias:
            name = f"{self.prefix}{alias}{suffix}"
        else:
            name = f"{self.prefix}RDX_{table_idx}_{texid}{suffix}"
        mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        mat.use_nodes = True
        tree = mat.node_tree
        bsdf = _bsdf(tree.nodes)
        _set_matte(bsdf)
        tex_node = tree.nodes.new("ShaderNodeTexImage")
        tex_node.image = img
        _safe_link(
            tree.links,
            tex_node.outputs.get("Color"),
            bsdf.inputs.get("Base Color"),
        )
        if transparent and kind != "OPAQUE":
            cutout = (self.alpha_mode == "DITHERED") and not nat
            _set_render(mat, not cutout)
            _set_alpha(mat, bsdf, tex_node, alpha)
        else:
            _reset_alpha(mat, bsdf, transparent, alpha)
        self.materials[key] = mat
        return mat

    def _fetch_image(self, table_idx, texid, alias):
        if table_idx < len(self.rdx.textures):
            pics = self.table_pics(table_idx)
            if 0 <= texid < len(pics):
                bi, pi, variant = pics[texid]
                return self.image(table_idx, bi, pi, variant, alias), self.alpha_kind(
                    table_idx, bi, pi, variant
                )
        return None, "OPAQUE"

    def _variant_pixels(self, table_idx, block_idx, pic_idx, variant):
        doc = self.doc(table_idx, block_idx)
        pic = doc.pictures[pic_idx]
        if variant is None:
            return pic, pic.pixels
        pli_entries = self.rdx.pli_state_at(table_idx, block_idx)[1]
        pal_colors = [c for c, *_ in pli_entries]
        return pic, tex.apply_pal_sub(
            pic.image_type, pic.image_data, pic.pixels, pal_colors
        )
