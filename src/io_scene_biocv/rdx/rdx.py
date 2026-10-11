import struct

from . import mlb, prs, tex

RDX_MAGIC_0 = 0x40028F5C  # Demo
RDX_MAGIC_1 = 0x40051EB8  # DC/PS2
RDX_MAGIC_2 = 0x41200000  # DC/PS2
RDX_MAGIC_3 = 0x41A00000  # GameCube
RDX_MAGICS = (RDX_MAGIC_1, RDX_MAGIC_2, RDX_MAGIC_3, RDX_MAGIC_0)

PRS_FLAG = 0xDF

SIZE_ETTY = 36
SIZE_EFFECT = 68
SIZE_ATR = 36
SIZE_PLAYER = 16
SIZE_CAMERA = 680
SIZE_CAMERA_BLOCK = 196
SIZE_LIGHT = 224


def _ascii(data, offset, size):
    raw = data[offset : offset + size]
    try:
        return raw.split(b"\x00")[0].decode("ascii")
    except (UnicodeDecodeError, IndexError):
        return ""


def _detect_endian(data):
    if len(data) < 4:
        return None
    le = struct.unpack_from("<I", data, 0)[0]
    if le in RDX_MAGICS:
        return "<"
    be = struct.unpack_from(">I", data, 0)[0]
    if be in RDX_MAGICS:
        return ">"
    return None


def _s16(val):
    val &= 0xFFFF
    return val - 0x10000 if val >= 0x8000 else val


class RdxHeader:
    def __init__(self):
        self.ver = 0.0
        self.sections = [0] * 8
        self.author = ""
        self.tables = [0] * 16
        self.counts = [0] * 16
        self.flg = 0
        self.bak_col = 0
        self.fog_col = 0
        self.fog_nr = 0.0
        self.fog_fr = 0.0
        self.room_size = (0.0, 0.0, 0.0)
        self.grand = [0.0] * 32

    def read(self, data, endian="<"):
        if len(data) < 0x260:
            raise ValueError("file too small for RDX header")
        self.ver = struct.unpack_from(endian + "f", data, 0)[0]
        self.sections = list(struct.unpack_from(endian + "8i", data, 0x10))
        self.author = _ascii(data, 0x60, 32)
        tables_ptr = struct.unpack_from(endian + "i", data, 0x10)[0]
        if tables_ptr < 0 or tables_ptr + 64 > len(data):
            tables_ptr = 0x80
        self.tables = list(struct.unpack_from(endian + "16i", data, tables_ptr))
        self.counts = list(struct.unpack_from(endian + "16i", data, 0x100))
        self.flg, self.bak_col, self.fog_col, self.fog_nr, self.fog_fr = (
            struct.unpack_from(endian + "IIIff", data, 0x180)
        )
        self.room_size = struct.unpack_from(endian + "3f", data, 0x194)
        self.grand = list(struct.unpack_from(endian + "32f", data, 0x1A0))
        return self


class EttyEntry:
    SIZE = SIZE_ETTY

    def __init__(self):
        self.flg = 0
        self.id = 0
        self.type = 0
        self.flr_no = 0
        self.mdlver = 0
        self.wrk_no = 0
        self.prm1 = 0
        self.pos = (0.0, 0.0, 0.0)
        self.ang = (0, 0, 0)
        self.aspd = 0
        self.hide = (0, 0, 0, 0)

    def read(self, data, offset, endian="<"):
        (
            self.flg,
            self.id,
            self.type,
            self.flr_no,
            self.mdlver,
            self.wrk_no,
            self.prm1,
            px,
            py,
            pz,
            ax,
            az,
            ay,
            self.aspd,
            h0,
            h1,
            h2,
            h3,
        ) = struct.unpack_from(endian + "IHHbBbbfffhhhh4b", data, offset)
        self.pos = (px, py, pz)
        self.ang = (ax, ay, az)
        self.hide = (h0, h1, h2, h3)
        return self


class EffectEntry:
    SIZE = SIZE_EFFECT

    def __init__(self):
        self.flg = 0
        self.id = 0
        self.type = 0
        self.flr_no = 0
        self.mdlver = 0
        self.pos = (0.0, 0.0, 0.0)
        self.scale = (1.0, 1.0, 1.0)
        self.ay_ax = 0
        self.ay = 0
        self.ax = 0
        self.lkflg = 0
        self.lkno = 0
        self.lkono = 0
        self.link = (0.0, 0.0, 0.0)
        self.param = 0

    def read(self, data, offset, endian="<"):
        (
            self.flg,
            self.id,
            self.type,
            flr_mdlver,
            px,
            py,
            pz,
            sx,
            sy,
            sz,
            self.ay,
            self.ax,
            self.lkflg,
            self.lkno,
            self.lkono,
            lx,
            ly,
            lz,
            self.param,
        ) = struct.unpack_from(endian + "ihhi6f2h3i3fi", data, offset)
        self.ay_ax = ((self.ax & 0xFFFF) << 16) | (self.ay & 0xFFFF)
        self.flr_no = flr_mdlver & 0xFFFF
        if self.flr_no >= 0x8000:
            self.flr_no -= 0x10000
        self.mdlver = (flr_mdlver >> 16) & 0xFFFF
        self.pos = (px, py, pz)
        self.scale = (sx, sy, sz)
        self.link = (lx, ly, lz)
        return self


class AtrEntry:
    SIZE = SIZE_ATR

    def __init__(self):
        self.flg = 0
        self.type = 0
        self.id = 0
        self.flr_no = 0
        self.attr = 0
        self.pos = (0.0, 0.0, 0.0)
        self.size = (0.0, 0.0, 0.0)
        self.prm = (0, 0, 0, 0)

    def read(self, data, offset, endian="<"):
        (
            self.flg,
            self.type,
            self.id,
            self.flr_no,
            self.attr,
            px,
            py,
            pz,
            w,
            h,
            dd,
            p0,
            p1,
            p2,
            p3,
        ) = struct.unpack_from(endian + "BBBBIffffffBBBB", data, offset)
        self.pos = (px, py, pz)
        self.size = (w, h, dd)
        self.prm = (p0, p1, p2, p3)
        return self

    def bounds(self):
        px, py, pz = self.pos
        w, h, dd = self.size
        lo = (min(px, px + w), min(py, py + h), min(pz, pz + dd))
        hi = (max(px, px + w), max(py, py + h), max(pz, pz + dd))
        return lo, hi


class PlayerEntry:
    SIZE = SIZE_PLAYER

    def __init__(self):
        self.pos = (0.0, 0.0, 0.0)
        self.ay = 0

    def read(self, data, offset, endian="<"):
        px, py, pz, self.ay = struct.unpack_from(endian + "3fi", data, offset)
        self.pos = (px, py, pz)
        return self


class CameraBlock:
    SIZE = SIZE_CAMERA_BLOCK

    def __init__(self):
        self.flg = 0
        self.lgtclip = 0
        self.spd = 0
        self.pos = (0.0, 0.0, 0.0)
        self.ln = 0.0
        self.blend = (0.0, 0.0, 0.0)
        self.y = (0.0, 0.0, 0.0, 0.0)
        self.am_spd = 0.0
        self.ang = (0, 0, 0)
        self.clamp = (0, 0)
        self.laz = (0, 0, 0, 0)
        self.aa_spd = 0
        self.fil_no = 0
        self.fil_rt = 0
        self.pers = 0
        self.hidobj = [0] * 16
        self.hidlgt = [0] * 8
        self.fog_col = 0
        self.fog_nr = 0.0
        self.fog_fr = 0.0

    def read(self, data, offset, endian="<"):
        vals = struct.unpack_from(endian + "HBb12f5i4h4Bi16I8II2f", data, offset)
        self.flg = vals[0]
        self.lgtclip = vals[1]
        self.spd = vals[2]
        self.pos = (vals[3], vals[4], vals[5])
        self.ln = vals[6]
        self.blend = (vals[7], vals[8], vals[9])
        self.y = (vals[10], vals[11], vals[12], vals[13])
        self.am_spd = vals[14]
        self.ang = (vals[15], vals[16], vals[17])
        self.clamp = (vals[18], vals[19])
        self.laz = (vals[20], vals[21], vals[22], vals[23])
        self.aa_spd = vals[24]
        self.fil_no = vals[25]
        self.fil_rt = vals[26]
        self.pers = vals[28]
        self.hidobj = list(vals[29:45])
        self.hidlgt = list(vals[45:53])
        self.fog_col = vals[53]
        self.fog_nr = vals[54]
        self.fog_fr = vals[55]
        return self


class CameraEntry:
    SIZE = SIZE_CAMERA

    def __init__(self):
        self.flg = 0
        self.type = 0
        self.flr_no = 0
        self.ctab_n = 0
        self.cuttp = 0
        self.ref = (0.0, 0.0, 0.0)
        self.blend_range = (0.0, 0.0, 0.0)
        self.blocks = []

    def read(self, data, offset, endian="<"):
        (
            self.flg,
            self.type,
            self.flr_no,
            self.ctab_n,
            self.cuttp,
            cx,
            cy,
            cz,
            cw,
            ch,
            cd,
        ) = struct.unpack_from(endian + "BBbBi6f", data, offset)
        self.ref = (cx, cy, cz)
        self.blend_range = (cw, ch, cd)
        self.blocks = []
        for i in range(2):
            blk = CameraBlock()
            blk.read(data, offset + 32 + i * SIZE_CAMERA_BLOCK, endian)
            self.blocks.append(blk)
        return self


class LightEntry:
    SIZE = SIZE_LIGHT

    IDX_AX = 19
    IDX_AY = 20
    IDX_AZ = 21

    def __init__(self):
        self.flg_lo = 0
        self.flg_hi = 0
        self.type = 0
        self.aspd = 0
        self.lkflg = 0
        self.lkno = 0
        self.lkono = 0
        self.lsrc = 0
        self.params = [0.0] * 49
        self.iparams = [0] * 49

    def read(self, data, offset, endian="<"):
        if endian == ">":
            flg_word = struct.unpack_from(">i", data, offset)[0]
            self.flg_lo = _s16(flg_word & 0xFFFF)
            self.flg_hi = _s16((flg_word >> 16) & 0xFFFF)
            vals = struct.unpack_from(">6i49f", data, offset + 4)
            self.type, self.aspd, self.lkflg, self.lkno, self.lkono, self.lsrc = vals[
                0:6
            ]
            self.params = list(vals[6:55])
            self.iparams = list(struct.unpack_from(">49i", data, offset + 28))
        else:
            vals = struct.unpack_from("<hh6i49f", data, offset)
            self.flg_lo = vals[0]
            self.flg_hi = vals[1]
            self.type, self.aspd, self.lkflg, self.lkno, self.lkono, self.lsrc = vals[
                2:8
            ]
            self.params = list(vals[8:57])
            self.iparams = list(struct.unpack_from("<49i", data, offset + 28))
        return self

    @property
    def pos(self):
        return (self.params[0], self.params[1], self.params[2])

    @property
    def ang(self):
        return (
            self.iparams[self.IDX_AX],
            self.iparams[self.IDX_AY],
            self.iparams[self.IDX_AZ],
        )


class TexBlock:
    def __init__(self):
        self.code = 0
        self.size = 0
        self.offset = 0
        self.data_offset = 0

    @property
    def kind(self):
        if self.code in (0x324D4954, 0x54494D32):
            return "TIM2"
        if self.code in (0x00494C50, 0x504C4900):
            return "PLI"
        if self.code in (0x52565050, 0x52565054):
            return "PVR"
        if self.code == 0x50565050:
            return "PVP"
        if self.code in (0x54505652, 0x50505652):
            return "GVR"
        if self.code == 0x50505650:
            return "GVP"
        if self.code == 0xFFFFFFFF:
            return "END"
        return f"UNK_{self.code:08X}"


class TexTable:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.blocks = []


class ModelTable:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.blobs = []
        self.blob_tex = []


class RdxFile:
    def __init__(self):
        self.header = RdxHeader()
        self.data = b""
        self.endian = "<"
        self.actor = []
        self.obj = []
        self.item = []
        self.effect = []
        self.sca = []
        self.aot = []
        self.trigger = []
        self.route = []
        self.player = []
        self.cameras = []
        self.lights = []
        self.models = []
        self.textures = []

    def read(self, source):
        if isinstance(source, (bytes, bytearray)):
            raw = bytes(source)
        else:
            with open(source, "rb") as fh:
                raw = fh.read()
        endian = _detect_endian(raw)
        if endian is not None:
            self.data = raw
        else:
            try:
                dec = prs.decompress(raw)
            except Exception as exc:
                raise ValueError("not a valid RDX/RDT file") from exc
            endian = _detect_endian(dec)
            if endian is None:
                raise ValueError("not a valid RDX/RDT file")
            self.data = dec
        self.endian = endian
        self.header.read(self.data, endian)
        self._read_tables()
        return self

    def _entries(self, cls, table_idx):
        out = []
        base = self.header.tables[table_idx]
        count = self.header.counts[table_idx]
        if base == 0 or count <= 0:
            return out
        for i in range(count):
            o = base + i * cls.SIZE
            if o + cls.SIZE > len(self.data):
                break
            out.append(cls().read(self.data, o, self.endian))
        return out

    def _read_tables(self):
        self.actor = self._entries(EttyEntry, 2)
        self.obj = self._entries(EttyEntry, 3)
        self.item = self._entries(EttyEntry, 4)
        self.effect = self._entries(EffectEntry, 5)
        self.sca = self._entries(AtrEntry, 6)
        self.aot = self._entries(AtrEntry, 7)
        self.trigger = self._entries(AtrEntry, 8)
        self.route = self._entries(AtrEntry, 10)
        self.player = self._entries(PlayerEntry, 9)
        self.cameras = self._entries(CameraEntry, 0)
        self.lights = self._entries(LightEntry, 1)
        self._read_models()
        self._read_textures()

    def _read_models(self):
        self.models = []
        base = self.header.sections[1]
        if base == 0:
            return
        e = self.endian
        ptrs = []
        o = base
        while len(ptrs) < 512 and o + 4 <= len(self.data):
            slot = self.data[o : o + 4].decode("ascii", errors="replace")
            v = struct.unpack_from(e + "i", self.data, o)[0]
            o += 4
            if v == 0 or slot == "SKIN" or slot.startswith("MDL"):
                break
            if v < 0 or v >= len(self.data):
                break
            ptrs.append(v)
        motion = self.header.sections[2] or len(self.data)
        for i, tp in enumerate(ptrs):
            table = ModelTable()
            table.offset = tp
            table.size = (ptrs[i + 1] if i + 1 < len(ptrs) else motion) - tp
            table.size = max(table.size, 0)
            end = min(tp + table.size, len(self.data))
            table.blobs = list(mlb.iter_mlb_blobs(self.data, tp, end, e))
            for bo, _bs in table.blobs:
                has = False
                if bo + 16 <= len(self.data):
                    has = struct.unpack_from(e + "i", self.data, bo + 8)[0] != -1
                table.blob_tex.append(has)
            self.models.append(table)

    def _read_textures(self):
        self.textures = []
        base = self.header.sections[4]
        if base == 0 or base + 4 > len(self.data):
            return
        e = self.endian
        count = struct.unpack_from(e + "I", self.data, base)[0]
        if count > 4096:
            return
        ptrs = []
        for i in range(count):
            o = base + 4 + i * 4
            if o + 4 > len(self.data):
                break
            v = struct.unpack_from(e + "i", self.data, o)[0]
            if v == 0:
                break
            ptrs.append(v)
        for i, tp in enumerate(ptrs):
            table = TexTable()
            table.offset = tp
            table.size = (ptrs[i + 1] if i + 1 < len(ptrs) else len(self.data)) - tp
            o = tp
            end = tp + table.size
            while o + 8 <= end and o + 8 <= len(self.data):
                code = struct.unpack_from(e + "I", self.data, o)[0]
                if code == 0xFFFFFFFF:
                    break
                size = struct.unpack_from(e + "i", self.data, o + 4)[0]
                if size <= 0:
                    o += 32
                    continue
                if o + 32 + size > len(self.data):
                    break
                blk = TexBlock()
                blk.code = code
                blk.size = size
                blk.offset = o
                blk.data_offset = o + 32
                table.blocks.append(blk)
                o += 32 + size
            self.textures.append(table)

    def model_table_map(self):
        candidates = [("room", None)]
        candidates.extend(("actor", i) for i, e in enumerate(self.actor) if e.flg & 0x1)
        candidates.extend(("obj", n + 4) for n, _ in enumerate(self.obj[4:]))
        candidates.extend(("item", i) for i, _ in enumerate(self.item))
        return dict(enumerate(candidates[: len(self.models)]))

    def texture_assignment(self):
        assign = {}
        t = 0
        ntex = len(self.textures)
        b = 0
        if b < len(self.models):
            if self._table_tex(0) and t < ntex:
                assign[(b, 0)] = t
                t += 1
            b += 1

        seen_ene = {}
        for e in self.actor:
            if not (e.flg & 0x1):
                continue
            if b >= len(self.models):
                break
            local = -1
            for bi, has in enumerate(self.models[b].blob_tex):
                if has:
                    local += 1
                    key = (e.id, e.mdlver, local)
                    if key not in seen_ene and t < ntex:
                        seen_ene[key] = t
                        t += 1
                    if key in seen_ene:
                        assign[(b, bi)] = seen_ene[key]

                else:
                    if local >= 0:
                        key = (e.id, e.mdlver, local)
                        if key in seen_ene:
                            assign[(b, bi)] = seen_ene[key]

            b += 1

        seen_obj = {}
        for e in self.obj[4:]:
            if b >= len(self.models):
                break
            if self._table_tex(b):
                if e.id not in seen_obj and t < ntex:
                    seen_obj[e.id] = t
                    t += 1
                if e.id in seen_obj:
                    assign[(b, 0)] = seen_obj[e.id]
            b += 1

        seen_itm = {}
        for e in self.item:
            if b >= len(self.models):
                break
            if self._table_tex(b):
                if e.id not in seen_itm and t < ntex:
                    seen_itm[e.id] = t
                    t += 1
                if e.id in seen_itm:
                    assign[(b, 0)] = seen_itm[e.id]
            b += 1

        return assign

    def _table_tex(self, ti):
        if ti < 0 or ti >= len(self.models):
            return False
        blob_tex = self.models[ti].blob_tex
        return bool(blob_tex) and bool(blob_tex[0])

    def pli_state_at(self, table_idx, block_idx):
        palnum = 0
        entries = []
        if table_idx < 0 or table_idx >= len(self.textures):
            return palnum, entries
        for blk in self.textures[table_idx].blocks[: block_idx + 1]:
            if blk.kind == "PLI":
                if blk.size == 0:
                    continue
                parsed_num, parsed_entries = tex.parse_pli(self.data, blk.data_offset)
            elif blk.kind == "PVP":
                if blk.size == 0:
                    continue
                parsed_num, parsed_entries = tex.parse_pvpl(self.data, blk.data_offset)
            elif blk.kind == "GVP":
                if blk.size == 0:
                    continue
                parsed_num, parsed_entries = tex.parse_gvpl(self.data, blk.data_offset)
            else:
                continue

            if parsed_num >= 1:
                palnum, entries = parsed_num, parsed_entries
        return palnum, entries
