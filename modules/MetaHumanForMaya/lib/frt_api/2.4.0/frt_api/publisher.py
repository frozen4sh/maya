# Copyright Epic Games, Inc. All Rights Reserved.


from typing import Any, Dict, Callable, ClassVar
from functools import wraps
from dataclasses import dataclass


@dataclass
class Publisher:
    subscribers: ClassVar[Dict[str, Callable[[Any], Any]]] = {}

    @classmethod
    def subscribe(cls, func):
        if cls.__name__ in Publisher.subscribers:
            Publisher.subscribers[cls.__name__].append(func)  # type: ignore
        else:
            Publisher.subscribers[cls.__name__] = [func]  # type: ignore

    @classmethod
    def unsubscribe(cls, func):
        for kls in Publisher.subscribers:
            if cls.__name__ == kls:
                if func in cls.subscribers[kls]:  # type: ignore
                    cls.subscribers[kls].remove(func)  # type: ignore

    @classmethod
    def emit(cls, *args, **kwargs):
        for kls in Publisher.subscribers:
            if cls.__name__ == kls:
                for subscriber in cls.subscribers[kls]:  # type: ignore
                    subscriber(*args, **kwargs)


class ExpressionChanged(Publisher):
    pass


class ProgressStart(Publisher):
    pass


class ProgressUpdate(Publisher):
    pass


class ProgressEnd(Publisher):
    pass


def progress_guard(max_value=0):
    def decorator(func):
        @wraps(func)
        def wrapper(*args: str, **kwargs: int):
            try:
                ProgressStart.emit(max_value)
                result = func(*args, **kwargs)
                ProgressEnd.emit()
                return result
            except Exception as e:
                ProgressEnd.emit()
                raise e

        return wrapper

    return decorator
