# -*- coding: utf-8 -*-
"""현장 포인트리스트 **양식**으로 바꾸는 층 — data/pointlist-form.json 이 사전이다.

  PYTHONIOENCODING=utf-8 python form.py e5.ahu        한 계열을 양식 모양으로 찍어 본다
  PYTHONIOENCODING=utf-8 python form.py --check       유도가 안 되는 행을 찾는다

왜 있나
  우리 템플릿은 "무슨 점이 있나" 까지만 말한다. 현장이 받는 양식은 한 점마다
  **태그 · 종류 · 신호 · 입출력 범위**를 요구한다.

      SYSTEM  POINT             DESCRIPTION      종류  신호        RANGE
      AHU     AHU01-SATEMP      AHU01 급기온도     T    PT1000Ω    LOW~HIGH

  그 넷이 없으면 "모델만 고르면 포인트리스트가 나온다" 가 성립하지 않는다 —
  무슨 점인지는 알아도 **어떤 태그로 어떻게 배선하나**를 못 말하기 때문이다.

  ⚠ 종류·신호는 **유도한다.** 327행에 손으로 적으면 다음 계열에서 또 적어야 하고,
    적다 말면 반쯤 빈 칸이 남는다. 유도가 틀리는 행만 행에 직접 적는다(formKind/formSignal).
"""
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
FORM = os.path.join(DATA, "pointlist-form.json")


def load():
    return json.load(io.open(FORM, encoding="utf-8"),
                     object_pairs_hook=collections.OrderedDict)


def derive(row, form=None):
    """행 → (종류, 신호). 사전의 규칙을 위에서부터 먼저 맞는 것으로.

    행이 직접 적어 두었으면(formKind/formSignal) 그것이 이긴다 — 유도는 기본값일 뿐이다.
    """
    form = form or load()
    if row.get("formKind") or row.get("formSignal"):
        return row.get("formKind", ""), row.get("formSignal", "")
    ot = (row.get("objectType") or "").upper()
    for rule in form["기본값유도"]["규칙"]:
        c = rule["조건"]
        if "unit" in c and (row.get("unit") or "") != c["unit"]:
            continue
        if "role" in c and (row.get("role") or "") != c["role"]:
            continue
        if "group" in c and (row.get("group") or "") != c["group"]:
            continue
        if "objectType" in c and c["objectType"] not in ot:
            continue
        return rule.get("종류", ""), rule.get("신호", "")
    return "", ""


def as_form(profile_id, profiles=None, form=None):
    """프로파일 → 양식 행 목록. 태그가 없는 행은 태그 칸이 빈다(지어내지 않는다)."""
    form = form or load()
    if profiles is None:
        profiles = json.load(io.open(os.path.join(DATA, "equip-templates.json"),
                                     encoding="utf-8"))["profiles"]
    p = profiles.get(profile_id) or {}
    system = p.get("system") or ""
    out = []
    for r in p.get("templatePoints") or []:
        kind, sig = derive(r, form)
        out.append(collections.OrderedDict([
            ("SYSTEM", system),
            ("POINT", r.get("tag") or ""),
            ("DESCRIPTION", r.get("name") or ""),
            ("POINT TYPE", r.get("objectType") or ""),
            ("종류", kind), ("신호", sig),
            ("LOW", r.get("formLow", "")), ("HIGH", r.get("formHigh", "")),
            ("등급", r.get("grade") or ""),
            ("근거", r.get("tagFrom") or ""),
        ]))
    return out


def to_xlsx(pid, out_path, profiles=None, form=None):
    """현장 양식 그대로 엑셀로 — 시운전 담당자가 받아 그대로 쓰는 물건.

    ⚠ 양식의 머리글·칸 차례를 **그대로** 쓴다(docs/포인트리스트_양식_20260911.xlsx).
      우리 편한 대로 바꾸면 현장에서 다시 옮겨 적어야 한다 — 그러면 안 쓴다.
    ⚠ 우리가 모르는 칸은 **비워 둔다.** 설치 위치·판넬 NO·ADD·노드·디바이스는 현장 것이다.
      지어내서 채우면 그 값이 그대로 배선된다.
    """
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side
    rows = as_form(pid, profiles, form)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "FP-1"
    thin = Side(style="thin", color="999999")
    box = Border(left=thin, right=thin, top=thin, bottom=thin)

    ws["A1"] = "POINT LIST(DDC)"
    ws["A1"].font = Font(bold=True, size=14)
    ws["A2"] = "* 설치 위치 및 판넬 NO :"
    ws["A3"] = "* 설 치 일 :          년      월      일"
    ws["A4"] = "* 계통(SYSTEM) : %s" % (rows[0]["SYSTEM"] if rows else "")
    ws["A5"] = ("* 이 표는 장비 템플릿에서 뽑은 것이다. 설비코드·ADD·노드·디바이스는 "
                "현장에서 채운다.")
    ws["A5"].font = Font(size=9, color="777777")

    head = ["명칭", "ADD", "POINT TYPE", "NO", "SYSTEM", "POINT",
            "D E S C R I P T I O N", "종류", "신호", "LOW(0)", "HIGH(1)", "등급", "태그 근거"]
    for i, h in enumerate(head, 1):
        c = ws.cell(row=7, column=i, value=h)
        c.font = Font(bold=True, size=9)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = box
    for n, r in enumerate(rows, 1):
        vals = ["", "", r["POINT TYPE"], n, r["SYSTEM"], r["POINT"], r["DESCRIPTION"],
                r["종류"], r["신호"], r["LOW"], r["HIGH"], r["등급"], r.get("근거", "")]
        for i, v in enumerate(vals, 1):
            c = ws.cell(row=7 + n, column=i, value=v)
            c.font = Font(size=9)
            c.border = box
    for col, w in zip("ABCDEFGHIJKLM",
                      (10, 8, 11, 5, 10, 16, 30, 5, 13, 8, 8, 6, 9)):
        ws.column_dimensions[col].width = w
    ws.freeze_panes = "A8"
    wb.save(out_path)
    return len(rows)


def main(argv):
    form = load()
    profiles = json.load(io.open(os.path.join(DATA, "equip-templates.json"),
                                 encoding="utf-8"))["profiles"]
    if "--check" in argv:
        bad = collections.Counter()
        notag = collections.Counter()
        for pid, p in profiles.items():
            for r in p.get("templatePoints") or []:
                k, s = derive(r, form)
                if not s:
                    bad[pid] += 1
                if not r.get("tag"):
                    notag[pid] += 1
        print("■ 신호를 못 고른 행 (유도 규칙에 안 걸린다)")
        for pid, n in bad.most_common():
            print("   %-16s %d" % (pid, n))
        print("   합계 %d" % sum(bad.values()))
        print()
        print("■ 태그가 아직 없는 행")
        for pid, n in notag.most_common():
            print("   %-16s %d" % (pid, n))
        print("   합계 %d" % sum(notag.values()))
        return 0
    if "--xlsx" in argv:
        i = argv.index("--xlsx")
        pid = argv[i + 1] if i + 1 < len(argv) else "e5.ahu"
        out = os.path.join(HERE, "..", "review", "export",
                           "포인트리스트_%s.xlsx" % pid.replace(".", "-"))
        os.makedirs(os.path.dirname(out), exist_ok=True)
        n = to_xlsx(pid, out, profiles, form)
        print("→ %s  (%d행)" % (os.path.relpath(out, HERE), n))
        return 0
    pid = argv[0] if argv else "e5.ahu"
    rows = as_form(pid, profiles, form)
    print("■ %s — 양식 모양 %d행 (SYSTEM=%s)"
          % (pid, len(rows), profiles.get(pid, {}).get("system") or "(아직 없음)"))
    print("   %-18s %-24s %-10s %-3s %-12s %s"
          % ("POINT", "DESCRIPTION", "TYPE", "종류", "신호", "등급"))
    for r in rows:
        print("   %-18s %-24s %-10s %-3s %-12s %s"
              % (r["POINT"][:18], r["DESCRIPTION"][:24], r["POINT TYPE"][:10],
                 r["종류"], r["신호"][:12], r["등급"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
