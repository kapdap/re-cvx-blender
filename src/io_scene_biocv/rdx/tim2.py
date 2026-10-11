import struct

TIM2_MAGIC = b"TIM2"

CT_UNDEFINED = 0
CT_RGBA16 = 1
CT_RGB32 = 2
CT_RGBA32 = 3
CT_INDEXED4 = 4
CT_INDEXED8 = 5


class Tim2Error(ValueError):
    pass


class Tim2Picture:
    def __init__(self):
        self.total_size = 0
        self.clut_size = 0
        self.image_size = 0
        self.header_size = 0
        self.clut_colors = 0
        self.pic_format = 0
        self.mipmaps = 0
        self.clut_type = CT_UNDEFINED
        self.image_type = CT_UNDEFINED
        self.width = 0
        self.height = 0

        self.texa = 0
        self.image_data = b""
        self.clut_data = None
        self.pixels = b""

    def read(self, data, offset):
        start = offset
        (
            self.total_size,
            self.clut_size,
            self.image_size,
            self.header_size,
            self.clut_colors,
            self.pic_format,
            self.mipmaps,
            self.clut_type,
            self.image_type,
            self.width,
            self.height,
        ) = struct.unpack_from("<iiiHHBBBBHH", data, offset)
        offset += 24
        offset += 16 + 8
        if start + 44 <= len(data):
            self.texa = struct.unpack_from("<I", data, start + 40)[0]
        if self.mipmaps > 1 and offset - start < self.header_size:
            offset += 48
        hdr_read = offset - start
        if hdr_read < self.header_size:
            offset += self.header_size - hdr_read
        self.image_data = data[offset : offset + self.image_size]
        offset += self.image_size
        self.clut_data = (
            data[offset : offset + self.clut_size] if self.clut_size > 0 else None
        )
        offset += self.clut_size
        end = start + self.total_size
        if offset != end:
            offset = end
        if self.width > 0 and self.height > 0:
            self.pixels = _decode_image_data(
                self.image_type,
                self.image_data,
                self.clut_data,
                self.clut_type,
                self.width,
                self.height,
                self.texa,
            )
        return offset


class Tim2Document:
    def __init__(self):
        self.version = 0
        self.format = 0
        self.picture_count = 0
        self.pictures = []

        self.org_color_type = None
        self.org_tex_type = None

    def read(self, data, offset=0):
        if data[offset : offset + 4] != TIM2_MAGIC:
            raise Tim2Error("not a TIM2 blob")
        self.version, self.format, self.picture_count = struct.unpack_from(
            "<BBh", data, offset + 4
        )
        if offset + 14 <= len(data):
            self.org_color_type = data[offset + 12]
            self.org_tex_type = data[offset + 13]
        offset += 16
        if self.format == 1:
            offset += 112
        for _ in range(self.picture_count):
            pic = Tim2Picture()
            offset = pic.read(data, offset)
            if self.org_color_type is not None:
                pic.pixels = _normalize_indexed_alpha(
                    pic.pixels,
                    pic.image_type,
                    self.org_color_type,
                    pic.pic_format,
                )
            self.pictures.append(pic)
        return offset


def decode_tim2(data, offset=0):
    doc = Tim2Document()
    doc.read(data, offset)
    return doc


def parse_pli(data, offset):
    try:
        palnum = struct.unpack_from("<i", data, offset)[0]
    except struct.error:
        return 0, []
    if palnum <= 0 or palnum > 64:
        return 0, []
    entries = []
    for lop in range(palnum):
        try:
            color = struct.unpack_from("<I", data, offset + 4 + lop * 8 + 4)[0]
        except struct.error:
            return 0, []
        entries.append(
            (color, color & 0xFF, (color >> 8) & 0xFF, (color >> 16) & 0xFFFF)
        )
    return palnum, entries


def apply_pal_sub(image_type, image_data, pixels, pal_colors):
    if not pal_colors or not pixels or not image_data:
        return pixels
    if image_type == CT_INDEXED8:
        buf = bytearray(pixels)
        n = len(image_data)
        for i in range(n):
            ci = image_data[i]
            if ci < len(pal_colors):
                d = i * 4
                if d + 4 > len(buf):
                    break
                c = pal_colors[ci]
                buf[d] = c & 0xFF
                buf[d + 1] = (c >> 8) & 0xFF
                buf[d + 2] = (c >> 16) & 0xFF
                buf[d + 3] = (c >> 24) & 0xFF
        return bytes(buf)
    if image_type == CT_INDEXED4:
        buf = bytearray(pixels)
        n = len(image_data) * 2
        for i in range(n):
            bi = i // 2
            if bi >= len(image_data):
                break
            byte = image_data[bi]
            ci = (byte & 0x0F) if (i % 2) == 0 else ((byte >> 4) & 0x0F)
            if ci < len(pal_colors):
                d = i * 4
                if d + 4 > len(buf):
                    break
                c = pal_colors[ci]
                buf[d] = c & 0xFF
                buf[d + 1] = (c >> 8) & 0xFF
                buf[d + 2] = (c >> 16) & 0xFF
                buf[d + 3] = (c >> 24) & 0xFF
        return bytes(buf)
    return pixels


def classify_alpha(pixels):
    if not pixels:
        return "OPAQUE"
    seen_zero = False
    seen_full = False
    seen_mid = False
    for i in range(3, len(pixels), 4):
        a = pixels[i]
        if a == 0:
            seen_zero = True
        elif a == 255:
            seen_full = True
        else:
            seen_mid = True
            break
    if seen_mid:
        return "BLEND"
    if seen_zero and seen_full:
        return "CUTOUT"
    return "OPAQUE"


def is_vq_path(pict_format):
    return not (5 <= pict_format < 9)


def _decode_image_data(
    image_type, image_data, clut_data, clut_type, width, height, texa=0
):
    pixels = width * height
    out = bytearray(pixels * 4)
    clut = None
    if clut_data:
        clut = _fix_palette_ps2(clut_data, clut_type, image_type)
    if image_type == CT_RGBA32:
        _rgba32_to_rgba(image_data, out, pixels)
    elif image_type == CT_RGB32:
        _rgb32_to_rgba(image_data, out, pixels)
    elif image_type == CT_RGBA16:
        _rgba16_to_rgba(image_data, out, pixels, texa)
    elif image_type == CT_INDEXED8:
        _indexed8_to_rgba(image_data, clut, out, pixels)
    elif image_type == CT_INDEXED4:
        _indexed4_to_rgba(image_data, clut, out, pixels)
    else:
        if image_data:
            n = min(len(image_data), len(out))
            out[:n] = image_data[:n]
    return bytes(out)


def _fix_palette_ps2(palette, clut_type, image_type):
    if palette is None:
        return None
    if image_type not in (CT_INDEXED4, CT_INDEXED8):
        return palette
    if (clut_type & 0x80) != 0:
        return palette
    entry = {1: 2, 2: 3, 3: 4}.get(clut_type & 0x3F)
    if entry is None:
        return palette
    if len(palette) % entry != 0:
        raise Tim2Error("palette length must be a multiple of entry size")
    group = 32 * entry
    if len(palette) < group:
        return palette
    result = bytearray(palette)
    for base in range(0, len(palette) - group + 1, group):
        q = group // 4
        result[base + q : base + 2 * q] = palette[base + 2 * q : base + 3 * q]
        result[base + 2 * q : base + 3 * q] = palette[base + q : base + 2 * q]
    return bytes(result)


def _rgba32_to_rgba(inp, out, pixels):
    out[:] = inp[: pixels * 4]


def _rgb32_to_rgba(inp, out, pixels):
    for i in range(pixels):
        s = i * 4
        out[s] = inp[s]
        out[s + 1] = inp[s + 1]
        out[s + 2] = inp[s + 2]
        out[s + 3] = 255


def _rgba16_to_rgba(inp, out, pixels, texa=0):
    aem = (texa >> 15) & 1
    ta0 = texa & 0xFF
    ta1 = (texa >> 16) & 0xFF
    for i in range(pixels):
        s = i * 2
        v = inp[s] | (inp[s + 1] << 8)
        r = (v & 0x1F) * 255 // 31
        g = ((v >> 5) & 0x1F) * 255 // 31
        b = ((v >> 10) & 0x1F) * 255 // 31
        if v & 0x8000:
            a = 255 if not aem else (min(255, ta1 * 2))
        else:
            a = 0 if not aem else (min(255, ta0 * 2))
        d = i * 4
        out[d] = r
        out[d + 1] = g
        out[d + 2] = b
        out[d + 3] = a


def _indexed8_to_rgba(inp, clut, out, pixels):
    if clut is None or inp is None:
        return
    for i in range(pixels):
        if i >= len(inp):
            break
        ci = inp[i] * 4
        d = i * 4
        if ci < len(clut) - 3:
            out[d] = clut[ci]
            out[d + 1] = clut[ci + 1]
            out[d + 2] = clut[ci + 2]
            out[d + 3] = clut[ci + 3]


def _indexed4_to_rgba(inp, clut, out, pixels):
    if clut is None or inp is None:
        return
    for i in range(pixels):
        bi = i // 2
        if bi >= len(inp):
            break
        byte = inp[bi]
        shift = 0 if (i % 2) == 0 else 4
        ci = ((byte >> shift) & 0x0F) * 4
        d = i * 4
        if ci < len(clut) - 3:
            out[d] = clut[ci]
            out[d + 1] = clut[ci + 1]
            out[d + 2] = clut[ci + 2]
            out[d + 3] = clut[ci + 3]


def _normalize_indexed_alpha(pixels, image_type, org_color_type, pict_format):
    if image_type not in (CT_INDEXED4, CT_INDEXED8):
        return pixels
    if org_color_type not in (0, 1, 2, 6):
        return pixels
    if not pixels:
        return pixels
    vq = is_vq_path(pict_format if pict_format is not None else -1)
    buf = bytearray(pixels)

    def alpha_is_000():
        for i in range(0, len(buf), 4):
            if buf[i + 3] != 0 and buf[i] == 0 and buf[i + 1] == 0 and buf[i + 2] == 0:
                buf[i + 3] = 0

    def alpha_4to8():
        for i in range(3, len(buf), 4):
            v = buf[i]
            buf[i] = v | (v >> 4)

    def alpha_is_half():
        for i in range(3, len(buf), 4):
            buf[i] = (buf[i] + 1) >> 1

    if vq:
        if org_color_type == 2:
            alpha_4to8()
            alpha_is_half()
        elif org_color_type == 6:
            alpha_is_half()
    else:
        if org_color_type in (0, 1):
            alpha_is_000()
        elif org_color_type == 2:
            alpha_is_000()
            alpha_4to8()
            alpha_is_half()
        elif org_color_type == 6:
            alpha_is_000()
            alpha_is_half()
    for i in range(3, len(buf), 4):
        v = buf[i] * 2
        buf[i] = min(v, 255)
    return bytes(buf)
