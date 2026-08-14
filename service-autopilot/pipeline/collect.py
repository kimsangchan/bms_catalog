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
import collections, json, os, sys, hashlib, time
import urllib.request, urllib.error, urllib.parse

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


def _hdr(src, extra=None):
    """소스가 요구하는 헤더를 얹는다.

    Belimo 처럼 봇 차단(Akamai)이 걸린 사이트는 UA 만으로는 403 이고,
    Referer 와 Sec-Fetch-* 를 함께 보내야 통과한다 — 브라우저가 보내는 것과
    같은 헤더다. 우회 기법이 아니라 정상 방문 형태를 갖추는 것이다.
    """
    h = {"User-Agent": UA}
    h.update((src or {}).get("headers") or {})
    h.update(extra or {})
    return h


def head(url, timeout=12, src=None):
    req = urllib.request.Request(url, method="HEAD", headers=_hdr(src))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            size = int(r.headers.get("Content-Length") or 0)
            # shareddocs(Carrier)는 HEAD 200 인데 Content-Length 를 안 준다 —
            # 크기 0 으로 두면 probe 의 최소 크기 필터에 걸려 살아있는 문서를 버린다
            if r.status == 200 and size == 0:
                return _head_by_range(url, timeout, src)
            return r.status, size
    except urllib.error.HTTPError as e:
        # Daikin(tahoeweb)처럼 HEAD 를 405 로 막는 서버가 있다 — 1바이트 GET 으로 다시 두드린다
        if e.code in (405, 501):
            return _head_by_range(url, timeout, src)
        return e.code, 0
    except Exception:
        return 0, 0


def _head_by_range(url, timeout, src):
    req = urllib.request.Request(url, headers=_hdr(src, {"Range": "bytes=0-0"}))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            rng = r.headers.get("Content-Range") or ""   # 예: bytes 0-0/2231509
            if "/" in rng:
                return 200, int(rng.split("/")[-1])
            # Range 를 무시하고 200 전체 응답을 주는 서버(tahoeweb) — 헤더만 읽고 닫는다
            size = int(r.headers.get("Content-Length") or 0)
            # 길이 헤더가 아예 없는 동적 생성 서버(Mitsubishi library — PDF 를 즉석
            # 조립해 attachment 로 내려준다). content-type 이 PDF 면 살아 있는 것으로
            # 보고 크기 필터를 통과할 답례 크기를 준다 — 실제 크기는 받을 때 잰다.
            if size == 0 and "pdf" in (r.headers.get("Content-Type") or "").lower():
                return 200, 10 ** 6
            return 200, size
    except Exception:
        return 0, 0


def fetch(url, dest, timeout=90, src=None):
    req = urllib.request.Request(url, headers=_hdr(src, {"Accept": "*/*"}))
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

    # 최소 크기는 **번호를 찍어 맞히는 series 열거의 방어선**이다 — 죽은 조합이
    # 오류 안내 페이지(수 KB)를 200 으로 돌려주기 때문이다. list 열거는 문서를
    # 지목한 것이라 이 필터가 살아 있는 문서를 **조용히 버린다**
    # (JCI YSAA Native 18,213 B 가 실제로 그렇게 빠져 56건 중 55건만 받았다).
    floor = 20000 if src["enumerate"] == "series" else 1000

    def first_alive(key):
        """이 번호의 후보를 차례로 두드려 처음 살아 있는 것을 돌려준다."""
        for u in groups[key]:
            code, size = head(u, src=src)
            if code == 200 and size > floor:
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


def files_of(source_id):
    """등록된 원문 경로 목록 — 소스 하나에 문서가 여럿인 벤더 파서가 쓴다.

    파서가 폴더를 훑으면 그 PC 에만 있는 임시 폴더에 묶인다(JCI 56건이 실제로
    그랬다 — 다른 PC 에서 재현이 안 됐다). 대장이 정본이면 어디서든
    `collect.py --run <소스ID>` 한 번으로 같은 목록이 선다.
    """
    out = []
    for v in load_ledger().values():
        if v.get("source") == source_id and v.get("file"):
            p = os.path.join(RAW, v["file"])
            if os.path.exists(p):
                out.append(p)
    return sorted(out)


def local_name(src, url):
    """저장할 파일 이름.

    보통은 URL 의 마지막 조각을 쓴다. 그런데 벤더가 'user guide.pdf' 처럼
    벤더도 제품도 안 들어간 이름으로 올려 두면 다른 벤더 문서와 부딪히고
    나중에 무슨 문서인지 알 수 없다. 그런 소스는 rename 에 이름을 적어 둔다.

    rename 의 열쇠는 **원 이름 또는 URL 전체**다. JCI khub 처럼 URL 끝이 전부
    'content' 인 사이트는 원 이름이 56건 모두 같아 이름 기준으로는 가를 수 없다
    (그래서 전에는 문서 하나당 소스 하나로 쪼갰다).
    """
    raw = os.path.basename(url.rstrip("/")).split("?")[0]
    raw = urllib.parse.unquote(raw)
    ren = src.get("rename") or {}
    fixed = ren.get(url) or ren.get(raw)
    return fixed or raw.replace(" ", "_")


def run(src, limit=None):
    os.makedirs(RAW, exist_ok=True)
    led = load_ledger()
    got = probe(src, limit=limit, verbose=True)
    new = 0
    for item in got:
        u = item["url"]
        if u in led and led[u].get("sha256"):
            continue
        name = local_name(src, u)
        dest = os.path.join(RAW, name)
        try:
            sha, size = fetch(u, dest, src=src)
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
