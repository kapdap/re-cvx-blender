import math

from mathutils import Matrix

TAU = math.pi * 2.0

_COS = [math.cos(i * TAU / 65536.0) for i in range(65536)]
_SIN = [math.sin(i * TAU / 65536.0) for i in range(65536)]


def _rx(a):
    c, s = math.cos(a), math.sin(a)
    return ((1.0, 0.0, 0.0), (0.0, c, -s), (0.0, s, c))


def _ry(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, 0.0, s), (0.0, 1.0, 0.0), (-s, 0.0, c))


def _rz(a):
    c, s = math.cos(a), math.sin(a)
    return ((c, -s, 0.0), (s, c, 0.0), (0.0, 0.0, 1.0))


def _mmul(A, B):
    return tuple(
        tuple(sum(A[i][k] * B[k][j] for k in range(3)) for j in range(3))
        for i in range(3)
    )


def _mat_to_euler(m):
    return Matrix((m[0], m[1], m[2])).to_euler("XYZ")


def _ninja_rad(angle):
    return (int(angle) & 0xFFFF) * TAU / 65536.0


def ninja_euler(ax, ay, az, zxy=False):
    if zxy:
        rax, ray, raz = _ninja_rad(ax), _ninja_rad(ay), _ninja_rad(az)
        rg = _mmul(_ry(ray), _mmul(_rx(rax), _rz(raz)))
        p = ((1.0, 0.0, 0.0), (0.0, 0.0, -1.0), (0.0, 1.0, 0.0))
        pt = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.0, -1.0, 0.0))
        return _mat_to_euler(_mmul(_mmul(p, rg), pt))
    ix = int(ax) & 0xFFFF
    iy = int(ay) & 0xFFFF
    iz = int(az) & 0xFFFF
    cx = _COS[ix]
    sx = _SIN[ix]
    cy = _COS[iy]
    sy = _SIN[iy]
    cz = _COS[iz]
    sz = _SIN[iz]
    a02 = cz * sy
    a12 = sz * sy
    r01 = -sz * cx + a02 * sx
    r02 = sz * sx + a02 * cx
    r11 = cz * cx + a12 * sx
    r12 = -cz * sx + a12 * cx
    m = (
        (cz * cy, -r02, r01),
        (sy, cy * cx, -cy * sx),
        (sz * cy, -r12, r11),
    )
    return _mat_to_euler(m)


def ninja_euler_camera(ax, ay, az):
    rax, ray, raz = _ninja_rad(ax), _ninja_rad(ay), _ninja_rad(az)
    m = _mmul(_rz(-ray), _mmul(_rx(-rax), _ry(raz)))
    m = _mmul(m, _rx(math.pi / 2.0))
    return _mat_to_euler(m)


def ninja_euler_sun(ax, ay, az):
    axr, ayr, azr = -_ninja_rad(ax), -_ninja_rad(ay), -_ninja_rad(az)
    ca, sa = math.cos(axr), math.sin(axr)
    cb, sb = math.cos(ayr), math.sin(ayr)
    cc, sc = math.cos(azr), math.sin(azr)
    r01 = cc * sb * sa - sc * ca
    r02 = cc * sb * ca + sc * sa
    r11 = sc * sb * sa + cc * ca
    r12 = sc * sb * ca - cc * sa
    r21 = cb * sa
    r22 = cb * ca

    dg = (-r02, -r12, -r22)
    ug = (r01, r11, r21)

    db = (dg[0], -dg[2], dg[1])
    ub = (ug[0], -ug[2], ug[1])

    zb = (db[0], db[1], db[2])
    dot = ub[0] * zb[0] + ub[1] * zb[1] + ub[2] * zb[2]
    yb = (ub[0] - dot * zb[0], ub[1] - dot * zb[1], ub[2] - dot * zb[2])
    n = math.sqrt(yb[0] * yb[0] + yb[1] * yb[1] + yb[2] * yb[2])
    if n < 1e-9:
        yb = (0.0, 1.0, 0.0) if abs(zb[2]) < 0.99 else (1.0, 0.0, 0.0)
        dot = yb[0] * zb[0] + yb[1] * zb[1] + yb[2] * zb[2]
        yb = (yb[0] - dot * zb[0], yb[1] - dot * zb[1], yb[2] - dot * zb[2])
        n = math.sqrt(yb[0] * yb[0] + yb[1] * yb[1] + yb[2] * yb[2])
    yb = (yb[0] / n, yb[1] / n, yb[2] / n)
    xb = (
        yb[1] * zb[2] - yb[2] * zb[1],
        yb[2] * zb[0] - yb[0] * zb[2],
        yb[0] * zb[1] - yb[1] * zb[0],
    )

    m00, m01, m02 = xb[0], yb[0], zb[0]
    m10, m11, m12 = xb[1], yb[1], zb[1]
    m20, m21, m22 = xb[2], yb[2], zb[2]
    return _mat_to_euler(((m00, m01, m02), (m10, m11, m12), (m20, m21, m22)))


def set_rotation(obj, ax, ay, az, camera=False, zxy=False):
    obj.rotation_mode = "XYZ"
    if camera:
        obj.rotation_euler = ninja_euler_camera(ax, ay, az)
    else:
        obj.rotation_euler = ninja_euler(ax, ay, az, zxy)
