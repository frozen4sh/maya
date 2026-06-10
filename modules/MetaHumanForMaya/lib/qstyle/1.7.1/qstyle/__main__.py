# Copyright Epic Games, Inc. All Rights Reserved.
import sys
import argparse

from . import example

FUNCTION_MAP = {
    "example": example.show,
}


def main():
    parser = argparse.ArgumentParser("qstyle")
    parser.add_argument("command", choices=FUNCTION_MAP.keys())
    args = parser.parse_args()
    func = FUNCTION_MAP[args.command]
    func()


if __name__ == "__main__":
    sys.exit(main())
