# -*- coding: utf-8 -*-
"""포인트 목록 CSV 내보내기 — BMS 자동 매핑에 넣을 형태로.

  PYTHONIOENCODING=utf-8 python export_points.py                 국내 벤더 취입분
  PYTHONIOENCODING=utf-8 python export_points.py --all           전 모델
  PYTHONIOENCODING=utf-8 python export_points.py --only <모델id>
  PYTHONIOENCODING=utf-8 python export_points.py --out <폴더>

────────────────────────────────────────────────────────────────────────
왜 이 모양인가 — 인터페이스별인가 프로토콜별인가
────────────────────────────────────────────────────────────────────────
**행은 인터페이스로 가르고, 프로토콜은 열로 편다.** 둘 다 지원하는 것이 아니라
둘의 성격이 다르기 때문이다.

  · **인터페이스(판)가 파일을 가르는 축**이다. 현장에서 사람이 하는 일은
    "이 장비에 이 목록을 물린다" 이고, 그 '이 목록' 이 곧 판이다. 같은 제품이라도
    게이트웨이가 붙으면 판이 갈리고 펌웨어가 오르면 목록이 바뀐다(D-016).
    그래서 파일 하나 = 판 하나로 떨어뜨려야 BMS 에서 장비 하나에 그대로 물린다.

  · **프로토콜은 행을 가르는 축이 아니다.** 한 포인트가 BACnet·Modbus·N2·LON
    주소를 **동시에** 갖는다(JCI E-Link 는 한 행에 네 종류가 나란히 온다).
    프로토콜로 행을 쪼개면 같은 물리 포인트가 네 행이 되고, BMS 는 그것을 다시
    합쳐야 한다 — 합치는 열쇠가 CSV 에 없으면 합칠 수 없다.
    그래서 1행 = 1포인트로 두고 주소는 `bacnet.instance` · `modbus.address` 처럼
    **접두 열**로 편다. 어떤 프로토콜이 실제로 채워졌는지는 `protocols` 열이 말한다.
    특정 프로토콜만 쓰는 BMS 는 제 접두 열만 읽으면 되고, 아무것도 잃지 않는다.

  · 되읽기·차이보기의 열쇠는 `pointKey` 다 — `<모델>|<판>|<타입><인스턴스>`.
    인스턴스가 없는 목록(LG 게이트웨이)은 `<모델>|<판>|#<원문 포인트번호>` 로 떨어진다.

⚠ 주소가 **현장에서 정해지는** 목록이 있다. LG 게이트웨이는 이름이 `..._XXX` 이고
  인스턴스가 유닛 주소에 달려 있다. 그런 판은 `nameVariable`·`addressVar`·
  `instanceFormula` 열에 규칙을 실어 보낸다 — 값을 지어 넣지 않는다.
  BMS 가 유닛 주소를 알 때 그 자리에서 이름과 인스턴스를 만들면 된다.

⚠ 인코딩은 **UTF-8 BOM** 이다. BOM 이 없으면 Windows Excel 이 한글을 깨뜨린다.
"""
import argparse
import collections
import csv
import glob
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)

DEFAULT_OUT = os.path.join(HERE, "..", "review", "export")
DOMESTIC = ("ingest_lg", "ingest_ls")

# 모델·판을 말하는 열 (모든 행에 같은 값이 반복된다 — 파일 하나만 떼어 가도 뜻이 산다)
HEAD = ["pointKey", "modelId", "vendor", "model", "equipId", "cat", "tag",
        "interfaceId", "interface", "family", "protocols", "appliesTo"]
# 포인트 자체를 말하는 열
BODY = ["pointNo", "name", "nameVariable", "addressVar", "instanceFormula",
        "pointKind", "readWrite", "unit", "unitRaw", "unitSystem",
        "states", "statesNote", "group", "note"]
# 출처 (값을 의심할 때 되짚는 자리)
TAIL = ["sourceFile", "sourcePage", "status", "gaps", "rawColumns"]

COLDOC = {
    "pointKey": "되읽기·차이보기의 열쇠. <모델>|<판>|<타입><인스턴스>",
    "protocols": "이 판이 실제로 주소를 주는 프로토콜(빈 열은 안 만든다)",
    "nameVariable": "이름 안의 현장값 자리. 'XXX' 면 유닛 주소를 넣어 이름을 완성한다",
    "addressVar": "_XXX 가 무엇인지 — 예: 유닛 주소(Device*16+Product)",
    "instanceFormula": "인스턴스를 현장값에서 만드는 식. 값이 정해져 있으면 빈칸",
    "unitSystem": "SI · IP — 어느 단위계 열에서 왔는지",
    "states": "코드=이름 을 ; 로 이음. 예: 1=Cool;2=Dry",
    "statesNote": "BACnet present-value 와의 관계(보정값 msvOffset)",
    "rawColumns": "스키마 필드로 못 올린 원문 칸. 이름=값 을 ; 로 이음",
    "gaps": "문서가 안 주는 것. 이 열이 비어 있지 않으면 그 필드는 믿지 마라",
}

LG_ADDR = ("유닛 주소 XXX = Device×16 + Product",
           "instance = 제품유형×0x10000 + Device×0x1000 + Product×0x100 + Point No.")


def load(only, take_all):
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        m = json.load(io.open(f, encoding="utf-8"))
        if not (m.get("interfaces") or []):
            continue
        if only:
            if m["id"] not in only:
                continue
        elif not take_all and m.get("extractor") not in DOMESTIC:
            continue
        out.append(m)
    return out


def proto_columns(models):
    """실제로 값이 있는 프로토콜 필드만 열로 만든다 — 빈 열은 읽는 쪽을 헷갈리게 한다."""
    seen = collections.OrderedDict()
    for m in models:
        for iface in m["interfaces"]:
            for p in iface.get("points") or []:
                for blk, fields in (p.get("blocks") or {}).items():
                    for k, v in (fields or {}).items():
                        if v is not None and v != "":
                            seen["%s.%s" % (blk, k)] = True
    return list(seen)


def row(m, iface, p, pcols):
    c = p.get("common") or {}
    prov = p.get("provenance") or {}
    src = prov.get("sourceColumns") or {}
    blocks = p.get("blocks") or {}
    bac = blocks.get("bacnet") or {}

    inst = bac.get("instance")
    no = src.get("Point No.") or src.get("Instance ID") or ""
    ident = ("%s%s" % (bac.get("objectType") or "", inst)) if inst is not None \
        else ("#%s" % no if no else (c.get("name") or ""))

    name = c.get("name") or ""
    # ⚠ 이름 열에는 **정리된 이름**만 넣는다. sourceColumns 의 'Object Name' 은
    #    조판 아티팩트를 지우기 전 값이라('StartStopCommand_ XXX') 그대로 내보내면
    #    BMS 가 빈칸 낀 이름으로 오브젝트를 찾게 된다. 그 원문은 rawColumns 로 간다.
    is_tmpl = "XXX" in name
    unit = c.get("unitSI") or c.get("unitIP") or ""
    usys = "SI" if c.get("unitSI") else ("IP" if c.get("unitIP") else "")

    states = ";".join("%s=%s" % (s.get("code"), s.get("label"))
                      for s in (c.get("states") or []))
    off = bac.get("msvOffset")
    snote = ("표의 코드 + %d = BACnet present-value" % off) if off is not None else ""

    used = {str(x) for x in (no, name, c.get("note"), unit,
                             c.get("unitSIRaw"), c.get("unitIPRaw"),
                             c.get("readWrite"), bac.get("objectType")) if x}
    used |= {s.get("label") for s in (c.get("states") or [])}
    raw = ";".join("%s=%s" % (k, v) for k, v in src.items()
                   if v and str(v) not in used)

    r = {
        "pointKey": "%s|%s|%s" % (m["id"], iface["id"], ident),
        "modelId": m["id"], "vendor": m.get("vendor") or "",
        "model": m.get("model") or "", "equipId": m.get("equipId") or "",
        "cat": m.get("cat") or "", "tag": m.get("tag") or "",
        "interfaceId": iface["id"], "interface": iface.get("label") or "",
        "family": iface.get("family") or "",
        "protocols": " ".join(iface.get("protocols") or []),
        "appliesTo": " · ".join(iface.get("appliesTo") or []),
        "pointNo": no, "name": name,
        "nameVariable": "XXX" if is_tmpl else "",
        "addressVar": LG_ADDR[0] if is_tmpl else "",
        "instanceFormula": LG_ADDR[1] if (is_tmpl and inst is None) else "",
        "pointKind": c.get("pointKind") or "",
        "readWrite": c.get("readWrite") or "",
        "unit": unit, "unitRaw": c.get("unitSIRaw") or c.get("unitIPRaw") or "",
        "unitSystem": usys,
        "states": states, "statesNote": snote,
        "group": c.get("group") or "", "note": c.get("note") or "",
        "sourceFile": prov.get("sourceFile") or "",
        "sourcePage": prov.get("sourcePage") if prov.get("sourcePage") is not None else "",
        "status": prov.get("status") or "",
        "gaps": " | ".join(prov.get("gaps") or []),
        "rawColumns": raw,
    }
    for col in pcols:
        blk, field = col.split(".", 1)
        v = (blocks.get(blk) or {}).get(field)
        r[col] = "" if v is None else v
    return r


def write_csv(path, cols, rows):
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    # BOM 을 붙인다 — 없으면 Windows Excel 이 한글을 깨뜨린다
    with io.open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return len(rows)


def main(argv):
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--only", nargs="*", default=[])
    ap.add_argument("--out", default=DEFAULT_OUT)
    a = ap.parse_args(argv)

    models = load(set(a.only), a.all)
    if not models:
        raise SystemExit("담을 모델이 없다 — --only 이름을 확인하거나 --all")

    pcols = proto_columns(models)
    cols = HEAD + BODY + pcols + TAIL

    allrows, per = [], []
    for m in models:
        for iface in m["interfaces"]:
            rows = [row(m, iface, p, pcols) for p in (iface.get("points") or [])]
            if not rows:
                continue
            allrows += rows
            per.append((m["id"], iface["id"], rows))

    out = os.path.abspath(a.out)
    n = write_csv(os.path.join(out, "points.csv"), cols, allrows)
    for mid, iid, rows in per:
        write_csv(os.path.join(out, "by-interface", "%s__%s.csv" % (mid, iid)), cols, rows)
    write_csv(os.path.join(out, "_columns.csv"), ["column", "meaning"],
              [{"column": c, "meaning": COLDOC.get(c, "")} for c in cols])

    print("모델 %d · 판 %d · %d행 → %s" % (len(models), len(per), n, out))
    print("   points.csv                 전부 한 파일 (열 %d개)" % len(cols))
    print("   by-interface\\*.csv         판 하나 = 파일 하나 (BMS 에 그대로 물린다)")
    print("   _columns.csv               열 뜻풀이")
    print("   프로토콜 열: %s" % (", ".join(pcols) or "(없음)"))
    for mid, iid, rows in per:
        print("      %-34s %4d행" % ("%s / %s" % (mid, iid), len(rows)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
