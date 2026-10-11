import bpy

from .common import convert_pos, create_collection
from .rotation import set_rotation


def import_cameras(entries, root):
    coll = create_collection("CAM", root)
    for i, cam in enumerate(entries):
        for b, blk in enumerate(cam.blocks):
            data = bpy.data.cameras.new(f"CAM_{i:03d}_{b}")
            data.clip_start = 1.0
            data.clip_end = 10000.0
            obj = bpy.data.objects.new(f"CAM_{i:03d}_{b}", data)
            obj.location = convert_pos(blk.pos)
            ax, ay, az = blk.ang
            set_rotation(obj, ax, ay, az, camera=True)
            coll.objects.link(obj)
    bpy.context.view_layer.update()
