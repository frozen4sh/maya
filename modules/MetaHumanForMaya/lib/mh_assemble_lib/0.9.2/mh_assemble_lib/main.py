# Copyright Epic Games, Inc. All Rights Reserved.
"""
Main module used for instantiating base (stand-alone) context.
It is used for testing and debugging purposes.
Also, it represents an example how MHViever is used.
"""
import sys

from mh_assemble_lib.context.factory import Factory
from mh_assemble_lib.control.business import Controller
from mh_assemble_lib.impl.maya.factory import MayaFactory


def get_factory(arg_impl: str) -> Factory:
    if arg_impl == "maya":
        return MayaFactory()
    return Factory()


def run(arg_impl: str) -> None:
    factory = get_factory(arg_impl)
    handler = factory.create_handler()
    controller = Controller(handler)

    factory.create_app()
    viewer = factory.create_viewer()
    viewer.set_controller(controller)
    factory.show_viewer()


def run_maya() -> None:
    run("maya")


if __name__ == "__main__":
    arg_impl = sys.argv[1]
    print(f"MAIN: {arg_impl}")
    run(arg_impl)
