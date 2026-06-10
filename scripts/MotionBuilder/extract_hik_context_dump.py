"""
HIK 프로퍼티를 찾고, 해당 바이트 위치 앞뒤 컨텍스트를 덤프하여
어느 캐릭터/노드에 속하는지 확인.
또한 ScaleCompensation=100 의 origin 특정.
"""
import struct
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

FBX_PATH = r"D:\Outsourced\Animost\20260527\FBX-20260527T083902Z-3-001\FBX\Test_Mobu.fbx"

HIK_DEFAULTS = {
    "CtrlPullLeftHand":         100.0,
    "CtrlPullRightHand":        100.0,
    "CtrlPullLeftFoot":         100.0,
    "CtrlPullRightFoot":        100.0,
    "CtrlChestPullLeftHand":     50.0,
    "CtrlChestPullRightHand":    50.0,
    "CtrlResistLeftCollar":       0.0,
    "CtrlResistRightCollar":      0.0,
    "LeftArmRoll":               50.0,
    "RightArmRoll":              50.0,
    "LeftForeArmRoll":           50.0,
    "RightForeArmRoll":          50.0,
    "LeftUpLegRoll":             50.0,
    "RightUpLegRoll":            50.0,
    "LeftLegRoll":               50.0,
    "RightLegRoll":              50.0,
    "ExtraCollarRatio":           0.0,
    "MassCenterCompensation":     0.0,
    "ScaleCompensation":          0.0,
    "FootBackToAnkle":            0.0,
    "FootMiddleToAnkle":          0.0,
    "FootFrontToMiddle":          0.0,
    "FootInToAnkle":              0.0,
    "FootOutToAnkle":             0.0,
    "HandBackToWrist":            0.0,
    "HandMiddleToWrist":          0.0,
    "HandFrontToMiddle":          0.0,
    "HandInToWrist":              0.0,
    "HandOutToWrist":             0.0,
}

def extract_readable_ascii(data, offset, window=200):
    """offset 근처의 가독 ASCII 문자들 추출."""
    start = max(0, offset - window)
    snippet = data[start:offset + 50]
    result = []
    i = 0
    current_word = []
    while i < len(snippet):
        b = snippet[i]
        if 32 <= b < 127:
            current_word.append(chr(b))
        else:
            if len(current_word) >= 3:
                result.append("".join(current_word))
            current_word = []
        i += 1
    if len(current_word) >= 3:
        result.append("".join(current_word))
    return result

def find_parent_node_name(data, offset, lookback=2048):
    """offset 앞에서 가장 가까운 노드명(알파벳 문자열)을 찾음."""
    start = max(0, offset - lookback)
    snippet = data[start:offset]

    # 뒤에서부터 의미있는 문자열 찾기
    candidates = []
    i = len(snippet) - 1
    while i >= 0:
        if 32 <= snippet[i] < 127 and chr(snippet[i]).isalpha():
            j = i
            while j >= 0 and (32 <= snippet[j] < 127) and (chr(snippet[j]).isalnum() or chr(snippet[j]) in '_: '):
                j -= 1
            word = snippet[j+1:i+1]
            try:
                w = word.decode("ascii").strip()
                if len(w) >= 4 and any(c.isupper() for c in w):
                    candidates.append(w)
                    if len(candidates) >= 5:
                        break
            except Exception:
                pass
            i = j
        else:
            i -= 1
    return candidates

def scan_prop_with_context(data, prop_name):
    """prop_name을 찾고 각 발생 위치의 값과 컨텍스트 반환."""
    sb = prop_name.encode("ascii")
    dlen = len(data)
    results = []
    idx = 0

    while True:
        p = data.find(sb, idx)
        if p == -1:
            break

        # 앞에 길이 바이트가 있는지 확인
        valid = False
        if p > 0 and data[p-1] == len(sb):
            valid = True
        elif p >= 4:
            slen = struct.unpack_from('<I', data, p-4)[0]
            if slen == len(sb):
                valid = True

        if valid:
            after = p + len(sb)
            # 값 읽기
            window = data[after:after+100]
            val = None
            val_offset = None
            for k in range(min(len(window)-8, 60)):
                tc = window[k]
                if tc == ord('D') and k+9 <= len(window):
                    v = struct.unpack_from('<d', window, k+1)[0]
                    if abs(v) < 1e9 and v == v:
                        val = v
                        val_offset = after + k
                        break
                elif tc == ord('F') and k+5 <= len(window):
                    v = struct.unpack_from('<f', window, k+1)[0]
                    if abs(v) < 1e9 and v == v:
                        val = float(v)
                        val_offset = after + k
                        break
                elif tc == ord('I') and k+5 <= len(window):
                    v = struct.unpack_from('<i', window, k+1)[0]
                    if abs(v) < 1e7:
                        val = float(v)
                        val_offset = after + k
                        break

            # 컨텍스트: 앞 512바이트의 ASCII 단어들
            ctx_words = extract_readable_ascii(data, p, 512)
            # 특히 HIK/Character 관련 키워드 필터
            hik_words = [w for w in ctx_words if any(k in w for k in
                ["Character", "HIK", "Ctrl", "Hik", "FBX", "Model", "NodeAttribute",
                 "Optitrack", "Metahuman", "Meta", "Skeleton", "Animost"])]

            results.append({
                "offset": p,
                "val": val,
                "val_offset": val_offset,
                "ctx_hik": hik_words[-8:] if hik_words else ctx_words[-5:],
            })

        idx = p + 1

    return results

def find_all_string_occurrences(data, search_str):
    """바이너리에서 문자열의 모든 위치 반환."""
    sb = search_str.encode("ascii")
    positions = []
    idx = 0
    while True:
        p = data.find(sb, idx)
        if p == -1:
            break
        positions.append(p)
        idx = p + 1
    return positions

def read_value_at(data, offset, size=8):
    """지정 offset에서 double 읽기."""
    if offset + size <= len(data):
        return struct.unpack_from('<d', data, offset)[0]
    return None

def dump_hex_context(data, offset, before=32, after=32):
    """offset 근처 hex 덤프."""
    start = max(0, offset - before)
    end = min(len(data), offset + after)
    line = []
    ascii_line = []
    result = []
    for i, b in enumerate(data[start:end]):
        abs_pos = start + i
        if abs_pos == offset:
            line.append(f"[{b:02X}]")
        else:
            line.append(f"{b:02X}")
        ascii_line.append(chr(b) if 32 <= b < 127 else '.')

    result.append(f"  hex  : {' '.join(line)}")
    result.append(f"  ascii: {''.join(ascii_line)}")
    return "\n".join(result)

def main():
    print("=" * 70)
    print("HIK 프로퍼티 컨텍스트 상세 덤프")
    print("=" * 70)

    data = open(FBX_PATH, "rb").read()
    print(f"로드: {len(data)} bytes\n")

    # ─────────────────────────────────
    # 1. 변경된 프로퍼티들의 실제 노드 컨텍스트
    # ─────────────────────────────────
    CHANGED_PROPS = [
        "CtrlPullLeftFoot",
        "CtrlPullRightFoot",
        "CtrlChestPullLeftHand",
        "CtrlChestPullRightHand",
        "CtrlResistLeftCollar",
        "CtrlResistRightCollar",
        "LeftArmRoll",
        "RightArmRoll",
        "LeftForeArmRoll",
        "RightForeArmRoll",
        "LeftUpLegRoll",
        "RightUpLegRoll",
        "LeftLegRoll",
        "RightLegRoll",
        "ExtraCollarRatio",
        "MassCenterCompensation",
        "ScaleCompensation",
        "FootBackToAnkle",
        "FootMiddleToAnkle",
        "FootFrontToMiddle",
        "FootInToAnkle",
        "FootOutToAnkle",
        "HandBackToWrist",
        "HandMiddleToWrist",
        "HandFrontToMiddle",
        "HandInToWrist",
        "HandOutToWrist",
    ]

    print("[ 변경된 프로퍼티별 위치 및 컨텍스트 ]")
    for prop in CHANGED_PROPS:
        results = scan_prop_with_context(data, prop)
        default = HIK_DEFAULTS.get(prop, "N/A")
        print(f"\n  {prop} (default={default}):")
        if not results:
            print("    -> 발견 없음")
            continue
        for r in results:
            val = r['val']
            offset = r['offset']
            ctx = r['ctx_hik']
            is_changed = isinstance(default, float) and val is not None and abs(val - default) > 0.0001
            flag = " <-- 변경됨" if is_changed else ""
            print(f"    offset={offset:8d}  val={val!s:>12}  ctx={ctx}{flag}")

    # ─────────────────────────────────
    # 2. ScaleCompensation 특별 분석
    # ─────────────────────────────────
    print("\n\n[ ScaleCompensation 상세 분석 ]")
    results = scan_prop_with_context(data, "ScaleCompensation")
    for r in results:
        print(f"  offset={r['offset']}  val={r['val']}")
        print(f"  hex context:")
        print(dump_hex_context(data, r['offset'], 16, 20))

    # ─────────────────────────────────
    # 3. FbxCharacter 노드 근처의 모든 값 덤프
    # ─────────────────────────────────
    print("\n\n[ FbxCharacter 노드 주변 HIK 프로퍼티 집중 스캔 ]")
    char_positions = find_all_string_occurrences(data, "FbxCharacter")
    print(f"  FbxCharacter 위치: {char_positions}")

    for cp in char_positions:
        print(f"\n  --- FbxCharacter @ offset {cp} ---")
        # 이후 32KB 내에서 모든 HIK 관련 값 스캔
        region = data[cp:cp+32768]
        region_offset = cp

        for prop in CHANGED_PROPS:
            sb = prop.encode("ascii")
            j = 0
            while True:
                pidx = region.find(sb, j)
                if pidx == -1:
                    break
                after = pidx + len(sb)
                for k in range(min(len(region)-after, 80)):
                    tc = region[after+k]
                    if tc == ord('D') and after+k+9 <= len(region):
                        v = struct.unpack_from('<d', region, after+k+1)[0]
                        if abs(v) < 1e9 and v == v:
                            default = HIK_DEFAULTS.get(prop, None)
                            is_changed = default is not None and abs(v - default) > 0.0001
                            flag = " <-- 변경됨" if is_changed else ""
                            print(f"    {prop:<35} = {v:>10.4f} (rel_offset={pidx}){flag}")
                            break
                    elif tc == ord('I') and after+k+5 <= len(region):
                        v = float(struct.unpack_from('<i', region, after+k+1)[0])
                        if abs(v) < 1e7:
                            default = HIK_DEFAULTS.get(prop, None)
                            is_changed = default is not None and abs(v - default) > 0.0001
                            flag = " <-- 변경됨" if is_changed else ""
                            print(f"    {prop:<35} = {v:>10.4f} (rel_offset={pidx}){flag}")
                            break
                j = pidx + 1

    # ─────────────────────────────────
    # 4. "Character" 노드명들 근처 스캔
    # ─────────────────────────────────
    print("\n\n[ 'Character' 노드 이름 전체 목록 (컨텍스트 추출) ]")
    char_all = find_all_string_occurrences(data, "Character")
    print(f"  총 {len(char_all)}개 발견")

    # 각 위치에서 노드명 추정
    seen_names = set()
    for cp in char_all[:80]:
        # 이 위치가 노드 이름 필드인지 확인
        # FBX 노드: name_len(u8) + name + ...
        if cp > 0 and data[cp-1] == 9:  # len("Character") = 9
            # 앞 32바이트 스캔하여 노드 전체 이름 확인
            prev = data[max(0,cp-64):cp-1]
            # 직후에 model 타입이나 UID 있을 수 있음
            after_bytes = data[cp+9:cp+200]

            # 노드 전체 이름 = "Character\x00\x01ModelName" 패턴 찾기
            if b"\x00\x01" in after_bytes[:30]:
                ni = after_bytes.find(b"\x00\x01")
                subname_start = ni + 2
                subname_end = after_bytes.find(b"\x00", subname_start, subname_start+64)
                if subname_end > subname_start:
                    try:
                        full_name = after_bytes[subname_start:subname_end].decode("ascii", errors="replace")
                        if full_name not in seen_names:
                            seen_names.add(full_name)
                            print(f"    offset={cp}: Character::{full_name}")
                    except Exception:
                        pass

    print("\n완료")

if __name__ == "__main__":
    main()
