"""
remove_ear_components_from_BP_CH.py
====================================
OWIS 프로젝트 전용 스크립트

BP_CH 로 시작하는 의상 블루프린트에서
'In_Ear' 또는 'Ear_Mic' 컴포넌트를 일괄 제거합니다.

핵심 원리
---------
어떤 BP는 컴포넌트를 직접 소유하고, 어떤 BP는 부모 BP에서 상속받습니다.
상속된 컴포넌트는 자식에서 삭제 불가하므로, **컴포넌트를 직접 소유한 BP에서만**
제거합니다. 그 BP를 저장하면 자식 BP들도 자동으로 갱신됩니다.

UE5의 SubobjectDataSubsystem 을 사용합니다.

사용법
------
    exec(open(r"C:/Users/Justin/Documents/maya/UE5_python_scripts/remove_ear_components_from_BP_CH.py").read())

    inspect("BP_CH_Mem1_DTV")    ← 특정 BP 트리 미리보기
    run(dry_run=True)            ← 어떤 BP에서 어떤 컴포넌트가 제거될지 미리 확인
    run(dry_run=False)           ← 실제 제거 + 저장
"""

import unreal

# ---------------------------------------------------------------------------
# 설정
# ---------------------------------------------------------------------------

DEFAULT_SEARCH_ROOTS = [
    "/Game/OWIS/ASSETS/Clothes/Concept",
    "/Game/OWIS/CHARACTER",
]

TARGET_COMPONENT_NAMES = {"In_Ear", "Ear_Mic"}
# 대소문자 무시 매칭용 (lower-case 집합)
TARGET_COMPONENT_NAMES_LOWER = {n.lower() for n in TARGET_COMPONENT_NAMES}
BP_NAME_PREFIX = "BP_CH"


# ---------------------------------------------------------------------------
# 에셋 수집
# ---------------------------------------------------------------------------

def _collect_bp_assets(search_roots):
    """지정 경로 아래 BP_CH* 블루프린트 에셋 데이터 목록을 반환."""
    ar = unreal.AssetRegistryHelpers.get_asset_registry()
    filter_ = unreal.ARFilter(
        class_names=["Blueprint"],
        recursive_paths=True,
        package_paths=search_roots,
    )
    asset_data_list = ar.get_assets(filter_)

    results = []
    for ad in asset_data_list:
        if str(ad.asset_name).startswith(BP_NAME_PREFIX):
            results.append(ad)
    results.sort(key=lambda a: f"{a.package_name}.{a.asset_name}")
    return results


def _asset_object_path(ad):
    return f"{ad.package_name}.{ad.asset_name}"


# ---------------------------------------------------------------------------
# SubobjectDataSubsystem 헬퍼
# ---------------------------------------------------------------------------

def _get_sds():
    # UE5 버전에 따라 접근 방식이 다름
    try:
        return unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    except Exception:
        pass
    try:
        return unreal.SubobjectDataSubsystem.get()
    except Exception:
        pass
    try:
        return unreal.SubobjectDataSubsystem()
    except Exception:
        return None


def _gather_subobjects(bp_obj):
    """BP의 모든 SubobjectDataHandle 리스트를 반환."""
    sds = _get_sds()
    return sds.k2_gather_subobject_data_for_blueprint(bp_obj)


_DELETE_METHOD_CACHE = {"name": None, "kind": None}  # kind: "single" / "plural"
_COMPILE_FN_CACHE = {"fn": None}


def _try_delete_subobject(sds, context_handle, handle, bp_obj):
    """
    UE 버전에 따라 다른 delete API 이름을 자동 탐색.
    가능한 후보:
      - k2_delete_subobject(context, handle, bp, flag)  [singular]
      - k2_delete_subobjects(context, [handle], bp)     [plural]
      - delete_subobject / delete_subobjects
    """
    # 캐시된 메서드가 있으면 우선 시도
    if _DELETE_METHOD_CACHE["name"]:
        try:
            fn = getattr(sds, _DELETE_METHOD_CACHE["name"])
            if _DELETE_METHOD_CACHE["kind"] == "plural":
                fn(context_handle, [handle], bp_obj)
            else:
                # singular - 시그니처는 4-arg or 3-arg
                try:
                    fn(context_handle, handle, bp_obj, False)
                except TypeError:
                    fn(context_handle, handle, bp_obj)
            return True
        except Exception:
            pass

    # 후보 순회
    candidates = [
        ("k2_delete_subobjects", "plural"),
        ("delete_subobjects", "plural"),
        ("k2_delete_subobject", "single"),
        ("delete_subobject", "single"),
    ]
    for name, kind in candidates:
        if not hasattr(sds, name):
            continue
        try:
            fn = getattr(sds, name)
            if kind == "plural":
                fn(context_handle, [handle], bp_obj)
            else:
                try:
                    fn(context_handle, handle, bp_obj, False)
                except TypeError:
                    fn(context_handle, handle, bp_obj)
            _DELETE_METHOD_CACHE["name"] = name
            _DELETE_METHOD_CACHE["kind"] = kind
            return True
        except Exception:
            continue

    # 마지막 수단: dir로 'delete' 포함 메서드 출력 (디버깅용)
    if _DELETE_METHOD_CACHE["name"] is None:
        avail = [m for m in dir(sds) if "delete" in m.lower()]
        print(f"             [DEBUG] 사용 가능한 delete 메서드: {avail}")
    return False


def _compile_blueprint(bp_obj):
    """UE 버전에 따라 다른 컴파일 API 자동 탐색."""
    if _COMPILE_FN_CACHE["fn"]:
        _COMPILE_FN_CACHE["fn"](bp_obj)
        return

    candidates = [
        lambda b: unreal.BlueprintEditorLibrary.compile_blueprint(b),
        lambda b: unreal.KismetEditorUtilities.compile_blueprint(b),
        lambda b: unreal.EditorAssetLibrary.compile_blueprint(b),
    ]
    last_exc = None
    for fn in candidates:
        try:
            fn(bp_obj)
            _COMPILE_FN_CACHE["fn"] = fn
            return
        except Exception as e:
            last_exc = e
            continue
    if last_exc:
        raise last_exc


def _handle_info(handle):
    """
    SubobjectDataHandle → (variable_name:str, is_inherited:bool, class_name:str)
    """
    sds = _get_sds()
    data = sds.k2_get_subobject_data(handle) if hasattr(sds, "k2_get_subobject_data") \
           else sds.get_data_for_handle(handle) if hasattr(sds, "get_data_for_handle") \
           else None

    # UE5 버전에 따라 함수 이름이 다름 - 둘 다 시도
    if data is None:
        try:
            data = unreal.SubobjectDataBlueprintFunctionLibrary.get_data(handle)
        except Exception:
            return ("?", False, "?")

    var_name = "?"
    is_inherited = False
    class_name = "?"

    # variable name
    try:
        var_name = str(unreal.SubobjectDataBlueprintFunctionLibrary.get_variable_name(data))
    except Exception:
        try:
            var_name = str(data.get_variable_name())
        except Exception:
            pass

    # inherited 여부
    try:
        is_inherited = bool(
            unreal.SubobjectDataBlueprintFunctionLibrary.is_inherited_component(data)
        )
    except Exception:
        try:
            is_inherited = bool(data.is_inherited_component())
        except Exception:
            pass
    # 추가로 inherited_blueprint_component도 검사
    if not is_inherited:
        try:
            is_inherited = bool(
                unreal.SubobjectDataBlueprintFunctionLibrary.is_inherited_blueprint_component(data)
            )
        except Exception:
            pass

    # 컴포넌트 클래스
    try:
        obj = unreal.SubobjectDataBlueprintFunctionLibrary.get_object(data)
        if obj:
            class_name = obj.get_class().get_name()
    except Exception:
        pass

    return (var_name, is_inherited, class_name)


# ---------------------------------------------------------------------------
# 진단 - 트리 출력
# ---------------------------------------------------------------------------

def inspect(name_filter=None, max_count=3, search_roots=None):
    """
    BP의 모든 컴포넌트(상속 포함)를 평면 리스트로 출력합니다.
    [OWN] / [INH] 표시로 자체 소유/상속 여부 구분.
    """
    if search_roots is None:
        search_roots = DEFAULT_SEARCH_ROOTS

    asset_data_list = _collect_bp_assets(search_roots)
    if name_filter:
        asset_data_list = [
            ad for ad in asset_data_list if name_filter in str(ad.asset_name)
        ]
    else:
        asset_data_list = asset_data_list[:max_count]

    print(f"\n[INSPECT] 대상 BP: {len(asset_data_list)}개\n")

    for ad in asset_data_list:
        object_path = _asset_object_path(ad)
        asset_name  = str(ad.asset_name)
        bp_obj = unreal.EditorAssetLibrary.load_asset(object_path)
        if bp_obj is None:
            print(f"[WARN] 로드 실패: {object_path}")
            continue

        print(f"=== {asset_name} ===")
        print(f"    {object_path}")

        try:
            handles = _gather_subobjects(bp_obj)
        except Exception as e:
            print(f"    [ERROR] gather 실패: {e}")
            continue

        print(f"    컴포넌트 총 {len(handles)}개")
        for h in handles:
            var_name, is_inherited, class_name = _handle_info(h)
            tag = "INH" if is_inherited else "OWN"
            print(f"      [{tag}] {var_name}  ({class_name})")
        print()


# ---------------------------------------------------------------------------
# 메인 - 실제 제거
# ---------------------------------------------------------------------------

def run(dry_run=True, search_roots=None):
    """
    Parameters
    ----------
    dry_run : bool
        True  → 제거 대상 목록만 출력
        False → 실제 제거 + 컴파일 + 저장
    """
    if search_roots is None:
        search_roots = DEFAULT_SEARCH_ROOTS

    mode_label = "[DRY-RUN]" if dry_run else "[EXECUTE]"
    print("=" * 70)
    print(f"{mode_label}  BP_CH Ear 컴포넌트 제거 스크립트")
    print(f"검색 경로: {search_roots}")
    print(f"제거 대상 컴포넌트: {TARGET_COMPONENT_NAMES}")
    print(f"방침: 자체 소유(OWN)인 컴포넌트만 제거 (상속(INH)은 부모에서 처리)")
    print("=" * 70)

    asset_data_list = _collect_bp_assets(search_roots)
    print(f"\n발견된 BP_CH 블루프린트 수: {len(asset_data_list)}\n")

    if not asset_data_list:
        print("대상 블루프린트가 없습니다.")
        return

    sds = _get_sds()

    hit_count = 0
    total_removed = 0
    inherited_skipped = 0
    error_count = 0
    assets_to_save = []  # (path, bp_obj)

    with unreal.ScopedSlowTask(len(asset_data_list), "BP_CH Ear 컴포넌트 처리 중...") as slow_task:
        slow_task.make_dialog(True)

        for ad in asset_data_list:
            if slow_task.should_cancel():
                print("\n[중단] 사용자가 작업을 취소했습니다.")
                break

            slow_task.enter_progress_frame(1, str(ad.asset_name))
            object_path = _asset_object_path(ad)
            asset_name  = str(ad.asset_name)

            try:
                bp_obj = unreal.EditorAssetLibrary.load_asset(object_path)
                if bp_obj is None:
                    print(f"  [WARN] 로드 실패: {object_path}")
                    error_count += 1
                    continue
            except Exception as e:
                print(f"  [ERROR] 로드 예외: {object_path}\n         {e}")
                error_count += 1
                continue

            # 모든 컴포넌트 핸들 수집
            try:
                handles = _gather_subobjects(bp_obj)
            except Exception as e:
                print(f"  [ERROR] gather 실패 {asset_name}: {e}")
                error_count += 1
                continue

            # 타겟 매칭 (이름별로 중복 핸들 제거 - 같은 컴포넌트가 여러 view로 잡힘)
            context_handle = handles[0] if handles else None  # 첫 핸들 = actor self
            own_targets_by_name = {}  # var_name → first matching handle
            inh_names = set()

            for h in handles:
                var_name, is_inherited, class_name = _handle_info(h)
                if var_name.lower() not in TARGET_COMPONENT_NAMES_LOWER:
                    continue
                if is_inherited:
                    inh_names.add(var_name)
                else:
                    if var_name not in own_targets_by_name:
                        own_targets_by_name[var_name] = h  # 첫 OWN handle만 유지

            if not own_targets_by_name and not inh_names:
                continue  # 관련 컴포넌트 없음

            print(f"\n[HIT] {asset_name}")
            print(f"      경로: {object_path}")

            for n in sorted(inh_names):
                inherited_skipped += 1
                print(f"      → [SKIP-INH] '{n}' (부모 BP에서 처리 예정)")

            if not own_targets_by_name:
                continue

            hit_count += 1

            for n, h in own_targets_by_name.items():
                total_removed += 1
                if dry_run:
                    print(f"      → [DRY-OWN] 제거 예정: '{n}'")
                else:
                    ok = _try_delete_subobject(sds, context_handle, h, bp_obj)
                    if ok:
                        print(f"      → [OK]  제거 완료: '{n}'")
                    else:
                        print(f"      → [FAIL] 제거 실패: '{n}'")
                        error_count += 1
                        total_removed -= 1

            if not dry_run and own_targets_by_name:
                assets_to_save.append((object_path, bp_obj))

    # 컴파일 + 저장
    if not dry_run and assets_to_save:
        print(f"\n{'='*70}")
        print(f"컴파일 + 저장 ({len(assets_to_save)}개 에셋)")
        save_ok = 0
        save_fail = 0
        for path, bp_obj in assets_to_save:
            try:
                _compile_blueprint(bp_obj)
                unreal.EditorAssetLibrary.save_asset(path, only_if_is_dirty=False)
                save_ok += 1
                print(f"  [SAVED] {path}")
            except Exception as e:
                save_fail += 1
                print(f"  [SAVE ERROR] {path}\n               {e}")
        print(f"\n저장 완료: {save_ok}개 / 실패: {save_fail}개")

    # 요약
    print(f"\n{'='*70}")
    print(f"[요약]  모드: {'DRY-RUN (변경 없음)' if dry_run else 'EXECUTE (실제 저장)'}")
    print(f"        검사한 BP 수: {len(asset_data_list)}")
    print(f"        제거 {'예정' if dry_run else '완료'} BP 수: {hit_count}")
    print(f"        제거 {'예정' if dry_run else '완료'} 컴포넌트 수 (OWN): {total_removed}")
    print(f"        상속(INH)으로 스킵된 항목: {inherited_skipped}")
    if error_count:
        print(f"        오류 발생: {error_count}")
    print("=" * 70)

    if dry_run and (hit_count > 0 or inherited_skipped > 0):
        print("\n실제 제거: run(dry_run=False)")


# ---------------------------------------------------------------------------
# 로드 메시지
# ---------------------------------------------------------------------------
print()
print("remove_ear_components_from_BP_CH.py 로드 완료.")
print("사용법:")
print("  inspect('BP_CH_Mem1_DTV')   ← 특정 BP 컴포넌트 트리 미리보기")
print("  run(dry_run=True)           ← 제거 대상 미리 확인")
print("  run(dry_run=False)          ← 실제 제거 + 저장")
print()
