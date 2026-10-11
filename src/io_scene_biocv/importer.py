import logging
import os

import bpy

from .rdx import RdxFile
from .scene.cameras import import_cameras
from .scene.collision import import_boxes
from .scene.effects import import_effects
from .scene.lights import import_lights
from .scene.models import import_models
from .scene.players import import_players
from .scene.points import import_points
from .scene.textures import TextureRepo

log = logging.getLogger(__name__)

__all__ = [
    "import_file",
]


def import_file(
    context,
    filepath,
    imp_rom_mdl=True,
    imp_ene_mdl=True,
    imp_obj_mdl=True,
    imp_itm_mdl=True,
    imp_tex=True,
    imp_cam=True,
    imp_lgt=True,
    imp_ene=True,
    imp_obj=True,
    imp_itm=True,
    imp_eff=True,
    imp_ply=True,
    imp_sca=True,
    imp_aot=True,
    imp_trg=True,
    imp_evt=True,
):
    rdx = RdxFile()
    rdx.read(filepath)

    root = bpy.data.collections.new(
        name=os.path.splitext(os.path.basename(filepath))[0]
    )
    context.scene.collection.children.link(root)
    stem = root.name + "_"

    context.scene.world = _load_world(stem)

    tex_repo = TextureRepo(rdx, prefix=stem) if imp_tex else None
    tex_assign = rdx.texture_assignment()

    kinds = set()
    if imp_rom_mdl:
        kinds.add("room")
    if imp_ene_mdl:
        kinds.add("actor")
    if imp_obj_mdl:
        kinds.add("obj")
    if imp_itm_mdl:
        kinds.add("item")
    if kinds:
        import_models(stem, rdx, root, tex_repo, tex_assign, kinds=kinds)
    if imp_cam:
        import_cameras(rdx.cameras, root)
    if imp_lgt:
        import_lights(rdx.lights, root)
    if imp_ene:
        import_points("ACT", rdx.actor, root, zero_ax_az=True)
    if imp_obj:
        import_points("OBJ", rdx.obj, root)
    if imp_itm:
        import_points("ITM", rdx.item, root)
    if imp_eff:
        import_effects(rdx.effect, root)
    if imp_ply:
        import_players(rdx.player, root)
    if imp_sca:
        import_boxes("SCA", rdx.sca, root, (0.5, 0.5, 0.5, 1.0))
    if imp_aot:
        import_boxes("AOT", rdx.aot, root, (1.0, 1.0, 0.0, 0.35))
    if imp_trg:
        import_boxes("TRG", rdx.trigger, root, (1.0, 0.0, 0.0, 0.35))
    if imp_evt:
        import_boxes("RUT", rdx.route, root, (0.0, 1.0, 1.0, 1.0))

    return {"FINISHED"}


def _load_world(stem):
    name = f"{stem}WORLD"
    world = bpy.data.worlds.get(name) or bpy.data.worlds.new(name)
    return world
