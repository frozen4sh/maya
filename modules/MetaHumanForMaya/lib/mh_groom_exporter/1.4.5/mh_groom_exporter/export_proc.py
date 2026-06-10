# Copyright Epic Games, Inc. All Rights Reserved.
import os
import sys
import json
import contextlib


def run_export(option_file):
    with open(option_file) as fp:
        options = json.load(fp)

    project_directory = options["project_directory"]
    scene_filepath = options["scene_filepath"]
    model_filepath = options["model_filepath"]
    model_mesh = options["model_mesh"]
    output_filepath = options["output_filepath"]
    scene_up_axis = options["scene_up_axis"]
    description_names = options["description_names"]
    groupids = options["groupids"]
    groupnames = options["groupnames"]
    export_guides = options["export_guides"]

    if not os.path.exists(project_directory):
        raise OSError(f'Invalid Project Path: "{project_directory}"')
    if not os.path.exists(scene_filepath):
        raise OSError(f'Invalid Scene Path: "{scene_filepath}"')
    if not model_filepath:
        model_filepath = scene_filepath
    if not os.path.exists(model_filepath):
        raise OSError(f'Invalid Model Path: "{model_filepath}"')
    if not output_filepath:
        raise OSError("Invalid Output File Path")

    descriptions, guides = dict(), dict()
    for guide, _id, desc, groupname in zip(export_guides, groupids, description_names, groupnames):
        if _id not in descriptions:
            descriptions[_id] = dict()
            descriptions[_id]["descriptions"] = list()
            descriptions[_id]["path"] = None
            descriptions[_id]["groupname"] = groupname
        descriptions[_id]["descriptions"].append(desc)

        if guide:
            if _id not in guides:
                guides[_id] = dict()
                guides[_id]["descriptions"] = list()
                guides[_id]["path"] = None
                guides[_id]["groupname"] = groupname
            guides[_id]["descriptions"].append(desc)

    if not descriptions:
        raise RuntimeError("Must select some descriptors for interpolated hair")

    # ------------------------------------------------------------------------------------------
    # EXPORT XGEN FILES
    #
    from .scene_utils import load_scene, set_project
    from .xgen_exporter import (
        export_geometry_instancer,
        export_geometry_instancer_guides,
    )

    # Dump intermediate files to the same directory with the option file
    TEMP_DIR = os.path.dirname(option_file)

    # Load xGen Groom
    with contextlib.suppress(Exception):
        set_project(project_directory)
    load_scene(scene_filepath)

    # Export Guides
    guide_counts = []
    if guides:
        for _id, guide in guides.items():
            guides_path = os.path.join(TEMP_DIR, f"guide_group{_id}.abc")
            guide_counts.append(export_geometry_instancer_guides(guide["descriptions"], guides_path))
            guide["path"] = guides_path

    # Export Interpolated
    spline_counts = []
    if descriptions:
        for _id, description in descriptions.items():
            interpolated_path = os.path.join(TEMP_DIR, f"interpolated_group{_id}.abc")
            spline_counts.append(export_geometry_instancer(description["descriptions"], interpolated_path))
            description["path"] = interpolated_path

    # --------------------------------------------------------------------------------------------------
    # EXPORT ALEMBICS
    # --------------------------------------------------------------------------------------------------

    from .scene_utils import new_scene, import_scene
    from .groom_export_utils import (
        export_curves,
        import_curves,
        create_group_id,
        transform_group,
        add_id_attribute,
        create_top_group,
        create_curves_group,
        create_guides_group,
        add_root_uv_attribute,
    )

    # Import Model
    new_scene()
    import_scene(model_filepath)

    # Create Top Group
    top_group = create_top_group()

    # Create Curves Group
    curves_group = create_curves_group(parent=top_group)

    # Import Interpolated
    group_ids = list()
    if descriptions:
        for _id, description in sorted(descriptions.items()):
            curve_shapes = import_curves(description["path"])
            groupname = description["groupname"]
            group_id, curve_shapes = create_group_id(
                curve_shapes, _id, name_=groupname, run_checks=True, parent=curves_group
            )
            group_ids.append(group_id)

    # Parent / Add Root-UV Interpolated Groups
    if group_ids:
        for group_id in group_ids:
            add_root_uv_attribute(group_id, mesh_node=model_mesh)  # , up_axis=model_up_axis)

    # add ids
    add_id_attribute(group_ids)

    # Create Guides Group
    guides_group = create_guides_group(parent=top_group)

    # Import Guide
    group_ids = list()
    if guides:
        for _id, description in sorted(guides.items()):
            curve_shapes = import_curves(description["path"])
            groupname = description["groupname"]
            group_id, curve_shapes = create_group_id(
                curve_shapes, _id, name_=groupname, run_checks=True, isGuide=True, parent=guides_group
            )
            group_ids.append(group_id)

    # add ids
    add_id_attribute(group_ids)

    # transform group
    transform_group(top_group, scene_up_axis=scene_up_axis)

    # export all curves
    export_curves(top_group, output_filepath)

    return (output_filepath, guide_counts, spline_counts)


def print_results(output_filepath, guide_counts, spline_counts):
    output_text = output_filepath + "\n"

    guide_counts_msg, total_guides = "", 0
    for item in guide_counts:
        for description, count in item.items():
            guide_counts_msg += f"\t{description} : {count} curves\n"
            total_guides += count

    guides_msg = f"\nGuides ({total_guides} curves):\n\n" + guide_counts_msg
    output_text += guides_msg

    interpolated_counts_msg, total_interpolated = "", 0
    for item in spline_counts:
        for description, count in item.items():
            interpolated_counts_msg += f"\t{description}: {count} curves\n"
            total_interpolated += count

    interpolated_msg = f"\nInterpolated ({total_interpolated} curves):\n\n" + interpolated_counts_msg
    output_text += interpolated_msg
    from . import logger

    logger.info(output_text)


if __name__ == "__main__":
    module_path = os.path.dirname(os.path.dirname(__file__))
    if module_path not in sys.path:
        sys.path.insert(0, module_path)

    # Load Maya Standalone
    from maya import standalone

    standalone.initialize()

    # argv[0]: path to mayapy
    # argv[1]: json file for export options
    import mh_groom_exporter.export_proc

    results = mh_groom_exporter.export_proc.run_export(sys.argv[1])
    mh_groom_exporter.export_proc.print_results(*results)
