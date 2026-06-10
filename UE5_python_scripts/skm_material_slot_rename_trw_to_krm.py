"""
Skeletal Mesh Material Slot Renamer: TRW -> KRM

Content Browser에서 선택된 Skeletal Mesh들의 매테리얼 슬롯 이름 중
'TRW' 문자열(대소문자 무시)을 'KRM'으로 일괄 치환한다.

사용법:
    1) Content Browser에서 대상 Skeletal Mesh들을 선택
    2) Tools > Execute Python Script... 로 본 스크립트 실행
"""

import unreal


FIND_STR = "TRW"
REPLACE_STR = "KRM"
CASE_INSENSITIVE = True   # 대소문자 무시 (tmv, Tmv 등도 매칭)
DRY_RUN = False           # True면 실제 변경 없이 로그만 출력


def _replace_ci(text: str, find: str, repl: str) -> str:
    """case-insensitive 치환."""
    if not CASE_INSENSITIVE:
        return text.replace(find, repl)
    out = ""
    i = 0
    flen = len(find)
    lower_find = find.lower()
    while i < len(text):
        if text[i : i + flen].lower() == lower_find:
            out += repl
            i += flen
        else:
            out += text[i]
            i += 1
    return out


def rename_material_slots(skm: unreal.SkeletalMesh) -> int:
    """SKM의 매테리얼 슬롯 이름을 치환. 변경된 슬롯 수 반환."""
    materials = skm.get_editor_property("materials")
    if not materials:
        unreal.log("  (materials 배열 비어있음)")
        return 0

    unreal.log(f"  슬롯 수: {len(materials)}")

    changed = 0
    new_materials = []
    for idx, skm_mat in enumerate(materials):
        slot_name = str(skm_mat.material_slot_name)
        unreal.log(f"  [{idx}] 현재 슬롯명: '{slot_name}'")

        target = FIND_STR.lower() if CASE_INSENSITIVE else FIND_STR
        hay = slot_name.lower() if CASE_INSENSITIVE else slot_name

        if target in hay:
            new_slot_name = _replace_ci(slot_name, FIND_STR, REPLACE_STR)
            unreal.log(f"       -> '{new_slot_name}'")

            # 신규 SkeletalMaterial 생성 (struct 직접 수정은 반영 안 될 수 있음)
            new_mat = unreal.SkeletalMaterial()
            new_mat.set_editor_property("material_interface", skm_mat.material_interface)
            new_mat.set_editor_property("material_slot_name", unreal.Name(new_slot_name))
            # 기존 SkeletalMaterial의 기타 필드 보존
            try:
                new_mat.set_editor_property(
                    "uv_channel_data", skm_mat.get_editor_property("uv_channel_data")
                )
            except Exception:
                pass
            new_materials.append(new_mat)
            changed += 1
        else:
            new_materials.append(skm_mat)

    if changed > 0 and not DRY_RUN:
        skm.set_editor_property("materials", new_materials)
        skm.modify()
        saved = unreal.EditorAssetLibrary.save_loaded_asset(skm, only_if_is_dirty=False)
        unreal.log(f"  저장 결과: {saved}")
    elif changed > 0 and DRY_RUN:
        unreal.log("  [DRY_RUN] 실제 저장 안 함")

    return changed


def main() -> None:
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        unreal.log_warning("Content Browser에서 선택된 에셋이 없습니다.")
        return

    unreal.log("=" * 60)
    unreal.log(f"선택된 에셋: {len(selected)}개 / DRY_RUN={DRY_RUN}")
    unreal.log(f"FIND='{FIND_STR}' -> REPLACE='{REPLACE_STR}' (CI={CASE_INSENSITIVE})")
    unreal.log("=" * 60)

    total_assets = 0
    total_slots = 0
    skipped = 0

    for asset in selected:
        if not isinstance(asset, unreal.SkeletalMesh):
            unreal.log(f"[SKIP] {asset.get_path_name()} (type={type(asset).__name__})")
            skipped += 1
            continue

        unreal.log(f"[SKM] {asset.get_path_name()}")
        changed = rename_material_slots(asset)
        if changed > 0:
            total_assets += 1
            total_slots += changed
        else:
            unreal.log("  (변경 대상 슬롯 없음)")

    unreal.log("=" * 60)
    unreal.log(f"완료: {total_assets}개 SKM에서 {total_slots}개 슬롯 변경")
    if skipped > 0:
        unreal.log(f"(SKM이 아니어서 건너뛴 에셋: {skipped}개)")


if __name__ == "__main__":
    main()
