"""
GreenOutliner: 선택 오브젝트 아웃라이너 색상 변경 (Maya용)

선택한 오브젝트의 아웃라이너 표시 색상을 지정 색으로 바꾼다.
리깅/정리 작업 시 아웃라이너에서 노드를 색으로 구분할 때 사용.
mesh_override_color.py(뷰포트 색상)와 세트로 쓰는 스크립트.

쉘프 원본:
- 2023/prefs/shelves/shelf_JustinScripts.mel - GreenOutliner 버튼
- 2025/prefs/shelves/shelf_Justin_Aurora.mel - GreenOutliner 버튼
"""

import maya.cmds as cmds

# 적용할 색상 (R, G, B)
COLOR = (0, 1, 0)

sel = cmds.ls(selection=True, long=True)
if not sel:
    cmds.warning("Select objects first.")
else:
    count = 0
    for obj in sel:
        try:
            cmds.setAttr(obj + ".useOutlinerColor", 1)
            cmds.setAttr(obj + ".outlinerColor", COLOR[0], COLOR[1], COLOR[2])
            count += 1
        except Exception as e:
            cmds.warning("Skipped {}: {}".format(obj, e))
    print("Set {} object(s) outliner color to {}.".format(count, COLOR))
