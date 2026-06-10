# Copyright Epic Games, Inc. All Rights Reserved.

from typing import List, Optional
from dataclasses import field, dataclass


@dataclass
class DataElement:
    """
    Data element base class (interface).

    This class is used for representing data element in tree like data structure.
    Tree like data structure is represented with class DataHolder.

    @see DataHolder
    """

    name: str = ""
    children: List = field(default_factory=list)
    parent: Optional["DataElement"] = None


class DataHolder:
    """
    Container class for data elements.

    This class represents tree like data structure of DataElement objects.
    It can contain more than one tree structure.

    @see DataElement
    """

    def __init__(self, root_list=None):
        self._node_list = None
        if root_list is None:
            root_list = []
        self._root_list = []
        self._node_list = []
        self._node_dict = {}
        self.init(root_list)

    def init(self, root_list):
        self._root_list = root_list
        self._node_list = []
        self._node_dict = {}
        for element in root_list:
            self._init_data_holder(element)

    def _init_data_holder(self, element):
        self._node_list.append(element)
        self._node_dict[element.name] = element
        for child in element.children:
            self._init_data_holder(child)

    def get_element(self, id_):
        """
        Gets data element for given index.

        @param id_: Data element index. (object)
        @return Data element. (DataElement)
        """

        if id_ in self._node_dict:
            return self._node_dict[id_]
        return None

    def get_elements(self):
        """
        Gets root elements as list.

        @return Root data elements. (DataElement[])
        """

        return self._root_list[:]

    def get_all_elements(self):
        """
        Gets all data elements from holder.

        @return All data elements. (DataElement[])
        """

        return self._node_list[:]

    def get_all_element_ids(self):
        """
        Gets all data element ids from holder.

        @return All data element ids. (object[])
        """

        return [el.name for el in self._node_list]

    def has_element(self, id_):
        """
        Checks if data holder contain element with given index.

        @param id_: Data element index. (object)
        @return True if contains element. Otherwise, False. (boolean)
        """

        return id_ in self._node_dict

    def __getitem__(self, key):
        """
        Overrides indexing operator.
        """

        return self._root_list[key]

    def __len__(self):
        """
        Overrides length operator.
        """

        return len(self._root_list)

    def append(self, element):
        """
        Appends data element to holder.

        @param element: New data element. (DataElement)
        """

        if not element.parent:
            self._root_list.append(element)
        self._node_list.append(element)
        self._node_dict[element.name] = element

    def extend(self, elements):
        """
        Extends holder with list of data elements.

        @param elements: List of new data elements. (DataElement[])
        """

        for element in elements:
            self.append(element)

    def sort_first_in_depth(self):
        """
        Sort all tree elements to list using first in depth algorithm.

        After calling this method, method getAllElements will return sorted
        list.
        """

        self._node_list = []
        for element in self._root_list:
            self._sort_first_in_depth_element(element)

    def _sort_first_in_depth_element(self, element):
        self._node_list.append(element)
        for child in element.children:
            self._sort_first_in_depth_element(child)


@dataclass
class CustomAttr:
    """
    Custom attribute base class.

    This class is used as base class for any Maya custom attribute.
    It defines custom attribute object and attribute pattern.
    """

    object_name: str = ""
    attr_name: str = ""

    def __str__(self):
        return self.object_name + "." + self.attr_name


@dataclass
class CustomFloatAttr(CustomAttr):
    """
    Custom float attribute class.

    @see CustomAttr
    """

    min_value: float = 0.0
    max_value: float = 1.0


class RangeFloatAttr(CustomFloatAttr):
    """
    Float attribute with range.

    It has minimum and maximum values it can have.
    @see CustomFloatAttr
    """

    def __init__(self, object_name, attr_name, min_value=0.0, max_value=1.0, from_value=0.0, to_value=1.0):
        super().__init__(object_name, attr_name, min_value, max_value)
        self.from_value = from_value
        self.to_value = to_value

    def shallow_copy(self):
        """
        @return New instance of range float attribute object. (RangeFloatAttr)
        """

        new = RangeFloatAttr(self.object_name, self.attr_name)
        new.min_value = self.min_value
        new.max_value = self.max_value
        new.from_value = self.from_value
        new.to_value = self.to_value
        return new

    def is_in_range(self, value):
        """
        Check if value is in attributes range.

        @param value: Value. (float)
        @return True if value is attribute range, False if it isn't. (boolean)
        """

        if self.from_value < self.to_value:
            if self.from_value <= value <= self.to_value:
                return True
        else:
            if value <= self.from_value >= value >= self.to_value:
                return True
        return False

    def get_multiplier(self, value):
        """
        Get attribute multiplier (0.0 to 1.0) that is equal to given value in
        attribute range.

        @param value: Value. (float)
        @return Multiplier. (float)
        """

        return (value - self.from_value) / (self.to_value - self.from_value)

    def is_negative_oriented(self):
        """
        Indicates if attribute range is negative oriented (from_value is greater than to_value).

        @return True if attribute is negative oriented. (boolean)
        """

        return self.to_value < self.from_value
