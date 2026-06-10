# Copyright Epic Games, Inc. All Rights Reserved.

from typing import Dict, List, Tuple, Union, Optional

from frt_api.model.rig_definition.map import MapType


class Shader:
    """
    Shader class.
    """

    # constants
    SHADER_TYPE_LEGACY_BLINN = 0
    SHADER_TYPE_BLINN = 1
    SHADER_TYPE_DX11 = 2

    SHADER_BASE_ATTRIBUTE_INDEX = 0
    SHADER_ANIM_ATTRIBUTE_INDEX = 1
    SHADER_BLINN_ATTRIBUTE_INDEX = 2

    SHADER_INPUT_TYPE_MAPPING: Dict[str, List[Union[str, None]]] = {
        "DiffuseCubeIBL": ["DiffuseCubeIBL", None, None],
        "SpecularCubeIBL": ["SpecularCubeIBL", None, None],
        "DitherTexture": ["DitherTexture", None, None],
        "LutTexture": ["LutTexture", None, None],
        "Diffuse": ["DiffuseTexture", "animColorMap_<index>", "color"],
        "Normal": ["NormalTexture", "animNormalMap_<index>", "normalCamera"],
        "Specular": ["SpecularTexture", None, "specular_color"],
        "SSSRadius": ["ScatteringRadiusTexture", None, None],
        "Backscatter": ["BackScatteringThicknessTexture", None, None],
        "Occlusion": ["OcclusionTexture", None, None],
        "Cavity": ["CavityTexture", None, None],
        "MicroCavity": ["MicroCavityTexture", None, None],
        "MicroNormal": ["MicroNormalTexture", None, None],
        "OpacityMask": ["OpacityMaskBias", None, None],
    }

    def __init__(self):
        self.name: str = ""  # (string)
        self.shader_type: int = Shader.SHADER_TYPE_LEGACY_BLINN  # (int)
        self.shader_code: str = ""
        self.eccentricity: float = 0.0  # (float)
        self.specular_roll_off: float = 0.0  # (float)
        self.specular_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (float[])
        self.shader_color: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (float[])
        self.transparency: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (float[])
        self.inputs: List[ShaderInput] = []  # (ShaderInput[])

    def __str__(self):
        return self.name

    def get_input_by_name(self, name: str) -> Optional["ShaderInput"]:
        """
        Get input with given attribute pattern.

        @param name: Attribute pattern. (pattern)
        @return Input. (ShaderInput)
        """

        for shader_input in self.inputs:
            if shader_input.attr_name == name:
                return shader_input
        return None

    def get_map_type_for_attribute(self, dx_attr_name: str) -> Optional[MapType]:
        """
        Gets map object_type which is connected to shader given input.

        @param dx_attr_name: Shader attribute pattern in dx shader, e.g. "Diffuse", "Normal"... (string)
        @return: Map object_type used for that input. (MapType)
        """

        map_type = None
        if dx_attr_name not in Shader.SHADER_INPUT_TYPE_MAPPING:
            return map_type
        blinn_input_name = Shader.SHADER_INPUT_TYPE_MAPPING[dx_attr_name][Shader.SHADER_BLINN_ATTRIBUTE_INDEX]
        for shader_input in self.inputs:
            if not shader_input.map_types:
                continue
            if self.shader_type == Shader.SHADER_TYPE_DX11:
                if shader_input.attr_name == dx_attr_name:
                    map_type = shader_input.map_types[0]
            else:
                if shader_input.attr_name == blinn_input_name:
                    map_type = shader_input.map_types[0]
        return map_type

    def get_color_map_type(self):
        """
        Gets map object_type which is used for color maps based on how it is connected to shader.

        @return: Map object_type representing color maps. (MapType)
        """

        return self.get_map_type_for_attribute("Diffuse")

    def get_normal_map_type(self):
        """
        Gets map object_type which is used for normal maps based on how it is connected to shader.

        @return: Map object_type representing normal maps. (MapType)
        """

        return self.get_map_type_for_attribute("Normal")


class ShaderInput:
    """
    ShaderInput class.
    """

    def __init__(self):
        self.attr_name: str = ""  # (string)
        self.map_types: List[MapType] = []  # (MapType[])

    def __str__(self):
        return self.attr_name

    def get_blinn_attribute_name(self, shader: Shader) -> str:
        """
        Gets shader inpunt pattern for blin shader.

        This is used when forcing blinn shader instead of other one in order to
        convert attribute names.

        @param shader: Shader to which shader input belongs. (Shader)
        @return: Blinn shader attribute pattern. (string)
        """

        attribute_name = None
        if shader.shader_type == Shader.SHADER_TYPE_DX11:
            if self.attr_name in Shader.SHADER_INPUT_TYPE_MAPPING:
                attribute_name = Shader.SHADER_INPUT_TYPE_MAPPING[self.attr_name][Shader.SHADER_BLINN_ATTRIBUTE_INDEX]
        if attribute_name is None:
            attribute_name = self.attr_name
        return attribute_name
