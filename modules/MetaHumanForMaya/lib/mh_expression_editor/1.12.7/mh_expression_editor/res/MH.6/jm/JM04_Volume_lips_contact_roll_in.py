# Copyright Epic Games, Inc. All Rights Reserved.

options = {
    "expressions": {
        "expression": [
            {"expName": "mouth_press"},
            {"expName": "Mpress_Jopen_tgt"},
            {"expName": "MlipsTogether_Mpress_Jopen__mouthSuck_tgt"},
            {"expName": "mouth_upperLipRollIn"},
            {"expName": "mouth_lowerLipRollIn"},
        ]
    },
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
                "name": "pass1_lipsContactRollIn",
                "paintConstraintSplitMap": "JO_05_pass1_lipsContactRollIn_1",
                "rotationRegularization": "1.0",
                "sculptMesh": "head_lod0_mesh",
                "startType": "0",
                "strainWeight": "0.0",
                "translationRegularization": "0.0",
            }
        ]
    },
    "name": "JO_04_pass1_lipsContactRollIn",
}
