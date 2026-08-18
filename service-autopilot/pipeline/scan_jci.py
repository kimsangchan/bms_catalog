# -*- coding: utf-8 -*-
"""JCI 문서 **본문** 전수 스캔 — 포인트 표를 품은 문서를 찾는다.

왜 본문인가
  제목만 보고 골랐더니 공조기·옥상형이 통째로 빠졌다. JCI 는 냉동기만 포인트
  리스트를 별도 문서로 내고, 공조기·자립형은 232쪽짜리 **IOM 매뉴얼 본문**에
  포인트 표를 묻어 둔다(실측: Millenium 옥상형 p180~ 419행 · Versecon p127~ 181행).
  제목에는 그 낌새가 없다 — 'Installation, Operation and Maintenance' 다.

어떻게 싸게 하나
  ① 표 인식(find_tables)은 느리다 → **페이지 텍스트**에서 머리글 낱말을 먼저 찾는다.
  ② 걸린 문서만 표 인식으로 행수를 센다.
  ③ 걸리지 않은 원문은 **지운다**. 5.7GB 를 남길 이유가 없다(D-008 — 원문은 보관 안 한다).

실행
  PYTHONIOENCODING=utf-8 python scan_jci.py --slice 0/6      # 6조각 중 0번
  PYTHONIOENCODING=utf-8 python scan_jci.py --merge          # 조각 합치기

입력과 산출물
  data/_jci_scan_tiers.json 의 t1은 JCI 포털 카탈로그 스냅샷에서 문서 성격으로
  좁힌 1,492건의 **고정 후보 목록**이며 저장소에 함께 둔다. 각 조각의 hits 파일은
  재생 가능한 중간물이어서 gitignore 하고, merge 결과 jci-body-scan.json만 근거로
  추적한다. 포털 전체 최신 목록을 다시 열거하는 일과 이 고정 코퍼스를 재검증하는
  일을 섞지 않는다.
"""
import argparse, io, json, os, re, sys, time, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
TMP = os.path.join(DATA, "raw", "_scan_jci")
UA = {"User-Agent": "Mozilla/5.0"}

# 포인트 표 머리글 — 지금까지 실측한 8계통 + IOM 본문형에서 뽑았다.
MARK = re.compile(
    r"BACNET\s*NAME|OBJECT\s*TYPE\s*AND\s*INSTANCE|MODBUS\s*REGISTER\s*ADDRESS|"
    r"POINT\s*LIST\s*DESCRIPTION|ENG\s*B?PAGE\s*REF|ASCII\s*PAGE\s*REF|ISN\s*LINC|"
    r"LOGIX\s*TAG|ITEM\s*REF\s*NUM|N2\s*(?:METASYS\s*)?ADDRESS|SNVT\s*TYPE|"
    r"PANEL\s*DISPLAYED\s*NAME|Enum\s*Set|Register\s*Address", re.I)
# 표가 아니라 문장에서 낱말만 스친 것을 거른다 — 한 쪽에 표식이 2종 이상이어야 표로 본다
MIN_KINDS = 2


def url_of(site, doc_id):
    return "https://docs.johnsoncontrols.com/%s/api/khub/documents/%s/content" % (site, doc_id)


def scan_one(c):
    """문서 하나 → 결과 dict. 원문은 걸린 것만 남긴다."""
    import fitz
    os.makedirs(TMP, exist_ok=True)
    path = os.path.join(TMP, c["id"] + ".pdf")
    if not os.path.exists(path):
        req = urllib.request.Request(url_of(c["site"], c["id"]), headers=UA)
        with urllib.request.urlopen(req, timeout=60) as r:
            body = r.read()
        with open(path, "wb") as f:
            f.write(body)
    out = {"id": c["id"], "site": c["site"], "title": c["title"], "cat": c.get("cat", ""),
           "prod": c.get("prod", ""), "bytes": os.path.getsize(path)}
    doc = fitz.open(path)
    out["pages"] = doc.page_count
    hits = []
    for i in range(doc.page_count):
        txt = doc[i].get_text()
        kinds = {m.group(0).upper() for m in MARK.finditer(txt)}
        if len(kinds) >= MIN_KINDS:
            hits.append(i + 1)
    out["markPages"] = hits
    rows = 0
    heads = []
    for i in hits[:40]:                      # 행수는 앞 40쪽까지만 세어 비용을 막는다
        try:
            tabs = doc[i - 1].find_tables().tables
        except Exception:
            continue
        for t in tabs:
            data = t.extract()
            if len(data) < 4:
                continue
            head = " | ".join((x or "").replace("\n", " ").strip() for x in data[0])
            if MARK.search(head):
                rows += len(data) - 1
                if len(heads) < 3:
                    heads.append(head[:150])
    out["tableRows"] = rows
    out["heads"] = heads
    doc.close()
    if not hits:
        os.remove(path)                      # 안 걸린 원문은 남기지 않는다
    return out


def run_slice(idx, total):
    tiers = json.load(io.open(os.path.join(DATA, "_jci_scan_tiers.json"), encoding="utf-8"))
    cands = tiers["t1"]
    mine = [c for n, c in enumerate(cands) if n % total == idx]
    outp = os.path.join(DATA, "_jci_scan_hits_%d.json" % idx)
    done = {}
    if os.path.exists(outp):
        for r in json.load(io.open(outp, encoding="utf-8")):
            done[r["id"]] = r
    t0 = time.time()
    for n, c in enumerate(mine, 1):
        if c["id"] in done:
            continue
        try:
            done[c["id"]] = scan_one(c)
        except Exception as e:
            done[c["id"]] = {"id": c["id"], "site": c["site"], "title": c["title"],
                             "error": str(e)[:120]}
        if n % 10 == 0 or n == len(mine):
            json.dump(list(done.values()), io.open(outp, "w", encoding="utf-8"),
                      ensure_ascii=False)
            hit = sum(1 for r in done.values() if r.get("markPages"))
            print("  %d/%d · 적중 %d · %.0f초" % (n, len(mine), hit, time.time() - t0),
                  flush=True)
    json.dump(list(done.values()), io.open(outp, "w", encoding="utf-8"), ensure_ascii=False)
    hit = [r for r in done.values() if r.get("markPages")]
    err = [r for r in done.values() if r.get("error")]
    print("조각 %d/%d — 문서 %d · 적중 %d · 오류 %d · 행 합계 %d"
          % (idx, total, len(done), len(hit), len(err),
             sum(r.get("tableRows", 0) for r in hit)))
    return 0


def merge():
    import glob
    all_ = []
    for f in sorted(glob.glob(os.path.join(DATA, "_jci_scan_hits_*.json"))):
        all_.extend(json.load(io.open(f, encoding="utf-8")))
    hit = [r for r in all_ if r.get("markPages")]
    hit.sort(key=lambda r: -r.get("tableRows", 0))
    out = os.path.join(DATA, "jci-body-scan.json")
    json.dump({"scanned": len(all_), "hits": hit}, io.open(out, "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print("훑은 문서 %d · 포인트 표를 품은 문서 %d · 행 합계 %d"
          % (len(all_), len(hit), sum(r.get("tableRows", 0) for r in hit)))
    print("  → %s" % out)
    for r in hit[:15]:
        print("   %6d행 p%-4s %-58s" % (r.get("tableRows", 0),
              (r["markPages"] or ["?"])[0], r["title"][:58]))
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="JCI 본문 전수 스캔")
    ap.add_argument("--slice", help="i/N 형식 — N 조각 중 i 번")
    ap.add_argument("--merge", action="store_true")
    a = ap.parse_args(argv)
    if a.merge:
        return merge()
    if a.slice:
        i, n = a.slice.split("/")
        return run_slice(int(i), int(n))
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
