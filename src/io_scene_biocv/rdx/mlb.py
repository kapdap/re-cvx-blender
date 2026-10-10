from __future__ import annotations

import struct

from .nj import (
    NjError,
    NjObject,
    NjTexList,
    read_model,
)

SIZE_CNK_OBJECT = 52


def _ascii4(data, offset):
    return data[offset : offset + 4].decode("ascii", errors="replace")


class Mlb:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.magic = ""
        self.status = 0
        self.is_chunk = False
        self.objects = []
        self.models = []
        self.texlist = NjTexList()
        self.notes = []
        self.dat_top = 0
        self.obj_base = 0
        self.dtop_off = 0
        self.obj_num = 0
        self.tex_off = -1
        self.obj_off = -1

    def object_index_of(self, offset):
        if offset == -1:
            return -1
        base_rel = self.obj_base - self.dat_top
        idx, rem = divmod(offset - base_rel, SIZE_CNK_OBJECT)
        if rem != 0 or idx < 0 or idx >= len(self.objects):
            return -1
        return idx

    def read(self, data, offset, size, endian="<"):
        self.offset = offset
        self.size = size
        if size < 16 or offset + 16 > len(data):
            raise NjError("MLB too small")
        self.magic = _ascii4(data, offset)
        self.status = data[offset + 3]
        self.is_chunk = bool(self.status & 0x80)
        dtop_off, obj_num = struct.unpack_from(endian + "2H", data, offset + 4)
        tex_off, obj_off = struct.unpack_from(endian + "2i", data, offset + 8)
        dat_top = offset + dtop_off
        self.dat_top = dat_top
        self.obj_base = dat_top + obj_off if obj_off != -1 else 0
        self.dtop_off = dtop_off
        self.obj_num = obj_num
        self.tex_off = tex_off
        self.obj_off = obj_off
        self.texlist.read(data, dat_top, tex_off, endian)
        if not self.is_chunk:
            return self
        if obj_off == -1 or obj_num <= 0 or obj_num > 100000:
            return self
        model_offs = []
        for i in range(obj_num):
            oo = dat_top + obj_off + i * SIZE_CNK_OBJECT
            if oo < 0 or oo + SIZE_CNK_OBJECT > len(data):
                self.notes.append("object array overrun at %d" % i)
                break
            obj = NjObject()
            mo = obj.read(data, oo, i, endian)
            model_offs.append(mo)
            self.objects.append(obj)
        uniq = {}
        for obj, mo in zip(self.objects, model_offs, strict=False):
            if mo == -1:
                continue
            mno = dat_top + mo
            if mno < 0 or mno + 8 > len(data):
                self.notes.append("model offset out of range")
                continue
            if mno not in uniq:
                uniq[mno] = len(self.models)
                self.models.append(None)
            obj.model_index = uniq[mno]
        inv = {v: k for k, v in uniq.items()}
        for idx in range(len(self.models)):
            mno = inv[idx]
            try:
                self.models[idx] = read_model(data, dat_top, mno, endian)
            except NjError as exc:
                self.models[idx] = None
                self.notes.append(f"model decode failed: {exc}")
        return self


def iter_mlb_blobs(data, base, end, endian="<"):
    if base + 4 > end or base < 0 or end > len(data):
        return
    if end - base >= 3 and data[base : base + 3] == b"MDL":
        yield (base, end - base)
        return
    o = base
    while o + 4 <= end:
        size = struct.unpack_from(endian + "i", data, o)[0]
        if size == -1:
            break
        if size == 0:
            o += 4
            continue
        if size < 0 or o + 4 + size > end:
            break
        blob = o + 4
        if blob + 4 > end:
            break
        magic = _ascii4(data, blob)
        if magic != "MASK" and data[blob : blob + 4] != b"SKIN":
            yield (blob, size)
        o += 4 + size
    if o + 3 <= end and data[o : o + 3] == b"MDL":
        yield (o, end - o)


def read_mlb(data, offset, size, endian="<"):
    mlb = Mlb()
    mlb.read(data, offset, size, endian)
    return mlb
