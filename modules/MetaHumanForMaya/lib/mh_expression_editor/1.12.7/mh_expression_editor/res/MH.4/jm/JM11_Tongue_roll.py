# Copyright Epic Games, Inc. All Rights Reserved.

options = {
    "expressions": {
        "expression": [
            {"expName": "tongue_roll_tgt"},
            {"expName": "tongue_outRoll_tgt"},
        ]
    },
    "passes": {
        "pass": [
            {
                "jointOptions": {
                    "jointOption": [
                        {"name": "FACIAL_C_Tongue1", "r": True, "t": True},
                        {"name": "FACIAL_C_Tongue2", "r": True, "t": True},
                        {"name": "FACIAL_C_Tongue3", "r": True, "t": True},
                        {"name": "FACIAL_C_Tongue4", "r": True, "t": True},
                    ]
                },
                "bendingWeight": "0.0",
                "meshName": "teeth_lod0_mesh",
                "nIterations": "10",
                "name": "pass1_tongueRoll",
                "paintConstraintSplitMap": "JO_15_pass1_tongueRoll_1",
                "rotationRegularization": "2.0",
                "sculptMesh": "teeth_lod0_mesh",
                "startType": "1",
                "strainWeight": "0.0",
                "translationRegularization": "0.0",
            },
            {
                "jointOptions": {
                    "jointOption": [
                        {"name": "FACIAL_C_TongueUpper1", "r": True, "t": True},
                        {"name": "FACIAL_L_TongueSide1", "r": True, "t": True},
                        {"name": "FACIAL_R_TongueSide1", "r": True, "t": True},
                        {"name": "FACIAL_C_TongueUpper2", "r": True, "t": True},
                        {"name": "FACIAL_L_TongueSide2", "r": True, "t": True},
                        {"name": "FACIAL_R_TongueSide2", "r": True, "t": True},
                        {"name": "FACIAL_C_TongueUpper3", "r": True, "t": True},
                        {"name": "FACIAL_C_TongueLower3", "r": True, "t": True},
                        {"name": "FACIAL_L_TongueSide3", "r": True, "t": True},
                        {"name": "FACIAL_R_TongueSide3", "r": True, "t": True},
                        {"name": "FACIAL_L_TongueSide4", "r": True, "t": True},
                        {"name": "FACIAL_R_TongueSide4", "r": True, "t": True},
                    ]
                },
                "bendingWeight": "0.0",
                "meshName": "teeth_lod0_mesh",
                "nIterations": "10",
                "name": "pass2_tongueRoll",
                "paintConstraintSplitMap": "JO_14_pass2_tongueDefault_1",
                "rotationRegularization": "0.5",
                "sculptMesh": "teeth_lod0_mesh",
                "startType": "1",
                "strainWeight": "0.0",
                "translationRegularization": "0.0",
            },
        ]
    },
    "name": "JO_11_pass12_tongueRoll",
}
