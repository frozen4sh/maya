# Copyright Epic Games, Inc. All Rights Reserved.
import os
import json

this_dir = os.path.dirname(os.path.abspath(__file__))
config_filepath = os.path.join(this_dir, "config.json")

with open(config_filepath) as f:
    CONFIG = json.load(f)
