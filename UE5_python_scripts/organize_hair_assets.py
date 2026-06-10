# -*- coding: utf-8 -*-
"""
OWIS - Hair 에셋 폴더/네이밍 정리 스크립트  (v3)
대상: /Game/OWIS/ASSETS/Hair  (콘텐츠 브라우저 /All/Game/OWIS/ASSETS/Hair)

폴더 구조 (각 MemN/Hair_X/ 기준)
  Rig/        <- SKM + PhysicsAsset + ABP(애님BP)
  Material/   <- MI + 머티리얼(Skin_Mat 등)

정책 (HA 유지 / 안전)
  - 네이밍 정리 : _Physics -> _PhysicsAsset , _hair -> _Hair , SKM_CH_Hair_ 중복토큰 제거
  - SKM_HA_ 는 유지 (헤어 단독 메시 != 리그용 SKM_CH_ 메시. 합치면 충돌/덮어쓰기)
  - ABP 접두어 통일(ABP_Hair_/ABP_CH_ -> ABP_HA_) 은 UNIFY_ABP_PREFIX 플래그로 선택
  - 이동/리네임은 rename_asset 사용 -> 리다이렉터 자동 생성(레퍼런스 보존)
  - 같은 목적지로 가는 두 원본(충돌)이 있으면 실제 실행을 중단

산출물
  - 같은 폴더에 'hair_cleanup_plan.txt' 리포트 생성 (가독성용). IDE 로 열어 검토.

사용법
  1) DRY_RUN = True 로 실행 -> 리포트(txt) 확인
  2) 이상 없으면 DRY_RUN = False 로 재실행 -> 실제 적용
  3) 콘텐츠 브라우저 Hair 폴더 우클릭 > Fix Up Redirectors in Folder
"""

import unreal

# =====================[ 설정 ]=====================
ROOT = "/Game/OWIS/ASSETS/Hair"
DRY_RUN = False                      # True: 미리보기(리포트만) / False: 실제 적용
UNIFY_ABP_PREFIX = True             # ABP_Hair_ / ABP_CH_  ->  ABP_HA_ 로 통일
DELETE_EMPTY_FOLDERS = True         # 이동 후 비어버린 원본 폴더(Rigs/, MV_A/ 등) 삭제
REPORT_PATH = r"C:\Users\Justin\Documents\maya\UE5_python_scripts\hair_cleanup_plan.txt"
# ==================================================

eal = unreal.EditorAssetLibrary


def normalize_name(name):
    new = name
    # --- ABP 접두어 통일 (옵션) ---
    if UNIFY_ABP_PREFIX:
        if new.startswith("ABP_Hair_"):
            new = "ABP_HA_" + new[len("ABP_Hair_"):]
        elif new.startswith("ABP_CH_"):
            new = "ABP_HA_" + new[len("ABP_CH_"):]
    # --- SKM_CH_Hair_ 중복 토큰 제거 (SKM_HA_ 는 건드리지 않음) ---
    if new.startswith("SKM_CH_Hair_"):
        new = "SKM_CH_" + new[len("SKM_CH_Hair_"):]
    # --- 소문자 hair -> Hair ---
    new = new.replace("_hair", "_Hair")
    # --- Physics 접미어 통일 ---
    if new.endswith("_Physics"):
        new = new + "Asset"
    return new


def asset_class(pkg):
    ad = eal.find_asset_data(pkg)
    try:
        return str(ad.asset_class_path.asset_name)   # UE5.1+
    except Exception:
        try:
            return str(ad.asset_class)
        except Exception:
            return ""


def classify(name, pkg):
    """RIG(=Rig/) / MAT(=Material/) / OTHER(수동확인)."""
    if (name.startswith("SKM_") or name.startswith("ABP_")
            or name.endswith("_PhysicsAsset") or name.endswith("_Physics")):
        return "RIG"
    if name.startswith("MI_") or name.startswith("M_") or name.startswith("MAT_"):
        return "MAT"
    if "Material" in asset_class(pkg):    # Skin_Mat 등 접두어 없는 머티리얼
        return "MAT"
    return "OTHER"


def get_base(pkg_path):
    if not pkg_path.startswith(ROOT + "/"):
        return None
    parts = pkg_path[len(ROOT) + 1:].split("/")
    if len(parts) < 3:
        return None
    return ROOT + "/" + parts[0] + "/" + parts[1], parts[0], parts[1]


def build_plan():
    raw = eal.list_assets(ROOT, recursive=True, include_folder=False)
    seen = set()
    plan = []        # dict: old, new, mem, hair, kind, moved, old_rel, new_rel
    skipped = []
    src_dirs = set()

    for a in raw:
        old = a.split(".")[0]
        if old in seen:                       # 중복 제거
            continue
        seen.add(old)

        folder, _, name = old.rpartition("/")
        based = get_base(old)
        if based is None:
            skipped.append((old, "경로구조 예외 - 수동확인"))
            continue
        base, mem, hair = based
        kind = classify(name, old)
        if kind == "OTHER":
            skipped.append((old, "분류불가(%s) - 수동확인" % asset_class(old)))
            continue

        new_folder = base + ("/Rig" if kind == "RIG" else "/Material")
        new = new_folder + "/" + normalize_name(name)
        if new == old:
            continue
        if new_folder != folder:
            src_dirs.add(folder)
        plan.append({
            "old": old, "new": new, "mem": mem, "hair": hair, "kind": kind,
            "moved": new_folder != folder,
            "old_rel": old[len(base) + 1:], "new_rel": new[len(base) + 1:],
        })
    return plan, skipped, src_dirs


def find_collisions(plan):
    """같은 목적지로 가는 원본이 2개 이상이면 충돌."""
    dest = {}
    for p in plan:
        dest.setdefault(p["new"], []).append(p["old"])
    return {d: srcs for d, srcs in dest.items() if len(srcs) > 1}


def write_report(plan, skipped, collisions):
    lines = []
    moved = sum(1 for p in plan if p["moved"])
    renamed = sum(1 for p in plan if p["old_rel"].rsplit("/", 1)[-1] != p["new_rel"].rsplit("/", 1)[-1])
    lines.append("=" * 64)
    lines.append(" OWIS Hair 정리 계획  (DRY-RUN=%s)" % DRY_RUN)
    lines.append("=" * 64)
    lines.append(" 변경 %d건 | 폴더이동 %d | 이름변경 %d | 충돌 %d | 스킵 %d"
                 % (len(plan), moved, renamed, len(collisions), len(skipped)))
    lines.append(" 옵션: UNIFY_ABP_PREFIX=%s" % UNIFY_ABP_PREFIX)
    lines.append("")

    if collisions:
        lines.append("!" * 64)
        lines.append(" [충돌] 아래는 목적지가 겹칩니다. 실제 실행이 중단됩니다.")
        for d, srcs in collisions.items():
            lines.append("   목적지: %s" % d)
            for s in srcs:
                lines.append("       <- %s" % s)
        lines.append("!" * 64)
        lines.append("")

    # 폴더별 그룹 출력
    groups = {}
    for p in plan:
        groups.setdefault((p["mem"], p["hair"]), []).append(p)
    for key in sorted(groups):
        lines.append("[%s/%s]" % key)
        for p in sorted(groups[key], key=lambda x: x["kind"]):
            tag = "[MOVE]" if p["moved"] else "      "
            lines.append("  %s %-3s %-40s -> %s"
                         % (tag, p["kind"], p["old_rel"], p["new_rel"]))
        lines.append("")

    if skipped:
        lines.append("-" * 64)
        lines.append(" [수동확인 필요]")
        for pkg, why in skipped:
            lines.append("   ! %s  (%s)" % (pkg, why))

    text = "\n".join(lines)
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as f:
            f.write(text)
        unreal.log("[리포트 저장] %s" % REPORT_PATH)
    except Exception as e:
        unreal.log_error("리포트 저장 실패: %s" % e)
    # 로그에는 요약만
    unreal.log(text.split("\n\n")[0])


def apply_plan(plan, src_dirs):
    ok, fail = 0, 0
    for p in plan:
        try:
            if eal.does_asset_exist(p["new"]):
                unreal.log_warning("  [충돌:존재] 건너뜀 %s" % p["new"]); fail += 1; continue
            if eal.rename_asset(p["old"], p["new"]):
                ok += 1
            else:
                unreal.log_warning("  [실패] %s" % p["old"]); fail += 1
        except Exception as e:
            unreal.log_error("  [예외] %s : %s" % (p["old"], e)); fail += 1
    unreal.log("[적용완료] 성공 %d / 실패 %d" % (ok, fail))

    eal.save_directory(ROOT, only_if_is_dirty=True, recursive=True)

    if DELETE_EMPTY_FOLDERS:
        for d in sorted(src_dirs):
            if not d.endswith("/Rig") and not d.endswith("/Material") \
                    and eal.does_directory_exist(d) \
                    and not eal.list_assets(d, recursive=True, include_folder=False):
                if eal.delete_directory(d):
                    unreal.log("  [폴더삭제] %s" % d)
    unreal.log("[안내] Hair 폴더 우클릭 > Fix Up Redirectors in Folder 를 실행하세요.")


def main():
    plan, skipped, src_dirs = build_plan()
    collisions = find_collisions(plan)
    write_report(plan, skipped, collisions)

    if DRY_RUN:
        unreal.log("[DRY_RUN] 변경 없음. 리포트(txt) 확인 후 DRY_RUN=False 로 재실행.")
        return
    if collisions:
        unreal.log_error("[중단] 충돌 %d건. 리포트 확인 후 규칙을 조정하세요." % len(collisions))
        return
    apply_plan(plan, src_dirs)


main()
