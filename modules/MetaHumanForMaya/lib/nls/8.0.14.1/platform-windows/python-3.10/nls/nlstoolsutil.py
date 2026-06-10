# Copyright Epic Games, Inc. All Rights Reserved.

import json

def ToJsonStr(dictionary):
    return json.dumps(dictionary)

def FromJsonStr(jsonStr):
    return json.loads(jsonStr)

def ToJsonFile(dictionary, filename):
    with open(filename, "w") as f:
        f.write(ToJsonStr(dictionary))

def FromJsonFile(filename):
    with open(filename, "r") as f:
        return FromJsonStr(f.read())
    