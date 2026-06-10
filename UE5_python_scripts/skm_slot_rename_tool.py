"""
Skeletal Mesh Material Slot Rename Tool (Find & Replace + Auto-Assign Material)

선택된 Skeletal Mesh들의 매테리얼 슬롯에 대해:
  - Find / Replace : 슬롯 이름 일괄 치환
  - Material        : 슬롯 이름과 동일한 이름의 매테리얼을 찾아 자동 할당

사용법:
    1) Content Browser에서 대상 SKM들을 선택
    2) Tools > Execute Python Script... 로 본 스크립트 실행
    3) 다이얼로그에서 작업 수행
"""

import tkinter as tk
from tkinter import ttk, scrolledtext
import unreal


# =========================================================================
# 슬롯 이름 치환 (Find & Replace)
# =========================================================================

def _replace_ci(text: str, find: str, repl: str, case_insensitive: bool) -> str:
    if not case_insensitive:
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


def rename_slots_on_asset(
    skm: unreal.SkeletalMesh,
    find_str: str,
    replace_str: str,
    case_insensitive: bool,
    dry_run: bool,
    log_fn,
) -> int:
    materials = skm.get_editor_property("materials")
    if not materials:
        log_fn("  (materials 비어있음)")
        return 0

    changed = 0
    new_materials = []
    target = find_str.lower() if case_insensitive else find_str

    for idx, skm_mat in enumerate(materials):
        slot_name = str(skm_mat.material_slot_name)
        hay = slot_name.lower() if case_insensitive else slot_name

        if find_str and target in hay:
            new_slot_name = _replace_ci(slot_name, find_str, replace_str, case_insensitive)
            log_fn(f"  [{idx}] '{slot_name}' -> '{new_slot_name}'")

            new_mat = unreal.SkeletalMaterial()
            new_mat.set_editor_property("material_interface", skm_mat.material_interface)
            new_mat.set_editor_property("material_slot_name", unreal.Name(new_slot_name))
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

    if changed > 0 and not dry_run:
        skm.set_editor_property("materials", new_materials)
        skm.modify()
        saved = unreal.EditorAssetLibrary.save_loaded_asset(skm, only_if_is_dirty=False)
        log_fn(f"  저장: {saved}")
    elif changed > 0 and dry_run:
        log_fn("  [DRY RUN] 저장 안 함")

    return changed


def run_rename(find_str: str, replace_str: str, case_insensitive: bool, dry_run: bool, log_fn):
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        log_fn("[!] Content Browser에서 선택된 에셋이 없습니다.")
        return

    if not find_str:
        log_fn("[!] Find 문자열이 비어있습니다.")
        return

    log_fn("=" * 60)
    log_fn(f"[Rename] FIND='{find_str}' -> REPLACE='{replace_str}'")
    log_fn(f"CaseInsensitive={case_insensitive}, DryRun={dry_run}")
    log_fn(f"선택된 에셋: {len(selected)}개")
    log_fn("=" * 60)

    total_assets = 0
    total_slots = 0
    skipped = 0

    for asset in selected:
        if not isinstance(asset, unreal.SkeletalMesh):
            log_fn(f"[SKIP] {asset.get_name()} (type={type(asset).__name__})")
            skipped += 1
            continue

        log_fn(f"[SKM] {asset.get_name()}")
        changed = rename_slots_on_asset(
            asset, find_str, replace_str, case_insensitive, dry_run, log_fn
        )
        if changed > 0:
            total_assets += 1
            total_slots += changed
        else:
            log_fn("  (변경 대상 없음)")

    log_fn("-" * 60)
    log_fn(f"완료: {total_assets}개 SKM / {total_slots}개 슬롯 변경")
    if skipped > 0:
        log_fn(f"건너뛴 비-SKM 에셋: {skipped}개")
    log_fn("")


# =========================================================================
# 슬롯명과 같은 이름의 매테리얼 자동 할당
# =========================================================================

def _normalize_folder(path: str) -> str:
    """Strip trailing slash. Accept /All/Game/... or /Game/... and normalize to /Game/..."""
    if not path:
        return ""
    p = path.strip().rstrip("/")
    if p.startswith("/All/Game/"):
        p = p[len("/All"):]  # -> /Game/...
    elif p.startswith("/All/"):
        p = "/Game" + p[len("/All"):]
    return p


def derive_material_folder(skm_package_path: str) -> str:
    """
    SKM의 package path에서 /Rig 이후를 잘라내고 /Material 로 치환.
    /Rig 하위 서브폴더 구조는 무시 (Material 하위 구조가 다를 수 있으므로 최상위 Material 폴더 사용)
    예) /Game/OWIS/.../Mem2/Rig/Bottom/SK_X  ->  /Game/OWIS/.../Mem2/Material
        /Game/OWIS/.../Mem2/Rig/SK_X         ->  /Game/OWIS/.../Mem2/Material
    """
    parts = skm_package_path.rsplit("/", 1)
    if len(parts) < 2:
        return ""
    folder = parts[0]

    lower = folder.lower()
    idx = lower.rfind("/rig")
    if idx >= 0:
        # /rig 뒤가 끝이거나 / 인 경우만 진짜 'Rig' 폴더
        after = folder[idx + 4 : idx + 5]
        if after == "" or after == "/":
            return folder[:idx] + "/Material"
    return folder


_SCANNED_FOLDERS = set()


def _scan_folder_once(folder: str):
    """AssetRegistry에 폴더를 한 번 강제 스캔해서 인덱스 생성."""
    if folder in _SCANNED_FOLDERS:
        return
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        ar.scan_paths_synchronous([folder], force_rescan=True, ignore_deny_list_scan_filters=False)
        _SCANNED_FOLDERS.add(folder)
    except Exception as e:
        unreal.log_warning(f"scan_paths_synchronous 실패: {e}")


def find_material_by_name(name: str, search_folder: str, log_fn=None) -> unreal.MaterialInterface:
    """search_folder 하위(재귀)에서 name과 일치하는 MaterialInterface 에셋 찾기."""
    if not name or not search_folder:
        return None

    folder = search_folder.rstrip("/")

    # 1) 직접 경로 시도 : <folder>/<name>
    candidate = f"{folder}/{name}"
    if unreal.EditorAssetLibrary.does_asset_exist(candidate):
        asset = unreal.EditorAssetLibrary.load_asset(candidate)
        if isinstance(asset, unreal.MaterialInterface):
            return asset

    # 2) AssetRegistry 재귀 탐색 (스캔 강제)
    _scan_folder_once(folder)
    try:
        ar = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = ar.get_assets_by_path(folder, recursive=True)
    except Exception as e:
        if log_fn:
            log_fn(f"     [warn] AssetRegistry 조회 실패: {e}")
        return None

    if log_fn and not getattr(find_material_by_name, "_logged_count", False):
        log_fn(f"     ({folder} 하위 에셋 수: {len(assets)})")
        find_material_by_name._logged_count = True

    for ad in assets:
        if str(ad.asset_name) == name:
            try:
                pkg_name = str(ad.package_name)
                loaded = unreal.EditorAssetLibrary.load_asset(pkg_name)
                if isinstance(loaded, unreal.MaterialInterface):
                    return loaded
            except Exception as e:
                if log_fn:
                    log_fn(f"     [warn] load 실패 {ad.package_name}: {e}")
                continue
    return None


def assign_materials_on_asset(
    skm: unreal.SkeletalMesh,
    explicit_folder: str,
    dry_run: bool,
    log_fn,
) -> int:
    materials = skm.get_editor_property("materials")
    if not materials:
        log_fn("  (materials 비어있음)")
        return 0

    # SKM 경로에서 매테리얼 폴더 추정 (사용자 지정이 비었을 때)
    skm_pkg = skm.get_path_name().split(".")[0]
    if explicit_folder:
        material_folder = explicit_folder
    else:
        material_folder = derive_material_folder(skm_pkg)

    log_fn(f"  매테리얼 탐색 폴더: {material_folder}")
    # 새 SKM마다 한 번씩 폴더 에셋수 로그를 다시 찍도록 리셋
    if hasattr(find_material_by_name, "_logged_count"):
        find_material_by_name._logged_count = False

    changed = 0
    missing = 0
    new_materials = []

    for idx, skm_mat in enumerate(materials):
        slot_name = str(skm_mat.material_slot_name)
        current_mat = skm_mat.material_interface
        current_name = current_mat.get_name() if current_mat else "(None)"

        found = find_material_by_name(slot_name, material_folder, log_fn=log_fn)

        if found is None:
            log_fn(f"  [{idx}] '{slot_name}': 매테리얼 못 찾음 (현재={current_name})")
            new_materials.append(skm_mat)
            missing += 1
            continue

        if found == current_mat:
            log_fn(f"  [{idx}] '{slot_name}': 이미 할당됨 ({found.get_name()})")
            new_materials.append(skm_mat)
            continue

        log_fn(f"  [{idx}] '{slot_name}': {current_name} -> {found.get_name()}")
        new_mat = unreal.SkeletalMaterial()
        new_mat.set_editor_property("material_interface", found)
        new_mat.set_editor_property("material_slot_name", unreal.Name(slot_name))
        try:
            new_mat.set_editor_property(
                "uv_channel_data", skm_mat.get_editor_property("uv_channel_data")
            )
        except Exception:
            pass
        new_materials.append(new_mat)
        changed += 1

    if changed > 0 and not dry_run:
        skm.set_editor_property("materials", new_materials)
        skm.modify()
        saved = unreal.EditorAssetLibrary.save_loaded_asset(skm, only_if_is_dirty=False)
        log_fn(f"  저장: {saved}")
    elif changed > 0 and dry_run:
        log_fn("  [DRY RUN] 저장 안 함")

    if missing > 0:
        log_fn(f"  -> 못 찾은 슬롯: {missing}개")

    return changed


def run_assign_materials(material_folder: str, dry_run: bool, log_fn):
    selected = unreal.EditorUtilityLibrary.get_selected_assets()
    if not selected:
        log_fn("[!] Content Browser에서 선택된 에셋이 없습니다.")
        return

    folder = _normalize_folder(material_folder)

    log_fn("=" * 60)
    log_fn("[Assign Materials] 슬롯명과 동일한 매테리얼 자동 할당")
    if folder:
        log_fn(f"지정 폴더: {folder}")
    else:
        log_fn("지정 폴더 없음 -> 각 SKM 경로의 /Rig 를 /Material 로 치환해서 자동 탐색")
    log_fn(f"DryRun={dry_run} / 선택된 에셋: {len(selected)}개")
    log_fn("=" * 60)

    total_assets = 0
    total_slots = 0
    skipped = 0

    for asset in selected:
        if not isinstance(asset, unreal.SkeletalMesh):
            log_fn(f"[SKIP] {asset.get_name()} (type={type(asset).__name__})")
            skipped += 1
            continue

        log_fn(f"[SKM] {asset.get_name()}")
        changed = assign_materials_on_asset(asset, folder, dry_run, log_fn)
        if changed > 0:
            total_assets += 1
            total_slots += changed
        else:
            log_fn("  (할당 변경 없음)")

    log_fn("-" * 60)
    log_fn(f"완료: {total_assets}개 SKM / {total_slots}개 슬롯 매테리얼 할당")
    if skipped > 0:
        log_fn(f"건너뛴 비-SKM 에셋: {skipped}개")
    log_fn("")


# =========================================================================
# UI
# =========================================================================

def show_tool():
    root = tk.Tk()
    root.title("SKM Material Slot Renamer")
    root.geometry("700x600")
    root.attributes("-topmost", True)

    # ----- Input frame -----
    frm = ttk.Frame(root, padding=10)
    frm.pack(fill="x")

    ttk.Label(frm, text="Find:").grid(row=0, column=0, sticky="w", pady=4)
    find_var = tk.StringVar(value="TRW")
    find_entry = ttk.Entry(frm, textvariable=find_var, width=50)
    find_entry.grid(row=0, column=1, sticky="we", padx=6)

    ttk.Label(frm, text="Replace:").grid(row=1, column=0, sticky="w", pady=4)
    repl_var = tk.StringVar(value="KRM")
    repl_entry = ttk.Entry(frm, textvariable=repl_var, width=50)
    repl_entry.grid(row=1, column=1, sticky="we", padx=6)

    ttk.Label(frm, text="Material Folder:").grid(row=2, column=0, sticky="w", pady=4)
    mat_var = tk.StringVar(value="")
    mat_entry = ttk.Entry(frm, textvariable=mat_var, width=50)
    mat_entry.grid(row=2, column=1, sticky="we", padx=6)

    ttk.Label(
        frm,
        text="(비우면 SKM 경로의 /Rig 를 /Material 로 치환해 자동 탐색)",
        foreground="#888",
    ).grid(row=3, column=1, sticky="w", padx=6)

    frm.columnconfigure(1, weight=1)

    # ----- Options -----
    opt_frm = ttk.Frame(root, padding=(10, 0))
    opt_frm.pack(fill="x")

    ci_var = tk.BooleanVar(value=True)
    ttk.Checkbutton(opt_frm, text="Case Insensitive", variable=ci_var).pack(side="left", padx=4)

    dry_var = tk.BooleanVar(value=False)
    ttk.Checkbutton(opt_frm, text="Dry Run (실제 변경 안 함)", variable=dry_var).pack(
        side="left", padx=10
    )

    # ----- Log area -----
    log_frm = ttk.Frame(root, padding=10)
    log_frm.pack(fill="both", expand=True)
    log_box = scrolledtext.ScrolledText(log_frm, wrap="word", font=("Consolas", 9))
    log_box.pack(fill="both", expand=True)

    def log_fn(msg: str):
        log_box.insert("end", msg + "\n")
        log_box.see("end")
        log_box.update_idletasks()
        unreal.log(msg)

    # ----- Buttons -----
    btn_frm = ttk.Frame(root, padding=10)
    btn_frm.pack(fill="x")

    def on_apply():
        log_box.delete("1.0", "end")
        try:
            run_rename(
                find_var.get().strip(),
                repl_var.get(),
                ci_var.get(),
                dry_var.get(),
                log_fn,
            )
        except Exception as e:
            log_fn(f"[ERROR] {e}")
            import traceback
            log_fn(traceback.format_exc())

    def on_material():
        log_box.delete("1.0", "end")
        try:
            run_assign_materials(
                mat_var.get().strip(),
                dry_var.get(),
                log_fn,
            )
        except Exception as e:
            log_fn(f"[ERROR] {e}")
            import traceback
            log_fn(traceback.format_exc())

    def on_clear():
        log_box.delete("1.0", "end")

    # 좌측: Material 버튼 (슬롯명으로 매테리얼 자동 할당)
    ttk.Button(btn_frm, text="Material", command=on_material).pack(side="left", padx=4)

    # 우측: 일반 액션
    ttk.Button(btn_frm, text="Apply", command=on_apply).pack(side="right", padx=4)
    ttk.Button(btn_frm, text="Clear Log", command=on_clear).pack(side="right", padx=4)
    ttk.Button(btn_frm, text="Close", command=root.destroy).pack(side="right", padx=4)

    find_entry.focus_set()
    root.mainloop()


if __name__ == "__main__":
    show_tool()
