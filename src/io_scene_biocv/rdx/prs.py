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

    def get_byte() -> int:
        nonlocal pos
        if pos >= n:
            raise PrsError(f"truncated PRS stream at offset {pos}")
        val = src[pos]
        pos += 1
        return val

    def get_bit() -> int:
        nonlocal cmd, bits
        if bits == 0:
            cmd = get_byte()
            bits = 8
        bit = cmd & 1
        cmd >>= 1
        bits -= 1
        return bit

    while pos < n:
        if get_bit():
            append(get_byte())
            continue
        if get_bit():
            a = get_byte()
            b = get_byte()
            offset = ((b << 8) | a) >> 3
            amount = a & 7
            if pos < n:
                if amount == 0:
                    amount = get_byte() + 1
                else:
                    amount += 2
            start = len(out) - 0x2000 + offset
        else:
            amount = 0
            amount = (amount << 1) | get_bit()
            amount = (amount << 1) | get_bit()
            amount += 2
            start = len(out) - 0x100 + get_byte()

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
