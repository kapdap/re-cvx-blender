from __future__ import annotations


class PrsError(ValueError):
    pass


def decompress(data: bytes | bytearray) -> bytes:
    src = bytes(data)
    n = len(src)
    out = bytearray()
    append = out.append
    extend = out.extend

    pos = 0
    cmd = 0
    bits = 0

    while pos < n:
        if bits == 0:
            cmd = src[pos]
            pos += 1
            bits = 8
        bits -= 1
        if cmd & 1:
            cmd >>= 1
            if pos >= n:
                raise PrsError(f"truncated PRS stream at offset {pos}")
            append(src[pos])
            pos += 1
            continue
        cmd >>= 1

        if bits == 0:
            cmd = src[pos]
            pos += 1
            bits = 8
        bits -= 1
        if cmd & 1:
            cmd >>= 1
            if pos + 1 >= n:
                raise PrsError(f"truncated PRS stream at offset {pos}")
            a = src[pos]
            b = src[pos + 1]
            pos += 2
            offset = ((b << 8) | a) >> 3
            amount = a & 7
            if pos < n:
                if amount == 0:
                    amount = src[pos] + 1
                    pos += 1
                else:
                    amount += 2
            start = len(out) - 0x2000 + offset
        else:
            cmd >>= 1
            amount = 0
            for _ in range(2):
                if bits == 0:
                    cmd = src[pos]
                    pos += 1
                    bits = 8
                bits -= 1
                amount = (amount << 1) | (cmd & 1)
                cmd >>= 1
            amount += 2
            if pos >= n:
                raise PrsError(f"truncated PRS stream at offset {pos}")
            start = len(out) - 0x100 + src[pos]
            pos += 1

        if start >= 0 and start + amount <= len(out):
            extend(out[start : start + amount])
        else:
            for _ in range(amount):
                if start < 0:
                    append(0)
                elif start < len(out):
                    append(out[start])
                else:
                    append(0)
                start += 1
    return bytes(out)
