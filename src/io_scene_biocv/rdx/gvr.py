import struct

GvrError = ValueError

GCIX_MAGIC = b"GCIX"
GVRT_MAGIC = b"GVRT"
GVPL_MAGIC = b"GVPL"

FMT_RGB565 = 4
FMT_RGB5A3 = 5
FMT_RGBA8 = 6
FMT_C4 = 8
FMT_C8 = 9
FMT_CMPR = 14

TLUT_IA8 = 0
TLUT_RGB565 = 1
TLUT_RGB5A3 = 2


def _scale5(v):
    return (v * 255) // 31


def _scale6(v):
    return (v * 255) // 63


def _scale4(v):
    return v * 17


def _decode_rgb565(v):
    r = _scale5((v >> 11) & 0x1F)
    g = _scale6((v >> 5) & 0x3F)
    b = _scale5(v & 0x1F)
    return r, g, b, 255


def _decode_rgb5a3(v):
    if v & 0x8000:
        r = _scale5((v >> 10) & 0x1F)
        g = _scale5((v >> 5) & 0x1F)
        b = _scale5(v & 0x1F)
        return r, g, b, 255
    a = (v >> 12) & 0x07
    r = _scale4((v >> 8) & 0x0F)
    g = _scale4((v >> 4) & 0x0F)
    b = _scale4(v & 0x0F)
    return r, g, b, (a * 255) // 7


def _decode_ia8(v):
    i = (v >> 8) & 0xFF
    a = v & 0xFF
    return i, i, i, a


def _decode_cmpr_block(data, off):
    c0 = struct.unpack_from(">H", data, off)[0]
    c1 = struct.unpack_from(">H", data, off + 2)[0]
    idx = struct.unpack_from(">I", data, off + 4)[0]
    r0, g0, b0, _ = _decode_rgb565(c0)
    r1, g1, b1, _ = _decode_rgb565(c1)
    if c0 > c1:
        r2 = (2 * r0 + r1) // 3
        g2 = (2 * g0 + g1) // 3
        b2 = (2 * b0 + b1) // 3
        r3 = (r0 + 2 * r1) // 3
        g3 = (g0 + 2 * g1) // 3
        b3 = (b0 + 2 * b1) // 3
        pal = [
            (r0, g0, b0, 255),
            (r1, g1, b1, 255),
            (r2, g2, b2, 255),
            (r3, g3, b3, 255),
        ]
    else:
        r2 = (r0 + r1) // 2
        g2 = (g0 + g1) // 2
        b2 = (b0 + b1) // 2
        pal = [(r0, g0, b0, 255), (r1, g1, b1, 255), (r2, g2, b2, 255), (0, 0, 0, 0)]
    out = []
    for i in range(16):
        shift = 2 * (15 - i)
        out.append(pal[(idx >> shift) & 3])
    return out


class GvrPicture:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.pixfmt = 0
        self.gidx = 0
        self.image_data = b""
        self.pixels = b""
        self.image_type = 1
        self.pic_format = 0
        self.total_size = 0

    def read(self, data, offset, palette=None):
        start = offset
        if len(data) < offset + 16:
            raise GvrError("truncated GVRT blob")
        if data[offset : offset + 4] == GCIX_MAGIC:
            offset += 16
        if len(data) < offset + 16 or data[offset : offset + 4] != GVRT_MAGIC:
            raise GvrError("not a GVRT blob")
        try:
            self.pixfmt = struct.unpack_from(">I", data, offset + 8)[0]
            self.width = struct.unpack_from(">H", data, offset + 12)[0]
            self.height = struct.unpack_from(">H", data, offset + 14)[0]
        except struct.error:
            raise GvrError("truncated GVRT header")
        if self.width <= 0 or self.height <= 0:
            raise GvrError("bad GVRT dimensions")
        fmt = self.pixfmt & 0xFF
        img = data[offset + 16 :]
        if fmt == FMT_RGB565:
            self.image_data = bytes(img[: self.width * self.height * 2])
            self.pixels = _decode_rgb565_tiled(self.image_data, self.width, self.height)
        elif fmt == FMT_RGB5A3:
            self.image_data = bytes(img[: self.width * self.height * 2])
            self.pixels = _decode_rgb5a3_tiled(self.image_data, self.width, self.height)
        elif fmt == FMT_RGBA8:
            self.image_data = bytes(img[: self.width * self.height * 4])
            self.pixels = _decode_rgba8_tiled(self.image_data, self.width, self.height)
        elif fmt == FMT_CMPR:
            self.image_data = bytes(img[: (self.width * self.height) // 2])
            self.pixels = _decode_cmpr_tiled(self.image_data, self.width, self.height)
        elif fmt == FMT_C4:
            self.image_data = bytes(img[: (self.width * self.height) // 2])
            self.image_type = 4
            self.pixels = _apply_gvpl_c4(
                self.image_data, palette, self.width, self.height
            )
        elif fmt == FMT_C8:
            self.image_data = bytes(img[: self.width * self.height])
            self.image_type = 5
            self.pixels = _apply_gvpl_c8(
                self.image_data, palette, self.width, self.height
            )
        else:
            raise GvrError(f"unsupported GameCube pixel format {self.pixfmt:#x}")
        self.total_size = 16 + len(self.image_data)
        if data[start : start + 4] == GCIX_MAGIC:
            self.total_size += 16
            try:
                self.gidx = struct.unpack_from(">I", data, start + 8)[0]
            except struct.error:
                self.gidx = 0
        return start + self.total_size


def _detile_4x4_16(src, width, height):
    if width <= 0 or height <= 0 or width % 4 or height % 4:
        raise GvrError(f"bad tiled dimensions {width}x{height}")
    n = width * height
    if len(src) < n * 2:
        raise GvrError("truncated tiled blob")
    words = struct.unpack_from(f">{n}H", src[: n * 2])
    dst = [0] * n
    tw = width // 4
    for ty in range(height // 4):
        for tx in range(tw):
            base = (ty * tw + tx) * 16
            for y in range(4):
                for x in range(4):
                    dst[(ty * 4 + y) * width + tx * 4 + x] = words[base + y * 4 + x]
    return dst


def _decode_rgb5a3_tiled(src, width, height):
    words = _detile_4x4_16(src, width, height)
    out = bytearray(len(words) * 4)
    for i, v in enumerate(words):
        r, g, b, a = _decode_rgb5a3(v)
        o = i * 4
        out[o] = r
        out[o + 1] = g
        out[o + 2] = b
        out[o + 3] = a
    return bytes(out)


def _decode_rgb565_tiled(src, width, height):
    words = _detile_4x4_16(src, width, height)
    out = bytearray(len(words) * 4)
    for i, v in enumerate(words):
        r, g, b, a = _decode_rgb565(v)
        o = i * 4
        out[o] = r
        out[o + 1] = g
        out[o + 2] = b
        out[o + 3] = a
    return bytes(out)


def _decode_rgba8_tiled(src, width, height):
    if width <= 0 or height <= 0 or width % 4 or height % 4:
        raise GvrError(f"bad RGBA8 dimensions {width}x{height}")
    if len(src) < width * height * 4:
        raise GvrError("truncated RGBA8 blob")
    out = bytearray(width * height * 4)
    tw = width // 4
    for ty in range(height // 4):
        for tx in range(tw):
            tbase = (ty * tw + tx) * 64
            ar = src[tbase : tbase + 32]
            gb = src[tbase + 32 : tbase + 64]
            for y in range(4):
                for x in range(4):
                    i = y * 4 + x
                    dx = tx * 4 + x
                    dy = ty * 4 + y
                    o = (dy * width + dx) * 4
                    out[o] = ar[i * 2 + 1]
                    out[o + 1] = gb[i * 2]
                    out[o + 2] = gb[i * 2 + 1]
                    out[o + 3] = ar[i * 2]
    return bytes(out)


def _decode_cmpr_tiled(src, width, height):
    if width <= 0 or height <= 0 or width % 8 or height % 8:
        raise GvrError(f"bad CMPR dimensions {width}x{height}")
    if len(src) < (width * height) // 2:
        raise GvrError("truncated CMPR blob")
    out = bytearray(width * height * 4)
    tw = width // 8
    for ty in range(height // 8):
        for tx in range(tw):
            tbase = (ty * tw + tx) * 32
            for sy in range(2):
                for sx in range(2):
                    blk = _decode_cmpr_block(src, tbase + (sy * 2 + sx) * 8)
                    for y in range(4):
                        for x in range(4):
                            r, g, b, a = blk[y * 4 + x]
                            dx = tx * 8 + sx * 4 + x
                            dy = ty * 8 + sy * 4 + y
                            o = (dy * width + dx) * 4
                            out[o] = r
                            out[o + 1] = g
                            out[o + 2] = b
                            out[o + 3] = a
    return bytes(out)


def _detile_8x8_c4(src, width, height):
    if width <= 0 or height <= 0 or width % 8 or height % 8:
        raise GvrError(f"bad C4 dimensions {width}x{height}")
    if len(src) < (width * height) // 2:
        raise GvrError("truncated C4 blob")
    n = width * height
    dst = [0] * n
    tw = width // 8
    for ty in range(height // 8):
        for tx in range(tw):
            tbase = (ty * tw + tx) * 32
            for y in range(8):
                for x in range(0, 8, 2):
                    b = src[tbase + y * 4 + x // 2]
                    dst[(ty * 8 + y) * width + tx * 8 + x] = (b >> 4) & 0x0F
                    dst[(ty * 8 + y) * width + tx * 8 + x + 1] = b & 0x0F
    return dst


def _apply_gvpl_c4(src, palette, width, height):
    indices = _detile_8x8_c4(src, width, height)
    pal_colors = None
    if palette:
        pal_colors = [c for (c, _a, _b, _c) in palette]
    out = bytearray(width * height * 4)
    for i, ci in enumerate(indices):
        o = i * 4
        if pal_colors is not None and ci < len(pal_colors):
            c = pal_colors[ci]
            out[o] = c & 0xFF
            out[o + 1] = (c >> 8) & 0xFF
            out[o + 2] = (c >> 16) & 0xFF
            out[o + 3] = (c >> 24) & 0xFF
        else:
            v = (ci * 17) & 0xFF
            out[o] = v
            out[o + 1] = v
            out[o + 2] = v
            out[o + 3] = 255
    return bytes(out)


def _detile_8x4_c8(src, width, height):
    if width <= 0 or height <= 0 or width % 8 or height % 4:
        raise GvrError(f"bad C8 dimensions {width}x{height}")
    if len(src) < width * height:
        raise GvrError("truncated C8 blob")
    n = width * height
    dst = [0] * n
    tw = width // 8
    for ty in range(height // 4):
        for tx in range(tw):
            tbase = (ty * tw + tx) * 32
            for y in range(4):
                for x in range(8):
                    dst[(ty * 4 + y) * width + tx * 8 + x] = src[tbase + y * 8 + x]
    return dst


def _apply_gvpl_c8(src, palette, width, height):
    indices = _detile_8x4_c8(src, width, height)
    pal_colors = None
    if palette:
        pal_colors = [c for (c, _a, _b, _c) in palette]
    out = bytearray(width * height * 4)
    for i, ci in enumerate(indices):
        o = i * 4
        if pal_colors is not None and ci < len(pal_colors):
            c = pal_colors[ci]
            out[o] = c & 0xFF
            out[o + 1] = (c >> 8) & 0xFF
            out[o + 2] = (c >> 16) & 0xFF
            out[o + 3] = (c >> 24) & 0xFF
        else:
            out[o] = ci
            out[o + 1] = ci
            out[o + 2] = ci
            out[o + 3] = 255
    return bytes(out)


class GvrDocument:
    def __init__(self):
        self.pictures = []

    @property
    def picture_count(self):
        return len(self.pictures)

    def read(self, data, offset=0, palette=None):
        pic = GvrPicture()
        pic.read(data, offset, palette)
        self.pictures = [pic]
        return offset + pic.total_size


def decode_gvr(data, offset=0, palette=None):
    doc = GvrDocument()
    doc.read(data, offset, palette)
    return doc


def parse_gvpl(data, offset):
    if data[offset : offset + 4] != GVPL_MAGIC:
        return 0, []
    try:
        _fmt = struct.unpack_from(">H", data, offset + 8)[0]
        count = struct.unpack_from(">H", data, offset + 14)[0]
    except struct.error:
        return 0, []
    if count <= 0 or count > 256:
        return 0, []
    if _fmt == TLUT_IA8:
        decode = _decode_ia8
    elif _fmt == TLUT_RGB5A3:
        decode = _decode_rgb5a3
    else:
        decode = _decode_rgb565
    entries = []
    for i in range(count):
        try:
            v = struct.unpack_from(">H", data, offset + 16 + i * 2)[0]
        except struct.error:
            return 0, []
        r, g, b, a = decode(v)
        c = r | (g << 8) | (b << 16) | (a << 24)
        entries.append((c, 0, 0, 0))
    return count, entries
