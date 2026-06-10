"""
RedMesh / GreenMesh: 선택 오브젝트 뷰포트 색상 오버라이드 (Maya용)

선택한 오브젝트(쉐이프 우선)의 drawing override를 켜고 RGB 색상을 적용한다.
리깅/정리 작업 시 메시를 색으로 구분할 때 사용.

쉘프 원본:
- 2023/prefs/shelves/shelf_JustinScripts.mel - RedMesh 버튼 (1, 0, 0)
- 2025/prefs/shelves/shelf_Justin_Aurora.mel - GreenMesh 버튼 (0, 1, 0)
"""

import maya.cmds as cmds

# 적용할 색상 (R, G, B) - RedMesh: (1, 0, 0) / GreenMesh: (0, 1, 0)
COLOR = (0, 1, 0)

sel = cmds.ls(selection=True, long=True)
if not sel:
    cmds.warning("Select objects first.")
else:
    count = 0
    for obj in sel:
        shapes = cmds.listRelatives(obj, shapes=True, fullPath=True) or []
        targets = shapes if shapes else [obj]
        for t in targets:
            try:
                # 오버라이드 속성 잠금 해제
                if cmds.getAttr(t + ".overrideEnabled", lock=True):
                    cmds.setAttr(t + ".overrideEnabled", lock=False)
                if cmds.getAttr(t + ".overrideRGBColors", lock=True):
                    cmds.setAttr(t + ".overrideRGBColors", lock=False)
                if cmds.getAttr(t + ".overrideColorRGB", lock=True):
                    cmds.setAttr(t + ".overrideColorRGB", lock=False)
                cmds.setAttr(t + ".overrideEnabled", 1)
                cmds.setAttr(t + ".overrideRGBColors", 1)
                cmds.setAttr(t + ".overrideColorRGB", COLOR[0], COLOR[1], COLOR[2])
                count += 1
            except Exception as e:
                cmds.warning("Skipped {}: {}".format(t, e))
    print("Set {} node(s) override color to {}.".format(count, COLOR))
