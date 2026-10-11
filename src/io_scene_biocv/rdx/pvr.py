import struct

PvrError = ValueError

GBIX_MAGIC = b"GBIX"
PVRT_MAGIC = b"PVRT"
PVPL_MAGIC = b"PVPL"

PIX_ARGB1555 = 0x00
PIX_RGB565 = 0x01
PIX_ARGB4444 = 0x02

DATA_TWIDDLED = 0x01
DATA_TWIDDLED_MIP = 0x02
DATA_VQ = 0x03
DATA_PAL4 = 0x05
DATA_PAL8 = 0x07
DATA_RECT = 0x09
DATA_RECT_TWIDDLED = 0x0D
DATA_SMALLVQ = 0x10


def _morton(x, y):
    out = 0
    shift = 0
    while x or y:
        out |= (y & 1) << shift
        out |= (x & 1) << (shift + 1)
        x >>= 1
        y >>= 1
        shift += 2
    return out


def _decode1555(v):
    r = ((v >> 10) & 0x1F) * 255 // 31
    g = ((v >> 5) & 0x1F) * 255 // 31
    b = (v & 0x1F) * 255 // 31
    a = 255 if v & 0x8000 else 0
    return r, g, b, a


def _decode565(v):
    r = ((v >> 11) & 0x1F) * 255 // 31
    g = ((v >> 5) & 0x3F) * 255 // 63
    b = (v & 0x1F) * 255 // 31
    return r, g, b, 255


def _decode4444(v):
    a = ((v >> 12) & 0x0F) * 17
    r = ((v >> 8) & 0x0F) * 17
    g = ((v >> 4) & 0x0F) * 17
    b = (v & 0x0F) * 17
    return r, g, b, a


_DECODERS = {
    PIX_ARGB1555: _decode1555,
    PIX_RGB565: _decode565,
    PIX_ARGB4444: _decode4444,
}


def _detwiddle_16(src, width, height):
    n = width * height
    words = struct.unpack_from(f"<{n}H", src)
    dst = [0] * n
    for y in range(height):
        base = y * width
        for x in range(width):
            dst[base + x] = words[_morton(x, y)]
    return dst


def _detwiddle_8(src, width, height):
    n = width * height
    dst = [0] * n
    for y in range(height):
        base = y * width
        for x in range(width):
            dst[base + x] = src[_morton(x, y)]
    return dst


def _detwiddle_4(src, width, height):
    n = width * height
    dst = [0] * n
    for y in range(height):
        base = y * width
        for x in range(width):
            mi = _morton(x, y)
            byte = src[mi // 2]
            idx = (byte & 0x0F) if (mi % 2) == 0 else ((byte >> 4) & 0x0F)
            dst[base + x] = idx
    return dst


def _detwiddle_rect_16(src, width, height):
    side = min(width, height)
    if max(width, height) % side != 0:
        raise PvrError(f"bad rectangular size {width}x{height}")
    tiles = max(width, height) // side
    if len(src) < tiles * side * side * 2:
        raise PvrError("truncated rectangular blob")
    dst = [0] * (width * height)
    for t in range(tiles):
        words = struct.unpack_from(f"<{side * side}H", src, t * side * side * 2)
        for y in range(side):
            for x in range(side):
                dx, dy = (t * side + x, y) if width >= height else (x, t * side + y)
                dst[dy * width + dx] = words[_morton(x, y)]
    return dst


def _decode_words(words, pixfmt):
    decode = _DECODERS.get(pixfmt)
    if decode is None:
        raise PvrError(f"unsupported Dreamcast pixel format {pixfmt:#x}")
    out = bytearray(len(words) * 4)
    for i, v in enumerate(words):
        r, g, b, a = decode(v)
        o = i * 4
        out[o] = r
        out[o + 1] = g
        out[o + 2] = b
        out[o + 3] = a
    return bytes(out)


def _decode_vq(pixdata, width, height, pixfmt):
    nidx = (width // 2) * (height // 2)
    codebook_size = len(pixdata) - nidx
    if codebook_size <= 0 or codebook_size % 8 != 0:
        raise PvrError(f"bad VQ codebook size {codebook_size}")
    codebook = pixdata[:codebook_size]
    indices = _detwiddle_8(pixdata[codebook_size:], width // 2, height // 2)
    nentries = codebook_size // 8
    words = [0] * (width * height)
    for by in range(height // 2):
        for bx in range(width // 2):
            entry = indices[by * (width // 2) + bx] % nentries
            base = entry * 8
            t0, t1, t2, t3 = struct.unpack_from("<4H", codebook, base)
            dx = bx * 2
            row0 = (by * 2) * width + dx
            row1 = (by * 2 + 1) * width + dx
            words[row0] = t0
            words[row0 + 1] = t2
            words[row1] = t1
            words[row1 + 1] = t3
    return _decode_words(words, pixfmt)


class PvrPicture:
    def __init__(self):
        self.width = 0
        self.height = 0
        self.pixfmt = 0
        self.datafmt = 0
        self.image_data = b""
        self.pixels = b""
        self.image_type = 1
        self.pic_format = 0
        self.total_size = 0

    def read(self, data, offset, palette=None):
        start = offset
        if data[offset : offset + 4] == GBIX_MAGIC:
            offset += 16
        if data[offset : offset + 4] != PVRT_MAGIC:
            raise PvrError("not a PVRT blob")
        size, self.pixfmt, self.datafmt = struct.unpack_from("<IBB", data, offset + 4)
        self.width, self.height = struct.unpack_from("<HH", data, offset + 12)
        if self.width <= 0 or self.height <= 0:
            raise PvrError("bad PVRT dimensions")
        pixdata = data[offset + 16 : offset + 8 + size]
        if len(pixdata) != size - 8:
            raise PvrError("truncated PVRT blob")
        end = offset + 8 + size
        if self.datafmt == DATA_TWIDDLED:
            words = _detwiddle_16(pixdata, self.width, self.height)
            self.pixels = _decode_words(words, self.pixfmt)
            self.image_data = pixdata
        elif self.datafmt == DATA_RECT_TWIDDLED:
            words = _detwiddle_rect_16(pixdata, self.width, self.height)
            self.pixels = _decode_words(words, self.pixfmt)
            self.image_data = pixdata
        elif self.datafmt == DATA_TWIDDLED_MIP:
            base = pixdata[-self.width * self.height * 2 :]
            words = _detwiddle_16(base, self.width, self.height)
            self.pixels = _decode_words(words, self.pixfmt)
            self.image_data = pixdata
        elif self.datafmt == DATA_RECT:
            n = self.width * self.height
            words = list(struct.unpack_from(f"<{n}H", pixdata))
            self.pixels = _decode_words(words, self.pixfmt)
            self.image_data = pixdata
        elif self.datafmt in (DATA_VQ, DATA_SMALLVQ):
            self.pixels = _decode_vq(pixdata, self.width, self.height, self.pixfmt)
            self.image_data = pixdata
        elif self.datafmt == DATA_PAL4:
            indices = _detwiddle_4(pixdata, self.width, self.height)
            self.image_data = _pack_nibbles(indices)
            self.image_type = 4
            self.pixels = _apply_palette(
                indices, palette, self.pixfmt, self.width * self.height
            )
        elif self.datafmt == DATA_PAL8:
            indices = _detwiddle_8(pixdata, self.width, self.height)
            self.image_data = bytes(indices)
            self.image_type = 5
            self.pixels = _apply_palette(
                indices, palette, self.pixfmt, self.width * self.height
            )
        else:
            raise PvrError(f"unsupported Dreamcast data format {self.datafmt:#x}")
        self.total_size = end - start
        return end


def _pack_nibbles(indices):
    out = bytearray((len(indices) + 1) // 2)
    for i, v in enumerate(indices):
        if i % 2 == 0:
            out[i // 2] = v & 0x0F
        else:
            out[i // 2] |= (v & 0x0F) << 4
    return bytes(out)


def _apply_palette(indices, palette, pixfmt, count):
    decode = _DECODERS.get(pixfmt, _decode4444)
    pal_colors = None
    if palette:
        pal_colors = [c for (c, _tf, _b, _e) in palette]
    out = bytearray(count * 4)
    for i in range(count):
        ci = indices[i] if i < len(indices) else 0
        if pal_colors is not None and ci < len(pal_colors):
            c = pal_colors[ci]
            out[i * 4] = c & 0xFF
            out[i * 4 + 1] = (c >> 8) & 0xFF
            out[i * 4 + 2] = (c >> 16) & 0xFF
            out[i * 4 + 3] = (c >> 24) & 0xFF
        else:
            v = (ci * 17) & 0xFFFF
            r, g, b, a = decode(v)
            out[i * 4] = r
            out[i * 4 + 1] = g
            out[i * 4 + 2] = b
            out[i * 4 + 3] = a
    return bytes(out)


class PvrDocument:
    def __init__(self):
        self.pictures = []

    @property
    def picture_count(self):
        return len(self.pictures)

    def read(self, data, offset=0, palette=None):
        pic = PvrPicture()
        pic.read(data, offset, palette)
        self.pictures = [pic]
        return offset + pic.total_size


def decode_pvr(data, offset=0, palette=None):
    doc = PvrDocument()
    doc.read(data, offset, palette)
    return doc


def parse_pvpl(data, offset, pixfmt=PIX_ARGB4444):
    if data[offset : offset + 4] != PVPL_MAGIC:
        return 0, []
    try:
        size = struct.unpack_from("<I", data, offset + 4)[0]
    except struct.error:
        return 0, []
    decode = _DECODERS.get(pixfmt, _decode4444)
    pal_off = offset + 16
    pal_bytes = data[pal_off : pal_off + max(0, size - 8)]
    if len(pal_bytes) < 2:
        return 0, []
    n = len(pal_bytes) // 2
    try:
        n_field = struct.unpack_from("<H", data, offset + 14)[0]
    except struct.error:
        n_field = 0
    if 1 <= n_field <= 256:
        n = min(n, n_field)
    if n <= 0 or n > 256:
        return 0, []
    entries = []
    for i in range(n):
        v = struct.unpack_from("<H", pal_bytes, i * 2)[0]
        r, g, b, a = decode(v)
        c = r | (g << 8) | (b << 16) | (a << 24)
        entries.append((c, 0, 0, 0))
    return n, entries
