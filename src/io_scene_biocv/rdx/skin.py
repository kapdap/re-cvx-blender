import struct

SKIN_LEVELS = (0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0)


class SkinError(ValueError):
    pass


def parse_skin(data, offset, size, obj_num, endian="<"):
    if obj_num <= 0 or obj_num > 100000:
        raise SkinError("bad obj_num")
    if size < 8 or offset < 0 or offset + size > len(data):
        raise SkinError("skin out of range")
    if data[offset : offset + 4] != b"SKIN":
        raise SkinError("bad skin magic")
    payload_off = offset + 4
    payload_len = size - 4
    if payload_len % 4 != 0:
        raise SkinError("skin not int-aligned")
    nints = payload_len // 4
    ints = list(struct.unpack_from(endian + str(nints) + "i", data, payload_off))
    meshes = []
    ii = 0
    for node in range(obj_num):
        if ii >= len(ints):
            raise SkinError("skin truncated")
        flg = ints[ii]
        ii += 1
        if flg == 0:
            continue
        if flg & 0x2:
            if ii + 1 >= len(ints):
                raise SkinError("skin mesh header truncated")
            nb = ints[ii + 1]
            ii += 2
            if nb < 0 or nb > 100000:
                raise SkinError("bad skin nb")
            if ii + nb > len(ints):
                raise SkinError("skin weights truncated")
            weights = []
            for v in ints[ii : ii + nb]:
                u = v & 0xFFFFFFFF
                bone = (u >> 24) & 0xFF
                lvl = (u >> 16) & 0xFF
                if bone >= obj_num:
                    raise SkinError("skin bone out of range")
                lvl = min(lvl, 9)
                weights.append((bone, SKIN_LEVELS[lvl]))
            ii += nb
            meshes.append((node, weights))
        else:
            if ii >= len(ints):
                raise SkinError("skin influencer truncated")
            ii += 1
    return meshes
