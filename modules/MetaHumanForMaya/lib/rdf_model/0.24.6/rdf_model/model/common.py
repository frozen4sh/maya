# Copyright Epic Games, Inc. All Rights Reserved.
from __future__ import annotations

import re
from typing import Dict, List, Generic, TypeVar, Iterator, Optional

from ..exceptions import NotUniqueException, InvalidKeyException, InvalidIndexException


class Key:
    UNDEF_KEY = ""

    def __init__(self) -> None:
        pass

    def key(self) -> str:
        return Key.UNDEF_KEY


class Index:
    UNDEF_INDEX: int = -1

    def __init__(self) -> None:
        self.index: int = Index.UNDEF_INDEX


class SectionItem(Key, Index):
    def __init__(self, container: Optional[Dict] = None) -> None:
        super().__init__()
        self._container = container

    def __setattr__(self, name, value):
        if name == "key" or name == "name":
            if self._container is not None:
                old = getattr(self, name, "")
                if hasattr(self, "key") and self.key() != Key.UNDEF_KEY:
                    if old == value:
                        return
                    items = list(self._container.items())
                    self._container.clear()
                    for k, v in items:
                        if k == old:
                            self._container[value] = self
                        else:
                            self._container[k] = v
        return super().__setattr__(name, value)


A = TypeVar("A", bound=SectionItem)
T = TypeVar("T", bound=SectionItem)


class SectionList(Generic[A]):
    def __init__(self, values: List[A] = []) -> None:
        self._store: List[A] = values.copy()

    def __len__(self) -> int:
        return len(self._store)

    def __iter__(self):
        return self._store.__iter__()

    def __repr__(self) -> str:
        return str(self._store)

    def clear(self) -> None:
        self._store.clear()

    def find(self, item: A) -> int:
        return self._store.index(item)

    def get(self, key: str) -> Optional[A]:
        for i in self._store:
            if i.key == key:
                return i
        return None

    def at(self, index: int) -> A:
        if index < 0 or index >= len(self._store):
            raise InvalidIndexException(self.__class__.__name__, index)
        return self._store[index]

    def keys(self) -> List[str]:
        return [item.key() for item in self._store]

    def values(self) -> List[A]:
        return self._store.copy()

    def add(self, item: A) -> None:
        if item is None:
            return
        self._store.append(item)

    def remove(self, index: int) -> Optional[A]:
        item = self.at(index)
        if item is not None:
            del self._store[index]
            self.index()
        return item

    def index(self) -> None:
        for i, value in enumerate(self._store):
            value.index = i

    def move(self, index: int, direction: int) -> None:
        if direction not in (-1, 1):
            raise ValueError("Direction must be -1 (up) or 1 (down)")

        move_item(self._store, index, direction)
        self.index()

    def move_under(self, keys: List[str], target_key: str) -> None:
        if not keys or target_key in keys:
            return

        orig = self._store.copy()
        mapping = {item.key(): item for item in orig}
        orig_keys = [item.key() for item in orig]

        key_order = {k: i for i, k in enumerate(orig_keys)}
        keys = sorted(set(keys), key=lambda k: key_order.get(k, -1))

        unselected = [k for k in orig_keys if k not in keys]

        new_order = []
        for k in unselected:
            new_order.append(k)
            if k == target_key:
                new_order.extend(keys)

        if target_key not in unselected:
            new_order.extend(keys)

        self._store = [mapping[k] for k in new_order]
        self.index()


class SectionDict(Generic[T]):
    def __init__(self, values: List[T] = []) -> None:
        self._store: Dict[str, T] = {}
        for val in values:
            self.add(val)

    def __len__(self) -> int:
        return len(self._store)

    def __iter__(self) -> Iterator[T]:
        return iter(self._store.values())

    def __repr__(self) -> str:
        return str(self._store)

    def clear(self) -> None:
        self._store.clear()

    def find(self, item: T) -> int:
        return int(list(self._store.keys()).index(item.key()))

    def data(self, key: str) -> T:
        value = self._store.get(key, None)
        if value is None:
            raise InvalidKeyException(self.__class__.__name__, key)
        return value

    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        return self._store.get(key, default)

    def has(self, key: str) -> bool:
        return key in self._store

    def at(self, index: int) -> T:
        if index < 0 or index >= len(self._store):
            raise InvalidIndexException(self.__class__.__name__, index)
        return self.values()[index]

    def filter(self, pattern: str) -> List[T]:
        results = []
        for key, val in self._store.items():
            if re.match(pattern, key):
                results.append(val)
        return results

    def keys(self) -> List[str]:
        return list(self._store.keys())

    def values(self) -> List[T]:
        return list(self._store.values())

    def add(self, item: T, key: Optional[str] = None) -> None:
        if item is None:
            return
        if key is None:
            key = item.key()
        if self.has(key):
            raise NotUniqueException(self.__class__.__name__, key)
        self._store[key] = item

    def remove(self, key: str) -> Optional[T]:
        item = self._store.get(key)
        if item is not None:
            del self._store[key]
            self.index()
        return item

    def _rename_key(self, old_key: str, new_key: str) -> None:
        # NOTE: Temporary solution until we figure out how to keep the
        # item key and dict key in sync
        if old_key not in self._store:
            raise InvalidKeyException(self.__class__.__name__, old_key)
        if new_key in self._store:
            raise NotUniqueException(self.__class__.__name__, new_key)
        item = self._store[old_key]
        new_store = {}
        for k, v in self._store.items():
            if k == old_key:
                new_store[new_key] = item
            else:
                new_store[k] = v
        self._store = new_store

    def index(self) -> None:
        for i, item in enumerate(self._store.values()):
            item.index = i
            item._container = self._store

    def move(self, key: str, direction: int) -> None:
        if direction not in (-1, 1):
            raise ValueError("Direction must be -1 (up) or 1 (down)")

        keys = list(self.keys())
        index = keys.index(key)
        move_item(keys, index, direction)

        new_data = {k: self._store[k] for k in keys}
        self._store = new_data
        self.index()

    def move_under(self, keys: List[str], target_key: str) -> None:
        if not keys or target_key in keys:
            return

        orig_keys = list(self.keys())
        key_order = {k: i for i, k in enumerate(orig_keys)}
        keys = sorted(set(keys), key=lambda k: key_order.get(k, -1))

        unselected = [k for k in orig_keys if k not in keys]

        new_order = []
        for k in unselected:
            new_order.append(k)
            if k == target_key:
                new_order.extend(keys)

        if target_key not in unselected:
            new_order.extend(keys)

        store = self._store.copy()
        self._store = {k: store[k] for k in new_order}
        self.index()


# --------------------------------------------------------------------------------------------------


def move_item(item_list, index, direction):
    if direction not in (-1, 1):
        raise ValueError("Direction must be -1 (up) or 1 (down)")

    new_index = index + direction

    if new_index < 0 or new_index >= len(item_list):
        return

    item_list[index], item_list[new_index] = item_list[new_index], item_list[index]


def reorder_and_add_leftovers(input_dict, order_list):
    ordered_dict = {}
    leftover_items = {}

    for key in order_list:
        if key in input_dict:
            ordered_dict[key] = input_dict[key]
            del input_dict[key]

    leftover_items = input_dict

    ordered_dict.update(leftover_items)

    return ordered_dict
