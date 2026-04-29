# -*- coding: utf-8 -*-
"""
MotionBuilder - 선택한 본(Skeleton)들의 색상을 주황색으로 변경
"""
from pyfbsdk import *

def set_selected_bones_color_orange():
    # 선택된 모델 가져오기
    selected = FBModelList()
    FBGetSelectedModels(selected, None, True)

    if len(selected) == 0:
        FBMessageBox("알림", "선택된 오브젝트가 없습니다.", "확인")
        return

    # 주황색 (R=1.0, G=0.5, B=0.0)
    orange = FBColor(1.0, 0.5, 0.0)

    count = 0
    for model in selected:
        if isinstance(model, FBModelSkeleton):
            model.Color = orange
            count += 1

    if count == 0:
        FBMessageBox("알림", "선택된 오브젝트 중 Skeleton이 없습니다.", "확인")
    else:
        FBMessageBox("완료", "%d개의 본 색상을 주황색으로 변경했습니다." % count, "확인")

set_selected_bones_color_orange()
