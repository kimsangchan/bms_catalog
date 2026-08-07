# -*- coding: utf-8 -*-
"""Audit curated Unit Model Number records for cross-column or cross-table drift.

This is a QA report, not a validator gate. Vendor catalogs use different table
layouts, so repeated model numbers are not always wrong. The report separates:
duplicates with conflicting field values, sparse records, and records sourced
only from a "(Continued)" table.

Run:
  PYTHONIOENCODING=utf-8 python audit_units.py
"""
import argparse
import glob
import json
import os
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
UNITS = os.path.join(DATA, "units")

META_FIELDS = {
    "unitModelNumber", "unitNumberKind", "unitRole", "status", "selectionStatus",
    "source", "units",
}


def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def unit_fields(unit):
    if "fields" in unit:
        return {
            fid: (entry or {}).get("value")
            for fid, entry in (unit.get("fields") or {}).items()
            if (entry or {}).get("value") and (entry or {}).get("value") != "—"
        }
    return {
        key: value for key, value in unit.items()
        if key not in META_FIELDS and value and value != "—"
    }


def source(unit):
    src = unit.get("source") or {}
    return {
        "file": src.get("file") or unit.get("sourceFile") or "",
        "page": src.get("page") or unit.get("sourcePage") or "",
        "table": src.get("table") or unit.get("sourceTable") or "",
    }


def audit_doc(path):
    doc = load_json(path)
    by_code = defaultdict(list)
    sparse = []
    continued_only = []
    for unit in doc.get("units") or []:
        code = unit.get("unitModelNumber") or ""
        fields = unit_fields(unit)
        src = source(unit)
        by_code[code].append((unit, fields, src))
        if len(fields) <= 3:
            sparse.append((code, sorted(fields), src))
        table_name = (src.get("table") or "").lower()
        if "continued" in table_name and "+ continued" not in table_name:
            continued_only.append((code, sorted(fields), src))

    duplicate_conflicts = []
    for code, items in by_code.items():
        if len(items) < 2:
            continue
        seen = {}
        conflicts = []
        for _unit, fields, src in items:
            for fid, value in fields.items():
                if fid in seen and seen[fid][0] != value:
                    conflicts.append((fid, seen[fid][0], value, seen[fid][1], src))
                else:
                    seen.setdefault(fid, (value, src))
        duplicate_conflicts.append((code, len(items), conflicts, [src for _u, _f, src in items]))

    return {
        "modelId": doc.get("modelId") or os.path.splitext(os.path.basename(path))[0],
        "equipId": doc.get("equipId") or "",
        "count": len(doc.get("units") or []),
        "sparse": sparse,
        "continuedOnly": continued_only,
        "duplicateConflicts": duplicate_conflicts,
    }


def print_report(reports, include_sparse):
    total_conflicts = 0
    total_continued = 0
    total_sparse = 0
    for report in reports:
        conflicts = [item for item in report["duplicateConflicts"] if item[2]]
        continued = report["continuedOnly"]
        sparse = report["sparse"]
        total_conflicts += len(conflicts)
        total_continued += len(continued)
        total_sparse += len(sparse)
        if not conflicts and not continued and not (include_sparse and sparse):
            continue
        print("\n■ %s  (%s · %d units)" % (
            report["modelId"], report["equipId"], report["count"]))
        for code, count, items, sources in conflicts:
            print("  ! duplicate-conflict %s ×%d" % (code, count))
            for fid, old, new, old_src, new_src in items[:5]:
                print("    - %s: %s  <>  %s" % (fid, old, new))
                print("      old p%s %s" % (old_src.get("page"), old_src.get("table")))
                print("      new p%s %s" % (new_src.get("page"), new_src.get("table")))
        for code, fields, src in continued[:10]:
            print("  ? continued-only %s fields=%s p%s %s" % (
                code, ",".join(fields), src.get("page"), src.get("table")))
        if include_sparse:
            for code, fields, src in sparse[:10]:
                print("  ? sparse %s fields=%s p%s %s" % (
                    code, ",".join(fields), src.get("page"), src.get("table")))
    print("\n요약: duplicate-conflict %d건 · continued-only %d건 · sparse %d건" % (
        total_conflicts, total_continued, total_sparse))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--include-sparse", action="store_true",
                    help="값 3개 이하 레코드도 모두 출력")
    args = ap.parse_args()
    reports = [audit_doc(path) for path in sorted(glob.glob(os.path.join(UNITS, "*.json")))]
    print_report(reports, args.include_sparse)


if __name__ == "__main__":
    main()
