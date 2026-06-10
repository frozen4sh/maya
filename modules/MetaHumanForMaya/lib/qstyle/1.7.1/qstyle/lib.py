# Copyright Epic Games, Inc. All Rights Reserved.
import os
import re
import logging

from qtpy import QtGui, QtCore

_LOADED_FONT_PATHS = {}
logger = logging.getLogger(__name__)


def resource(*path):
    path = os.path.join(os.path.dirname(__file__), "res", *path)
    return path.replace("\\", "/")


def parse_css_variables(css_file_path):
    """
    Parses CSS variables from the :root block of a CSS file.
    Returns a dictionary mapping full variable names (with --) to their values.
    """
    with open(css_file_path) as file:
        content = file.read()

    # Extract the :root { ... } block
    root_match = re.search(r":root\s*{([^}]*)}", content, re.DOTALL)
    if not root_match:
        return {}

    root_content = root_match.group(1)

    # Match --var-name: value;
    variables = dict(re.findall(r"(--[\w-]+)\s*:\s*(#[0-9A-Fa-f]{6})\s*;", root_content))
    return variables


def get_value(variable_name):
    colors = resource("style", "colors.css")
    variables = parse_css_variables(colors)
    return variables.get(variable_name)


def load_css(*file):
    content = ""
    colors = resource("style", "colors.css")
    for f in file:
        content += compile_css(f, colors)
    return content


def compile_css(css_file, colors_file=None):
    variables = {}

    # Read the main CSS file
    with open(css_file) as file:
        lines = file.readlines()

    # Parse variables from :root section
    in_root_section = False
    for line in lines:
        line = line.strip()
        if line == ":root {":
            in_root_section = True
        elif line == "}":
            in_root_section = False
        elif in_root_section and line and not line.startswith("/*"):
            parts = line.split(":")
            if len(parts) == 2:
                name = parts[0].strip()
                value = parts[1].strip().rstrip(";")
                variables[name] = value

    # Read the values CSS file and override variables
    if colors_file:
        with open(colors_file) as file:
            value_lines = file.readlines()
        for line in value_lines:
            line = line.strip()
            if line and not line.startswith("/*"):
                parts = line.split(":")
                if len(parts) == 2:
                    name = parts[0].strip()
                    value = parts[1].strip().rstrip(";")
                    variables[name] = value

    # Replace variable references in CSS rules
    parsed_css = []
    for line in lines:
        line = line.strip()
        if line.startswith("/*") or line.startswith(":root"):
            # Skip comments and :root section
            continue
        else:
            for var_name, var_value in variables.items():
                if f"var({var_name})" in line:
                    line = line.replace(f"var({var_name})", var_value)
            parsed_css.append(line)

    css = "\n".join(parsed_css)

    return css


def set_style(widget, css=None, with_main=True):
    css = css or []
    files = []
    if isinstance(css, str):
        css = [css]
    if with_main:
        QtCore.QDir.addSearchPath("icon", resource("icon"))
        main_css = resource("style", "style.css")
        files.append(main_css)
    files.extend(css)
    if files:
        loaded = load_css(*files)
        widget.setStyleSheet(loaded)


def install_fonts(silent=False, reset=False):

    def _log_msg(msg, silent=silent):
        if silent:
            logger.debug(msg)
        else:
            logger.info(msg)

    qfd = QtGui.QFontDatabase

    if reset and _LOADED_FONT_PATHS:
        _log_msg("resetting previously installed application fonts")
        for fid in list(_LOADED_FONT_PATHS.values()):
            qfd.removeApplicationFont(fid)
        _LOADED_FONT_PATHS.clear()

    fonts = {
        "Open Sans": os.path.join("opensans", "OpenSans-Regular.ttf"),
        "Open Sans Bold": os.path.join("opensans", "OpenSans-Bold.ttf"),
        "Open Sans Semibold": os.path.join("opensans", "OpenSans-Semibold.ttf"),
        "Open Sans Light": os.path.join("opensans", "OpenSans-Light.ttf"),
        "Open Sans Italic": os.path.join("opensans", "OpenSans-Italic.ttf"),
        "Material Icons": os.path.join("material", "MaterialIcons-Regular.ttf"),
        "Material Icons Outlined": os.path.join("material", "MaterialIconsOutlined-Regular.otf"),
        "Material Icons Round": os.path.join("material", "MaterialIconsRound-Regular.otf"),
        "Material Icons Sharp": os.path.join("material", "MaterialIconsSharp-Regular.otf"),
        "Material Icons TwoTone": os.path.join("material", "MaterialIconsTwoTone-Regular.otf"),
        "epicdesignsystem": os.path.join("epic", "epicdesignsystem.ttf"),
    }

    _log_msg("installing fonts")

    for label, rel_path in fonts.items():
        path = resource("font", rel_path)
        norm_path = os.path.normcase(os.path.realpath(path))

        if norm_path in _LOADED_FONT_PATHS:
            _log_msg(f"font '{label}' already loaded in this process, skipping")
            continue

        fid = qfd.addApplicationFont(norm_path)
        if fid < 0:
            logger.warning("could not install '%s' from %s", label, path)
            continue

        _LOADED_FONT_PATHS[norm_path] = fid
        fams = qfd.applicationFontFamilies(fid)
        if fams:
            _log_msg(f"installed '{label}' as families: {', '.join(fams)}")
        else:
            _log_msg(f"installed '{label}' (no families reported)")
