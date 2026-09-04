# -*- coding: utf-8 -*-
"""LS ELECTRIC H100 인버터 — BACnet/IP 오브젝트 목록 취입.

  PYTHONIOENCODING=utf-8 python ingest_ls.py            바꿀 내용만 보여 준다
  PYTHONIOENCODING=utf-8 python ingest_ls.py --run      실제로 기록한다

무엇을 세우나
  제품 = H100 인버터, 판 = **BACnet/IP 이더넷 옵션 모듈**(D-016).
  오브젝트를 내보내는 것은 본체가 아니라 이 옵션 카드다 — JCI SC-EQ 통신카드,
  LG AC Smart 게이트웨이를 세운 것과 같은 자리다.
  같은 카드가 EtherNet/IP · Modbus TCP 도 하지만 그 둘은 오브젝트 목록이 아니라
  레지스터·인스턴스 표다. 판을 나눠 따로 취입해야 하므로 여기서는 손대지 않는다.

⚠ 표가 여러 쪽에 걸쳐 **머리글 없이** 이어진다(AI 는 3쪽, BI 는 2쪽).
  이어지는 표는 앞 머리글을 물려받되 **열 수가 다르면 멈춘다** — 조용히 열이
  밀리면 이름 자리에 설명이 들어간다.

⚠ 열의 뜻을 열 이름으로 정한다. 같은 4번째 열이 계열마다 다른 것을 담는다:
    AV  'Range (REAL)'            → 값 범위   (스키마에 단위중립 range 자리가 없다)
    AI  'Units REAL'              → 단위
    BV  'Active / Inactive Text'  → 참/거짓 표기
    MSV 'Range Enumeration'       → 상태 열거
    MSI 'Units Enumeration'       → 상태 열거
  열 이름을 안 보고 위치로 읽으면 MSV 의 열거가 단위 자리에 들어간다.
"""
import collections
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")

SRC_ID = "ls-electric-h100"
DOC = "LS_H100_BACnetIP_EN_V1.0_210526.pdf"     # 두 문서 중 오브젝트 목록을 가진 쪽
MODEL_ID = "ls-electric-h100-vfd"
FAMILY = "Drive/BACnet"
IFACE_ID = "bacnet-ip"

# 오브젝트 타입 → common.pointKind. 문서 원문이 아니라 **규정된 파생**이다 —
# vendor_jci_sceq_config.KIND 와 같은 표를 쓴다(두 벌이 되면 어긋난다).
KIND = {"AV": "analog", "AI": "analog", "AO": "analog",
        "BV": "binary", "BI": "binary", "BO": "binary",
        "MSV": "code", "MSI": "code", "MSO": "code"}

ROW = re.compile(r"^(AV|AO|AI|BV|BO|BI|MSV|MSO|MSI)(\d+)$")
SECT = re.compile(r"(11\.2\.5\.\d+)\s+((?:Multi\s*State|Analog|Binary)\s+"
                  r"(?:Value|Input|Output)\s+Object Instance)", re.I)
# 절 제목 낱말 → 오브젝트 타입. 제목을 읽어 맞추므로 절 번호를 셈하지 않는다.
SECT_TYPE = {("analog", "value"): "AV", ("analog", "input"): "AI",
             ("binary", "value"): "BV", ("binary", "input"): "BI",
             ("multistate", "value"): "MSV", ("multistate", "input"): "MSI"}


def ledger_entry():
    """대장에서 원문을 찾는다 — 폴더를 훑으면 그 PC 에만 묶인다."""
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file") == DOC:
            return url, v
    raise SystemExit("대장에 %s / %s 가 없다 — collect.py --run %s" % (SRC_ID, DOC, SRC_ID))


def printed_no(page, fallback):
    """머리글의 인쇄 쪽번호. 이 문서는 PDF 쪽 - 5 지만 **가정하지 않고 읽는다**."""
    for line in page.get_text().splitlines()[:5]:
        s = line.strip()
        if s.isdigit() and 1 <= int(s) <= 999:
            return int(s)
    return fallback


def sections(doc):
    """절 제목을 문서에서 읽어 오브젝트 타입에 붙인다 — 절 번호를 셈하지 않는다."""
    out = {}
    for i in range(doc.page_count):
        for num, title in SECT.findall(doc[i].get_text()):
            w = re.sub(r"\s+", "", title).lower()
            for (a, b), ty in SECT_TYPE.items():
                if w.startswith(a) and w[len(a):].startswith(b):
                    out[ty] = "%s %s" % (num, re.sub(r"\s+", " ", title).strip())
    return out


def header_of(rows, first_data):
    """머리글이 여러 줄에 갈려 있다 — 열마다 이어 붙인다('Unit'+'s' → 'Units')."""
    ncol = max(len(r) for r in rows)
    cols = []
    for c in range(ncol):
        parts = []
        for r in rows[:first_data]:
            v = ((r[c] if c < len(r) else "") or "").strip()
            if v and v not in parts:
                parts.append(v)
        cols.append(re.sub(r"\s+", " ", " ".join(parts)).strip())
    # 'Unit s' 처럼 낱말이 두 줄로 갈린 자리를 되붙인다
    return [re.sub(r"Unit s", "Units", c) for c in cols]


def role_of(label):
    """열 이름 → 하는 일. 못 알아본 열이 있으면 부르는 쪽에서 멈춘다."""
    lo = (label or "").lower()
    if "instance" in lo:
        return "instance"
    if "object name" in lo:
        return "name"
    if "description" in lo:
        return "desc"
    if "enumeration" in lo:
        return "states"
    if "units" in lo:
        return "units"
    if "range" in lo:
        return "range"
    if "active" in lo or "inactive" in lo:
        return "activeText"
    if lo.replace(" ", "") in ("r/w", "rw"):
        return "rw"
    return None


def extract(doc, pages):
    """표에서 포인트를 뽑는다. 이어지는 표는 앞 머리글을 물려받는다."""
    head, headpage, out = None, None, []
    for p in pages:
        page = doc[p - 1]
        pr = printed_no(page, p)
        for t in page.find_tables().tables:
            rows = [r for r in t.extract() if any((c or "").strip() for c in r)]
            if not rows:
                continue
            first = next((n for n, r in enumerate(rows)
                          if ROW.match(((r[0] or "").strip()))), None)
            if first is None:
                continue
            # 데이터 행 앞에 오는 것이 **머리글일 수도, 앞 쪽 마지막 행의 꼬리일 수도**
            # 있다. 실제로 30쪽은 'setting**' 한 조각으로 시작한다 — AV4 의 설명이
            # 쪽을 넘어 갈린 것이다. 머리글로 오인하면 열 이름이 통째로 어그러지고,
            # 그냥 버리면 AV4 설명이 'Command frequency' 에서 끊긴다.
            # 가르는 근거는 원문에 있다: 진짜 머리글의 첫 칸은 'Instance' 로 시작한다.
            if first and "instance" in " ".join(
                    ((r[0] or "").strip()) for r in rows[:first]).lower():
                head = header_of(rows, first)
                headpage = pr
                bad = [c for c in head if c and role_of(c) is None]
                if bad:
                    raise SystemExit("모르는 열 이름: %s (원문 %d쪽) — role_of 를 넓혀라"
                                     % (bad, pr))
            elif first and out:
                tail = out[-1]["points"][-1]
                for r in rows[:first]:
                    for c, label in enumerate(head or []):
                        v = re.sub(r"\s+", " ", str(r[c] or "").strip()) if c < len(r) else ""
                        if v and label:
                            tail["cols"][label] = (tail["cols"].get(label, "") + " " + v).strip()
            if head is None:
                raise SystemExit("머리글 없이 시작하는 표 (원문 %d쪽)" % pr)
            # 열 수가 어긋나면 값이 통째로 한 칸씩 밀린다. 조용히 넘기지 않는다.
            ncol = max(len(r) for r in rows[first:])
            if ncol != len(head):
                raise SystemExit("열 수가 머리글과 다르다: 원문 %d쪽 %d열 vs %s쪽 머리글 %d열"
                                 % (pr, ncol, headpage, len(head)))
            pts = []
            for r in rows[first:]:
                m = ROW.match(((r[0] or "").strip()))
                if not m:
                    continue
                rec = {"type": m.group(1), "inst": int(m.group(2)), "cols": {}}
                for c, label in enumerate(head):
                    v = re.sub(r"\s+", " ", str(r[c] or "").strip()) if c < len(r) else ""
                    if v and label:
                        rec["cols"][label] = v
                pts.append(rec)
            if pts:
                out.append({"page": p, "printed": pr, "head": list(head), "points": pts})
    return out


def name_col(head):
    return next((h for h in head if role_of(h) == "name"), None)


def crosscheck(doc, tables):
    """표 인식이 아닌 **쪽 글자 흐름**에서 'AV1 CommTimeoutSet' 짝을 다시 읽어 맞춘다.

    같은 판독기로 두 번 읽으면 같은 맹점을 그대로 통과한다. find_tables 를 쓰지 않고
    get_text 의 글자를 공백만 지워 이어 붙인 뒤, 인스턴스 ID 바로 뒤에 오브젝트
    이름이 붙어 있는지 본다 — 열이 한 칸 밀리면 여기서 어긋난다.
    """
    flat = {t["page"]: re.sub(r"\s+", "", doc[t["page"] - 1].get_text()) for t in tables}
    same, total, diff = 0, 0, []
    for t in tables:
        nc = name_col(t["head"])
        for p in t["points"]:
            total += 1
            nm = p["cols"].get(nc, "") if nc else ""
            probe = re.sub(r"\s+", "", "%s%d%s" % (p["type"], p["inst"], nm))
            if nm and probe in flat[t["page"]]:
                same += 1
            elif len(diff) < 8:
                diff.append("%d쪽 %s%d %s" % (t["printed"], p["type"], p["inst"], nm))
    return {"method": "쪽 글자 흐름에서 '인스턴스ID+오브젝트이름' 을 다시 읽어 맞췄다"
                      "(표 인식 경로가 아니다)",
            "total": total, "both": same,
            "rate": round(same / total, 4) if total else 0.0, "diff": diff}


def states_of(raw):
    """'0: None 1: FreeRun …' · '1 Hz 2 RPM' → [{code,label}].

    코드가 둘 이상 붙어 있을 때만 만든다 — 자유 문장에서 지어내면 시뮬레이터가 믿는다.
    """
    hits = re.findall(r"(?:^|\s)(\d+)\s*:?\s+([A-Za-z][\w/+-]*)", raw)
    return [{"code": c, "label": l} for c, l in hits] if len(hits) >= 2 else []


def build(meta, tables, sect, cc):
    seen, pts, pages = set(), [], []
    for t in tables:
        pages.append(t["printed"])
        role = {h: role_of(h) for h in t["head"]}
        for p in t["points"]:
            oid = "%s%d" % (p["type"], p["inst"])
            if oid in seen:
                raise SystemExit("같은 오브젝트가 두 번 나온다: %s (원문 %d쪽)"
                                 % (oid, t["printed"]))
            seen.add(oid)
            common, src, gaps = {}, {"Instance ID": oid}, []
            for label, v in p["cols"].items():
                r = role[label]
                if r == "instance":
                    continue
                src[label] = v
                if r == "name":
                    common["name"] = v
                elif r == "desc":
                    common["note"] = v
                elif r == "rw" and v in ("R", "W", "R/W"):
                    common["readWrite"] = v
                elif r == "units" and v != "-" and KIND.get(p["type"]) != "code":
                    # 단위 열은 하나뿐이고 대부분 SI 다. HP(마력)만 야드파운드라
                    # 그 한 줄을 unitIP 로 보낸다 — 열이 아니라 **값**을 보고 가른다.
                    # ⚠ 코드형(MSV·MSI)은 뺀다. MSV1 의 단위 칸은 'MSG' 인데 이건
                    #    물리량이 아니라 자료형 표시다 — unitSI 에 넣으면 거짓이 된다.
                    #    원문은 sourceColumns 에 그대로 남는다.
                    k = "unitIP" if v.upper() == "HP" else "unitSI"
                    common[k] = common[k + "Raw"] = v
                elif r == "states":
                    st = states_of(v)
                    if st:
                        common["states"] = st
                        # MSV 상태값 보정: 원문에 'add 1 to number' 같은 노트가 없다.
                        # 0 으로도 1 로도 단정하지 않고 모른다고 적는다(스키마 v2.2 선례).
                        gaps.append("blocks.bacnet.msvOffset — 원문이 BACnet MSV 상태값 "
                                    "보정을 밝히지 않는다. 표의 코드는 %s 부터다."
                                    % st[0]["code"])
                elif r == "range":
                    gaps.append("common.range — 원문 'Range' 열은 sourceColumns 에만 "
                                "남겼다. 포인트 스키마에 단위중립 범위 자리가 없다"
                                "(rangeIP·rangeSI 는 야드파운드/SI 쌍을 주는 계통 전용).")
            kind = KIND.get(p["type"])
            if kind:
                common["pointKind"] = kind
            g = sect.get(p["type"])
            if g:
                common["group"] = g
            prov = {"sourceFile": meta["file"], "sourcePage": t["printed"],
                    "family": FAMILY, "sourceColumns": src,
                    "status": "extracted", "interfaceId": IFACE_ID}
            if gaps:
                prov["gaps"] = sorted(set(gaps))
            pts.append({
                "common": common,
                "blocks": {"bacnet": {"objectType": p["type"], "instance": p["inst"]}},
                "provenance": prov,
            })

    iface = {
        "id": IFACE_ID,
        "label": "BACnet/IP 이더넷 옵션 모듈",
        "family": FAMILY,
        "protocols": ["bacnet"],
        "sourceFile": meta["file"],
        "sourcePages": sorted(set(pages)),
        "pointCount": len(pts),
        "appliesTo": ["H100"],
        "status": "extracted",
        "note": ("인버터에 꽂는 이더넷 통신 옵션 카드가 내보내는 오브젝트 목록. "
                 "오브젝트 인스턴스 번호는 표가 직접 준다(AV1·BI30 꼴). "
                 "디바이스 오브젝트의 인스턴스만 표에 없고 키패드 COM-84·COM-85 로 "
                 "정한다(원문 28쪽). 같은 카드가 EtherNet/IP · Modbus TCP 도 하지만 "
                 "그 둘은 오브젝트 목록이 아니라 별도의 인스턴스·레지스터 표라 "
                 "이 판에 섞지 않았다."),
        "gaps": ["Device Object 의 인스턴스 번호 — 현장에서 COM-84·COM-85 로 정한다(원문 28쪽).",
                 "EtherNet/IP · Modbus TCP 표(원문 36~60쪽)는 아직 취입하지 않았다."],
        "points": pts,
    }
    return {
        "id": MODEL_ID,
        "equipId": "e15",
        "vendor": "LS ELECTRIC",
        "model": "H100",
        "name": "H100 팬·펌프 전용 인버터",
        "cat": "HVAC.AUX.VFD",
        "tag": "vfd",
        "tags": ["vfd"],
        "status": "active",
        "classifiedBy": ("팬·펌프 전용 드라이브다 — Danfoss FC-101 을 HVAC.AUX.VFD 로 "
                         "둔 것과 같은 자리."),
        "summary": "BACnet/IP 옵션 매뉴얼 1건 · 판 1개에서 취입 — 오브젝트 %d점" % len(pts),
        "has": {"spec": False, "points": True},
        "ede": False,
        "spec": [], "io": [], "elec": None, "points": [],
        "gap": ("정격·형번이 없다 — 이 문서는 통신 옵션 매뉴얼이다. 용량별 형번과 정격은 "
                "본체 매뉴얼(LS_H100_UserManual_EN_190621.pdf, 같은 소스로 대장에 있다)에 "
                "있고 아직 취입하지 않았다. 오브젝트의 'Range' 열도 sourceColumns 에만 "
                "있다 — 스키마에 단위중립 범위 자리가 없다."),
        "extractor": "ingest_ls",
        "sourceDoc": meta["file"],
        "interfaces": [iface],
        "crosscheck": cc,
    }


def object_pages(doc):
    """오브젝트 표가 실린 쪽 — 절 제목이 있거나 본문에 'AV1' 꼴 줄이 있는 쪽."""
    out = []
    for i in range(doc.page_count):
        txt = doc[i].get_text()
        if SECT.search(txt) or any(ROW.match(l.strip()) for l in txt.splitlines()):
            out.append(i + 1)
    return out


def main(argv):
    import fitz
    run = "--run" in argv
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    sect = sections(doc)
    tables = extract(doc, object_pages(doc))
    types = sorted({p["type"] for t in tables for p in t["points"]})
    missing = [ty for ty in types if ty not in sect]
    if missing:
        raise SystemExit("절 제목을 못 찾은 오브젝트 타입: %s — SECT 를 넓혀라" % missing)

    cc = crosscheck(doc, tables)
    model = build(meta, tables, sect, cc)
    iface = model["interfaces"][0]

    print("모델 %s — 판 %s · %d점" % (model["id"], iface["id"], iface["pointCount"]))
    per = collections.Counter(p["blocks"]["bacnet"]["objectType"] for p in iface["points"])
    for ty in types:
        print("   %-4s %2d점   %s" % (ty, per[ty], sect[ty]))
    print("   원문 %s쪽 (PDF %s)" % (iface["sourcePages"], [t["page"] for t in tables]))
    print("   교차 대조 %d/%d = %.1f%% (%s)"
          % (cc["both"], cc["total"], 100 * cc["rate"], cc["method"]))
    if cc["diff"]:
        print("   ⚠ 안 맞은 것:", " · ".join(cc["diff"]))

    out = os.path.join(DATA, "models", MODEL_ID + ".json")
    if not run:
        print("\n(미리보기다. 기록하려면 --run)")
        return 0
    with io.open(out, "w", encoding="utf-8", newline="\n") as f:
        json.dump(model, f, ensure_ascii=False, indent=1)
        f.write("\n")
    print("\n→ %s" % os.path.relpath(out, HERE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
