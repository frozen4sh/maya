# Copyright Epic Games, Inc. All Rights Reserved.

options = {
    "expressions": {
        "expression": [
            {"expName": "mouth_press"},
            {"expName": "Mpress_Jopen_tgt"},
            {"expName": "MlipsTogether_Mpress_Jopen__mouthSuck_tgt"},
            {"expName": "mouth_upperLipRollIn"},
            {"expName": "mouth_upperLipRollOut"},
            {"expName": "mouth_lowerLipRollIn"},
            {"expName": "mouth_lowerLipRollOut"},
            {"expName": "mouth_left"},
            {"expName": "mouth_right"},
        ]
    },
    "passes": {
        "pass": [
            {
                "jointOptions": {
                    "jointOption": [
                        {"name": "FACIAL_C_LipUpper", "r": True, "t": True},
                        {"name": "FACIAL_L_LipUpper", "r": True, "t": True},
                        {"name": "FACIAL_R_LipUpper", "r": True, "t": True},
                        {"name": "FACIAL_L_LipUpperOuter", "r": True, "t": True},
                        {"name": "FACIAL_R_LipUpperOuter", "r": True, "t": True},
                        {"name": "FACIAL_C_LipLower", "r": True, "t": True},
                        {"name": "FACIAL_L_LipLower", "r": True, "t": True},
                        {"name": "FACIAL_R_LipLower", "r": True, "t": True},
                        {"name": "FACIAL_L_LipLowerOuter", "r": True, "t": True},
                        {"name": "FACIAL_R_LipLowerOuter", "r": True, "t": True},
                    ]
                },
                "bendingWeight": "0.0",
                "meshName": "headMatchPass1_mesh",
                "nIterations": "10",
                "name": "pass1_rolls",
                "paintConstraintSplitMap": "JO_03_pass1_rolls_1",
                "rotationRegularization": "0.5",
                "sculptMesh": "head_lod0_mesh",
                "startType": "1",
                "strainWeight": "0.0",
                "translationRegularization": "0.0",
            }
        ]
    },
    "name": "JO_02_pass1_rolls",
}
