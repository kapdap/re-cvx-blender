import bpy


def convert_pos(p):
    return (p[0], -p[2], p[1])


def convert_scale(s):
    return (s[0], s[2], s[1])


def convert_normal(n):
    v = (n[0], -n[2], n[1])
    l2 = v[0] * v[0] + v[1] * v[1] + v[2] * v[2]
    if l2 <= 1e-24:
        return (0.0, 0.0, 0.0)
    inv = 1.0 / (l2**0.5)
    return (v[0] * inv, v[1] * inv, v[2] * inv)


def create_collection(name, parent):
    coll = bpy.data.collections.new(name=name)
    parent.children.link(coll)
    return coll


def create_empty(name, display, collection, location, size=5.0):
    obj = bpy.data.objects.new(name, None)
    obj.empty_display_type = display
    obj.empty_display_size = size
    obj.location = location
    collection.objects.link(obj)
    return obj
