from . import gvr, pvr, tim2

TexError = ValueError


def kind_at(data, offset):
    magic = data[offset : offset + 4]
    if magic == tim2.TIM2_MAGIC:
        return "TIM2"
    if magic == pvr.GBIX_MAGIC or magic == pvr.PVRT_MAGIC:
        return "PVR"
    if magic == gvr.GCIX_MAGIC or magic == gvr.GVRT_MAGIC:
        return "GVR"
    return None


def decode(data, offset=0, palette=None):
    kind = kind_at(data, offset)
    if kind == "TIM2":
        return tim2.decode_tim2(data, offset)
    if kind == "PVR":
        pal = None
        if palette is not None:
            pal = palette[1] if isinstance(palette, tuple) else palette
        return pvr.decode_pvr(data, offset, pal)
    if kind == "GVR":
        pal = None
        if palette is not None:
            pal = palette[1] if isinstance(palette, tuple) else palette
        return gvr.decode_gvr(data, offset, pal)
    raise TexError(f"unknown texture blob at offset {offset}")


def parse_pli(data, offset):
    return tim2.parse_pli(data, offset)


def parse_pvpl(data, offset, pixfmt=pvr.PIX_ARGB4444):
    return pvr.parse_pvpl(data, offset, pixfmt)


def parse_gvpl(data, offset):
    return gvr.parse_gvpl(data, offset)


def apply_pal_sub(image_type, image_data, pixels, pal_colors):
    return tim2.apply_pal_sub(image_type, image_data, pixels, pal_colors)


def is_vq_path(pict_format):
    return tim2.is_vq_path(pict_format)


def classify_alpha(pixels):
    return tim2.classify_alpha(pixels)
