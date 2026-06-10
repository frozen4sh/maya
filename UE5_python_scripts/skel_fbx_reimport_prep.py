"""
skel_fbx_reimport_prep.py
--------------------------
OWIS Project — FBX 재임포트를 통한 스켈레톤 본 제거 자동화 보조

개요:
    Python API로 스켈레톤 본을 직접 삭제할 수 없는 경우의 현실적 우회 방안.

    워크플로우:
        [외부 DCC] FBX에서 Mem4_MVB 본 제거 (Maya/Blender)
            ↓
        [이 스크립트] UE5 Python으로 자동 재임포트
            ↓
        UE5가 스켈레톤을 재구성 → 불필요한 본 자연히 제거

기능:
    1. 대상 스켈레탈 메시 목록 출력 (어떤 메시를 재임포트해야 하는지 안내)
    2. FBX 경로를 지정하면 자동 재임포트 실행
    3. 재임포트 후 본 목록 변화 확인

주의:
    - 재임포트 전 반드시 P4 체크아웃 필요 (binary+l)
    - 재임포트 시 LOD 설정, 머티리얼 슬롯 이름이 유지되는지 확인
    - metahuman_base_skel에 연결된 모든 메시가 영향받을 수 있음

사용법:
    1. REIMPORT_CONFIGS 에 {mesh_path, fbx_path} 쌍을 설정
    2. DRY_RUN = True 로 먼저 확인
    3. DRY_RUN = False 로 실제 재임포트
"""

import unreal
import os
import re

# ============================================================
# 사용자 설정
# ============================================================

SKELETON_PATH = "/Game/MetaHumans/Common/BaseChar/Body/metahuman_base_skel"

# 삭제 대상 본 패턴 (확인용)
BONE_PATTERNS = [
    r"mem4_mvb",
]

DRY_RUN = True

# 재임포트 설정: 메시별 FBX 경로 지정
# FBX 경로는 외부 DCC에서 Mem4_MVB 본 제거 후 내보낸 파일
REIMPORT_CONFIGS = [
    # {
    #     "mesh_path": "/Game/OWIS/CHARACTER/Mem4/SK_Mem4_Body",
    #     "fbx_path":  "C:/justin_owis/Export/Mem4_Body_cleaned.fbx",
    # },
    # 필요한 메시를 추가...
]

# ============================================================
# 이하 수정 불필요
# ============================================================

LOG_PREFIX = "[REIMPORT]"


def log(msg):
    print(f"{LOG_PREFIX} {msg}")
    unreal.log(f"{LOG_PREFIX} {msg}")


def log_warn(msg):
    print(f"{LOG_PREFIX} [WARNING] {msg}")
    unreal.log_warning(f"{LOG_PREFIX} {msg}")


def log_error(msg):
    print(f"{LOG_PREFIX} [ERROR] {msg}")
    unreal.log_error(f"{LOG_PREFIX} {msg}")


def find_meshes_using_skeleton(skeleton_path):
    """지정된 스켈레톤을 사용하는 모든 SkeletalMesh 찾기"""
    skeleton = unreal.load_asset(skeleton_path)
    if skeleton is None:
        log_error(f"스켈레톤 로드 실패: {skeleton_path}")
        return []

    log("스켈레톤 연결 메시 탐색 중...")

    registry = unreal.AssetRegistryHelpers.get_asset_registry()

    # SkeletalMesh 전체 목록에서 필터링
    filter_obj = unreal.ARFilter(
        class_names=["SkeletalMesh"],
        recursive_classes=True,
        recursive_paths=True,
        package_paths=["/Game"]
    )

    all_assets = registry.get_assets(filter_obj)
    matched_meshes = []

    with unreal.ScopedSlowTask(len(all_assets), "스켈레탈 메시 검색 중...") as task:
        task.make_dialog(True)
        for asset_data in all_assets:
            if task.should_cancel():
                break
            task.enter_progress_frame(1)

            try:
                mesh = asset_data.get_asset()
                if isinstance(mesh, unreal.SkeletalMesh):
                    mesh_skel = mesh.get_editor_property("skeleton")
                    if mesh_skel and str(mesh_skel.get_path_name()).split(".")[0] == skeleton_path:
                        matched_meshes.append(str(asset_data.package_name))
            except Exception:
                pass

    return matched_meshes


def get_bone_names_from_modifier(skeleton):
    """SkeletonModifier로 현재 본 목록 수집"""
    try:
        modifier = unreal.SkeletonModifier()
        modifier.set_skeleton(skeleton)
        bones = modifier.get_bones()
        names = []
        for b in bones:
            name = str(b.get_editor_property("name") if hasattr(b, "get_editor_property") else b)
            names.append(name)
        return names
    except Exception as e:
        log_warn(f"본 목록 수집 실패: {e}")
        return []


def checkout_files_for_reimport(mesh_paths):
    """재임포트 대상 파일들 P4 체크아웃"""
    sc_provider = unreal.SourceControl.get_provider()
    if sc_provider is None:
        log_warn("Source Control 없음 — 체크아웃 건너뜀")
        return True

    all_ok = True
    for mesh_path in mesh_paths:
        package_file = unreal.PackageTools.filename_from_package_name(mesh_path)
        result = unreal.SourceControlHelpers.checkout_or_mark_for_add(package_file)
        if result:
            log(f"  체크아웃 OK: {mesh_path}")
        else:
            log_error(f"  체크아웃 실패: {mesh_path}")
            all_ok = False

    return all_ok


def reimport_mesh_from_fbx(mesh_path, fbx_path):
    """
    지정 FBX로 SkeletalMesh 재임포트
    FBX ImportTask 를 사용한 자동화
    """
    if not os.path.exists(fbx_path):
        log_error(f"FBX 파일 없음: {fbx_path}")
        return False

    mesh = unreal.load_asset(mesh_path)
    if mesh is None or not isinstance(mesh, unreal.SkeletalMesh):
        log_error(f"메시 로드 실패: {mesh_path}")
        return False

    log(f"재임포트 시작: {mesh_path}")
    log(f"  소스 FBX: {fbx_path}")

    # ImportTask 구성
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", fbx_path)
    task.set_editor_property("destination_path", os.path.dirname(mesh_path))
    task.set_editor_property("destination_name", os.path.basename(mesh_path))
    task.set_editor_property("replace_existing", True)
    task.set_editor_property("automated", True)
    task.set_editor_property("save", False)  # 저장은 나중에 수동으로

    # FBX Import Options
    options = unreal.FbxImportUI()
    options.set_editor_property("import_mesh", True)
    options.set_editor_property("import_animations", False)
    options.set_editor_property("import_as_skeletal", True)
    options.set_editor_property("create_physics_asset", False)

    skel_options = unreal.FbxSkeletalMeshImportData()
    skel_options.set_editor_property("import_morph_targets", True)
    skel_options.set_editor_property("use_t0_as_ref_pose", True)
    skel_options.set_editor_property("preserve_smoothing_groups", True)
    # 기존 스켈레톤 유지 (본 삭제를 위해 False로 설정)
    skel_options.set_editor_property("update_skeleton_reference_pose", True)

    options.set_editor_property("skeletal_mesh_import_data", skel_options)
    options.set_editor_property("skeleton", unreal.load_asset(SKELETON_PATH))

    task.set_editor_property("options", options)

    # 임포트 실행
    tools = unreal.AssetToolsHelpers.get_asset_tools()
    tools.import_asset_tasks([task])

    imported = task.get_editor_property("imported_object_paths")
    if imported:
        log(f"  재임포트 성공: {imported}")
        return True
    else:
        log_error(f"  재임포트 실패 (결과 없음)")
        return False


def print_workflow_guide():
    """FBX 기반 본 제거 워크플로우 안내"""
    print("\n" + "=" * 70)
    print("  FBX 재임포트 워크플로우 안내")
    print("=" * 70)
    print("""
[단계 1] 현재 스켈레탈 메시 FBX 내보내기
  - UE5 에디터 > Content Browser > SK_Mem4_XXX 우클릭
  - Asset Actions > Export
  - FBX 형식으로 내보내기
  - 경로: C:\\justin_owis\\Export\\Mem4_original.fbx

[단계 2] Maya 또는 Blender에서 본 제거
  Maya:
    import maya.cmds as cmds
    # Mem4_MVB 패턴 본 선택 후 삭제
    bones_to_delete = [j for j in cmds.ls(type='joint')
                       if 'Mem4_MVB' in j or 'MEM4_MVB' in j]
    for b in bones_to_delete:
        cmds.delete(b)  # 자식 포함 삭제됨
    # FBX 내보내기
    cmds.FBXExport('-f', 'C:/justin_owis/Export/Mem4_cleaned.fbx', '-s')

  Blender (Python):
    import bpy
    armature = bpy.data.objects['Armature']
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    bones_to_remove = [b for b in armature.data.edit_bones
                       if 'Mem4_MVB' in b.name or 'MEM4_MVB' in b.name]
    for b in bones_to_remove:
        armature.data.edit_bones.remove(b)
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.export_scene.fbx(filepath='C:/justin_owis/Export/Mem4_cleaned.fbx')

[단계 3] 이 스크립트로 자동 재임포트
  - REIMPORT_CONFIGS 에 mesh_path / fbx_path 입력
  - DRY_RUN = False 설정
  - 재실행

[단계 4] 검증
  - 재임포트 후 Skeleton Editor에서 본 트리 확인
  - Mem4_MVB 관련 본이 제거됐는지 확인
  - ABP 컴파일 오류 없는지 확인
""")
    print("=" * 70)


def main():
    print("=" * 70)
    print("  OWIS FBX Reimport Prep")
    print(f"  스켈레톤: {SKELETON_PATH}")
    print(f"  DRY_RUN: {DRY_RUN}")
    print("=" * 70)

    skeleton = unreal.load_asset(SKELETON_PATH)
    if skeleton is None:
        log_error("스켈레톤 로드 실패")
        return

    # 1. 현재 본 목록에서 삭제 대상 확인
    bone_names = get_bone_names_from_modifier(skeleton)
    target_bones = [b for b in bone_names if any(
        re.search(pat, b, re.IGNORECASE) for pat in BONE_PATTERNS
    )]

    print(f"\n[현재 상태]")
    print(f"  전체 본 수: {len(bone_names)}")
    print(f"  삭제 대상 본: {len(target_bones)}개")
    for b in sorted(target_bones)[:30]:
        print(f"    {b}")
    if len(target_bones) > 30:
        print(f"    ... (총 {len(target_bones)}개)")

    # 2. 연결된 메시 목록 출력
    print(f"\n[스켈레톤 연결 메시 탐색]")
    log("이 과정은 시간이 걸릴 수 있습니다...")
    meshes = find_meshes_using_skeleton(SKELETON_PATH)
    print(f"  총 {len(meshes)}개 메시:")
    for m in meshes:
        print(f"    {m}")

    # 3. 워크플로우 안내
    print_workflow_guide()

    # 4. 재임포트 실행 (설정이 있는 경우)
    if not REIMPORT_CONFIGS:
        log("REIMPORT_CONFIGS 가 비어있습니다.")
        log("위 안내를 참고하여 FBX 준비 후 REIMPORT_CONFIGS 를 설정하세요.")
        return

    if DRY_RUN:
        print("\n[DRY RUN] 재임포트 대상 확인만 수행:")
        for cfg in REIMPORT_CONFIGS:
            mesh_path = cfg.get("mesh_path", "")
            fbx_path = cfg.get("fbx_path", "")
            fbx_exists = os.path.exists(fbx_path)
            print(f"  메시: {mesh_path}")
            print(f"  FBX: {fbx_path} ({'존재' if fbx_exists else '없음 — 준비 필요'})")
        return

    # 실제 재임포트
    mesh_paths = [cfg["mesh_path"] for cfg in REIMPORT_CONFIGS]
    if not checkout_files_for_reimport(mesh_paths):
        log_error("체크아웃 실패 — 작업 중단")
        return

    success_count = 0
    for cfg in REIMPORT_CONFIGS:
        if reimport_mesh_from_fbx(cfg["mesh_path"], cfg["fbx_path"]):
            success_count += 1

    print(f"\n[RESULT] {success_count}/{len(REIMPORT_CONFIGS)} 재임포트 완료")

    # 재임포트 후 본 목록 재확인
    if success_count > 0:
        skeleton_after = unreal.load_asset(SKELETON_PATH)
        bone_names_after = get_bone_names_from_modifier(skeleton_after)
        remaining_targets = [b for b in bone_names_after if any(
            re.search(pat, b, re.IGNORECASE) for pat in BONE_PATTERNS
        )]
        print(f"\n[재임포트 후 상태]")
        print(f"  전체 본 수: {len(bone_names_after)} (이전: {len(bone_names)})")
        print(f"  잔여 대상 본: {len(remaining_targets)}개")
        if remaining_targets:
            log_warn("일부 대상 본이 아직 남아있습니다. 다른 메시에서도 재임포트 필요.")


main()
