# Copyright Epic Games, Inc. All Rights Reserved.


class MapInExpression:
    """
    Class representing map which is deformed by expression.

    It is used when some expressions have for example wrinkle maps.
    This class holds information which map should be added to shader and through
    which masks should be passed.
    """

    def __init__(self):
        self.map = None  # (Map)
        self.masks = []  # (Mask[])

    def __str__(self):
        return self.map.name if self.map else ""


class MapMaskMultipliers:
    """
    Describes map mask multipliers which drive shader.
    It represents reordered RigDefinition data to be more suitable for connecting
    shader node network.
    It consist of list of MapMaskMultiplier objects, where each object describe one multiplier.
    """

    MAP_TYPES_SUPPORTED_IN_DX_SHADER = ["head_color_type", "head_normal_type"]

    def __init__(self):
        self.multipliers = {}

    def add_multiplier(self, map, mask, expression):
        """
        Updates internal multipliers data based on new multiplier info.
        """

        name = MapMaskMultiplier.get_multiplier_name(map, mask)
        if name not in self.multipliers:
            index = len(self.multipliers)
            mult = MapMaskMultiplier(index, map, mask)
            self.multipliers[name] = mult
        mult = self.multipliers[name]
        mult.expressions.append(expression)

    def get_multipliers_for_expression_name(self, expression_name):
        """
        Gets all map mask multiplier objects that are dependent on given expression pattern.

        @param expression_name: Expression pattern. (string)
        @return: List of multiplers that are dependent on given expression. (MapMaskMultiplier[])
        """

        expression_multipliers = []
        for multiplier in list(self.multipliers.values()):
            for expression in multiplier.expressions:
                if expression.name == expression_name:
                    expression_multipliers.append(multiplier)
        return expression_multipliers

    def get_multipliers_for_map_name(self, map_name):
        """
        Gets all map mask multiplier objects that are dependent on given map pattern.

        @param map_name: Map pattern. (string)
        @return: List of multiplers that are dependent on given map pattern. (MapMaskMultiplier[])
        """

        map_multipliers = []
        for multiplier in list(self.multipliers.values()):
            if multiplier.map.name == map_name:
                map_multipliers.append(multiplier)
        return map_multipliers

    def get_multipliers_for_dx_shader(self):
        """
        Get all map mask multiplier objects whose map object_type is supported in DX Shader

        @return: Filtered list of multipliers which are supported in DX Shader
        """

        filtered_mask_multipliers = []
        for multiplier in list(self.multipliers.values()):
            if multiplier.map.map_type.name in MapMaskMultipliers.MAP_TYPES_SUPPORTED_IN_DX_SHADER:
                filtered_mask_multipliers.append(multiplier)
        filtered_mask_multipliers.sort(key=lambda x: x.index)

        return filtered_mask_multipliers


class MapMaskMultiplier:
    """
    Represents data for shader netvork multiplier, such as order number,
    which expression drive it, etc.
    """

    @staticmethod
    def get_multiplier_name(map, mask):
        return map.name + "_" + mask.name

    def __init__(self, index, map, mask):
        self.index = index
        self.map = map
        self.mask = mask
        self.expressions = []

    def get_name(self):
        return MapMaskMultiplier.get_multiplier_name(self.map, self.mask)

    def get_map_index(self, rig_definition, map_type_name):
        """
        Gets anim map index for given map object_type in rig definition.

        @param rig_definition: Rig definition used to get map and mask indexes. (RigDefinition)
        @param map_type_name: Anim map object_type pattern. (string)
        @return: Anim map index in rig definition for given map object_type.
            If index is None, map is not part of rig definition.(int)
        """

        anim_maps = rig_definition.get_animated_maps(map_type_name)
        if self.map not in anim_maps:
            return None
        return anim_maps.index(self.map)

    def get_mask_index(self, rig_definition):
        """
        Gets mask index in rig definition.

        @param rig_definition: Rig definition used to get map and mask indexes. (RigDefinition)
        @return: Mask index in rig definition.
            If index is None, mask is not part of rig definition.(int)
        """

        if self.mask not in rig_definition.masks:
            return None
        return rig_definition.masks.index(self.mask)
