import bpy

from .operators import ImportOperator


class DragDropFileHandler(bpy.types.FileHandler):
    bl_idname = "RDX_FH_rdx"
    bl_label = "RDX Room File"
    bl_file_extensions = ".rdx;.rdt"
    bl_import_operator = ImportOperator.bl_idname

    @classmethod
    def poll_drop(cls, context):
        return context.area is not None and context.area.type == "VIEW_3D"
