"""
skel_bone_delete_attempt.py
----------------------------
OWIS Project — metahuman_base_skel 본 삭제 시도
UE5 에디터 Python 콘솔에서 실행: Tools > Execute Python Script

주의사항 (반드시 읽으세요):
    UE5.4~5.6 Python API에는 스켈레톤 본을 직접 삭제하는 공식 메서드가
    노출되어 있지 않습니다 (C++ 내부 USkeleton::RemoveBonesFromSkeleton()은
    존재하지만 Python 바인딩 미제공).

    이 스크립트는:
    1. P4 체크아웃 (source_control API)
    2. SkeletonModifier로 삭제 시도 (UE5.4+ 실험적)
    3. 실패 시 명확한 fallback 안내

    실제 삭제가 필요하다면 skel_fbx_reimport_prep.py 를 사용하세요.

설정:
    DRY_RUN = True  → 삭제 없이 대상 목록만 출력 (기본값, 안전)
    DRY_RUN = False → 실제 삭제 시도
    CHILD_POLICY     → "delete" (자식도 삭제) / "reparent" (부모로 연결)
"""

import unreal
import re

# ============================================================
# 사용자 설정 영역 — 실행 전 반드시 확인
# ============================================================

SKELETON_PATH = "/Game/MetaHumans/Common/BaseChar/Body/metahuman_base_skel"

BONE_PATTERNS = [
    r"mem4_mvb",   # Mem4_MVB, MEM4_MVB, mem4_mvb 등 대소문자 무시
    # r"^Mem4_MVB_Skirt",  # 특정 서브트리만 삭제 시
]

# True = Dry-run (안전, 삭제 없음) / False = 실제 삭제 시도
DRY_RUN = True

# 자식 본 처리 정책
# "delete"   → 삭제 대상 본의 자식 본도 모두 재귀 삭제
# "reparent" → 자식 본을 삭제 대상의 부모 본으로 reparent 후 삭제
CHILD_POLICY = "delete"

# P4 체크아웃 시도 여부
USE_SOURCE_CONTROL = True

# ============================================================
# 이하 수정 불필요
# ============================================================

LOG_PREFIX = "[SKEL_DELETE]"


def log(msg):
    print(f"{LOG_PREFIX} {msg}")
    unreal.log(f"{LOG_PREFIX} {msg}")


def log_warn(msg):
    print(f"{LOG_PREFIX} [WARNING] {msg}")
    unreal.log_warning(f"{LOG_PREFIX} {msg}")


def log_error(msg):
    print(f"{LOG_PREFIX} [ERROR] {msg}")
    unreal.log_error(f"{LOG_PREFIX} {msg}")


# ------------------------------------------------------------------
# 1. P4 체크아웃
# ------------------------------------------------------------------

def checkout_asset(asset_path):
    """
    UE5 Source Control API를 통해 에셋 체크아웃
    binary+l (Exclusive Lock) 파일이므로 다른 사용자가 체크아웃 중이면 실패
    """
    if not USE_SOURCE_CONTROL:
        log("Source Control 건너뜀 (USE_SOURCE_CONTROL=False)")
        return True

    log(f"P4 체크아웃 시도: {asset_path}")

    # Source Control Provider 확인
    sc_provider = unreal.SourceControl.get_provider()
    if sc_provider is None:
        log_warn("Source Control Provider 없음 — 체크아웃 건너뜀")
        return True

    # 에셋의 실제 파일 경로 조회
    package_filename = unreal.PackageTools.filename_from_package_name(asset_path)
    if not package_filename:
        log_warn(f"패키지 파일 경로 조회 실패: {asset_path}")
        return False

    log(f"실제 파일: {package_filename}")

    # 체크아웃 실행
    result = unreal.SourceControlHelpers.checkout_or_mark_for_add(package_filename)
    if result:
        log("체크아웃 성공")
        return True
    else:
        # 이미 체크아웃된 경우도 확인
        status = unreal.SourceControlHelpers.query_file_state(package_filename)
        if status and status.is_checked_out:
            log("이미 체크아웃 상태 — 진행 가능")
            return True
        log_error("체크아웃 실패. 다른 사용자가 Exclusive Lock 중일 수 있습니다.")
        log_error("  p4 opened //owis/... 로 Lock 보유자 확인 필요")
        return False


# ------------------------------------------------------------------
# 2. 본 목록 수집
# ------------------------------------------------------------------

def get_skeleton_modifier(skeleton):
    """SkeletonModifier 인스턴스 생성 (UE5.4+)"""
    try:
        modifier = unreal.SkeletonModifier()
        modifier.set_skeleton(skeleton)
        return modifier
    except Exception as e:
        log_warn(f"SkeletonModifier 생성 실패: {e}")
        return None


def collect_all_bones(modifier):
    """
    SkeletonModifier.get_bones() 로 전체 본 정보 수집
    반환: { bone_name_str: parent_name_str } 딕셔너리
    """
    bone_hierarchy = {}
    try:
        bones = modifier.get_bones()
        for b in bones:
            # UE5.4에서 get_bones()는 FBoneNode 배열 또는 Name 배열을 반환
            # 버전에 따라 타입이 다를 수 있음
            if hasattr(b, "get_editor_property"):
                name = str(b.get_editor_property("name"))
            else:
                name = str(b)

            try:
                parent = modifier.get_parent_bone(unreal.Name(name))
                parent_str = str(parent) if parent else ""
            except Exception:
                parent_str = ""

            bone_hierarchy[name] = parent_str

        log(f"본 목록 수집 완료: {len(bone_hierarchy)}개")
    except Exception as e:
        log_error(f"get_bones() 실패: {e}")

    return bone_hierarchy


# ------------------------------------------------------------------
# 3. 삭제 대상 탐색 (재귀적 자식 포함)
# ------------------------------------------------------------------

def match_patterns(bone_name, patterns):
    for pat in patterns:
        if re.search(pat, bone_name, re.IGNORECASE):
            return True
    return False


def get_recursive_children(bone_name, bone_hierarchy):
    """bone_hierarchy에서 특정 본의 모든 하위 자식(재귀) 반환"""
    children = []
    direct_children = [b for b, parent in bone_hierarchy.items() if parent == bone_name]
    for child in direct_children:
        children.append(child)
        children.extend(get_recursive_children(child, bone_hierarchy))
    return children


def resolve_delete_set(bone_hierarchy, patterns, child_policy):
    """
    패턴 매칭된 본 + child_policy에 따라 최종 삭제 집합 결정
    반환: (delete_set, reparent_dict)
          delete_set    — 실제 삭제할 본 이름 집합
          reparent_dict — {bone_name: new_parent} (REPARENT 정책일 때만 사용)
    """
    # 1차 패턴 매칭
    primary_targets = {b for b in bone_hierarchy if match_patterns(b, patterns)}

    delete_set = set(primary_targets)
    reparent_dict = {}

    for target in primary_targets:
        children = get_recursive_children(target, bone_hierarchy)
        if child_policy == "delete":
            delete_set.update(children)
        elif child_policy == "reparent":
            parent_of_target = bone_hierarchy.get(target, "")
            for child in children:
                # 직접 자식만 reparent (패턴 미매칭인 경우만)
                if child not in primary_targets:
                    reparent_dict[child] = parent_of_target
                    # 자식 자신은 삭제 집합에 넣지 않음
                    # (reparent 후 계속 존재)

    return delete_set, reparent_dict


# ------------------------------------------------------------------
# 4. 실제 삭제 수행 (SkeletonModifier)
# ------------------------------------------------------------------

def attempt_delete_bones(modifier, delete_set, reparent_dict, bone_hierarchy):
    """
    SkeletonModifier를 통한 삭제 시도
    UE5.4+ remove_bone() 메서드 존재 여부 확인 후 실행
    """
    results = {"success": [], "failed": [], "not_found": []}

    # reparent 먼저 수행 (삭제 전에)
    if reparent_dict:
        log(f"Reparent 대상: {len(reparent_dict)}개")
        for bone, new_parent in reparent_dict.items():
            try:
                modifier.set_bone_parent(unreal.Name(bone), unreal.Name(new_parent))
                log(f"  REPARENT: {bone} -> {new_parent}")
            except Exception as e:
                log_warn(f"  REPARENT 실패: {bone} -> {new_parent}: {e}")

    # SkeletonModifier에 remove_bone 메서드 존재 확인
    has_remove_bone = hasattr(modifier, "remove_bone")
    if not has_remove_bone:
        log_error("=" * 60)
        log_error("SkeletonModifier.remove_bone() 이 이 버전 UE5에서")
        log_error("Python 레이어에 노출되어 있지 않습니다.")
        log_error("")
        log_error("이것은 UE5.4~5.6 공식 Python 바인딩의 제약입니다.")
        log_error("실제 삭제를 위해 아래 방법 중 하나를 사용하세요:")
        log_error("")
        log_error("  [방법 A] FBX 재임포트 (권장)")
        log_error("    1. 현재 스켈레탈 메시 FBX 내보내기")
        log_error("    2. 외부 툴(Maya/Blender)에서 Mem4_MVB 본 제거")
        log_error("    3. skel_fbx_reimport_prep.py 로 자동 재임포트")
        log_error("")
        log_error("  [방법 B] Skeleton Editor 수동 작업")
        log_error("    1. Content Browser에서 metahuman_base_skel 더블클릭")
        log_error("    2. Skeleton Tree에서 Mem4_MVB 본 우클릭")
        log_error("    3. Delete (자식 포함 선택 가능)")
        log_error("")
        log_error("  [방법 C] C++ Editor Plugin 제작")
        log_error("    USkeleton::RemoveBonesFromSkeleton() 직접 호출")
        log_error("=" * 60)

        return results

    # remove_bone 존재하는 경우 (미래 버전 또는 커스텀 플러그인)
    log(f"remove_bone() 발견 — 삭제 시작: {len(delete_set)}개")

    # 삭제 순서: 자식 본부터 (부모 먼저 삭제하면 오류)
    # 계층 깊이 기준 정렬 (깊은 것부터)
    def depth_of(bone):
        d = 0
        current = bone
        seen = set()
        while current in bone_hierarchy and current not in seen:
            seen.add(current)
            current = bone_hierarchy[current]
            d += 1
        return d

    sorted_delete = sorted(delete_set, key=depth_of, reverse=True)

    for bone in sorted_delete:
        try:
            modifier.remove_bone(unreal.Name(bone))
            results["success"].append(bone)
            log(f"  DELETED: {bone}")
        except Exception as e:
            results["failed"].append(bone)
            log_warn(f"  FAILED:  {bone} ({e})")

    return results


# ------------------------------------------------------------------
# 5. 저장
# ------------------------------------------------------------------

def save_skeleton(skeleton_path):
    """수정된 스켈레톤 저장"""
    try:
        package = unreal.load_package(skeleton_path)
        if package:
            unreal.PackageTools.save_package(package, only_if_is_dirty=False)
            log(f"저장 완료: {skeleton_path}")
            return True
    except Exception as e:
        log_warn(f"PackageTools.save_package 실패: {e}")

    # Fallback: EditorAssetLibrary
    try:
        unreal.EditorAssetLibrary.save_asset(skeleton_path)
        log(f"저장 완료 (EditorAssetLibrary): {skeleton_path}")
        return True
    except Exception as e:
        log_error(f"저장 실패: {e}")
        return False


# ------------------------------------------------------------------
# 메인
# ------------------------------------------------------------------

def main():
    print("=" * 70)
    print("  OWIS Skeleton Bone Delete")
    print(f"  스켈레톤: {SKELETON_PATH}")
    print(f"  패턴: {BONE_PATTERNS}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print(f"  CHILD_POLICY: {CHILD_POLICY}")
    print("=" * 70)

    # 1. 스켈레톤 로드
    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None or not isinstance(skeleton, unreal.Skeleton):
        log_error(f"스켈레톤 로드 실패: {SKELETON_PATH}")
        return

    # 2. SkeletonModifier 초기화
    modifier = get_skeleton_modifier(skeleton)
    if modifier is None:
        log_error("SkeletonModifier 초기화 실패 — UE5.4 이상에서 실행하세요.")
        return

    # 3. 전체 본 계층 수집
    bone_hierarchy = collect_all_bones(modifier)
    if not bone_hierarchy:
        log_error("본 정보 수집 실패")
        return

    # 4. 삭제 집합 결정
    delete_set, reparent_dict = resolve_delete_set(bone_hierarchy, BONE_PATTERNS, CHILD_POLICY)

    if not delete_set:
        log("삭제 대상 본이 없습니다. 패턴을 확인하세요.")
        log(f"패턴: {BONE_PATTERNS}")
        # 힌트: 유사한 본 이름 샘플
        samples = [b for b in bone_hierarchy if re.search(r"mem4", b, re.IGNORECASE)][:20]
        if samples:
            log("'mem4' 포함 본 샘플:")
            for s in samples:
                log(f"    {s}")
        return

    # 5. 삭제 대상 출력
    print(f"\n[DELETE TARGETS] {len(delete_set)}개:")
    for i, bone in enumerate(sorted(delete_set), 1):
        print(f"  [{i:3d}] {bone}")

    if reparent_dict:
        print(f"\n[REPARENT] {len(reparent_dict)}개:")
        for bone, new_parent in sorted(reparent_dict.items()):
            print(f"    {bone} -> {new_parent}")

    print(f"\n  잔여 본 수: {len(bone_hierarchy) - len(delete_set)}")

    # 6. Dry-run이면 여기서 종료
    if DRY_RUN:
        print("\n[DRY RUN] 실제 삭제 없이 종료합니다.")
        print("  삭제를 진행하려면 DRY_RUN = False 로 변경 후 재실행하세요.")
        return

    # 7. P4 체크아웃
    if not checkout_asset(SKELETON_PATH):
        log_error("체크아웃 실패 — 작업 중단")
        return

    # 8. 삭제 수행
    print("\n[DELETING...]")
    results = attempt_delete_bones(modifier, delete_set, reparent_dict, bone_hierarchy)

    # 9. 결과 요약
    print("\n[RESULT SUMMARY]")
    print(f"  성공: {len(results['success'])}개")
    print(f"  실패: {len(results['failed'])}개")
    if results["failed"]:
        for b in results["failed"]:
            print(f"    FAILED: {b}")

    # 10. 성공이 있으면 저장
    if results["success"]:
        print("\n[SAVING...]")
        save_skeleton(SKELETON_PATH)
    else:
        log_warn("삭제된 본이 없어 저장을 건너뜁니다.")

    print("\n[DONE]")
    print("=" * 70)


main()
