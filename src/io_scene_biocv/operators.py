import os

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ImportHelper

from .importer import import_file


class ImportOperator(Operator, ImportHelper):
    bl_idname = "import_scene.rdx"
    bl_label = "Import RDX"
    bl_description = "Load a RDX file"
    bl_options = {"PRESET", "UNDO"}

    filename_ext = ".rdx"

    filter_glob: StringProperty(default="*.rdx;*.rdt;*.bin", options={"HIDDEN"})

    directory: StringProperty(subtype="FILE_PATH", options={"SKIP_SAVE", "HIDDEN"})
    files: CollectionProperty(
        type=bpy.types.OperatorFileListElement, options={"SKIP_SAVE", "HIDDEN"}
    )

    imp_rom_mdl: BoolProperty(name="Room", default=True)
    imp_ene_mdl: BoolProperty(name="Actors", default=True)
    imp_obj_mdl: BoolProperty(name="Objects", default=True)
    imp_itm_mdl: BoolProperty(name="Items", default=True)
    imp_ene_mtn: BoolProperty(
        name="Enemy",
        default=False,
        description="Per-actor motion sets (walk, idle, attacks)",
    )
    imp_rom_mtn: BoolProperty(
        name="Room",
        default=False,
        description="Takes assigned by room scripts (cutscenes, zombies)",
    )
    imp_mtn_layout: EnumProperty(
        name="Layout",
        items=[
            ("STRIPS", "Separate strips", "One action per take on muted NLA tracks"),
            ("SINGLE", "Single animation", "All takes joined end to end in one action"),
        ],
        default="STRIPS",
    )
    imp_cam: BoolProperty(name="Cameras", default=True)
    imp_lgt: BoolProperty(name="Lights", default=True)
    imp_tex: BoolProperty(name="Textures", default=True)
    imp_alpha: EnumProperty(
        name="Alpha",
        items=[
            ("BLENDED", "Blended", "Smooth alpha blending"),
            ("DITHERED", "Dithered", "Alpha-tested dithering"),
        ],
        default="BLENDED",
    )
    imp_eff: BoolProperty(name="Effects", default=False)
    imp_ply: BoolProperty(name="Player", default=False)
    imp_sca: BoolProperty(name="Collisions", default=False)
    imp_aot: BoolProperty(name="Interactions", default=False)
    imp_trg: BoolProperty(name="Triggers", default=False)
    imp_rut: BoolProperty(name="Routes", default=False)
    imp_ene: BoolProperty(name="Actors", default=False)
    imp_obj: BoolProperty(name="Objects", default=False)
    imp_itm: BoolProperty(name="Items", default=False)

    def draw(self, _):
        layout = self.layout
        box = layout.box()
        box.label(text="Models")
        box.prop(self, "imp_rom_mdl")
        box.prop(self, "imp_ene_mdl")
        box.prop(self, "imp_obj_mdl")
        box.prop(self, "imp_itm_mdl")
        box = layout.box()
        box.label(text="Motions")
        box.prop(self, "imp_ene_mtn")
        box.prop(self, "imp_rom_mtn")
        box.prop(self, "imp_mtn_layout")
        layout.prop(self, "imp_cam")
        layout.prop(self, "imp_lgt")
        layout.prop(self, "imp_tex")
        layout.prop(self, "imp_alpha")
        box = layout.box()
        box.label(text="Areas")
        box.prop(self, "imp_eff")
        box.prop(self, "imp_ply")
        box.prop(self, "imp_sca")
        box.prop(self, "imp_aot")
        box.prop(self, "imp_trg")
        box.prop(self, "imp_rut")
        box = layout.box()
        box.label(text="Positions")
        box.prop(self, "imp_ene")
        box.prop(self, "imp_obj")
        box.prop(self, "imp_itm")

    def _import_file(self, context, filepath):
        return import_file(
            context,
            filepath,
            imp_rom_mdl=self.imp_rom_mdl,
            imp_ene_mdl=self.imp_ene_mdl,
            imp_obj_mdl=self.imp_obj_mdl,
            imp_itm_mdl=self.imp_itm_mdl,
            imp_ene_mtn=self.imp_ene_mtn,
            imp_rom_mtn=self.imp_rom_mtn,
            imp_mtn_layout=self.imp_mtn_layout,
            imp_cam=self.imp_cam,
            imp_lgt=self.imp_lgt,
            imp_tex=self.imp_tex,
            imp_alpha=self.imp_alpha,
            imp_ene=self.imp_ene,
            imp_obj=self.imp_obj,
            imp_itm=self.imp_itm,
            imp_eff=self.imp_eff,
            imp_ply=self.imp_ply,
            imp_sca=self.imp_sca,
            imp_aot=self.imp_aot,
            imp_trg=self.imp_trg,
            imp_evt=self.imp_rut,
        )

    def execute(self, context):
        targets = [os.path.join(self.directory, f.name) for f in self.files if f.name]
        if not targets and self.filepath:
            targets = [self.filepath]
        if not targets:
            self.report({"ERROR"}, "No file selected")
            return {"CANCELLED"}
        for path in targets:
            result = self._import_file(context, path)
            if result != {"FINISHED"}:
                return result
        return {"FINISHED"}

    def invoke(self, context, event):
        if self.directory:
            return self.execute(context)
        return super().invoke(context, event)
