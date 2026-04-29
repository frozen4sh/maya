# add_ref_layer.py
# ============================================================
# 용도: 현재 선택된 메시를 새 Display Layer에 추가하고
#       해당 레이어를 Reference(R) 모드로 전환하여 선택 불가 처리
# 작성: Blue (OWIS Maya Pipeline)
# 사용법:
#   from add_ref_layer import add_to_ref_layer
#   add_to_ref_layer()                   # 레이어 이름 자동 생성
#   add_to_ref_layer("CL_Mem1_MVA_REF")  # 레이어 이름 직접 지정
# ============================================================

import maya.cmds as cmds


def add_to_ref_layer(layer_name=None):
    """
    현재 선택된 노드를 새 Display Layer에 추가하고 Reference 모드로 설정한다.

    Parameters
    ----------
    layer_name : str, optional
        생성할 레이어 이름. 미지정 시 "REF_Layer_001" 형식으로 자동 생성.

    Returns
    -------
    str or None
        생성된 레이어 이름. 선택이 없으면 None 반환.

    Display Type 참고
    -----------------
    0 = Normal   (기본, 선택/편집 가능)
    1 = Template (선택 가능하지만 편집 불가)
    2 = Reference(선택 및 편집 완전 차단)  ← 이 함수의 목적
    """

    # 1. 선택 확인
    sel = cmds.ls(selection=True)
    if not sel:
        cmds.warning("[add_ref_layer] 선택된 오브젝트가 없습니다. 레이어에 추가할 메시를 먼저 선택하세요.")
        return None

    # 2. 레이어 이름 결정 (중복 방지 자동 넘버링)
    if layer_name is None:
        layer_name = _get_unique_layer_name("REF_Layer")
    else:
        # 사용자 지정 이름도 중복이면 넘버링
        if cmds.objExists(layer_name):
            base = layer_name
            layer_name = _get_unique_layer_name(base)
            cmds.warning(
                "[add_ref_layer] '{}' 레이어가 이미 존재합니다. '{}' 으로 생성합니다.".format(base, layer_name)
            )

    # 3. Display Layer 생성 (-nr: noRecurse, 선택된 노드만 포함)
    #    cmds.createDisplayLayer 는 생성 시점의 선택을 자동으로 레이어에 포함
    created_layer = cmds.createDisplayLayer(name=layer_name, number=1, noRecurse=True)

    # 4. Reference 모드 설정 (displayType = 2)
    cmds.setAttr("{}.displayType".format(created_layer), 2)

    # 5. 결과 출력
    print("[add_ref_layer] 레이어 '{}' 생성 완료 — {} 개 오브젝트 포함, Reference 모드 적용".format(
        created_layer, len(sel)
    ))
    for obj in sel:
        print("  └ {}".format(obj))

    return created_layer


def _get_unique_layer_name(base_name):
    """
    base_name_001, base_name_002 ... 형식으로 씬에 없는 이름을 반환한다.
    """
    counter = 1
    while True:
        candidate = "{:s}_{:03d}".format(base_name, counter)
        if not cmds.objExists(candidate):
            return candidate
        counter += 1


# ============================================================
# 셸프 버튼에서 한 줄로 바로 실행할 수 있는 래퍼
# 셸프 Command 칸에 아래 한 줄을 그대로 붙여넣기
# ============================================================
if __name__ == "__main__":
    # Script Editor에서 직접 실행 시 동작 확인용
    add_to_ref_layer()
