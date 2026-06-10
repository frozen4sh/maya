# Copyright Epic Games, Inc. All Rights Reserved.

from functools import wraps

import dna
import rdf
import dnacalib2 as dnacalib


class FRTApiError(Exception):
    pass


def status_validator(modules):
    def wrapper(func):
        @wraps(func)
        def inner_wrapper(*args, **kwargs):
            res = func(*args, **kwargs)
            for module in modules:
                if not module.Status.isOk():
                    exception = module.Status.get()
                    raise FRTApiError(
                        f"Method `{func.__qualname__}` has encountered in error at module `{module.__name__}`.\n\nException message: `{exception.message}`\n\nException code: `{exception.code}`."
                    )
            return res

        return inner_wrapper

    return wrapper


status_validator_dna = status_validator([dna])
status_validator_dnacalib = status_validator([dnacalib])
status_validator_rdf = status_validator([rdf])
