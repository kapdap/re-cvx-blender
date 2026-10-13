import struct


class MotionError(ValueError):
    pass


def iter_motion_bins(data, base, end, endian="<"):
    o = base
    while o + 4 <= end:
        size = struct.unpack_from(endian + "i", data, o)[0]
        if size == -1:
            return
        if size == 0:
            o += 4
            continue
        if size < 16 or o + 4 + size > end:
            return
        blob = o + 4
        if data[blob : blob + 3] != b"MTN":
            return
        yield (blob, size)
        o += 4 + size


def parse_mnb(data, offset, size, endian="<"):
    if size < 16 or offset < 0 or offset + size > len(data):
        raise MotionError("motion out of range")
    if data[offset : offset + 3] != b"MTN":
        raise MotionError("bad motion magic")
    dtop_rel = struct.unpack_from(endian + "H", data, offset + 4)[0]
    obj_num = struct.unpack_from(endian + "H", data, offset + 6)[0]
    mtn_off = struct.unpack_from(endian + "i", data, offset + 8)[0]
    if obj_num <= 0 or obj_num > 512:
        raise MotionError("bad motion obj_num")
    dtop = offset + dtop_rel
    if dtop > len(data):
        raise MotionError("bad motion base")
    mtn = dtop + mtn_off
    if mtn < 0 or mtn + 12 > len(data):
        raise MotionError("bad motion header")
    mdata_off, frm_num = struct.unpack_from(endian + "ii", data, mtn)
    if frm_num <= 0 or frm_num > 4096:
        raise MotionError("bad motion frames")
    md = dtop + mdata_off
    if md < 0 or md + obj_num * 8 > len(data):
        raise MotionError("bad motion nodes")
    tracks = []
    for i in range(obj_num):
        p0, p1 = struct.unpack_from(endian + "ii", data, md + i * 8)
        pos = None
        ang = None
        if p0 != -1:
            po = dtop + p0
            if po < 0 or po + frm_num * 12 > len(data):
                raise MotionError("bad motion pos")
            pos = [
                struct.unpack_from(endian + "3f", data, po + f * 12)
                for f in range(frm_num)
            ]
        if p1 != -1:
            ao = dtop + p1
            if ao < 0 or ao + frm_num * 6 > len(data):
                raise MotionError("bad motion ang")
            ang = [
                struct.unpack_from(endian + "3H", data, ao + f * 6)
                for f in range(frm_num)
            ]
        tracks.append((pos, ang))
    return (obj_num, frm_num, tracks)
