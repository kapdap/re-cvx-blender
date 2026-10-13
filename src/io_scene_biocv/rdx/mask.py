import struct


class MaskError(ValueError):
    pass


def _parse_param(data, offset, endian="<"):
    muscle = list(struct.unpack_from(endian + "32f", data, offset))
    jawang, jawtrans = struct.unpack_from(endian + "2f", data, offset + 128)
    eye = struct.unpack_from(endian + "3f", data, offset + 136)
    tangx, tangy, tangz = struct.unpack_from(endian + "3f", data, offset + 148)
    frame, flag = struct.unpack_from(endian + "2h", data, offset + 160)
    return (muscle, jawang, jawtrans, eye, tangx, tangy, tangz, frame, flag)


class Mask:
    def __init__(self):
        self.offset = 0
        self.size = 0
        self.version = 0
        self.flag = 0
        self.jaw_ids = (0, 0)
        self.n_attr = 0
        self.n_list = 0
        self.n_connect = 0
        self.n_jaw = 0
        self.n_tang = 0
        self.n_face = 0
        self.face_id = -1
        self.tang_id = -1
        self.tooth_id = -1
        self.eye_ids = []
        self.vlist = []
        self.nvpt = []
        self.list = []
        self.jaw = []
        self.tang = []
        self.face = []

    def read(self, data, offset, size, endian="<"):
        self.offset = offset
        self.size = size
        if size < 64 or offset < 0 or offset + size > len(data):
            raise MaskError("mask out of range")
        if data[offset : offset + 4] != b"MASK":
            raise MaskError("bad mask magic")
        self.version, self.flag = struct.unpack_from(endian + "2H", data, offset + 4)
        self.jaw_ids = struct.unpack_from(endian + "2H", data, offset + 8)
        (
            self.n_attr,
            self.n_list,
            self.n_connect,
            self.n_jaw,
            self.n_tang,
            self.n_face,
        ) = struct.unpack_from(endian + "6I", data, offset + 12)
        fid, tid, toid = struct.unpack_from("3b", data, offset + 52)
        self.face_id = fid
        self.tang_id = tid
        self.tooth_id = toid
        self.eye_ids = list(struct.unpack_from("9b", data, offset + 55))
        if self.n_list > 100000:
            raise MaskError("bad mask n_list")
        if self.n_connect > 1000000:
            raise MaskError("bad mask n_connect")
        if self.n_jaw > 100000:
            raise MaskError("bad mask n_jaw")
        if self.n_tang > 100000:
            raise MaskError("bad mask n_tang")
        if self.n_face > 10000:
            raise MaskError("bad mask n_face")
        o = offset + 64
        end = offset + size
        self.vlist = []
        for _ in range(self.n_list):
            if o + 4 > end:
                raise MaskError("mask vlist truncated")
            vid, mnum, nvnum = struct.unpack_from(endian + "hBB", data, o)
            self.vlist.append((vid, mnum, nvnum))
            o += 4
        total_nv = sum(nvnum for _, _, nvnum in self.vlist)
        if o + total_nv * 4 > end:
            raise MaskError("mask nvpt truncated")
        self.nvpt = (
            list(struct.unpack_from(endian + str(total_nv) + "i", data, o))
            if total_nv
            else []
        )
        o += total_nv * 4
        self.list = []
        for _ in range(self.n_connect):
            if o + 20 > end:
                raise MaskError("mask list truncated")
            lid, x, y, z, scal = struct.unpack_from(endian + "i4f", data, o)
            self.list.append((lid, (x, y, z), scal))
            o += 20
        self.jaw = []
        for _ in range(self.n_jaw):
            if o + 8 > end:
                raise MaskError("mask jaw truncated")
            jid, rate = struct.unpack_from(endian + "if", data, o)
            self.jaw.append((jid, rate))
            o += 8
        self.tang = []
        for _ in range(self.n_tang):
            if o + 8 > end:
                raise MaskError("mask tang truncated")
            jid, rate = struct.unpack_from(endian + "if", data, o)
            self.tang.append((jid, rate))
            o += 8
        self.face = []
        for _ in range(self.n_face):
            if o + 164 > end:
                raise MaskError("mask face truncated")
            self.face.append(_parse_param(data, o, endian))
            o += 164
        return self


def parse_mask(data, offset, size, endian="<"):
    return Mask().read(data, offset, size, endian)


def search_object(mlb_data, obj_id):
    if obj_id < 0:
        return None
    count = 0
    stack = []
    obj = mlb_data.objects[0] if mlb_data.objects else None
    seen = set()
    while obj is not None:
        if obj.model_index != -1:
            if count == obj_id:
                return obj
            count += 1
        if obj.index in seen:
            break
        seen.add(obj.index)
        sib = mlb_data.object_index_of(obj.sibling)
        child = mlb_data.object_index_of(obj.child)
        if child != -1:
            if sib != -1:
                stack.append(sib)
            obj = mlb_data.objects[child]
            continue
        if sib != -1:
            obj = mlb_data.objects[sib]
            continue
        if stack:
            obj = mlb_data.objects[stack.pop()]
        else:
            obj = None
    return None


def apply_muscle(verts, mask, muscle):
    out = [tuple(v) for v in verts]
    con_idx = 0
    for vid, mnum, _nvnum in mask.vlist:
        if vid < 0 or vid >= len(out):
            con_idx += mnum
            continue
        total = 0.0
        acc = []
        for _ in range(mnum):
            if con_idx >= len(mask.list):
                break
            lid, vec, scal = mask.list[con_idx]
            con_idx += 1
            if lid < 0 or lid >= len(muscle):
                continue
            para = muscle[lid]
            if para == 0.0:
                continue
            rate = scal * abs(para)
            total += rate
            acc.append((vec, para * rate))
        if total == 0.0:
            continue
        rsum = 1.0 / total
        dx, dy, dz = out[vid]
        for (vx, vy, vz), mr in acc:
            k = mr * rsum
            dx += vx * k
            dy += vy * k
            dz += vz * k
        out[vid] = (dx, dy, dz)
    return out


def parse_mask_pool(data, offset, end, endian="<"):
    pools = []
    o = offset
    while o + 4 <= end:
        size = struct.unpack_from(endian + "i", data, o)[0]
        if size == -1:
            break
        if size <= 0 or o + 4 + size > end:
            break
        d = o + 4
        mid = data[d]
        fnum = struct.unpack_from(endian + "i", data, d + 4)[0]
        if fnum < 0 or fnum > 10000 or size != 8 + fnum * 164:
            break
        faces = [_parse_param(data, d + 8 + i * 164, endian) for i in range(fnum)]
        pools.append((mid, faces))
        o += 4 + size
    return pools


def parse_lip_pool(data, offset, end, endian="<"):
    pools = []
    o = offset
    while o + 4 <= end:
        size = struct.unpack_from(endian + "i", data, o)[0]
        if size == -1:
            break
        if size < 0 or o + 4 + size > end:
            break
        pools.append(bytes(data[o + 4 : o + 4 + size]))
        o += 4 + size
    return pools
