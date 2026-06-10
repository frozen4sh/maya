"""
Roll 값의 다중 레이어 구조를 분석.
FbxCharacter 노드 내부에서 rel_offset 기준으로 어느 블록인지 확인.
"""
import struct
import os
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

FBX_PATH = r"D:\Outsourced\Animost\20260527\FBX-20260527T083902Z-3-001\FBX\Test_Mobu.fbx"

def extract_ascii_words_around(data, offset, before=256, after=64, min_len=5):
    start = max(0, offset - before)
    end = min(len(data), offset + after)
    snippet = data[start:end]
    words = []
    current = []
    for b in snippet:
        if 32 <= b < 127 and chr(b) not in '\x00':
            current.append(chr(b))
        else:
            w = "".join(current).strip()
            if len(w) >= min_len and any(c.isupper() for c in w):
                words.append(w)
            current = []
    if current:
        w = "".join(current).strip()
        if len(w) >= min_len:
            words.append(w)
    return words

def find_roll_block_label(data, abs_offset, block_start, lookback=500):
    """Roll 값 앞에서 해당 블록의 레이블 추정."""
    start = max(block_start, abs_offset - lookback)
    snippet = data[start:abs_offset]

    # 특징적 레이블 찾기
    labels = []
    for kw in [b"ControlSet", b"Effector", b"RollMode", b"Roll", b"Spine", b"Arm", b"Leg"]:
        idx = snippet.rfind(kw)
        if idx != -1:
            # 해당 위치에서 전체 단어 읽기
            j = idx
            while j < len(snippet) and (32 <= snippet[j] < 127):
                j += 1
            try:
                word = snippet[idx:j].decode("ascii", errors="replace")
                labels.append(word)
            except Exception:
                pass
    return labels

def scan_roll_in_fbx_char_node(data):
    """FbxCharacter 노드 내부의 Roll 관련 모든 프로퍼티를 오프셋과 함께 덤프."""
    # FbxCharacter 위치
    char_pos = data.find(b"FbxCharacter")
    if char_pos == -1:
        print("FbxCharacter 노드 없음")
        return

    print(f"FbxCharacter 노드 시작: offset {char_pos}")
    print(f"32KB 윈도우 내 Roll 관련 프로퍼티 분석:")

    region = data[char_pos:char_pos+32768]

    # Roll 프로퍼티 목록
    roll_props = [
        "LeftArmRoll", "RightArmRoll",
        "LeftForeArmRoll", "RightForeArmRoll",
        "LeftUpLegRoll", "RightUpLegRoll",
        "LeftLegRoll", "RightLegRoll",
        "LeftArmRollMode", "RightArmRollMode",
        "LeftForeArmRollMode", "RightForeArmRollMode",
        "LeftUpLegRollMode", "RightUpLegRollMode",
        "LeftLegRollMode", "RightLegRollMode",
    ]

    all_hits = []
    for prop in roll_props:
        sb = prop.encode("ascii")
        j = 0
        while True:
            pidx = region.find(sb, j)
            if pidx == -1:
                break

            after = pidx + len(sb)
            val = None
            val_type = None
            for k in range(min(len(region)-after, 80)):
                tc = region[after+k]
                if tc == ord('D') and after+k+9 <= len(region):
                    v = struct.unpack_from('<d', region, after+k+1)[0]
                    if abs(v) < 1e9 and v == v:
                        val = v
                        val_type = 'D'
                        break
                elif tc == ord('I') and after+k+5 <= len(region):
                    v = float(struct.unpack_from('<i', region, after+k+1)[0])
                    if abs(v) < 1e7:
                        val = v
                        val_type = 'I'
                        break

            all_hits.append({
                "prop": prop,
                "rel_offset": pidx,
                "val": val,
                "val_type": val_type,
            })
            j = pidx + 1

    # rel_offset 기준 정렬
    all_hits.sort(key=lambda x: x["rel_offset"])

    print("\n  rel_offset 순서로 정렬된 Roll 프로퍼티:")
    print(f"  {'rel_offset':>10}  {'prop':<30}  {'val':>10}  type")
    print("  " + "-" * 65)

    # 블록 그룹 탐지 (rel_offset의 점프로 구분)
    prev_offset = 0
    block_num = 1
    for h in all_hits:
        if h["rel_offset"] - prev_offset > 300 and prev_offset > 0:
            print(f"  {'--- 블록':>10}  {block_num} 끝 / 블록 {block_num+1} 시작 (gap={h['rel_offset']-prev_offset}) ---")
            block_num += 1
        flag = ""
        val = h['val']
        if val is not None:
            if "Roll" in h["prop"] and "Mode" not in h["prop"]:
                if abs(val) < 1.0:
                    flag = " [전체_0% = 롤 비활성]"
                elif abs(val - 40) < 1.0:
                    flag = " [40% 설정]"
                elif abs(val - 50) < 1.0:
                    flag = " [디폴트 50%]"
                elif abs(val - 60) < 1.0:
                    flag = " [60% 설정]"
                elif abs(val - 80) < 1.0:
                    flag = " [80% 설정]"
                elif abs(val - 100) < 1.0:
                    flag = " [100% 설정]"
        print(f"  {h['rel_offset']:>10}  {h['prop']:<30}  {str(val):>10}  {h['val_type']}{flag}")
        prev_offset = h["rel_offset"]

    print(f"\n  총 {len(all_hits)}개 Roll 프로퍼티 엔트리 (블록 {block_num}개)")

    # 블록별 요약
    print("\n  [블록 요약 해석]")
    print("  블록 1 (rel_offset ~4000-5300): HIK 캐릭터 현재 세팅")
    print("  블록 2 (rel_offset ~5400-6600): ControlSet/Effector 관련 세팅")
    print("  블록 3+ (rel_offset >6600): 애니메이션 레이어 또는 다른 캐릭터 노드")

def main():
    print("=" * 70)
    print("Roll 레이어 구조 분석")
    print("=" * 70)

    data = open(FBX_PATH, "rb").read()
    print(f"로드: {len(data)} bytes\n")

    scan_roll_in_fbx_char_node(data)

    # 별도: 각 Roll 값의 실제 의미 요약
    print("\n\n[ 최종 확정값 (FbxCharacter 직접 세팅, rel_offset 가장 작은 값) ]")
    # 이미 첫 스크립트에서 확인: 가장 첫 번째 등장값 = 현재 세팅
    # rel_offset 기준 블록1 = HIK 캐릭터 정의값
    confirmed = {
        "LeftArmRoll":     0.0,
        "RightArmRoll":    0.0,
        "LeftForeArmRoll": 0.0,
        "RightForeArmRoll":0.0,
        "LeftUpLegRoll":   0.0,
        "RightUpLegRoll":  0.0,
        "LeftLegRoll":     60.0,
        "RightLegRoll":    60.0,
    }
    defaults = {
        "LeftArmRoll":     50.0,
        "RightArmRoll":    50.0,
        "LeftForeArmRoll": 50.0,
        "RightForeArmRoll":50.0,
        "LeftUpLegRoll":   50.0,
        "RightUpLegRoll":  50.0,
        "LeftLegRoll":     50.0,
        "RightLegRoll":    50.0,
    }
    for p, v in confirmed.items():
        d = defaults[p]
        diff = v - d
        print(f"  {p:<25} = {v:>5.1f}%  (디폴트 {d:.1f}%, 차이 {diff:+.1f}%)")

    print("\n  해석:")
    print("  - 팔/대퇴부 Roll 0%: 상체 회전이 팔/허벅지 롤본에 전달되지 않음")
    print("    → Optitrack 마커 기반 데이터의 롤 노이즈를 완전 차단하는 선택")
    print("  - 정강이 Roll 60%: 발목 비틀림의 60%를 정강이 롤에 배분")
    print("    → 디폴트(50%)보다 상향, 무릎-발목 연결 자연스럽게 하기 위한 조정")

if __name__ == "__main__":
    main()
