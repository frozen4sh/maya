# Copyright Epic Games, Inc. All Rights Reserved.
"""
Export / Import a XGen setup into a new mesh with same UVs

NOTE: XGen seems to be quite hacky, having commands not working without having the UI open.
"""

import os
import tempfile

import xgenm
import xgenm.XgExternalAPI
from maya import mel, cmds
from xgenm import xgg

from .xgen_utils import get_descriptions


def export_preset(palette, directory=None):
    """
    Export Preset
    """
    if directory is None:
        directory = tempfile.mkdtemp()

    # get all descriptions in palette
    descriptions = get_descriptions(palette)

    for description in descriptions:
        # Export XGP
        xgp_filepath = os.path.join(directory, f"{description}.xgp")
        xgenm.exportDescriptionAsPreset(palette, description, xgp_filepath, activeModuleOnly=False, guides=True)

        # Export Material
        export_material(palette, description, xgp_filepath)

        print(xgp_filepath)


def export_material(palette, description, xgp_filepath):
    """
    Export the material of the given description to the same folder of the xgp file

    Copied from:
        C:/Program Files/Autodesk/Maya2018/plug-ins/xgen/scripts/xgenm/ui/dialogs/xgExportPreset.py
    """

    shading_engines = []
    shapes = cmds.listRelatives(description, shapes=True)
    if shapes:
        for shape in shapes:
            if cmds.objExists(shape):
                dest = cmds.listConnections(shape, destination=True, source=False, plugs=False, type="shadingEngine")
                if dest and len(dest):
                    shading_engines = shading_engines + dest

    archive_materials = list()
    primType = xgenm.getActive(palette, description, "Primitive")
    if primType == "ArchivePrimitive":
        files = xgenm.getAttr("files", palette, description, primType)
        files = files.decode("string_escape")
        lines = files.splitlines()
        for line in lines:
            words = line.split()
            for w in words:
                if w.startswith("material="):
                    mat = w[len("material=") :]
                    # Make sure that the material has been imported in maya, then export it.
                    if cmds.objExists(mat):
                        archive_materials.append(mat)

    cmds.select(shading_engines, r=True, ne=True)
    cmds.select(archive_materials, add=True, ne=False)

    filename = os.path.splitext(xgp_filepath)[0]
    materialFile = filename + "_material.ma"
    result = cmds.file(materialFile, force=True, options="v=0;", typ="mayaAscii", pr=True, es=True)

    return result


# ==================================================================================================


def import_preset(mesh, directory, name="head"):
    """
    >>> mesh = 'head_groom_mesh'
    >>> directory = 'C:/Users/david.corral/Documents/xgen'
    >>> import_preset(mesh, directory)

    TODO: there is still an isue creating maps for guides.
    """

    if list(xgenm.palettes()):
        raise RuntimeError("Unable to import a new palette. Found: ")

    # get filepaths
    xgp_files = list()
    for filename in os.listdir(directory):
        _name, ext = os.path.splitext(filename)
        if ext == ".xgp":
            xgp_filepath = os.path.join(directory, filename)
            xgp_filepath = xgp_filepath.replace("\\", "/")
            xgp_files.append(xgp_filepath)

    #
    palette = None
    descriptions = list()
    for i, xgp_filepath in enumerate(xgp_files):
        # Create Validator
        if palette is None:
            action = xgenm.ADD_TO_NEW_PALETTE
        else:
            action = xgenm.ADD_TO_EXISTING_PALETTE
        validator = PresetValidator(action)

        cmds.select(mesh)
        description = xgenm.importDescriptionAsPreset(
            palette or name, xgp_filepath, validator, guides=True, placeGuidesWithUVBasedMethod=True, rotateGuide=False
        )
        descriptions.append(description)

        # get palette from new description as it might have been changed during the validation
        palette = xgenm.XgExternalAPI.palette(description)

        # do import material
        import_material(palette, description, xgp_filepath)

        # ----------------------------------------------------------------------------------------------
        #

        # Generate point map and clump map
        modules = xgenm.fxModules(palette, description)
        for mod in modules:
            _type = xgenm.fxModuleType(palette, description, mod)
            if _type != "ClumpingFXModule" and _type != "AnimWiresFXModule":
                continue

            density = xgenm.getAttr("ptDensity", palette, description, mod)
            mask = xgenm.getAttr("ptMask", palette, description, mod)
            point_path = xgenm.getAttr("pointDir", palette, description, mod)
            map_path = xgenm.getAttr("mapDir", palette, description, mod)
            tex_per_unit = xgenm.getAttr("texelsPerUnit", palette, description, mod)
            rad_variance = xgenm.getAttr("radiusVariance", palette, description, mod)

            # Apparently some commands only work if the gui enabled and refreshed ?!
            xgg.DescriptionEditor.setCurrentPalette(palette)
            xgg.DescriptionEditor.setCurrentDescription(description)

            cmds.xgmPoints(guidePoints=True)
            cmds.xgmPoints(generatePoints=[float(density), mask], module=mod)
            cmds.xgmPoints(savePoints=point_path, module=mod)

            cmds.xgmClumpMap(
                progressBar=False,
                fxmodule=mod,
                mapDir=map_path,
                pointDir=point_path,
                texelsPerUnit=float(tex_per_unit),
                radiusVariance=rad_variance,
                description=description,
            )


def import_material(palette, description, xgp_filepath):
    """
    Imports material and assign it to hair
    """

    # Import the material for non archive based primitive
    default_shader = True
    filename = os.path.splitext(xgp_filepath)[0]
    material_file = filename + "_material.ma"

    if os.path.isfile(material_file):
        nodes = cmds.file(
            material_file,
            i=True,
            type="mayaAscii",
            ignoreVersion=True,
            ra=True,
            mergeNamespacesOnClash=True,
            options="v=0;p=17;f=0",
            pr=True,
            rnn=True,
        )

        if nodes:
            primType = xgenm.getActive(palette, description, "Primitive")
            for node in nodes:
                if primType != "ArchivePrimitive" and cmds.nodeType(node) == "shadingEngine":
                    cmds.select(description, r=True)
                    cmds.hyperShade(assign=node)
                    default_shader = False

                prefix = os.path.basename(filename) + "_material_"
                if node.startswith(prefix):
                    newName = node[len(prefix) :]
                    if len(newName) > 0:
                        cmds.rename(node, newName)

    # If the preset has no material attached, create a default one for it.
    if default_shader and mel.eval('exists "xgmr"'):
        cmds.xgmr(applyShader="hair", description=description, palette=palette)


# --------------------------------------------------------------------------------------------------


class PresetValidator:
    """
    Copied from:
        C:/Program Files/Autodesk/Maya2018/plug-ins/xgen/scripts/xgenm/ui/dialogs/xgImportPreset.py
    """

    overwrite = False

    def __init__(self, action):
        """
        PresetValidator(xgenm.ADD_TO_NEW_PALETTE)
        """
        self.__action = action

    @property
    def action(self):
        return self.__action

    @staticmethod
    def on_collide_description(ui_parent, new_descrition, description, description_path):
        """
        Called by xgen.validateDescription when a new description collides with an existing one. If the user chooses to overwrite
        the collection then we assume the user also wants to reuse the same description data.
        """
        # there is a name clash, use newDesc to solve it
        valid_description = new_descrition
        if PresetValidator.overwrite:
            # use suggested description name if the collection was overwritten
            valid_description = description

        return (True, valid_description)

    def __call__(self, description_name, palette_name, _id):
        # get loaded palettes
        loaded_palettes = list(xgenm.palettes())
        loaded_descriptions = list(xgenm.descriptions())
        loaded_descriptions.append(palette_name)

        # get folders and map paths
        palette_folder_names, palette_path_maps = xgenm.paletteFolderNames()
        description_folder_names, description_path_maps = xgenm.descriptionFolderNames()

        # construct tuples
        palette_info = (palette_name, loaded_palettes, palette_folder_names, palette_path_maps, None)
        description_info = (
            description_name,
            loaded_descriptions,
            description_folder_names,
            description_path_maps,
            PresetValidator.on_collide_description,
        )
        return xgenm.validateDescription(self.__action, palette_info, description_info, None)
