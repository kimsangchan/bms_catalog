# -*- coding: utf-8 -*-
"""수집기 — 소스 레지스트리를 읽어 문서를 열거·내려받고 대장에 기록한다.

  · 이미 받은 문서는 SHA-256으로 걸러 다시 받지 않는다
  · 실패한 URL도 기록해서 다음에 다시 시도하지 않는다
  · 봇 차단(403)은 '브라우저 필요'로 표시하고 넘어간다 — 사람이 받을 목록이 된다

실행
  python collect.py --list                    소스 목록
  python collect.py --probe trane-points-list 열거만 (내려받지 않음)
  python collect.py --run   trane-points-list 실제 수집

--limit N 은 '문서번호 N개까지'라는 뜻이다 (조회 횟수가 아니다).
"""
import collections, json, os, sys, hashlib, time, urllib.request, urllib.error

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


def series_key(src, url):
    """시리즈에서 '같은 문서의 다른 판'을 묶는 키 — 번호+개정만 보고 날짜는 뺀다."""
    if src["enumerate"] != "series" or "BAS-PTS" not in url:
        return url
    return url.split("BAS-PTS")[1][:4]


def probe(src, limit=None, verbose=True, workers=12):
    """열거만 — 어떤 URL이 살아 있는지 센다.

    문서번호×개정×날짜 조합이라 후보가 1,000개를 넘는다. 순차로 돌면 20분이 넘어
    **번호별로 묶어 병렬**로 두드린다. 한 번호에서 하나만 살아 있으면 되므로
    번호 안에서는 순차, 번호끼리는 동시에 간다.
    """
    from concurrent.futures import ThreadPoolExecutor
    urls = candidates(src)
    if not urls:
        print("  · %s 은 페이지 스크레이핑 방식 — 브라우저가 필요하다 (%s)"
              % (src["id"], src.get("page", "")))
        return []

    groups = collections.OrderedDict()
    for u in urls:
        groups.setdefault(series_key(src, u), []).append(u)
    keys = list(groups)[:limit] if limit else list(groups)

    def first_alive(key):
        """이 번호의 후보를 차례로 두드려 처음 살아 있는 것을 돌려준다."""
        for u in groups[key]:
            code, size = head(u)
            if code == 200 and size > 20000:
                return {"url": u, "size": size, "key": key}
            if code == 403:
                return {"url": u, "size": 0, "key": key, "blocked": True}
        return None

    found = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for r in ex.map(first_alive, keys):
            if not r:
                continue
            if r.get("blocked"):
                if verbose:
                    print("  △ 403 봇차단 — 브라우저 필요: %s" % os.path.basename(r["url"]))
                continue
            found.append(r)
            if verbose:
                print("  ✓ %7d B  %s" % (r["size"], os.path.basename(r["url"])))
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
