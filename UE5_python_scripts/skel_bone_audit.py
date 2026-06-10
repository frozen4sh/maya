"""
skel_bone_audit.py
------------------
OWIS Project — metahuman_base_skel 본 감사 (Dry-run 전용)
UE5 에디터 Python 콘솔에서 실행: Tools > Execute Python Script

목적:
    삭제 후보 본 목록을 출력합니다. 실제 삭제는 수행하지 않습니다.
    이 스크립트는 항상 안전하게 실행할 수 있습니다.

사용법:
    1. UE5 에디터 메뉴 > Tools > Execute Python Script
    2. 이 파일을 선택하거나 Output Log > Python 콘솔에 붙여넣기
    3. 출력된 본 목록을 확인한 뒤 skel_bone_delete_attempt.py 실행 여부 결정

수정 지점:
    MODE           — "fast": 메시 경로에 키워드 포함된 것만 우선 처리
                     "full": 전체 referencer SkeletalMesh 순회
    FAST_KEYWORDS  — fast 모드에서 우선 처리할 경로 키워드 목록
    BONE_PATTERNS  — 삭제 대상 본 이름 패턴 (대소문자 무시 매칭)
    SKELETON_PATH  — 스켈레톤 에셋 경로

[UE 5.6 API 변경 이력]
    - SkeletonModifier.set_skeleton()  → 존재하지 않음 (UE 5.6에서 제거)
    - SkeletonModifier.set_skeletal_mesh(mesh) 를 사용해야 함
    - Skeleton.get_bone_count() / get_bone_name() → Python 바인딩 없음
    - Skeleton.bone_tree (read-only Array[BoneNode]) 이 있으나,
      BoneNode 구조체가 Python 에 프로퍼티를 노출하지 않아 이름 추출 불가.
      bone_tree 는 본 수 확인에만 활용.

[v2 변경사항 — 2026-05-13]
    - find_skeletal_mesh_for_skeleton() 단일 반환 → find_all_skeletal_meshes() 전체 리스트 반환
    - get_all_bone_names() 에서 전체 메시를 순회하며 set union으로 본 이름 합산
    - MODE = "fast" / "full" 토글 추가
    - FAST_KEYWORDS 로 우선 처리 메시 필터링
    - 메시별 진행 상황 로그: [PROGRESS] N/Total mesh 처리됨, 누적 본 수: M
    - AssetRegistryData 클래스 필터: SkeletalMesh만 추출, Animation/AnimBP 제외
"""

import unreal
import re
from collections import Counter

# ============================================================
# 사용자 설정 영역 — 필요에 따라 수정하세요
# ============================================================

SKELETON_PATH = "/Game/MetaHumans/Common/BaseChar/Body/metahuman_base_skel"

# 삭제 대상 패턴 목록 (정규식, 대소문자 무시)
BONE_PATTERNS = [
    r"mem4_mvb",   # Mem4_MVB, MEM4_MVB, mem4_mvb 등
    # r"mem4_mv_b",  # 필요 시 추가
    # r"^Mem4_MVB_",  # 접두사 정확 매칭 시 ^ 사용
]

# ----------------------------------------------------------
# 모드 설정
# "fast" : FAST_KEYWORDS 에 매칭되는 메시만 처리 (빠름, 특정 멤버 타겟)
# "full" : 전체 referencer SkeletalMesh 786개 전부 순회 (느리지만 완전)
# ----------------------------------------------------------
MODE = "fast"

# fast 모드에서 우선 처리할 메시 경로 키워드 (대소문자 무시)
# "Mem4" 가 포함된 메시만 처리하고 싶으면 ["Mem4"] 로 설정
# 멤버 전체를 빠르게 훑으려면 ["Mem1", "Mem2", "Mem3", "Mem4", "Mem5"] 로 확장
FAST_KEYWORDS = ["Mem4"]

# ============================================================
# 이하 수정 불필요
# ============================================================


def load_skeleton(path):
    """스켈레톤 에셋 로드"""
    skel = unreal.load_asset(path)
    if skel is None:
        unreal.log_error(f"[AUDIT] 스켈레톤 로드 실패: {path}")
        return None
    if not isinstance(skel, unreal.Skeleton):
        unreal.log_error(f"[AUDIT] 로드된 에셋이 Skeleton 타입이 아닙니다: {type(skel)}")
        return None
    unreal.log(f"[AUDIT] 스켈레톤 로드 성공: {path}")
    return skel


def diagnose_bone_tree(skeleton):
    """
    BoneNode 구조체 첫 번째 원소에 dir() 을 출력해
    Python 에 노출된 프로퍼티를 확인합니다.
    실제 이름 추출 시도 결과도 함께 기록합니다.
    """
    try:
        bone_tree = skeleton.get_editor_property("bone_tree")
        if bone_tree is None or len(bone_tree) == 0:
            unreal.log_warning("[DIAG] bone_tree 가 비어있어 진단 불가")
            return

        node = bone_tree[0]
        unreal.log(f"[DIAG] bone_tree[0] type  : {type(node)}")
        unreal.log(f"[DIAG] bone_tree[0] repr  : {repr(node)}")
        unreal.log(f"[DIAG] bone_tree[0] dir() : {dir(node)}")

        # Python 속성 직접 접근 시도 (자주 쓰이는 후보들)
        for attr in ("name", "bone_name", "bone", "value", "fname", "display_name"):
            try:
                val = getattr(node, attr)
                unreal.log(f"[DIAG]   getattr(node, '{attr}') = {val!r}")
            except AttributeError:
                pass

        # get_editor_property 시도
        for prop in ("name", "bone_name"):
            try:
                val = node.get_editor_property(prop)
                unreal.log(f"[DIAG]   get_editor_property('{prop}') = {val!r}")
            except Exception as e:
                unreal.log(f"[DIAG]   get_editor_property('{prop}') 예외: {e}")

    except Exception as e:
        unreal.log_warning(f"[DIAG] bone_tree 진단 중 예외: {e}")


def find_all_skeletal_meshes(skeleton, mode="fast", fast_keywords=None):
    """
    AssetRegistry에서 주어진 Skeleton을 참조하는 SkeletalMesh 전체 목록을 반환.

    mode="fast" : fast_keywords 가 경로에 포함된 메시만 반환
    mode="full" : 모든 referencer SkeletalMesh 반환

    반환값: list of unreal.AssetData (아직 load_asset() 안 함 — 순회 시 개별 로드)
    SkeletalMesh 가 아닌 에셋(Animation, AnimBP 등)은 클래스 필터로 제외.
    """
    if fast_keywords is None:
        fast_keywords = []

    unreal.log(f"[AUDIT] AssetRegistry에서 Skeleton referencers 검색 중... (mode={mode})")
    ar = unreal.AssetRegistryHelpers.get_asset_registry()

    mesh_asset_data_list = []

    # ----------------------------------------------------------
    # 방법 A: get_referencers — 이 스켈레톤을 직접 참조하는 에셋 패키지 목록
    # 각 패키지를 get_assets_by_package_name() 으로 풀어서 SkeletalMesh 필터링
    # ----------------------------------------------------------
    try:
        skel_package = skeleton.get_path_name().split(".")[0]
        ref_options = unreal.AssetRegistryDependencyOptions(
            include_soft_package_references=False,
            include_hard_package_references=True,
            include_searchable_names=False,
            include_soft_management_references=False,
            include_hard_management_references=False
        )
        referencers = ar.get_referencers(skel_package, ref_options)
        unreal.log(f"[AUDIT] 전체 referencer 패키지 수: {len(referencers)}")

        skipped_non_mesh = 0
        skipped_keyword  = 0

        for ref_pkg in referencers:
            assets = ar.get_assets_by_package_name(ref_pkg)
            for asset_data in assets:
                # --------------------------------------------------
                # 클래스 필터: SkeletalMesh 만 허용
                # AssetData 단계에서 필터링하므로 load_asset() 없이 빠름
                # --------------------------------------------------
                class_path = str(asset_data.asset_class_path)
                if "SkeletalMesh" not in class_path:
                    skipped_non_mesh += 1
                    continue

                # fast 모드: 경로 키워드 필터
                if mode == "fast" and fast_keywords:
                    pkg_name = str(ref_pkg)
                    if not any(kw.lower() in pkg_name.lower() for kw in fast_keywords):
                        skipped_keyword += 1
                        continue

                mesh_asset_data_list.append(asset_data)

        unreal.log(
            f"[AUDIT] SkeletalMesh 후보: {len(mesh_asset_data_list)}개 "
            f"(비-메시 제외: {skipped_non_mesh}, 키워드 미매칭 제외: {skipped_keyword})"
        )
        return mesh_asset_data_list

    except Exception as e:
        unreal.log_warning(f"[AUDIT] get_referencers 실패: {e}")

    # ----------------------------------------------------------
    # 방법 B (폴백): 전체 SkeletalMesh 에셋을 태그로 필터
    # get_referencers 가 실패한 경우에만 사용
    # ----------------------------------------------------------
    unreal.log("[AUDIT] 방법 B(폴백): 전체 SkeletalMesh 태그 스캔으로 전환...")
    try:
        all_meshes = ar.get_assets_by_class(
            unreal.TopLevelAssetPath("/Script/Engine", "SkeletalMesh")
        )
        unreal.log(f"[AUDIT] 전체 SkeletalMesh (레지스트리): {len(all_meshes)}개")

        skipped_keyword = 0
        for mesh_data in all_meshes:
            tags = mesh_data.get_tag_value("Skeleton")
            if not (tags and "metahuman_base_skel" in str(tags)):
                continue
            if mode == "fast" and fast_keywords:
                pkg_name = str(mesh_data.package_name)
                if not any(kw.lower() in pkg_name.lower() for kw in fast_keywords):
                    skipped_keyword += 1
                    continue
            mesh_asset_data_list.append(mesh_data)

        unreal.log(
            f"[AUDIT] 방법 B 후보: {len(mesh_asset_data_list)}개 "
            f"(키워드 미매칭: {skipped_keyword})"
        )
    except Exception as e:
        unreal.log_warning(f"[AUDIT] 방법 B 실패: {e}")

    return mesh_asset_data_list


def _names_from_skeleton_modifier(mesh):
    """SkeletonModifier.set_skeletal_mesh() 경유 본 이름 추출."""
    try:
        modifier = unreal.SkeletonModifier()
        result = modifier.set_skeletal_mesh(mesh)
        names = modifier.get_all_bone_names()
        if names and len(names) > 0:
            out = []
            for n in names:
                s = str(n)
                if s and s.lower() != "none":
                    out.append(s)
            if out:
                return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] SkeletonModifier 실패 ({mesh.get_path_name()}): {e}")
    return []


def _names_from_mesh_get_bone_names(mesh):
    """SkeletalMesh.get_bone_names() — UE 5.6 신규 API."""
    try:
        if hasattr(mesh, "get_bone_names"):
            result = mesh.get_bone_names()
            if result:
                out = [str(n) for n in result if str(n).lower() != "none"]
                if out:
                    return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] mesh.get_bone_names() 실패: {e}")
    return []


def _names_from_editor_skel_lib(mesh):
    """EditorSkeletalMeshLibrary.get_bone_names() 경유."""
    try:
        lib = unreal.EditorSkeletalMeshLibrary
        if hasattr(lib, "get_bone_names"):
            result = lib.get_bone_names(mesh)
            if result:
                out = [str(n) for n in result if str(n).lower() != "none"]
                if out:
                    return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] EditorSkeletalMeshLibrary 실패: {e}")
    return []


def _names_from_single_mesh(mesh):
    """
    단일 SkeletalMesh에서 본 이름을 추출하는 통합 함수.
    방법 1(SkeletonModifier) → 2(get_bone_names) → 3(EditorLib) 순서로 시도.
    """
    names = _names_from_skeleton_modifier(mesh)
    if names:
        return names
    names = _names_from_mesh_get_bone_names(mesh)
    if names:
        return names
    names = _names_from_editor_skel_lib(mesh)
    return names


def _names_from_anim_blueprint_library(skeleton):
    """AnimationBlueprintLibrary 가 있으면 skeleton 기반 본 이름 시도."""
    try:
        lib = unreal.AnimationBlueprintLibrary
        if hasattr(lib, "get_bone_names"):
            result = lib.get_bone_names(skeleton)
            if result:
                out = [str(n) for n in result if str(n).lower() != "none"]
                if out:
                    unreal.log(f"[AUDIT] AnimationBlueprintLibrary.get_bone_names() 성공 — 본 수: {len(out)}")
                    return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] AnimationBlueprintLibrary.get_bone_names() 실패: {e}")
    return []


def _names_from_control_rig_lib(skeleton):
    """ControlRigBlueprintLibrary 또는 RigHierarchy 경유."""
    try:
        if hasattr(unreal, "ControlRigBlueprintLibrary"):
            lib = unreal.ControlRigBlueprintLibrary
            if hasattr(lib, "get_bone_names"):
                result = lib.get_bone_names(skeleton)
                if result:
                    out = [str(n) for n in result if str(n).lower() != "none"]
                    if out:
                        unreal.log(f"[AUDIT] ControlRigBlueprintLibrary.get_bone_names() 성공 — 본 수: {len(out)}")
                        return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] ControlRigBlueprintLibrary 실패: {e}")
    return []


def _names_from_anim_sequence(skeleton):
    """
    AnimSequence 트랙에서 본 이름 수집 (최후 수단).
    주의: 키프레임이 있는 본만 포함되므로 전체 목록이 아닐 수 있음.
    """
    unreal.log("[AUDIT] 방법(AnimSeq): AnimSequence 트랙에서 본 이름 추출 시도...")
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        anim_assets = ar.get_assets_by_class(
            unreal.TopLevelAssetPath("/Script/Engine", "AnimSequence")
        )
        collected = set()
        for anim_data in anim_assets[:100]:
            tags = anim_data.get_tag_value("Skeleton")
            if not (tags and "metahuman_base_skel" in str(tags)):
                continue
            anim = anim_data.get_asset()
            if not isinstance(anim, unreal.AnimSequence):
                continue
            try:
                model = anim.get_editor_property("data_model")
                if model:
                    tracks = model.get_editor_property("bone_animation_tracks")
                    for track in tracks:
                        try:
                            tname = str(track.get_editor_property("name"))
                            if tname and tname.lower() != "none":
                                collected.add(tname)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                ctrl = unreal.AnimationDataController(anim)
                if hasattr(ctrl, "get_model"):
                    model2 = ctrl.get_model()
                    if model2:
                        tracks2 = model2.get_editor_property("bone_animation_tracks")
                        for track in tracks2:
                            try:
                                tname = str(track.get_editor_property("name"))
                                if tname and tname.lower() != "none":
                                    collected.add(tname)
                            except Exception:
                                pass
            except Exception:
                pass
            if len(collected) > 200:
                break

        if collected:
            out = sorted(collected)
            unreal.log(f"[AUDIT] AnimSequence 경유 성공 — 본 수(부분): {len(out)}")
            unreal.log_warning("[AUDIT] AnimSequence 방법은 키프레임 있는 본만 반환. 전체 목록이 아닐 수 있음.")
            return out
    except Exception as e:
        unreal.log_warning(f"[AUDIT] AnimSequence 방법 실패: {e}")
    return []


def get_all_bone_names_multi_mesh(skeleton, mode="fast", fast_keywords=None):
    """
    v2 핵심 함수: referencer SkeletalMesh 전체를 순회하며 본 이름을 set union으로 합산.

    동작 순서:
      1. find_all_skeletal_meshes() 로 대상 메시 목록 확보
      2. 각 메시를 load_asset() 해서 _names_from_single_mesh() 호출
      3. 결과를 accumulated_bones (set) 에 union
      4. 진행 상황을 [PROGRESS] 로 로깅
      5. 메시에서 본을 못 얻으면 fallback: AnimBP / ControlRig / AnimSeq 시도
    """
    if fast_keywords is None:
        fast_keywords = []

    # 1. 대상 메시 목록 확보
    mesh_asset_data_list = find_all_skeletal_meshes(skeleton, mode=mode, fast_keywords=fast_keywords)

    if not mesh_asset_data_list:
        unreal.log_warning("[AUDIT] 처리할 SkeletalMesh 에셋이 없음 — fallback 방법으로 전환")
    else:
        total = len(mesh_asset_data_list)
        unreal.log(f"[AUDIT] 처리 대상 SkeletalMesh: {total}개 (mode={mode})")

    # 2. 메시 순회 + set union
    accumulated_bones = set()
    failed_meshes     = []
    processed         = 0

    for asset_data in mesh_asset_data_list:
        processed += 1
        mesh_path = str(asset_data.package_name)

        try:
            mesh = asset_data.get_asset()
            if mesh is None:
                # get_asset() 이 None 이면 load_asset() 으로 재시도
                mesh = unreal.load_asset(mesh_path)

            if mesh is None or not isinstance(mesh, unreal.SkeletalMesh):
                unreal.log_warning(f"[AUDIT] 로드 실패 또는 SkeletalMesh 아님: {mesh_path}")
                failed_meshes.append(mesh_path)
                continue

            names = _names_from_single_mesh(mesh)

            if names:
                before = len(accumulated_bones)
                accumulated_bones.update(names)
                new_count = len(accumulated_bones) - before
                # 진행 상황 로그 (10개 단위 또는 새 본이 추가될 때)
                if processed % 10 == 0 or new_count > 0:
                    unreal.log(
                        f"[PROGRESS] {processed}/{total} mesh 처리됨 | "
                        f"누적 본 수: {len(accumulated_bones)} "
                        f"(+{new_count} from {mesh_path.split('/')[-1]})"
                    )
            else:
                unreal.log_warning(f"[AUDIT] 본 이름 추출 실패 (스킵): {mesh_path}")
                failed_meshes.append(mesh_path)

        except Exception as e:
            unreal.log_warning(f"[AUDIT] 메시 처리 중 예외 ({mesh_path}): {e}")
            failed_meshes.append(mesh_path)

    # 3. 최종 진행 요약
    if mesh_asset_data_list:
        unreal.log(
            f"[AUDIT] 순회 완료: {processed}개 처리 | "
            f"성공: {processed - len(failed_meshes)} | "
            f"실패: {len(failed_meshes)} | "
            f"누적 본 수: {len(accumulated_bones)}"
        )
        if failed_meshes:
            unreal.log_warning(f"[AUDIT] 실패한 메시 목록 ({len(failed_meshes)}개):")
            for fp in failed_meshes[:20]:
                unreal.log_warning(f"  - {fp}")
            if len(failed_meshes) > 20:
                unreal.log_warning(f"  ... 외 {len(failed_meshes) - 20}개")

    # 4. 메시 순회로 본을 모았으면 반환
    if accumulated_bones:
        return sorted(accumulated_bones)

    # 5. 메시 순회 실패 → 기존 폴백 방법들
    unreal.log("[AUDIT] 메시 순회 결과 없음 — fallback 방법 시도")

    names = _names_from_anim_blueprint_library(skeleton)
    if names:
        return names

    names = _names_from_control_rig_lib(skeleton)
    if names:
        return names

    names = _names_from_anim_sequence(skeleton)
    if names:
        return names

    return []


def match_patterns(bone_name, patterns):
    """본 이름이 패턴 중 하나라도 매칭되는지 확인"""
    for pat in patterns:
        if re.search(pat, bone_name, re.IGNORECASE):
            return True
    return False


def run_audit():
    """메인 감사 실행"""
    print("=" * 70)
    print("  OWIS Skeleton Bone Audit — Dry Run  [v2]")
    print(f"  스켈레톤 : {SKELETON_PATH}")
    print(f"  패턴     : {BONE_PATTERNS}")
    print(f"  모드     : {MODE}  (fast_keywords={FAST_KEYWORDS})")
    print("=" * 70)

    # 1. 스켈레톤 로드
    skeleton = load_skeleton(SKELETON_PATH)
    if skeleton is None:
        print("[FAIL] 스켈레톤 로드 실패. 경로 및 에디터 상태 확인.")
        return

    # 2. BoneNode 진단 (한 번만) — dir() 및 프로퍼티 접근 시도
    print("\n[DIAG] BoneNode 구조체 진단 시작...")
    diagnose_bone_tree(skeleton)

    # 3. bone_tree 로 본 수 확인 (이름 추출 없이 카운트만)
    try:
        bone_tree = skeleton.get_editor_property("bone_tree")
        if bone_tree is not None:
            print(f"[INFO] skeleton.bone_tree 본 수(카운트 전용): {len(bone_tree)}")
    except Exception as e:
        print(f"[INFO] bone_tree 카운트 실패: {e}")

    # 4. 전체 본 이름 수집 — v2: 멀티 메시 순회
    print(f"\n[INFO] 본 이름 수집 시작 (mode={MODE})...")
    if MODE == "fast":
        print(f"[INFO] Fast mode: 메시 경로에 {FAST_KEYWORDS} 포함된 것만 처리")
    else:
        print("[INFO] Full mode: 전체 referencer SkeletalMesh 순회 (시간 소요 예상)")

    all_bones = get_all_bone_names_multi_mesh(
        skeleton,
        mode=MODE,
        fast_keywords=FAST_KEYWORDS
    )

    if not all_bones:
        print("[FAIL] 모든 방법으로 본 이름 수집 실패.")
        print("  가능한 원인:")
        print("  - SkeletalMesh 가 AssetRegistry 에 없거나 로드 실패")
        print("  - Fast mode 에서 FAST_KEYWORDS 가 어떤 메시 경로와도 매칭 안됨")
        print("  - SkeletonModifier API 미지원 (UE 버전 확인)")
        print("  권장 조치:")
        print("  - MODE = 'full' 로 변경 후 재시도")
        print("  - FAST_KEYWORDS 에 다른 키워드 추가 (예: ['Mem4', 'mem4'])")
        print("  - 에디터에서 Skeleton Editor 를 열고 본 트리 확인")
        return

    print(f"\n[INFO] 총 본 수 (set union 결과): {len(all_bones)}")

    # 5. prefix 통계 (전체 본 현황 파악용)
    prefix_all = Counter()
    for b in all_bones:
        prefix = b.split("_")[0] if "_" in b else b
        prefix_all[prefix] += 1
    print("\n[INFO] 전체 본 prefix 분포 (상위 20개):")
    for prefix, count in prefix_all.most_common(20):
        print(f"    {prefix}: {count}개")

    # 6. 패턴 매칭
    matched = [b for b in all_bones if match_patterns(b, BONE_PATTERNS)]

    if not matched:
        print(f"\n[RESULT] 패턴에 매칭된 본이 없습니다.")
        print("  패턴을 확인하세요:", BONE_PATTERNS)

        # Mem4 관련 본 샘플 출력 (매칭 힌트)
        print("\n[HINT] 'mem4' 포함 본 샘플 (최대 30개):")
        samples = [b for b in all_bones if re.search(r"mem4", b, re.IGNORECASE)][:30]
        if samples:
            for s in samples:
                print(f"    {s}")
        else:
            print("    (없음)")
            if MODE == "fast":
                print(f"  -> Fast mode 에서 FAST_KEYWORDS={FAST_KEYWORDS} 로 찾은 메시가")
                print("     Mem4_MVB 본을 포함하지 않을 수 있음.")
                print("  -> MODE = 'full' 로 변경 후 재시도 권장")
            print("\n[HINT] 수집된 본 첫 50개:")
            for b in all_bones[:50]:
                print(f"    {b}")
        return

    # 7. 결과 출력
    print(f"\n[RESULT] 삭제 후보 본: {len(matched)}개")
    print("-" * 70)
    for i, bone in enumerate(sorted(matched), 1):
        print(f"  [{i:3d}] {bone}")
    print("-" * 70)

    # 8. 잔여 본 통계
    remaining = [b for b in all_bones if not match_patterns(b, BONE_PATTERNS)]
    print(f"\n[INFO] 삭제 후 잔여 본 수: {len(remaining)}")

    # 9. 삭제 대상 prefix 분포
    prefix_counter = Counter()
    for b in matched:
        prefix = b.split("_")[0] if "_" in b else b
        prefix_counter[prefix] += 1
    print("\n[INFO] 삭제 대상 prefix 분포:")
    for prefix, count in prefix_counter.most_common():
        print(f"    {prefix}: {count}개")

    print("\n[DRY RUN COMPLETE] 실제 삭제는 수행되지 않았습니다.")
    print("  삭제를 진행하려면 skel_bone_delete_attempt.py 를 실행하세요.")
    print("=" * 70)


# 실행
run_audit()
