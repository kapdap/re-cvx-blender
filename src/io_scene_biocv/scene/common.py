import bpy

EMPTY_SIZE = 5.0


def convert_pos(p):
    return (p[0], -p[2], p[1])


def convert_scale(s):
    return (s[0], s[2], s[1])


def create_collection(name, parent):
    coll = bpy.data.collections.new(name=name)
    parent.children.link(coll)
    return coll
