"""
HIK Retarget Property Extractor
FBX 바이너리에서 HIK 및 리타겟 품질 관련 실제 설정값을 추출.
Default 값과 비교하여 의도적으로 튜닝된 항목을 식별.
"""

import struct
import os
import sys
import re
import io

# Force UTF-8 stdout for Korean output
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

FBX_PATH = r"D:\Outsourced\Animost\20260527\FBX-20260527T083902Z-3-001\FBX\Test_Mobu.fbx"

# ─────────────────────────────────────────────────────────────────
# HIK / Retarget 프로퍼티 기본값 (MotionBuilder 공식 디폴트)
# ─────────────────────────────────────────────────────────────────
HIK_DEFAULTS = {
    # Reach
    "ReachTranslation":               0.0,
    "ReachRotation":                  0.0,
    "CtrlPullLeftHand":               100.0,
    "CtrlPullRightHand":              100.0,
    "CtrlPullLeftFoot":               100.0,
    "CtrlPullRightFoot":              100.0,
    "CtrlChestPullLeftHand":          50.0,
    "CtrlChestPullRightHand":         50.0,
    "CtrlPullLeftFingerBase":         0.0,
    "CtrlPullRightFingerBase":        0.0,
    "CtrlPullLeftToeBase":            0.0,
    "CtrlPullRightToeBase":           0.0,
    # Resist / Stiffness
    "CtrlResistHipsPosition":         0.0,
    "CtrlResistHipsOrient":           0.0,
    "CtrlResistChestPosition":        0.0,
    "CtrlResistChestOrient":          0.0,
    "CtrlResistLeftCollar":           0.0,
    "CtrlResistRightCollar":          0.0,
    "CtrlResistTwist":                0.0,
    "CtrlResistCompression":          0.0,
    "CtrlSpineStiffness":             0.0,
    "CtrlNeckStiffness":              0.0,
    # Effector Reach (0~100)
    "LeftHandReachT":                 0.0,
    "LeftHandReachR":                 0.0,
    "RightHandReachT":                0.0,
    "RightHandReachR":                0.0,
    "LeftFootReachT":                 0.0,
    "LeftFootReachR":                 0.0,
    "RightFootReachT":                0.0,
    "RightFootReachR":                0.0,
    # Floor Contact Geometry Offsets (cm, 통상 스켈레톤 크기 의존)
    "FootBottomToAnkle":              0.0,
    "FootBackToAnkle":                0.0,
    "FootMiddleToAnkle":              0.0,
    "FootFrontToMiddle":              0.0,
    "FootInToAnkle":                  0.0,
    "FootOutToAnkle":                 0.0,
    "HandBottomToWrist":              0.0,
    "HandBackToWrist":                0.0,
    "HandMiddleToWrist":              0.0,
    "HandFrontToMiddle":              0.0,
    "HandInToWrist":                  0.0,
    "HandOutToWrist":                 0.0,
    # Roll
    "LeftArmRoll":                    50.0,
    "RightArmRoll":                   50.0,
    "LeftForeArmRoll":                50.0,
    "RightForeArmRoll":               50.0,
    "LeftUpLegRoll":                  50.0,
    "RightUpLegRoll":                 50.0,
    "LeftLegRoll":                    50.0,
    "RightLegRoll":                   50.0,
    "ExtraCollarRatio":               0.0,
    # Height Compensation
    "HipsHeightCompensation":         0.0,
    "AnkleHeightCompensation":        0.0,
    "MassCenterCompensation":         0.0,
    # Solver / Realism
    "RealisticShoulder":              0.0,
    "ScaleCompensation":              0.0,
    "HipsTranslationMode":            0.0,
    "MatchSource":                    0.0,   # bool: 0=off 1=on
    "Mirror":                         0.0,   # bool
    # Contact
    "ContactBehavior":                0.0,
}

# ─────────────────────────────────────────────────────────────────
# FBX 바이너리 파서 (lightweight, property scan 전용)
# ─────────────────────────────────────────────────────────────────
def read_fbx_binary(path):
    with open(path, "rb") as f:
        return f.read()

def scan_string_properties(data):
    """
    FBX 바이너리에서 모든 문자열 프로퍼티명과 바로 뒤의 타입코드+값을 스캔.
    FBX 바이너리 프로퍼티 레이아웃:
      [name_len:u8][name:bytes][type_code:char][...value...]
    혹은 노드 레코드 내부에서 문자열 키를 찾고 인접 double/float/int를 읽음.
    """
    results = {}  # prop_name -> list of values

    i = 0
    dlen = len(data)

    while i < dlen - 32:
        # 알파벳으로 시작하는 가능성 있는 프로퍼티명 찾기
        # FBX 노드 레코드의 프로퍼티 이름은 null-terminated 또는 length-prefixed
        # 여기서는 raw byte 스캔: ASCII 가능한 길이 1-2바이트 뒤에 알파벳 문자열
        b = data[i]
        if 8 <= b <= 80:  # 가능한 문자열 길이
            end = i + 1 + b
            if end < dlen:
                candidate = data[i+1:end]
                try:
                    name = candidate.decode("ascii")
                    if name.isidentifier() and len(name) >= 4:
                        # 이름 다음 바이트가 타입코드일 수 있음
                        tc_pos = end
                        if tc_pos < dlen:
                            tc = chr(data[tc_pos])
                            val = None
                            if tc == 'D' and tc_pos + 9 <= dlen:  # double
                                val = struct.unpack_from('<d', data, tc_pos + 1)[0]
                            elif tc == 'F' and tc_pos + 5 <= dlen:  # float
                                val = struct.unpack_from('<f', data, tc_pos + 1)[0]
                            elif tc == 'I' and tc_pos + 5 <= dlen:  # int32
                                val = struct.unpack_from('<i', data, tc_pos + 1)[0]
                            elif tc == 'L' and tc_pos + 9 <= dlen:  # int64
                                val = struct.unpack_from('<q', data, tc_pos + 1)[0]
                            elif tc == 'C' and tc_pos + 2 <= dlen:  # bool
                                val = bool(data[tc_pos + 1])

                            if val is not None:
                                if name not in results:
                                    results[name] = []
                                results[name].append((val, tc))
                except (UnicodeDecodeError, ValueError):
                    pass
        i += 1
    return results

def scan_raw_pattern(data):
    """
    더 정확한 스캔: FBX P 레코드 (프로퍼티 배열) 패턴을 직접 찾음.
    FBX P record: "P\x00" 다음에 [str_len:u8][name][str_len:u8][type_str][...][value]
    실제로는 노드 내 Properties70 블록의 각 P 레코드를 파싱.
    """
    results = {}

    # "Properties70" 마커 찾기
    marker = b"Properties70"
    pos = 0
    sections = []
    while True:
        idx = data.find(marker, pos)
        if idx == -1:
            break
        sections.append(idx)
        pos = idx + 1

    print(f"  [*] Properties70 섹션 {len(sections)}개 발견")

    for sec_start in sections:
        # Properties70 노드 내부: 'P' 레코드들을 파싱
        # FBX 노드 구조: [end_offset:u32/u64][num_props:u32/u64][prop_list_len:u32/u64][name_len:u8][name:bytes][props...][children...]
        # Properties70 다음 위치부터 P 노드들 스캔
        scan_start = sec_start + len(marker) + 13  # 헤더 스킵 (근사)
        scan_end = min(sec_start + 65536, len(data))  # 64KB 윈도우

        j = scan_start
        while j < scan_end - 4:
            # 'P' 노드 시작 탐지 (name_len=1, name=b'P')
            if data[j] == 1 and data[j+1] == ord('P'):
                try:
                    parse_p_record(data, j+2, results)
                except Exception:
                    pass
            j += 1

    return results

def parse_p_record(data, pos, results):
    """
    P 레코드 파싱: [name_len:u8][name:bytes][type_len:u8][type:bytes][flag_len:u8][flag:bytes][...][value_type:char][value:...]
    FBX P 레코드 실제 레이아웃 (FBX SDK 기준):
      "P" node with props: name(S), type(S), label(S), flags(S), value(D/F/I/...)
    """
    dlen = len(data)
    if pos >= dlen:
        return

    # name
    name_len = data[pos]
    if name_len == 0 or pos + 1 + name_len > dlen:
        return
    try:
        name = data[pos+1:pos+1+name_len].decode("ascii")
    except UnicodeDecodeError:
        return
    if not (name[0].isalpha() or name[0] == '_'):
        return

    # type string
    pos2 = pos + 1 + name_len
    if pos2 >= dlen:
        return
    type_len = data[pos2]
    if type_len == 0 or pos2 + 1 + type_len > dlen:
        return
    try:
        type_str = data[pos2+1:pos2+1+type_len].decode("ascii")
    except UnicodeDecodeError:
        return

    # label
    pos3 = pos2 + 1 + type_len
    if pos3 >= dlen:
        return
    lbl_len = data[pos3]
    pos4 = pos3 + 1 + max(lbl_len, 0)

    # flags
    if pos4 >= dlen:
        return
    flag_len = data[pos4]
    pos5 = pos4 + 1 + max(flag_len, 0)

    # value
    if pos5 >= dlen:
        return

    val = None
    tc = chr(data[pos5]) if data[pos5] in range(32, 127) else None

    if tc == 'D' and pos5 + 9 <= dlen:
        val = struct.unpack_from('<d', data, pos5+1)[0]
    elif tc == 'F' and pos5 + 5 <= dlen:
        val = struct.unpack_from('<f', data, pos5+1)[0]
    elif tc == 'I' and pos5 + 5 <= dlen:
        val = struct.unpack_from('<i', data, pos5+1)[0]
    elif tc == 'C' and pos5 + 2 <= dlen:
        val = bool(data[pos5+1])

    if val is not None and name in HIK_DEFAULTS:
        if name not in results:
            results[name] = []
        results[name].append((val, tc, type_str))

def deep_scan_known_props(data):
    """
    알려진 HIK 프로퍼티명을 바이트로 직접 검색 후 인근 값을 추출.
    가장 신뢰도 높은 방법.
    """
    results = {}
    dlen = len(data)

    for prop_name in HIK_DEFAULTS.keys():
        search_bytes = prop_name.encode("ascii")
        pos = 0
        found_vals = []
        while True:
            idx = data.find(search_bytes, pos)
            if idx == -1:
                break
            # 문자열 앞 바이트가 길이 필드인지 확인 (FBX S-type)
            # 또는 length-prefixed string 확인
            match_ok = False

            # 방법 1: 앞에 u8 length
            if idx > 0 and data[idx-1] == len(search_bytes):
                match_ok = True
                after = idx + len(search_bytes)
            # 방법 2: 앞에 u32 little-endian length
            elif idx >= 4:
                slen = struct.unpack_from('<I', data, idx-4)[0]
                if slen == len(search_bytes):
                    match_ok = True
                    after = idx + len(search_bytes)

            if match_ok and after < dlen:
                # after 위치부터 값 타입 코드 + 값을 찾음
                # FBX P record에서는 name 뒤에 type_str, label, flags, then value
                # 간단하게: 다음 40바이트 내에서 D/F/I 타입 코드 + 합리적 값 찾기
                window = data[after:after+80]
                for k in range(len(window) - 8):
                    tc_byte = window[k]
                    if tc_byte == ord('D') and k+9 <= len(window):
                        v = struct.unpack_from('<d', window, k+1)[0]
                        if -1e6 < v < 1e6 and not (v != v):  # finite, reasonable
                            found_vals.append(('D', v, idx))
                            break
                    elif tc_byte == ord('F') and k+5 <= len(window):
                        v = struct.unpack_from('<f', window, k+1)[0]
                        if -1e6 < v < 1e6 and not (v != v):
                            found_vals.append(('F', float(v), idx))
                            break
                    elif tc_byte == ord('I') and k+5 <= len(window):
                        v = struct.unpack_from('<i', window, k+1)[0]
                        if -1000 < v < 1000:
                            found_vals.append(('I', float(v), idx))
                            break

            pos = idx + 1

        if found_vals:
            results[prop_name] = found_vals

    return results

def find_hik_character_nodes(data):
    """HIK Character 노드 식별."""
    markers = [b"HIKCharacterNode", b"HikCharacterNode", b"HIKCharacter",
               b"Character", b"FbxCharacter"]
    found = {}
    for m in markers:
        idx = 0
        positions = []
        while True:
            p = data.find(m, idx)
            if p == -1:
                break
            positions.append(p)
            idx = p + 1
        if positions:
            found[m.decode("ascii", errors="replace")] = positions
    return found

def find_floor_contact_values(data):
    """Floor Contact 관련 값 전용 스캔."""
    fc_props = [
        "FootContactEnable", "HandContactEnable",
        "FootBottomToAnkle", "FootBackToAnkle", "FootMiddleToAnkle",
        "FootFrontToMiddle", "FootInToAnkle", "FootOutToAnkle",
        "HandBottomToWrist", "HandBackToWrist", "HandMiddleToWrist",
        "HandFrontToMiddle", "HandInToWrist", "HandOutToWrist",
        "FootFloorPivot", "HandFloorPivot",
        "FootAutoPlant", "HandAutoPlant",
    ]
    results = {}
    for prop in fc_props:
        sb = prop.encode("ascii")
        idx = 0
        while True:
            p = data.find(sb, idx)
            if p == -1:
                break
            after = p + len(sb)
            window = data[after:after+60]
            for k in range(len(window)-8):
                tc = window[k]
                if tc == ord('D') and k+9 <= len(window):
                    v = struct.unpack_from('<d', window, k+1)[0]
                    if -10000 < v < 10000 and v == v:
                        results.setdefault(prop, []).append(v)
                        break
                elif tc == ord('F') and k+5 <= len(window):
                    v = struct.unpack_from('<f', window, k+1)[0]
                    if -10000 < v < 10000 and v == v:
                        results.setdefault(prop, []).append(float(v))
                        break
                elif tc == ord('C') and k+2 <= len(window):
                    results.setdefault(prop, []).append(bool(window[k+1]))
                    break
            idx = p + 1
    return results

def extract_number_after_keyword(data, keyword_bytes, window_size=100):
    """키워드 직후 처음 나오는 숫자값(D/F/I)을 추출."""
    results = []
    idx = 0
    while True:
        p = data.find(keyword_bytes, idx)
        if p == -1:
            break
        after = p + len(keyword_bytes)
        window = data[after:after+window_size]
        for k in range(len(window)-8):
            tc = window[k]
            if tc == ord('D') and k+9 <= len(window):
                v = struct.unpack_from('<d', window, k+1)[0]
                if abs(v) < 1e9 and v == v:
                    results.append(('D', v, p))
                    break
            elif tc == ord('F') and k+5 <= len(window):
                v = struct.unpack_from('<f', window, k+1)[0]
                if abs(v) < 1e9 and v == v:
                    results.append(('F', float(v), p))
                    break
            elif tc == ord('I') and k+5 <= len(window):
                v = struct.unpack_from('<i', window, k+1)[0]
                if abs(v) < 100000:
                    results.append(('I', float(v), p))
                    break
        idx = p + 1
    return results

def check_ascii_fbx(data):
    """ASCII FBX 여부 확인."""
    header = data[:50]
    if b"Kaydara FBX Binary" in header:
        return False
    if b"; FBX" in header or b"FBXHeaderExtension" in data[:200]:
        return True
    return None

def parse_ascii_fbx_props(data):
    """ASCII FBX인 경우 텍스트 파싱으로 HIK 프로퍼티 추출."""
    try:
        text = data.decode("utf-8", errors="replace")
    except Exception:
        return {}

    results = {}
    lines = text.splitlines()

    for line in lines:
        # P record: P: "PropName","Type","Label","Flags",value
        m = re.match(r'\s*P:\s*"([^"]+)"[^,]*,[^,]*,[^,]*,[^,]*,\s*([-\d.eE+]+)', line)
        if m:
            name = m.group(1)
            try:
                val = float(m.group(2))
                if name in HIK_DEFAULTS:
                    results.setdefault(name, []).append(val)
            except ValueError:
                pass
    return results

# ─────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────
def main():
    print("=" * 70)
    print("HIK Retarget Property Extractor")
    print(f"파일: {FBX_PATH}")
    print("=" * 70)

    if not os.path.exists(FBX_PATH):
        print(f"[ERROR] 파일 없음: {FBX_PATH}")
        sys.exit(1)

    fsize = os.path.getsize(FBX_PATH)
    print(f"파일 크기: {fsize/1024/1024:.2f} MB")

    print("파일 로딩 중...")
    data = read_fbx_binary(FBX_PATH)
    print(f"로드 완료: {len(data)} bytes")

    # ASCII or Binary 확인
    is_ascii = check_ascii_fbx(data)
    if is_ascii:
        print("[INFO] ASCII FBX 포맷 감지 → 텍스트 파싱 모드")
        prop_results = parse_ascii_fbx_props(data)
    else:
        print("[INFO] Binary FBX 포맷 → 바이너리 스캔 모드")
        prop_results = {}

    print("\n[1] HIK 문자열 노드 위치 스캔...")
    hik_nodes = find_hik_character_nodes(data)
    for name, positions in hik_nodes.items():
        print(f"  '{name}': {len(positions)}회 등장 (첫 위치: offset {positions[0]})")

    print("\n[2] 알려진 HIK 프로퍼티 딥스캔...")
    deep_results = deep_scan_known_props(data)
    prop_results.update(deep_results)

    print(f"  발견된 HIK 프로퍼티: {len(prop_results)}개")

    print("\n[3] Floor Contact 전용 스캔...")
    fc_results = find_floor_contact_values(data)
    print(f"  발견된 Floor Contact 프로퍼티: {len(fc_results)}개")

    # ─────────────────────────────────────────────────────────────
    # 결과 분석: 디폴트와 비교
    # ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("[ HIK / 리타겟 프로퍼티 실제값 vs 디폴트 비교 ]")
    print("=" * 70)

    TOLERANCE = 0.0001  # 비교 허용 오차

    tuned_props = {}   # 의도적으로 조정된 것
    default_props = {} # 디폴트와 같은 것
    found_in_fc = {}   # Floor contact

    # HIK 일반 프로퍼티
    for prop_name, default_val in HIK_DEFAULTS.items():
        found = prop_results.get(prop_name, [])
        # 중복값 제거 (가장 흔한 값 선택)
        if found:
            vals = [v for (tc, v, *_) in found] if isinstance(found[0], tuple) else found
            # 가장 빈도 높은 값
            from collections import Counter
            rounded_vals = [round(v, 4) for v in vals]
            most_common_val = Counter(rounded_vals).most_common(1)[0][0]
            actual_val = most_common_val

            diff = abs(actual_val - default_val)
            if diff > TOLERANCE:
                tuned_props[prop_name] = (actual_val, default_val, diff)
            else:
                default_props[prop_name] = actual_val

    # Floor Contact
    for prop_name, vals in fc_results.items():
        if vals:
            actual = vals[0]
            default = HIK_DEFAULTS.get(prop_name, None)
            if default is not None:
                diff = abs(float(actual) - default)
                if diff > TOLERANCE:
                    found_in_fc[prop_name] = (float(actual), default, diff)
            else:
                found_in_fc[prop_name] = (float(actual), "N/A", 0)

    # ─── 출력: 튜닝된 값 우선 ───
    print("\n★ 디폴트에서 변경된 (의도적 튜닝) 프로퍼티:")
    if not tuned_props and not found_in_fc:
        print("  → 발견된 비-디폴트 값 없음 (혹은 파일 내 HIK 프로퍼티 미기록)")
    else:
        # 카테고리별 출력
        categories = {
            "Reach / Pull": ["ReachTranslation","ReachRotation",
                             "CtrlPullLeftHand","CtrlPullRightHand",
                             "CtrlPullLeftFoot","CtrlPullRightFoot",
                             "CtrlChestPullLeftHand","CtrlChestPullRightHand",
                             "LeftHandReachT","LeftHandReachR",
                             "RightHandReachT","RightHandReachR",
                             "LeftFootReachT","LeftFootReachR",
                             "RightFootReachT","RightFootReachR"],
            "Resist / Stiffness": ["CtrlResistHipsPosition","CtrlResistHipsOrient",
                                   "CtrlResistChestPosition","CtrlResistChestOrient",
                                   "CtrlResistLeftCollar","CtrlResistRightCollar",
                                   "CtrlResistTwist","CtrlResistCompression",
                                   "CtrlSpineStiffness","CtrlNeckStiffness"],
            "Floor Contact Geometry": list(fc_results.keys()),
            "Roll 보정": ["LeftArmRoll","RightArmRoll","LeftForeArmRoll","RightForeArmRoll",
                          "LeftUpLegRoll","RightUpLegRoll","LeftLegRoll","RightLegRoll",
                          "ExtraCollarRatio"],
            "Height Compensation": ["HipsHeightCompensation","AnkleHeightCompensation",
                                    "MassCenterCompensation"],
            "Solver / Realism": ["RealisticShoulder","ScaleCompensation",
                                 "HipsTranslationMode","MatchSource","Mirror"],
        }

        for cat_name, cat_props in categories.items():
            cat_items = []
            for p in cat_props:
                if p in tuned_props:
                    actual, default, diff = tuned_props[p]
                    cat_items.append((p, actual, default, "★ 변경됨"))
                elif p in found_in_fc:
                    actual, default, diff = found_in_fc[p]
                    cat_items.append((p, actual, default, "★ 변경됨"))
            if cat_items:
                print(f"\n  [{cat_name}]")
                for p, actual, default, flag in cat_items:
                    print(f"    {p:<35} = {actual:>10.4f}  (디폴트: {str(default):>8})  {flag}")

    # ─── 발견은 됐지만 디폴트와 같은 것 ───
    print("\n◎ 발견되었으나 디폴트값과 동일한 프로퍼티:")
    if default_props:
        for p, v in sorted(default_props.items()):
            print(f"    {p:<35} = {v:>10.4f}  (디폴트와 동일)")
    else:
        print("  → 없음")

    # ─── 파일에서 전혀 발견 안 된 것 ───
    not_found = [p for p in HIK_DEFAULTS if p not in prop_results and p not in fc_results]
    print(f"\n✗ 파일에서 발견되지 않은 프로퍼티 ({len(not_found)}개):")
    print("  (FBX 저장 시 디폴트는 생략되므로 '기록 없음 = 디폴트값 사용' 가능성 높음)")
    for p in sorted(not_found):
        print(f"    {p:<35} (디폴트: {HIK_DEFAULTS[p]})")

    # ─── Floor Contact 전체 ───
    print("\n[ Floor Contact 전체 발견값 ]")
    if fc_results:
        for p, vals in fc_results.items():
            print(f"    {p:<35} = {vals}")
    else:
        print("  → Floor Contact 프로퍼티 없음")

    # ─── 원시 매칭된 모든 HIK 값 덤프 ───
    print("\n[ 원시 발견 HIK 프로퍼티 전체 목록 ]")
    if prop_results:
        for p in sorted(prop_results.keys()):
            entries = prop_results[p]
            vals_str = ", ".join([f"{v:.4f}({tc})" for tc,v,*_ in entries] if isinstance(entries[0],tuple) else [f"{v}" for v in entries])
            print(f"    {p:<35} : {vals_str}")
    else:
        print("  → 없음")

    print("\n" + "=" * 70)
    print("완료")

if __name__ == "__main__":
    main()
