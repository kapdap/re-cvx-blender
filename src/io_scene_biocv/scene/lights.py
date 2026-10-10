import math

import bpy

from .common import create_collection, convert_pos
from .rotation import ninja_euler_sun


def _game_light_levels(r, g, b):
    k = max(float(r), float(g), float(b))
    if k <= 0.0:
        return (1.0, 1.0, 1.0), 0.0
    return ((float(r) / k, float(g) / k, float(b) / k), k)


def import_lights(entries, root):
    coll = create_collection("LGT", root)
    for i, light in enumerate(entries):
        ltype = "SUN" if light.lsrc == 2 else "POINT"
        data = bpy.data.lights.new("LGT_%03d" % i, ltype)
        r, g, b = light.params[12], light.params[13], light.params[14]
        nr, fr = light.params[15], light.params[16]
        col, k = _game_light_levels(r, g, b)
        data.color = col
        if ltype == "SUN":
            data.energy = k
        else:
            data.energy = k * nr * nr * 4.0 * math.pi
            if fr > 0.0:
                data.cutoff_distance = fr
        obj = bpy.data.objects.new("LGT_%03d" % i, data)
        px, py, pz = light.pos
        finite = all(math.isfinite(v) for v in (px, py, pz))
        obj.location = convert_pos((px, py, pz)) if finite else (0.0, 0.0, 0.0)
        ax, ay, az = light.ang
        if ltype == "SUN":
            obj.rotation_mode = "XYZ"
            obj.rotation_euler = ninja_euler_sun(ax, ay, az)
        coll.objects.link(obj)
    bpy.context.view_layer.update()
