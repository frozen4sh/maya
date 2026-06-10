"""
MatBlack: 머티리얼 정리 스크립트 (Maya용)

1. 모든 머티리얼의 reflectedColor / specularColor를 검정으로 설정
2. M_ 프리픽스 머티리얼을 MI_로 일괄 리네임 (UE5 임포트 시 머티리얼 슬롯 네이밍용)

쉘프 원본: 2023/prefs/shelves/shelf_JustinScripts.mel - MatBlack 버튼
"""

import maya.cmds as cmds

# ----------------------------------------------
# 1. reflectedColor / specularColor 블랙 처리
#    (rename 여부와 상관없이 모든 머티리얼에 적용)
# ----------------------------------------------
materials = cmds.ls(materials=True)

for mat in materials:

    # reflectedColor
    attr1 = mat + ".reflectedColor"
    if cmds.objExists(attr1):
        try:
            cmds.setAttr(attr1, 0, 0, 0, type="double3")
        except:
            pass

    # specularColor
    attr2 = mat + ".specularColor"
    if cmds.objExists(attr2):
        try:
            cmds.setAttr(attr2, 0, 0, 0, type="double3")
        except:
            pass

print("All material reflectedColor and specularColor set to black.")

# ----------------------------------------------
# 2. M_ -> MI_ 이름 변경
#    prefix가 정확히 M_로 시작하는 경우에만 변경.
#    SM_, FM_, M_Wall_M_Detail 같은 중간 M_ 패턴은 건드리지 않음.
#    이미 MI_로 시작하는 머티리얼은 중복 적용 방지를 위해 건너뜀.
# ----------------------------------------------
rename_count = 0
materials = cmds.ls(materials=True)

for mat in materials:
    mat_short = mat.split("|")[-1]

    if not mat_short.startswith("M_"):
        continue
    if mat_short.startswith("MI_"):
        continue

    new_name = "MI_" + mat_short[2:]

    try:
        result = cmds.rename(mat, new_name)
        print("Renamed: {} -> {}".format(mat_short, result))
        rename_count += 1
    except Exception as e:
        # lambert1 등 Maya 기본 머티리얼은 rename이 안 될 수 있음
        print("Skipped (rename failed): {} | {}".format(mat_short, e))

print("Rename complete. {} material(s) renamed.".format(rename_count))
