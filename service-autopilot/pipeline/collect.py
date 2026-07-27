# -*- coding: utf-8 -*-
"""수집기 — 소스 레지스트리를 읽어 문서를 열거·내려받고 대장에 기록한다.

  · 이미 받은 문서는 SHA-256으로 걸러 다시 받지 않는다
  · 실패한 URL도 기록해서 다음에 다시 시도하지 않는다
  · 봇 차단(403)은 '브라우저 필요'로 표시하고 넘어간다 — 사람이 받을 목록이 된다

실행
  python collect.py --list                    소스 목록
  python collect.py --probe trane-points-list 열거만 (내려받지 않음)
  python collect.py --run   trane-points-list 실제 수집
"""
import json, os, sys, hashlib, time, urllib.request, urllib.error

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
LEDGER = os.path.join(DATA, "collected.json")
sys.path.insert(0, HERE)
from sources import SOURCES, by_id, UA  # noqa: E402


def load_ledger():
    return json.load(open(LEDGER, encoding="utf-8")) if os.path.exists(LEDGER) else {}


def save_ledger(d):
    os.makedirs(DATA, exist_ok=True)
    json.dump(d, open(LEDGER, "w", encoding="utf-8"), ensure_ascii=False, indent=1)


def candidates(src):
    """소스 규칙 → 시도할 URL 목록"""
    if src["enumerate"] == "list":
        return list(src["urls"])
    if src["enumerate"] == "series":
        out = []
        for n in src["num"]:
            for rev in src["rev"]:
                for d in src["date"]:
                    out.append(src["url"].format(num=n, rev=rev, date=d))
        return out
    return []  # page 방식은 브라우저가 필요 — probe에서 안내만


def head(url, timeout=12):
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, int(r.headers.get("Content-Length") or 0)
    except urllib.error.HTTPError as e:
        return e.code, 0
    except Exception:
        return 0, 0


def fetch(url, dest, timeout=90):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        body = r.read()
    open(dest, "wb").write(body)
    return hashlib.sha256(body).hexdigest(), len(body)


def probe(src, limit=None, verbose=True):
    """열거만 — 어떤 URL이 살아 있는지 센다. 시리즈는 번호당 첫 성공에서 멈춘다."""
    urls = candidates(src)
    if not urls:
        print("  · %s 은 페이지 스크레이핑 방식 — 브라우저가 필요하다 (%s)"
              % (src["id"], src.get("page", "")))
        return []
    found, tried, seen_num = [], 0, set()
    for u in urls:
        if src["enumerate"] == "series":
            key = u.split("BAS-PTS")[1][:4] if "BAS-PTS" in u else u
            if key in seen_num:
                continue
        tried += 1
        if limit and tried > limit:
            break
        code, size = head(u)
        if code == 200 and size > 20000:
            found.append({"url": u, "size": size})
            if src["enumerate"] == "series":
                seen_num.add(u.split("BAS-PTS")[1][:4])
            if verbose:
                print("  ✓ %7d B  %s" % (size, os.path.basename(u)))
        elif code == 403 and verbose:
            print("  △ 403 봇차단 — 브라우저 필요: %s" % os.path.basename(u))
    return found


def run(src, limit=None):
    os.makedirs(RAW, exist_ok=True)
    led = load_ledger()
    got = probe(src, limit=limit, verbose=True)
    new = 0
    for item in got:
        u = item["url"]
        if u in led and led[u].get("sha256"):
            continue
        name = os.path.basename(u).split("?")[0]
        dest = os.path.join(RAW, name)
        try:
            sha, size = fetch(u, dest)
            led[u] = {"source": src["id"], "vendor": src["vendor"], "kind": src["kind"],
                      "file": name, "sha256": sha, "bytes": size,
                      "extractor": src["extractor"], "at": time.strftime("%Y-%m-%d %H:%M")}
            new += 1
            print("  ↓ %-52s %7d B" % (name, size))
        except Exception as e:
            led[u] = {"source": src["id"], "error": str(e)[:80],
                      "at": time.strftime("%Y-%m-%d %H:%M")}
    save_ledger(led)
    return len(got), new


def main(argv):
    if not argv or "--list" in argv:
        print("%-26s %-22s %-14s %s" % ("소스 ID", "벤더", "접근", "종류"))
        print("─" * 92)
        for s in SOURCES:
            print("%-26s %-22s %-14s %s" % (s["id"], s["vendor"], s["access"], s["kind"]))
        print("\n총 %d개 소스" % len(SOURCES))
        return 0
    mode = "--probe" if "--probe" in argv else "--run"
    sid = argv[argv.index(mode) + 1]
    lim = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    src = by_id(sid)
    print("■ %s (%s · %s)\n  %s\n" % (src["id"], src["vendor"], src["access"], src["note"]))
    if mode == "--probe":
        got = probe(src, limit=lim)
        print("\n  → 살아 있는 문서 %d건" % len(got))
    else:
        n, new = run(src, limit=lim)
        print("\n  → 확인 %d건 · 새로 받음 %d건 · 대장 data/collected.json" % (n, new))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
