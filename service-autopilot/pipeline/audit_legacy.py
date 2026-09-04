# -*- coding: utf-8 -*-
"""옛 평면 `points[]` 손실 잣대 — 무엇이 얼마나 비었나를 전수로 센다.

왜 있나
  LG 공조기 킷에서 원문 `Value explanation` 열을 통째로 버려 47점이 상태 0 ·
  범위 0 · 단위 0 이었다. 개수만 맞고 내용이 비어 있었다. 같은 부류가 평면
  24,376점에 더 있는지 세려고 만들었다. 재취입할 때마다 다시 돌려 줄어드는지 본다.

무엇을 세나
  (1) 필드   — 옛 레코드에는 상태·범위·읽기쓰기를 담을 **칸 자체가 없다**.
               그래서 그런 값은 비고 문장으로 눌리거나 사라진다.
  (2) 비고   — 서로 다른 원문 칸이 ' · ' 하나로 뭉친 점. 240자에서 잘린 점.
  (3) 원문   — `--docs`. 원문 표를 다시 열어 추출기가 **집지 않은 칸**의 값을 센다.

⚠ 판정을 추출기 출력으로 하지 않는다. 옛 어댑터는 알아본 열을 되남기지 않아
   "원문 칸과 일치" 로는 판정할 수 없다(잣대를 두 번 틀렸던 자리다). 그래서
   원문을 다시 읽는다. 그리고 `--docs` 결과도 그대로 믿지 않는다 — 코드 흉내가
   틀린 만큼 틀리므로, 큰 항목은 값이 모델 어디에도 없는지 문자열로 되짚는다
   (실제로 York modbus 5열·Systemair BACnet/Function 이 이 되짚기에서 오탐으로 걸렸다).
"""
import json, glob, os, re, sys, collections

HERE = os.path.dirname(os.path.abspath(__file__))
MODELS = os.path.join(HERE, "data", "models")

# 비고 문장에 눌려 들어간 원문 칸 — 머리표로 어느 칸이었는지 되짚는다
NOTE_KINDS = {
    "상태 열거": r"(?:^|[\s·(])\d{1,3}\s*[=:]\s*[A-Za-z가-힣]",
    "범위": r"범위 ",
    "기본값": r"기본 ",
    "쓰기 가능": r"쓰기 가능",
    "조건": r"조건: ",
    "벤더 코드": r"코드 ",
    "원문 주소 표기": r"원표기 ",
    "BACnet 주소": r"BACnet [A-Z]{2}, \d",
    "BACnet OID": r"BACnet OID",
    "Modbus 주소": r"Modbus (?:reg|coil|\w+) \d",
}


def survey():
    """모델별 손실 지표 — 원문 없이 레코드만 본다."""
    out = []
    for f in sorted(glob.glob(os.path.join(MODELS, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        lp = d.get("points") or []
        if not lp:
            continue
        r = {"id": d["id"], "n": len(lp), "vendor": d.get("vendor"),
             "unit": sum(1 for p in lp if p.get("unit")),
             "states": sum(1 for p in lp if p.get("states")),
             "rw": sum(1 for p in lp if p.get("readWrite")),
             "빈 비고": sum(1 for p in lp if not (p.get("note") or "")),
             "뭉친 비고": sum(1 for p in lp if " · " in (p.get("note") or "")),
             "잘린 비고": sum(1 for p in lp if len(p.get("note") or "") >= 239),
             "출처없음": sum(1 for p in lp if not p.get("sourceFile")),
             "kinds": collections.Counter()}
        for p in lp:
            note = p.get("note") or ""
            for k, pat in NOTE_KINDS.items():
                if re.search(pat, note):
                    r["kinds"][k] += 1
        out.append(r)
    return out


def dropped_columns():
    """원문 표에서 추출기가 집지 않은 칸의 값 수 — 느리다(원문 PDF 를 다시 연다)."""
    import extract as E
    import fitz

    def consumed(hdr):
        idx = E._mk_idx(hdr)
        i_id, i_nm = idx(*E.COL["id"]), idx(*E.COL["name"])
        i_mb = idx(*E.COL["modbus"])
        if i_id < 0 and i_mb >= 0:
            i_id = i_mb
            if i_nm < 0:
                i_nm = idx(*E.COL["desc"])
        i_ty, i_in = idx(*E.COL["objtype"]), idx(*E.COL["instance"])
        split = i_ty >= 0 and i_in >= 0 and i_ty != i_in
        if (i_id < 0 and not split) or i_nm < 0:
            return None
        i_ds = idx(*E.COL["desc"])
        got = {i_id, i_nm, -1 if i_ds == i_nm else i_ds,
               idx(*E.COL["unit"]), idx(*E.COL["range"]), idx(*E.COL["rw"]),
               idx(*E.COL["dep"]), idx(*E.COL["states"]), idx(*E.COL["notes"]),
               idx("object name"), idx("bacoid", "bac oid"), idx("relinquish"),
               idx("register\naddres", "register address", "address"),
               idx("register\ntype", "register type"), idx("modbus type"),
               idx("bacnet"), idx("function"),
               idx("modbus scale factor", "scale factor"),
               idx("modbus boolean flag", "boolean flag"),
               idx("modbus signed flag", "signed flag"),
               idx("modbus offset", "offset"),
               idx("modbus writable flag", "writable flag")}
        if split:
            got |= {i_ty, i_in}
        return {i for i in got if i >= 0}

    # ID 열의 복사본·행번호는 손실이 아니다
    SKIP = {"no.", "object instance", "#", "item"}
    lost = collections.Counter()
    for f in sorted(glob.glob(os.path.join(MODELS, "*.json"))):
        d = json.load(open(f, encoding="utf-8"))
        lp = d.get("points") or []
        if not lp:
            continue
        bysrc = collections.defaultdict(set)
        for p in lp:
            if p.get("sourceFile") and p.get("sourcePage"):
                bysrc[p["sourceFile"]].add(p["sourcePage"])
        # 쪽을 안 남긴 모델은 문서 전체를 훑는다. 출처가 아예 없는 모델(Vertiv 19건 등)은
        # 여기서 못 센다 — 재취입 때 sourceFile/sourcePage 부터 남겨야 셀 수 있다.
        if not bysrc and isinstance(d.get("sourceDoc"), str) and d["sourceDoc"]:
            bysrc[d["sourceDoc"]] = None
        for sf, pages in bysrc.items():
            path = os.path.join(HERE, "data", "raw", sf)
            if not os.path.exists(path):
                continue
            doc = fitz.open(path)
            for pn in (sorted(pages) if pages else range(1, doc.page_count + 1)):
                if pn > doc.page_count:
                    continue
                try:
                    tabs = doc[pn - 1].find_tables()
                except Exception:
                    continue
                for t in tabs.tables:
                    data = t.extract()
                    if len(data) < 2:
                        continue
                    h0 = E._header_row(data)
                    if h0 is None:
                        continue
                    hdr = [E._c(c).lower() for c in data[h0]]
                    keep = consumed(hdr)
                    if keep is None:
                        continue
                    for j, h in enumerate(hdr):
                        name = re.sub(r"\s+", " ", h).strip()
                        if j in keep or not name or name in SKIP:
                            continue
                        v = sum(1 for r in data[h0 + 1:]
                                if j < len(r) and E._c(r[j]).strip())
                        if v:
                            lost[(d["id"], name)] += v
            doc.close()
        print("  …", d["id"], file=sys.stderr, flush=True)
    return lost


def selftest():
    got = {k for k, pat in NOTE_KINDS.items()
           if re.search(pat, "원표기 0x0007 · 0=manual reset, 1=auto reset")}
    assert got == {"원문 주소 표기", "상태 열거"}, got
    assert not re.search(NOTE_KINDS["상태 열거"], "코드 5008_1")   # 벤더 코드는 상태가 아니다
    assert re.search(NOTE_KINDS["BACnet 주소"], "BACnet BV, 10001")
    print("selftest ok")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
        raise SystemExit
    rows = survey()
    tot = sum(r["n"] for r in rows)
    print("평면 포인트 %d점 · %d모델" % (tot, len(rows)))
    print("필드 채움:  단위 %d · 상태 %d · 읽기쓰기 %d"
          % (sum(r["unit"] for r in rows), sum(r["states"] for r in rows),
             sum(r["rw"] for r in rows)))
    k = collections.Counter()
    for r in rows:
        k.update(r["kinds"])
    print("비고 문장에 눌린 원문 칸:")
    for name, v in k.most_common():
        print("   %-16s %6d점 (%.1f%%)" % (name, v, 100.0 * v / tot))
    print("뭉친 비고 %d · 240자에서 잘린 비고 %d · 출처 미기록 %d"
          % (sum(r["뭉친 비고"] for r in rows), sum(r["잘린 비고"] for r in rows),
             sum(r["출처없음"] for r in rows)))
    print()
    print("%-46s %6s %6s %6s %6s %6s" % ("모델", "점", "상태문", "뭉침", "빈비고", "단위"))
    for r in sorted(rows, key=lambda r: -(r["kinds"]["상태 열거"] + r["빈 비고"])):
        print("%-46s %6d %6d %6d %6d %6d"
              % (r["id"][:46], r["n"], r["kinds"]["상태 열거"], r["뭉친 비고"],
                 r["빈 비고"], r["unit"]))
    if "--docs" in sys.argv:
        print("\n원문에서 추출기가 집지 않은 칸 (값 개수)", file=sys.stderr)
        lost = dropped_columns()
        bym = collections.Counter()
        cols = collections.defaultdict(set)
        for (m, c), v in lost.items():
            bym[m] += v
            cols[m].add(c)
        print("\n=== 안 읽힌 원문 칸: 값 %d개 · %d모델 ===" % (sum(bym.values()), len(bym)))
        for m, v in bym.most_common():
            print("  %6d  %-44s  %s" % (v, m[:44], ", ".join(sorted(cols[m]))[:70]))
