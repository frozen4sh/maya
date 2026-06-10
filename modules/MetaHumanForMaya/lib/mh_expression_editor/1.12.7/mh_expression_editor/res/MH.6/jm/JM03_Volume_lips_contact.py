# Copyright Epic Games, Inc. All Rights Reserved.

options = {
    "expressions": {"expression": [{"expName": "mouth_left"}, {"expName": "mouth_right"}]},
    "passes": {
        "pass": [
            {
                "jointOptions": {
                    "jointOption": [
                        {"name": "FACIAL_C_LipUpper", "r": False, "t": True},
                        {"name": "FACIAL_L_LipUpper", "r": False, "t": True},
                        {"name": "FACIAL_R_LipUpper", "r": False, "t": True},
                        {"name": "FACIAL_L_LipUpperOuter", "r": False, "t": True},
                        {"name": "FACIAL_R_LipUpperOuter", "r": False, "t": True},
                        {"name": "FACIAL_C_LipLower", "r": False, "t": True},
                        {"name": "FACIAL_L_LipLower", "r": False, "t": True},
                        {"name": "FACIAL_R_LipLower", "r": False, "t": True},
                        {"name": "FACIAL_L_LipLowerOuter", "r": False, "t": True},
                        {"name": "FACIAL_R_LipLowerOuter", "r": False, "t": True},
                    ]
                },
                "bendingWeight": "0.0",
                "meshName": "headMatchPass1_mesh",
                "nIterations": "10",
                "name": "pass1_lipsContact",
                "paintConstraintSplitMap": "JO_04_pass1_lipsContact_1",
                "rotationRegularization": "1.0",
                "sculptMesh": "head_lod0_mesh",
                "startType": "0",
                "strainWeight": "0.0",
                "translationRegularization": "0.0",
            }
        ]
    },
    "name": "JO_03_pass1_lipsContact",
}
