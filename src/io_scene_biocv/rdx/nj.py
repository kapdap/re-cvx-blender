import struct

CHUNK_CN = 0x00
CHUNK_CB_BA = 0x01
CHUNK_CB_DA = 0x02
CHUNK_CB_EXP = 0x03
CHUNK_TID = 0x08
CHUNK_CM_D = 0x11
CHUNK_CM_A = 0x12
CHUNK_CM_DA = 0x13
CHUNK_CM_S = 0x14
CHUNK_CM_DS = 0x15
CHUNK_CM_AS = 0x16
CHUNK_CM_DAS = 0x17
CHUNK_CV = 0x22
CHUNK_CV_VN = 0x29
CHUNK_CV_VN_PS2 = 0x33
CHUNK_CO_P3 = 0x38
CHUNK_CO_P4 = 0x39
CHUNK_CO_ST = 0x3A
CHUNK_CS = 0x40
CHUNK_CS_UVN = 0x41
CHUNK_CS_UVH = 0x42
CHUNK_END = 0xFF

UVH_SCALE = 0.0009775171
UVN_SCALE = 0.003921569

HDR_PS_SIZE = 64
HDR_CV_SIZE = 8

VERT_STRIDE_PS2 = 32
VERT_STRIDE_CV = 12
VERT_STRIDE_CV_VN = 24

SIZE_CNK_MODEL = 24
SIZE_TEXLIST = 8
SIZE_TEXNAME = 12


def _cstr(data, offset, limit=256):
    if offset < 0 or offset >= len(data):
        return ""
    end = data.find(b"\x00", offset)
    if end < 0 or end - offset > limit:
        return ""
    try:
        return data[offset:end].decode("ascii")
    except UnicodeDecodeError:
        return ""


def _chunk_head(data, o, endian="<"):
    if endian == ">":
        if o + 4 > len(data) or o < 0:
            return 0, 0, 0
        w0 = struct.unpack_from(">H", data, o)[0]
        t = w0 & 0xFF
        attr = (w0 >> 8) & 0xFF
        sizew = struct.unpack_from(">H", data, o + 2)[0]
        return t, attr, sizew
    t = data[o] if 0 <= o < len(data) else 0
    attr = data[o + 1] if 0 <= o + 1 < len(data) else 0
    sizew = (
        struct.unpack_from("<H", data, o + 2)[0] if o + 4 <= len(data) and o >= 0 else 0
    )
    return t, attr, sizew


def _vlist_head(data, o, endian="<"):
    if endian == ">":
        if o + 8 > len(data) or o < 0:
            return -1, 0, 0
        w0 = struct.unpack_from(">I", data, o)[0]
        w1 = struct.unpack_from(">I", data, o + 4)[0]
        return (w0 & 0xFF, w1 & 0xFFFF, (w1 >> 16) & 0xFFFF)
    vtype = data[o] if 0 <= o < len(data) else -1
    if o + 8 > len(data) or o < 0:
        return vtype, 0, 0
    us_ofs, us_max = struct.unpack_from("<2H", data, o + 4)
    return vtype, us_ofs, us_max


def _t0_at(data, o, endian="<"):
    if endian == ">":
        if o + 2 > len(data) or o < 0:
            return CHUNK_END
        return struct.unpack_from(">H", data, o)[0] & 0xFF
    return data[o] if 0 <= o < len(data) else CHUNK_END


class NjError(ValueError):
    pass


class NjTexName:
    def __init__(self):
        self.index = -1
        self.entry_offset = 0
        self.fn_off = -1
        self.attr = 0
        self.texaddr = 0
        self.name_offset = 0
        self.name = ""


class NjTexList:
    def __init__(self):
        self.present = False
        self.tex_off = -1
        self.header_offset = 0
        self.tex_ptr = 0
        self.count = 0
        self.array_offset = 0
        self.entries = []
        self.names = []

    def read(self, data, dat_top, tex_off, endian="<"):
        self.present = False
        self.tex_off = tex_off
        self.header_offset = 0
        self.tex_ptr = 0
        self.count = 0
        self.array_offset = 0
        self.entries = []
        self.names = []
        if tex_off == -1:
            return self
        o = dat_top + tex_off
        if o < 0 or o + SIZE_TEXLIST > len(data):
            return self
        tex_ptr, count = struct.unpack_from(endian + "2i", data, o)
        if count < 0 or count > 4096:
            return self
        self.present = True
        self.header_offset = o
        self.tex_ptr = tex_ptr
        self.count = count
        arr = dat_top + tex_ptr
        self.array_offset = arr
        for i in range(count):
            eo = arr + i * SIZE_TEXNAME
            if eo < 0 or eo + SIZE_TEXNAME > len(data):
                break
            fn_off, attr, texaddr = struct.unpack_from(endian + "3i", data, eo)
            entry = NjTexName()
            entry.index = i
            entry.entry_offset = eo
            entry.fn_off = fn_off
            entry.attr = attr
            entry.texaddr = texaddr
            if fn_off < 0:
                self.entries.append(entry)
                self.names.append("")
                continue
            entry.name_offset = dat_top + fn_off
            entry.name = _cstr(data, dat_top + fn_off)
            self.entries.append(entry)
            self.names.append(entry.name)
        return self


class NjObject:
    def __init__(self):
        self.index = -1
        self.evalflags = 0
        self.pos = (0.0, 0.0, 0.0)
        self.ang = (0, 0, 0)
        self.scl = (1.0, 1.0, 1.0)
        self.child = -1
        self.sibling = -1
        self.model_index = -1
        self.hidden = False

    def read(self, data, offset, index, endian="<"):
        self.index = index
        (
            self.evalflags,
            _model_off,
            px,
            py,
            pz,
            ax,
            ay,
            az,
            sx,
            sy,
            sz,
            self.child,
            self.sibling,
        ) = struct.unpack_from(endian + "2i3f3i3f2i", data, offset)
        self.pos = (px, py, pz)
        self.ang = (ax, ay, az)
        self.scl = (sx, sy, sz)
        self.hidden = bool(self.evalflags & 0x8)
        return _model_off


class NjModel:
    def __init__(self):
        self.verts = []
        self.normals = []
        self.faces = []
        self.uvs = []
        self.texids = []
        self.mats = []
        self.materials = []
        self.face_blend = []
        self.face_nat = []
        self.center = (0.0, 0.0, 0.0)
        self.radius = 0.0
        self.notes = []


def read_model(data, dat_top, mno, endian="<"):
    if mno + SIZE_CNK_MODEL > len(data):
        raise NjError("model node out of range")
    vlist_off, plist_off = struct.unpack_from(endian + "2i", data, mno)
    cx, cy, cz, r = struct.unpack_from(endian + "4f", data, mno + 8)
    model = NjModel()
    model.center = (cx, cy, cz)

    model.radius = -r if r < 0 else r
    if vlist_off in (-1, 0):
        model.notes.append("no vlist")
        return model
    vo = dat_top + vlist_off
    if endian == ">":
        vtype, _, _ = (
            _vlist_head(data, vo, endian) if 0 <= vo < len(data) else (-1, 0, 0)
        )
    else:
        vtype = data[vo] if 0 <= vo < len(data) else -1
    if vtype == CHUNK_CV_VN_PS2:
        _read_vlist_ps2(data, vo, model, endian)
    elif vtype == CHUNK_CV_VN:
        _read_vlist_cv_vn(data, vo, model, endian)
    elif vtype == CHUNK_CV:
        _read_vlist_cv(data, vo, model, endian)
    else:
        model.notes.append(f"unsupported vertex type {vtype:#x}")
        return model
    if plist_off == -1:
        model.notes.append("no plist")
        return model
    if plist_off == 0:
        t0 = _t0_at(data, dat_top, endian) if 0 <= dat_top < len(data) else CHUNK_END
        if t0 == CHUNK_END:
            return model
        if t0 >= 76:
            model.notes.append("no plist")
            return model
    _read_plist(data, dat_top + plist_off, model, endian)
    return model


def _read_vlist_ps2(data, o, model, endian="<"):
    if o + HDR_PS_SIZE > len(data) or o < 0:
        model.notes.append("vlist out of range")
        return
    if endian == ">":
        vtype, us_ofs, us_max = _vlist_head(data, o, endian)
    else:
        vtype = data[o]
        us_ofs, us_max = struct.unpack_from("<2H", data, o + 4)
    if vtype != CHUNK_CV_VN_PS2:
        model.notes.append(f"unsupported vertex type {vtype:#x}")
        return

    base = o + HDR_PS_SIZE
    need = us_ofs + us_max
    while len(model.verts) < need:
        model.verts.append((0.0, 0.0, 0.0))
        model.normals.append((0.0, 0.0, 0.0))
    for i in range(us_max):
        bo = base + i * VERT_STRIDE_PS2
        if bo + 28 > len(data):
            model.notes.append(f"vertex overrun at {i}")
            break
        x, y, z = struct.unpack_from(endian + "3f", data, bo)
        nx, ny, nz = struct.unpack_from(endian + "3f", data, bo + 16)
        model.verts[us_ofs + i] = (x, y, z)
        model.normals[us_ofs + i] = (nx, ny, nz)


def _read_vlist_cv(data, o, model, endian="<"):
    if o + HDR_CV_SIZE > len(data) or o < 0:
        model.notes.append("vlist out of range")
        return
    if endian == ">":
        vtype, us_ofs, us_max = _vlist_head(data, o, endian)
    else:
        vtype = data[o]
        us_ofs, us_max = struct.unpack_from("<2H", data, o + 4)
    if vtype != CHUNK_CV:
        model.notes.append(f"unsupported vertex type {vtype:#x}")
        return
    base = o + HDR_CV_SIZE
    need = us_ofs + us_max
    while len(model.verts) < need:
        model.verts.append((0.0, 0.0, 0.0))
        model.normals.append((0.0, 0.0, 0.0))
    for i in range(us_max):
        bo = base + i * VERT_STRIDE_CV
        if bo + 12 > len(data):
            model.notes.append(f"vertex overrun at {i}")
            break
        x, y, z = struct.unpack_from(endian + "3f", data, bo)
        model.verts[us_ofs + i] = (x, y, z)
        model.normals[us_ofs + i] = (0.0, 0.0, 0.0)


def _read_vlist_cv_vn(data, o, model, endian="<"):
    if o + HDR_CV_SIZE > len(data) or o < 0:
        model.notes.append("vlist out of range")
        return
    if endian == ">":
        vtype, us_ofs, us_max = _vlist_head(data, o, endian)
    else:
        vtype = data[o]
        us_ofs, us_max = struct.unpack_from("<2H", data, o + 4)
    if vtype != CHUNK_CV_VN:
        model.notes.append(f"unsupported vertex type {vtype:#x}")
        return
    base = o + HDR_CV_SIZE
    need = us_ofs + us_max
    while len(model.verts) < need:
        model.verts.append((0.0, 0.0, 0.0))
        model.normals.append((0.0, 0.0, 0.0))
    for i in range(us_max):
        bo = base + i * VERT_STRIDE_CV_VN
        if bo + 24 > len(data):
            model.notes.append(f"vertex overrun at {i}")
            break
        x, y, z = struct.unpack_from(endian + "3f", data, bo)
        nx, ny, nz = struct.unpack_from(endian + "3f", data, bo + 12)
        model.verts[us_ofs + i] = (x, y, z)
        model.normals[us_ofs + i] = (nx, ny, nz)


def _read_plist(data, o, model, endian="<"):
    texid = 0
    mat = -1
    guard = 0
    while True:
        guard += 1
        if guard > 100000 or o + 1 > len(data) or o < 0:
            model.notes.append("plist overrun/guard")
            return
        if endian == ">":
            t, attr, _sz = _chunk_head(data, o, endian)
        else:
            t = data[o]
            attr = 0
        if t == CHUNK_END:
            return
        if t >= 76:
            model.notes.append(f"unknown chunk type {t:#x}")
            return
        if t == CHUNK_CN:
            o += 2
            continue
        if t in (CHUNK_CB_BA, CHUNK_CB_DA, CHUNK_CB_EXP):
            if o + 4 > len(data):
                model.notes.append("bits chunk overrun")
                return
            o += 4
            continue
        if CHUNK_TID <= t <= 0x0F:
            if o + 4 > len(data):
                model.notes.append("tiny chunk overrun")
                return
            if t == CHUNK_TID:
                raw = struct.unpack_from(endian + "H", data, o + 2)[0]
                texid = raw & 0xFFF
            o += 4
            continue
        if o + 4 > len(data):
            model.notes.append("plist head overrun")
            return
        if endian == ">":
            _t, _attr, sizew = _chunk_head(data, o, endian)
        else:
            sizew = struct.unpack_from("<H", data, o + 2)[0]
        if t in (
            CHUNK_CM_D,
            CHUNK_CM_A,
            CHUNK_CM_DA,
            CHUNK_CM_S,
            CHUNK_CM_DS,
            CHUNK_CM_AS,
            CHUNK_CM_DAS,
        ):
            o = _read_material(data, o, t, model)
            if o < 0:
                model.notes.append(f"material overrun t={t:#x}")
                return
            mat = len(model.materials) - 1
            continue
        if t in (CHUNK_CS, CHUNK_CS_UVN, CHUNK_CS_UVH):
            if endian == ">":
                _t, attr, _sz2 = _chunk_head(data, o, endian)
            else:
                attr = data[o + 1] if o + 1 < len(data) else 0
            no = _read_strips(data, o, t, texid, mat, model, attr, endian)
            if no < 0:
                model.notes.append(f"strip chunk overrun t={t:#x}")
                return
            o = no
            continue
        if t == CHUNK_CO_P3:
            no = _skip_cop3(data, o, endian)
            if no < 0:
                model.notes.append("cop3 overrun")
                return
            o = no
            continue
        if t in (CHUNK_CO_P4, CHUNK_CO_ST):
            end = o + 4 + sizew * 2
            if end > len(data):
                model.notes.append(f"volume chunk overrun t={t:#x}")
                return
            o = end
            continue
        if t in (CHUNK_CV_VN_PS2, CHUNK_CV_VN, CHUNK_CV):
            no = _skip_cvn(data, o, t, endian)
            if no < 0:
                model.notes.append("vertex chunk in plist overrun")
                return
            o = no
            continue

        if (32 <= t <= 40) or (42 <= t <= 50) or (52 <= t <= 55):
            end = o + 4 + sizew * 4
        else:
            end = o + 4 + sizew * 2
        if end > len(data) or end < o:
            model.notes.append(f"plist chunk overrun t={t:#x}")
            return
        o = end


def _read_material(data, o, t, model):
    need = {
        CHUNK_CM_D: 4,
        CHUNK_CM_A: 4,
        CHUNK_CM_DA: 8,
        CHUNK_CM_S: 4,
        CHUNK_CM_DS: 8,
        CHUNK_CM_AS: 8,
        CHUNK_CM_DAS: 12,
    }[t]
    if o + 4 + need > len(data):
        return -1
    p = o + 4
    entry = {
        "type": t,
        "diffuse": None,
        "ambient": None,
        "specular": None,
        "exponent": None,
        "alpha": 1.0,
    }
    if t in (CHUNK_CM_D, CHUNK_CM_DA, CHUNK_CM_DS, CHUNK_CM_DAS):
        b, g, r, a = data[p], data[p + 1], data[p + 2], data[p + 3]
        entry["diffuse"] = (r / 255.0, g / 255.0, b / 255.0)
        entry["alpha"] = a / 255.0
        p += 4
    if t in (CHUNK_CM_A, CHUNK_CM_DA, CHUNK_CM_AS, CHUNK_CM_DAS):
        b, g, r = data[p], data[p + 1], data[p + 2]
        entry["ambient"] = (r / 255.0, g / 255.0, b / 255.0)
        p += 4
    if t in (CHUNK_CM_S, CHUNK_CM_DS, CHUNK_CM_AS, CHUNK_CM_DAS):
        b, g, r, e = data[p], data[p + 1], data[p + 2], data[p + 3]
        entry["specular"] = (r / 255.0, g / 255.0, b / 255.0)
        entry["exponent"] = float(e)
        p += 4
    model.materials.append(entry)
    return o + 4 + need


def _read_strips(data, o, t, texid, mat, model, attr=0, endian="<"):
    if t == CHUNK_CS:
        scale = None
    elif t == CHUNK_CS_UVN:
        scale = UVN_SCALE
    elif t == CHUNK_CS_UVH:
        scale = UVH_SCALE
    else:
        return -1
    blend = bool(attr & 0x08)
    nat = bool(attr & 0x80)
    if o + 6 > len(data):
        return -1
    first = struct.unpack_from(endian + "H", data, o + 4)[0]
    if t == CHUNK_CS:
        us_next = (first >> 14) & 0x3
        nstrips = first & 0x3FFF
    else:
        us_next = 0
        nstrips = first & 0x3FFF
    p = o + 6
    for _ in range(nstrips):
        if p + 2 > len(data):
            break
        h = struct.unpack_from(endian + "h", data, p)[0]
        p += 2
        n = -h if h < 0 else h
        if n < 0 or n > 100000:
            model.notes.append(f"bad strip length {h}")
            break
        est = 2 if scale is None else 6
        els = []
        ok = True
        for _k in range(n):
            if p + est > len(data):
                ok = False
                break
            idx = struct.unpack_from(endian + "H", data, p)[0]
            if scale is None:
                els.append((idx, 0.0, 0.0))
                p += 2
            else:
                u = struct.unpack_from(endian + "H", data, p + 2)[0] * scale
                v = struct.unpack_from(endian + "H", data, p + 4)[0] * scale
                els.append((idx, u, v))
                p += 6
            if scale is None and _k >= 2 and us_next:
                if p + us_next * 2 > len(data):
                    ok = False
                    break
                p += us_next * 2
        if not ok:
            model.notes.append(f"strip overrun len={n}")
            break
        nv = len(model.verts)
        if any(idx < 0 or idx >= nv for (idx, _u, _v) in els):
            model.notes.append("strip index out of range")
            continue

        for k in range(len(els) - 2):
            a, b, c = els[k], els[k + 1], els[k + 2]
            if a[0] == b[0] or b[0] == c[0] or a[0] == c[0]:
                continue
            if (k % 2) == 1:
                a, b = b, a
            model.faces.append((a[0], b[0], c[0]))
            model.uvs.append(((a[1], a[2]), (b[1], b[2]), (c[1], c[2])))
            model.texids.append(texid)
            model.mats.append(mat)
            model.face_blend.append(blend)
            model.face_nat.append(nat)
    return p


def _skip_cvn(data, o, t, endian="<"):
    if t == CHUNK_CV_VN_PS2:
        if o + HDR_PS_SIZE > len(data):
            return -1
        if endian == ">":
            w1 = struct.unpack_from(">I", data, o + 4)[0]
            us_max = (w1 >> 16) & 0xFFFF
        else:
            us_max = struct.unpack_from("<H", data, o + 6)[0]
        end = o + HDR_PS_SIZE + us_max * VERT_STRIDE_PS2
        if end > len(data):
            return -1
        return end
    if o + 8 > len(data):
        return -1
    if endian == ">":
        w1 = struct.unpack_from(">I", data, o + 4)[0]
        count = (w1 >> 16) & 0xFFFF
    else:
        count = struct.unpack_from("<H", data, o + 6)[0]
    if t == CHUNK_CV:
        end = o + HDR_CV_SIZE + count * VERT_STRIDE_CV
    else:
        end = o + 8 + count * 24
    if end > len(data):
        return -1
    return end


def _skip_cop3(data, o, endian="<"):
    if o + 6 > len(data):
        return -1
    word = struct.unpack_from(endian + "H", data, o + 4)[0]
    us_next = (word >> 14) & 0x3
    us_poly = word & 0x3FFF
    end = o + 6 + us_poly * (3 + us_next) * 2
    if end > len(data) or us_poly > 100000:
        return -1
    return end
