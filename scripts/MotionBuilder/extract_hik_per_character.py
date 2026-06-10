"""
HIK 프로퍼티를 캐릭터 노드별로 구분하여 추출.
Properties70 섹션 컨텍스트를 유지하면서 파싱.
"""
import struct
import os
import sys
import io
import re
from collections import defaultdict

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

FBX_PATH = r"D:\Outsourced\Animost\20260527\FBX-20260527T083902Z-3-001\FBX\Test_Mobu.fbx"

# HIK 관련 타겟 프로퍼티
TARGET_PROPS = {
    # Pull
    "CtrlPullLeftHand", "CtrlPullRightHand",
    "CtrlPullLeftFoot", "CtrlPullRightFoot",
    "CtrlChestPullLeftHand", "CtrlChestPullRightHand",
    "CtrlPullLeftFingerBase", "CtrlPullRightFingerBase",
    "CtrlPullLeftToeBase", "CtrlPullRightToeBase",
    # Resist / Stiffness
    "CtrlResistHipsPosition", "CtrlResistHipsOrient",
    "CtrlResistChestPosition", "CtrlResistChestOrient",
    "CtrlResistLeftCollar", "CtrlResistRightCollar",
    "CtrlResistTwist", "CtrlResistCompression",
    "CtrlSpineStiffness", "CtrlNeckStiffness",
    # Floor Contact
    "FootBottomToAnkle", "FootBackToAnkle", "FootMiddleToAnkle",
    "FootFrontToMiddle", "FootInToAnkle", "FootOutToAnkle",
    "HandBottomToWrist", "HandBackToWrist", "HandMiddleToWrist",
    "HandFrontToMiddle", "HandInToWrist", "HandOutToWrist",
    "FootContactEnable", "HandContactEnable",
    "FootFloorPivot", "HandFloorPivot",
    # Roll
    "LeftArmRoll", "RightArmRoll",
    "LeftForeArmRoll", "RightForeArmRoll",
    "LeftUpLegRoll", "RightUpLegRoll",
    "LeftLegRoll", "RightLegRoll",
    "ExtraCollarRatio",
    # Height / Compensation
    "HipsHeightCompensation", "AnkleHeightCompensation",
    "MassCenterCompensation", "ScaleCompensation",
    # Solver
    "RealisticShoulder", "HipsTranslationMode",
    "MatchSource", "Mirror",
    # Reach
    "ReachTranslation", "ReachRotation",
    "LeftHandReachT", "LeftHandReachR",
    "RightHandReachT", "RightHandReachR",
    "LeftFootReachT", "LeftFootReachR",
    "RightFootReachT", "RightFootReachR",
}

HIK_DEFAULTS = {
    "CtrlPullLeftHand":         100.0,
    "CtrlPullRightHand":        100.0,
    "CtrlPullLeftFoot":         100.0,
    "CtrlPullRightFoot":        100.0,
    "CtrlChestPullLeftHand":     50.0,
    "CtrlChestPullRightHand":    50.0,
    "CtrlPullLeftFingerBase":     0.0,
    "CtrlPullRightFingerBase":    0.0,
    "CtrlPullLeftToeBase":        0.0,
    "CtrlPullRightToeBase":       0.0,
    "CtrlResistHipsPosition":     0.0,
    "CtrlResistHipsOrient":       0.0,
    "CtrlResistChestPosition":    0.0,
    "CtrlResistChestOrient":      0.0,
    "CtrlResistLeftCollar":       0.0,
    "CtrlResistRightCollar":      0.0,
    "CtrlResistTwist":            0.0,
    "CtrlResistCompression":      0.0,
    "CtrlSpineStiffness":         0.0,
    "CtrlNeckStiffness":          0.0,
    "FootBottomToAnkle":          0.0,
    "FootBackToAnkle":            0.0,
    "FootMiddleToAnkle":          0.0,
    "FootFrontToMiddle":          0.0,
    "FootInToAnkle":              0.0,
    "FootOutToAnkle":             0.0,
    "HandBottomToWrist":          0.0,
    "HandBackToWrist":            0.0,
    "HandMiddleToWrist":          0.0,
    "HandFrontToMiddle":          0.0,
    "HandInToWrist":              0.0,
    "HandOutToWrist":             0.0,
    "LeftArmRoll":               50.0,
    "RightArmRoll":              50.0,
    "LeftForeArmRoll":           50.0,
    "RightForeArmRoll":          50.0,
    "LeftUpLegRoll":             50.0,
    "RightUpLegRoll":            50.0,
    "LeftLegRoll":               50.0,
    "RightLegRoll":              50.0,
    "ExtraCollarRatio":           0.0,
    "HipsHeightCompensation":     0.0,
    "AnkleHeightCompensation":    0.0,
    "MassCenterCompensation":     0.0,
    "ScaleCompensation":          0.0,
    "RealisticShoulder":          0.0,
    "HipsTranslationMode":        0.0,
    "MatchSource":                0.0,
    "Mirror":                     0.0,
    "ReachTranslation":           0.0,
    "ReachRotation":              0.0,
    "LeftHandReachT":             0.0,
    "LeftHandReachR":             0.0,
    "RightHandReachT":            0.0,
    "RightHandReachR":            0.0,
    "LeftFootReachT":             0.0,
    "LeftFootReachR":             0.0,
    "RightFootReachT":            0.0,
    "RightFootReachR":            0.0,
    "FootContactEnable":          0.0,
    "HandContactEnable":          0.0,
}

def read_null_term(data, pos):
    end = data.find(b'\x00', pos)
    if end == -1:
        return "", pos
    try:
        s = data[pos:end].decode('ascii')
    except UnicodeDecodeError:
        s = ""
    return s, end + 1

def read_len_str(data, pos):
    """u8 length prefix string."""
    if pos >= len(data):
        return "", pos
    slen = data[pos]
    end = pos + 1 + slen
    if end > len(data):
        return "", pos
    try:
        s = data[pos+1:end].decode('ascii', errors='replace')
    except Exception:
        s = ""
    return s, end

def find_character_sections(data):
    """
    FBX 바이너리에서 Character(FbxCharacter) 노드들의 바이트 범위를 탐지.
    각 노드의 시작 offset과 이름을 반환.
    """
    sections = []

    # FbxCharacter 마커로 노드 경계 탐지
    marker = b"FbxCharacter"
    pos = 0
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        # 이 위치 근처에서 노드 이름 읽기 시도
        # FBX 노드: end_offset(u32), num_props(u32), prop_list_len(u32), name_len(u8), name(bytes)
        # marker 앞에 name_len 바이트가 있어야 함
        if idx > 0 and data[idx-1] == len(marker):
            sections.append(idx - 1)
        pos = idx + 1

    return sections

def parse_properties70_block(data, block_start, block_end, char_label):
    """
    주어진 바이트 범위 내의 Properties70 블록에서 P 레코드를 파싱.
    """
    props = {}
    pos = block_start

    # Properties70 마커 찾기
    prop_marker = b"Properties70"
    pidx = data.find(prop_marker, pos, block_end)
    if pidx == -1:
        return props

    # Properties70 노드 헤더 스킵
    scan_start = pidx + len(prop_marker) + 13

    # P 레코드 스캔
    j = scan_start
    while j < min(block_end, pidx + 65536):
        if j < len(data) and data[j] == 1 and j+1 < len(data) and data[j+1] == ord('P'):
            # P 레코드 파싱 시도
            result = try_parse_p_at(data, j+2)
            if result:
                name, val, type_str = result
                if name in TARGET_PROPS:
                    props[name] = (val, type_str)
        j += 1

    return props

def try_parse_p_at(data, pos):
    """
    pos에서 P 레코드 파싱 시도.
    Returns (name, value, type_str) or None.
    """
    dlen = len(data)
    if pos >= dlen:
        return None

    # name (u8 len-prefix)
    name_len = data[pos]
    if name_len == 0 or name_len > 60 or pos + 1 + name_len > dlen:
        return None
    try:
        name = data[pos+1:pos+1+name_len].decode("ascii")
    except UnicodeDecodeError:
        return None
    if not (name[0].isalpha() or name[0] == '_'):
        return None

    # type string
    pos2 = pos + 1 + name_len
    if pos2 >= dlen:
        return None
    type_len = data[pos2]
    if type_len > 40 or pos2 + 1 + type_len > dlen:
        return None
    try:
        type_str = data[pos2+1:pos2+1+type_len].decode("ascii")
    except UnicodeDecodeError:
        return None

    # label
    pos3 = pos2 + 1 + type_len
    if pos3 >= dlen:
        return None
    lbl_len = data[pos3]
    pos4 = pos3 + 1 + max(lbl_len, 0)

    # flags
    if pos4 >= dlen:
        return None
    flag_len = data[pos4]
    pos5 = pos4 + 1 + max(flag_len, 0)

    if pos5 >= dlen:
        return None

    val = None
    tc = chr(data[pos5]) if 32 <= data[pos5] < 127 else None

    if tc == 'D' and pos5 + 9 <= dlen:
        val = struct.unpack_from('<d', data, pos5+1)[0]
    elif tc == 'F' and pos5 + 5 <= dlen:
        val = float(struct.unpack_from('<f', data, pos5+1)[0])
    elif tc == 'I' and pos5 + 5 <= dlen:
        val = float(struct.unpack_from('<i', data, pos5+1)[0])
    elif tc == 'C' and pos5 + 2 <= dlen:
        val = float(data[pos5+1])

    if val is not None and abs(val) < 1e9 and val == val:
        return (name, val, type_str)

    return None

def scan_all_prop70_sections(data):
    """
    모든 Properties70 섹션을 찾고, 각 섹션의 컨텍스트(부모 노드명)를 추적.
    """
    dlen = len(data)
    marker = b"Properties70"
    sections = []

    pos = 0
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break

        # 이 Properties70이 어느 노드에 속하는지 파악
        # 앞으로 최대 512바이트 스캔하여 부모 노드명 추정
        context_start = max(0, idx - 512)
        context_data = data[context_start:idx]

        # Character, HIK 관련 키워드 검색
        parent_label = "Unknown"
        for kw in [b"FbxCharacter", b"HIKCharacterNode", b"Character",
                   b"HIKProperty", b"HIK_"]:
            if kw in context_data:
                try:
                    parent_label = kw.decode("ascii")
                except Exception:
                    pass
                break

        # 섹션 내 P 레코드들 파싱
        section_end = min(dlen, idx + 131072)  # 128KB 윈도우
        props = {}

        j = idx + len(marker) + 13
        while j < section_end:
            if data[j] == 1 and j+1 < dlen and data[j+1] == ord('P'):
                result = try_parse_p_at(data, j+2)
                if result:
                    name, val, type_str = result
                    if name in TARGET_PROPS:
                        props[name] = (val, type_str)
            j += 1

            # 다음 Properties70 만나면 중단
            if data[j:j+12] == b"Properties70":
                break

        if props:
            sections.append({
                "offset": idx,
                "parent": parent_label,
                "props": props,
            })

        pos = idx + 1

    return sections

def find_character_name_near(data, offset, window=1024):
    """offset 근처에서 캐릭터 이름 탐색."""
    start = max(0, offset - window)
    snippet = data[start:offset]

    # "Model::", "Character::", "HIK" 등 패턴
    for pattern in [b"HIKCharacterNode", b"FbxCharacter", b"Character"]:
        idx = snippet.rfind(pattern)
        if idx != -1:
            # 이름 읽기 시도
            name_start = start + idx + len(pattern)
            if name_start < len(data) and data[name_start] == ord(':'):
                name_start += 2
                end = data.find(b'\x00', name_start, name_start + 128)
                if end != -1:
                    try:
                        return data[name_start:end].decode("ascii", errors="replace")
                    except Exception:
                        pass
    return None

def main():
    print("=" * 70)
    print("HIK 리타겟 세팅 캐릭터별 상세 분석")
    print(f"파일: {FBX_PATH}")
    print("=" * 70)

    if not os.path.exists(FBX_PATH):
        print(f"[ERROR] 파일 없음")
        sys.exit(1)

    fsize = os.path.getsize(FBX_PATH)
    print(f"파일 크기: {fsize/1024/1024:.2f} MB")
    print("파일 로딩 중...")
    data = open(FBX_PATH, "rb").read()
    print(f"로드 완료: {len(data)} bytes")

    print("\n[단계 1] 모든 Properties70 섹션 스캔...")
    sections = scan_all_prop70_sections(data)
    print(f"  HIK 관련 Properties70 섹션 {len(sections)}개 발견")

    # 섹션별 출력
    for i, sec in enumerate(sections):
        print(f"\n  섹션 #{i+1} (offset {sec['offset']}, 부모: {sec['parent']})")
        for pname, (val, tstr) in sorted(sec['props'].items()):
            default = HIK_DEFAULTS.get(pname, "N/A")
            is_changed = isinstance(default, float) and abs(val - default) > 0.0001
            flag = "  <-- 변경됨" if is_changed else ""
            print(f"    {pname:<38} = {val:>10.4f}  (type={tstr}, default={default}){flag}")

    # ─── 섹션 통합 분석 ───
    print("\n" + "=" * 70)
    print("[ 통합 분석: 모든 섹션에서 수집된 값 ]")
    print("=" * 70)

    # 프로퍼티별로 모든 섹션의 값 수집
    all_vals = defaultdict(list)
    for sec in sections:
        for pname, (val, tstr) in sec['props'].items():
            all_vals[pname].append(val)

    # 변경된 것만 출력
    print("\n★ 디폴트와 다른 값 (의도적 튜닝된 것):")
    changed_count = 0
    for pname in sorted(all_vals.keys()):
        vals = all_vals[pname]
        default = HIK_DEFAULTS.get(pname, None)
        unique_vals = list(set(round(v, 4) for v in vals))

        if default is not None:
            changed = [v for v in unique_vals if abs(v - default) > 0.0001]
            if changed:
                print(f"  {pname:<38} : 발견값={unique_vals}  디폴트={default}")
                changed_count += 1

    if changed_count == 0:
        print("  (없음)")

    # ─── ScaleCompensation 특이값 분석 ───
    print("\n[특이 분석] ScaleCompensation = 100 의 의미:")
    if "ScaleCompensation" in all_vals:
        vals = all_vals["ScaleCompensation"]
        print(f"  수집된 모든 값: {vals}")
        print(f"  100.0이 포함됨: {100.0 in vals or any(abs(v-100)<0.01 for v in vals)}")
        print(f"  → ScaleCompensation=100 은 '스케일 보정 100% 활성화' 의미")
        print(f"    (Source-Target 체형 비율 차이를 HIK가 자동 보정하도록 허용)")

    # ─── Floor Contact 값 해석 ───
    print("\n[Floor Contact 지오메트리 오프셋 해석]")
    print("(단위: cm 기준, MetaHuman 실제 발 크기에 맞춰 수동 조정된 값)")
    fc_foot = {
        "FootBackToAnkle":   all_vals.get("FootBackToAnkle", []),
        "FootMiddleToAnkle": all_vals.get("FootMiddleToAnkle", []),
        "FootFrontToMiddle": all_vals.get("FootFrontToMiddle", []),
        "FootInToAnkle":     all_vals.get("FootInToAnkle", []),
        "FootOutToAnkle":    all_vals.get("FootOutToAnkle", []),
        "FootBottomToAnkle": all_vals.get("FootBottomToAnkle", []),
    }
    fc_hand = {
        "HandBackToWrist":   all_vals.get("HandBackToWrist", []),
        "HandMiddleToWrist": all_vals.get("HandMiddleToWrist", []),
        "HandFrontToMiddle": all_vals.get("HandFrontToMiddle", []),
        "HandInToWrist":     all_vals.get("HandInToWrist", []),
        "HandOutToWrist":    all_vals.get("HandOutToWrist", []),
        "HandBottomToWrist": all_vals.get("HandBottomToWrist", []),
    }

    print("  [발 컨택]")
    for k, v in fc_foot.items():
        unique = list(set(round(x, 3) for x in v))
        default = HIK_DEFAULTS.get(k, 0.0)
        # 수동 입력값(정수 근사값)과 자동 계산값 구분
        manual = [x for x in unique if abs(x - round(x)) < 0.01]  # 정수에 가까운 값
        auto   = [x for x in unique if abs(x - round(x)) >= 0.01]
        print(f"    {k:<25}: 수동설정추정={manual}  자동계산={auto}  (default={default})")

    print("  [손 컨택]")
    for k, v in fc_hand.items():
        unique = list(set(round(x, 3) for x in v))
        default = HIK_DEFAULTS.get(k, 0.0)
        manual = [x for x in unique if abs(x - round(x)) < 0.01]
        auto   = [x for x in unique if abs(x - round(x)) >= 0.01]
        print(f"    {k:<25}: 수동설정추정={manual}  자동계산={auto}  (default={default})")

    print("\n" + "=" * 70)
    print("분석 완료")

if __name__ == "__main__":
    main()
