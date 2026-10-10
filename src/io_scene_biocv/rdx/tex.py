from . import gvr, pvr, tim2

TexError = ValueError

Tim2Error = tim2.Tim2Error
Tim2Document = tim2.Tim2Document
Tim2Picture = tim2.Tim2Picture
TIM2_MAGIC = tim2.TIM2_MAGIC

PvrError = pvr.PvrError
PvrDocument = pvr.PvrDocument
PvrPicture = pvr.PvrPicture

GvrError = gvr.GvrError
GvrDocument = gvr.GvrDocument
GvrPicture = gvr.GvrPicture
GCIX_MAGIC = gvr.GCIX_MAGIC
GVRT_MAGIC = gvr.GVRT_MAGIC
GVPL_MAGIC = gvr.GVPL_MAGIC

CT_UNDEFINED = tim2.CT_UNDEFINED
CT_RGBA16 = tim2.CT_RGBA16
CT_RGB32 = tim2.CT_RGB32
CT_RGBA32 = tim2.CT_RGBA32
CT_INDEXED4 = tim2.CT_INDEXED4
CT_INDEXED8 = tim2.CT_INDEXED8


def kind_at(data, offset):
    magic = data[offset : offset + 4]
    if magic == TIM2_MAGIC:
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
    raise TexError("unknown texture blob at offset %d" % offset)


def decode_tim2(data, offset=0):
    return tim2.decode_tim2(data, offset)


def decode_pvr(data, offset=0, palette=None):
    pal = palette[1] if isinstance(palette, tuple) else palette
    return pvr.decode_pvr(data, offset, pal)


def decode_gvr(data, offset=0, palette=None):
    pal = palette[1] if isinstance(palette, tuple) else palette
    return gvr.decode_gvr(data, offset, pal)


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
