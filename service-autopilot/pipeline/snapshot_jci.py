# -*- coding: utf-8 -*-
"""JCI 문서 포털 전수 열거 → data/haystack/_jci_docs.json

왜 있나
  이 스냅샷은 원래 **스크립트 없이** 만들어져 있었다. 어느 포털을 왜 골랐는지
  기록이 없었고, 실제로는 `chillers`·`ductedsystems`·`bas` **셋만** 담겨 있었다.
  그래서 모든 "분모"가 그 셋 위에서 계산됐고, **공조기 전용 포털
  (`airhandling`)과 산업용 냉동(`industrialrefrigeration`)이 통째로 빠져 있었다.**
  "공조기가 이만큼밖에 없냐"는 지적을 받고서야 드러났다(2026-08-31).

  포털을 손으로 고르면 또 빠진다. 그래서 **후보를 훑어 열리는 것을 전부 담고**,
  담지 않은 것은 사유를 남긴다.

포털을 어떻게 찾았나
  johnsoncontrols.com/services-and-support/product-documentation 이 포털 목록을
  안내한다(2026-08-31 확인). 거기 이름 + 흔한 제품 낱말을 후보로 두고 API 를
  두드려 200 이 오는 것만 담는다. 새 포털이 생기면 CANDIDATES 에 한 줄 더한다.

API 의 성질 (실측)
  · `GET /<포털>/api/khub/documents?maxResults=N` — 한 번에 전량이 온다.
    `from`·`offset`·`page` 는 **먹지 않는다**(같은 결과가 되돌아온다).
    상한이 있는 줄 알고 `airhandling` 236건을 '잘린 것'으로 의심했는데,
    `chillers` 가 2,525건을 한 번에 주는 것으로 상한이 아님을 확인했다.
  · 색인·패싯 엔드포인트는 없다(`/facets`·`/categories` 등 전부 404).

실행
  PYTHONIOENCODING=utf-8 python snapshot_jci.py --probe    포털만 두드려 본다
  PYTHONIOENCODING=utf-8 python snapshot_jci.py --run      스냅샷을 다시 만든다
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(DATA, "haystack", "_jci_docs.json")
UA = {"User-Agent": "Mozilla/5.0"}

# 담을 포털 — HVAC·BMS 만. 담지 않는 것도 **사유와 함께** 남긴다.
KEEP = {
    "airhandling": "공조기(AHU·VAV 터미널·CRAH·Solution·Custom)",
    "chillers": "냉동기·열원",
    "ductedsystems": "덕트·옥상형·스플릿",
    "bas": "제어·계측(Metasys)",
    "industrialrefrigeration": "산업용 냉동(Frick 등)",
    "openblue": "디지털 플랫폼",
}
SKIP = {
    "sensormatic": "유통 매장 보안 — 설비가 아니다",
    "tycofire": "소방 — 계열 e21 이지만 BMS 연동 문서가 아니다",
    "simplex": "소방 — 위와 같다",
}
# 두드려 볼 후보. 열리는 것만 담긴다 — 404 는 그냥 없는 포털이다.
CANDIDATES = sorted(set(KEEP) | set(SKIP) | {
    "unitary", "terminalunits", "vrf", "coolingtowers", "controls", "hvac",
    "appliedequipment", "residential", "lightcommercial", "refrigeration",
    "york", "hitachi", "metasys", "facilityexplorer", "verasys", "smartequipment",
    "airsidesystems", "applied", "boilers", "heatpumps",
})


def fetch(site, timeout=180):
    u = ("https://docs.johnsoncontrols.com/%s/api/khub/documents?maxResults=100000"
         % site)
    with urllib.request.urlopen(urllib.request.Request(u, headers=UA),
                                timeout=timeout) as r:
        return json.load(r)


def probe(verbose=True):
    """후보를 두드려 열리는 포털과 문서 수를 돌려준다."""
    found = {}
    for s in CANDIDATES:
        try:
            found[s] = len(fetch(s))
        except urllib.error.HTTPError:
            continue
        except Exception as e:
            if verbose:
                print("  ⚠ %-26s %s" % (s, str(e)[:50]))
            continue
        if verbose:
            mark = "담는다" if s in KEEP else "뺀다  "
            why = KEEP.get(s) or SKIP.get(s, "사유 미기재 — KEEP/SKIP 에 적어야 한다")
            print("  %s %-26s %6d건  %s" % (mark, s, found[s], why))
    return found


def run():
    found = probe()
    unknown = [s for s in found if s not in KEEP and s not in SKIP]
    if unknown:
        # 새 포털이 생겼는데 사유가 없다 — 조용히 빠뜨리지 않는다
        print("\n⚠ 사유가 없는 포털 %d개: %s" % (len(unknown), ", ".join(unknown)))
        print("  KEEP 이나 SKIP 에 한 줄 적고 다시 돌려라.")
        return 1

    old = {}
    if os.path.exists(OUT):
        with open(OUT, encoding="utf-8") as f:
            old = json.load(f)
    snap = {}
    for s in sorted(KEEP):
        if s not in found:
            print("  ⚠ %s 가 안 열린다 — 건너뛴다" % s)
            continue
        snap[s] = fetch(s)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(snap, f, ensure_ascii=False)

    print("\n%-26s %8s %8s %8s" % ("포털", "이전", "지금", "차이"))
    print("─" * 56)
    tot_o = tot_n = 0
    for s in sorted(set(snap) | set(old)):
        o, n = len(old.get(s, [])), len(snap.get(s, []))
        tot_o += o
        tot_n += n
        print("%-26s %8d %8d %+8d" % (s, o, n, n - o))
    print("─" * 56)
    print("%-26s %8d %8d %+8d" % ("합계", tot_o, tot_n, tot_n - tot_o))
    print("\n→ %s" % OUT)
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description="JCI 문서 포털 전수 열거")
    ap.add_argument("--probe", action="store_true", help="두드려만 본다")
    ap.add_argument("--run", action="store_true", help="스냅샷을 다시 만든다")
    a = ap.parse_args(argv)
    if a.run:
        return run()
    if a.probe:
        probe()
        return 0
    ap.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
