# -*- coding: utf-8 -*-
"""원문 대조 — 우리가 읽은 정격 표를 원문 그림과 나란히 놓고 사람이 판정한다.

왜 필요한가
  포인트에는 교차 대조(crosscheck.py)가 있지만 **정격 표에는 2차 경로가 없다**.
  특히 전치(세로) 표는 첫 칸이 속성이라 행·열을 한 번 잘못 잡으면 값이 통째로
  밀리는데, 지금은 그걸 잡아 주는 게 아무것도 없다.
  실측: 사양 표 1,674개 중 전치 169개, 그중 정격(rating) 138개가 무방비다.

  그래서 사람이 봐야 한다. 사람이 보려면 원문이 옆에 있어야 하는데, PDF 를 따로
  띄우면 쪽을 찾다가 지친다 — **그 표가 있는 자리만 그림으로 잘라 값 옆에 붙인다.**
  폐쇄망·팀 공유를 감안해 그림은 파일 안에 넣는다(base64, 외부 파일 없음).

무엇을 보여 주나
  왼쪽 = 원문 표 그림, 오른쪽 = 우리가 읽어 낸 값.
  오른쪽 항목에는 **우리가 물리량으로 알아본 것**과 아닌 것을 색으로 갈라 둔다.
  '원문엔 있는데 우리가 값으로 안 쓴 항목'이 바로 보이는 게 이 화면의 핵심이다.

실행
  PYTHONIOENCODING=utf-8 python verify.py                # 위험 상위(전치 정격표)
  PYTHONIOENCODING=utf-8 python verify.py --equip e5     # 계열 전체
  PYTHONIOENCODING=utf-8 python verify.py --only <모델ID>
  PYTHONIOENCODING=utf-8 python verify.py --all          # 전 사양표

판정 결과는 브라우저에 저장되고 [판정 내보내기] 로 JSON 을 받는다.
"""
import argparse
import base64
import glob
import html
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
OUT = os.path.join(HERE, "..", "review")
sys.path.insert(0, HERE)
import specs as SP  # noqa: E402

# 표 그림 해상도. 표 한 덩이만 자르므로 쪽 전체보다 작다 — 글자가 읽혀야 대조가 된다.
DPI = 150
DPI_FALLBACK = 110          # 그림이 너무 크면 한 단계 낮춘다
MAX_IMG_BYTES = 320 * 1024
CAPTION_MARGIN = 58         # 표 위 제목까지 함께 자른다 (단위·조건이 제목에 붙는다)
PAD = 8


def load_models():
    out = []
    for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json"))):
        with open(f, encoding="utf-8") as fp:
            out.append(json.load(fp))
    return out


def risk_of(t):
    """대조 우선순위. 낮을수록 먼저 본다.

    전치 정격표가 1순위인 이유는 방향을 잘못 읽으면 값이 통째로 어긋나는데
    그걸 잡는 자동 검사가 없어서다.
    """
    orient, kind = t.get("orientation"), t.get("kind")
    if orient == "row" and kind == "rating":
        return 0
    if kind == "rating":
        return 1
    if orient == "row":
        return 2
    return 3


def pick_tables(models, equip=None, only=None, take_all=False):
    picked = []
    for m in models:
        if only and m.get("id") != only:
            continue
        if equip and m.get("equipId") != equip:
            continue
        for i, t in enumerate(m.get("specTables") or []):
            r = risk_of(t)
            if not take_all and not (equip or only) and r != 0:
                continue          # 기본은 위험 상위만
            picked.append((r, m, i, t))
    picked.sort(key=lambda x: (x[0], x[1].get("id") or "", x[2]))
    return picked


def stored_key(header, rows):
    return (tuple(header or []), len(rows or []),
            (rows[0][0] if rows and rows[0] else ""))


def find_bbox(page, header, rows):
    """저장된 표가 원문 어디에 있었는지 되찾는다.

    specs.extract_specs 와 **같은 전처리**(merge_header + 공백 정리)를 거쳐야
    같은 키가 나온다. 못 찾으면 None — 그때는 쪽 전체를 보여 준다.
    """
    try:
        tabs = page.find_tables()
    except Exception:
        return None
    want = stored_key(header, rows)
    best, best_score = None, 0.0
    want_head = set(x for x in (header or []) if x)
    for t in tabs.tables:
        try:
            data = t.extract()
        except Exception:
            continue
        if len(data) < 3 or len(data[0]) < 2:
            continue
        h, rr = SP.merge_header(data)
        h = [SP._c(c) for c in h]
        rr = [[SP._c(c) for c in r] for r in rr if any(SP._c(c) for c in r)]
        if stored_key(h, rr) == want:
            return t.bbox
        if want_head:
            hit = len(want_head & set(x for x in h if x)) / float(len(want_head))
            if hit > best_score:
                best, best_score = t.bbox, hit
    return best if best_score >= 0.6 else None


def render(page, bbox):
    """표 자리를 잘라 JPEG 로. bbox 가 없으면 쪽 전체."""
    import fitz
    if bbox:
        r = fitz.Rect(bbox[0] - PAD, bbox[1] - CAPTION_MARGIN,
                      bbox[2] + PAD, bbox[3] + PAD) & page.rect
    else:
        r = page.rect
    for dpi in (DPI, DPI_FALLBACK):
        pix = page.get_pixmap(clip=r, dpi=dpi)
        buf = pix.tobytes("jpeg", jpg_quality=72)
        if len(buf) <= MAX_IMG_BYTES:
            break
    return buf, bool(bbox)


def build_cards(picked):
    import fitz
    cards, imgs, index = [], [], {}
    docs = {}
    # 같은 문서를 되풀이해 열지 않도록 (문서, 쪽) 으로 묶는다
    picked_sorted = sorted(picked, key=lambda x: ((x[3].get("source") or ""),
                                                  int(x[3].get("page") or 0)))
    bboxes = {}
    for _, m, i, t in picked_sorted:
        src = (t.get("source") or "").split("#")[0]
        pno = int(t.get("page") or 0)
        if not src or pno < 1:
            continue
        path = os.path.join(RAW, src)
        if not os.path.exists(path):
            continue
        if src not in docs:
            try:
                docs[src] = fitz.open(path)
            except Exception:
                docs[src] = None
        doc = docs[src]
        if doc is None or pno > doc.page_count:
            continue
        page = doc[pno - 1]
        bbox = find_bbox(page, t.get("header"), t.get("rows"))
        key = (src, pno, tuple(round(v, 1) for v in bbox) if bbox else None)
        if key not in index:
            buf, cropped = render(page, bbox)
            index[key] = len(imgs)
            imgs.append("data:image/jpeg;base64," +
                        base64.b64encode(buf).decode("ascii"))
        bboxes[(m.get("id"), i)] = (index[key], bool(bbox))

    for r, m, i, t in picked:
        got = bboxes.get((m.get("id"), i))
        if got is None:
            continue                     # 원문이 없으면 대조할 수 없다 — 싣지 않는다
        img_i, located = got
        cards.append({
            "id": "%s#%d" % (m.get("id"), i),
            "model": m.get("model") or m.get("id"),
            "modelId": m.get("id"),
            "vendor": m.get("vendor") or "",
            "equipId": m.get("equipId") or "",
            "title": t.get("title") or "",
            "source": t.get("source") or "",
            "page": t.get("page"),
            "kind": t.get("kind") or "",
            "orientation": t.get("orientation") or "",
            "header": t.get("header") or [],
            "rows": t.get("rows") or [],
            "quantities": t.get("quantities") or [],
            "img": img_i,
            "located": located,
            "risk": r,
        })
    for d in docs.values():
        if d is not None:
            d.close()
    return cards, imgs


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>원문 대조 — 정격 표</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
:root{
  --bg:#fafaf9; --panel:#fff; --ink:#18181b; --dim:#71717a; --faint:#a1a1aa;
  --line:#e4e4e7; --line2:#f4f4f5; --accent:#15803d; --accent-bg:#f0fdf4;
  --warn:#b45309; --warn-bg:#fffbeb; --bad:#b91c1c; --bad-bg:#fef2f2; --sel:#f4f4f5;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,"Cascadia Mono",Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#18181b; --panel:#1f1f23; --ink:#f4f4f5; --dim:#a1a1aa; --faint:#71717a;
  --line:#3f3f46; --line2:#27272a; --accent:#4ade80; --accent-bg:#14251a;
  --warn:#fbbf24; --warn-bg:#2a2113; --bad:#f87171; --bad-bg:#2a1516; --sel:#27272a;}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
  font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif}
header{position:sticky;top:0;z-index:9;background:var(--panel);
  border-bottom:1px solid var(--line);padding:14px 20px}
h1{margin:0 0 4px;font-size:17px;letter-spacing:-.01em}
.sub{color:var(--dim);font-size:13px}
.bar{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:10px}
button{font:inherit;padding:5px 12px;border:1px solid var(--line);border-radius:7px;
  background:var(--panel);color:var(--ink);cursor:pointer}
button:hover{background:var(--sel)}
button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
.wrap{padding:20px;max-width:1600px;margin:0 auto}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  margin-bottom:18px;overflow:hidden}
.card.done-ok{border-color:var(--accent)}
.card.done-bad{border-color:var(--bad)}
.meta{padding:11px 14px;border-bottom:1px solid var(--line2);display:flex;
  gap:10px;align-items:baseline;flex-wrap:wrap}
.meta .m{font-weight:600}
.meta .s{color:var(--dim);font-size:13px}
.tag{font-size:11px;padding:2px 7px;border-radius:5px;border:1px solid var(--line);
  color:var(--dim);white-space:nowrap}
.tag.row{background:var(--warn-bg);color:var(--warn);border-color:transparent}
.tag.rating{background:var(--accent-bg);color:var(--accent);border-color:transparent}
.tag.warn{background:var(--bad-bg);color:var(--bad);border-color:transparent}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:0}
@media(max-width:1100px){.cols{grid-template-columns:1fr}}
.side{padding:14px;min-width:0}
.side+.side{border-left:1px solid var(--line2)}
@media(max-width:1100px){.side+.side{border-left:0;border-top:1px solid var(--line2)}}
.lab{font-size:11px;color:var(--faint);text-transform:uppercase;
  letter-spacing:.06em;margin-bottom:8px}
.side img{width:100%;height:auto;border:1px solid var(--line);border-radius:6px;
  background:#fff;cursor:zoom-in}
.tblbox{overflow-x:auto}
table{border-collapse:collapse;font-size:13px;width:100%}
th,td{border:1px solid var(--line);padding:4px 8px;text-align:left;
  vertical-align:top;white-space:nowrap}
th{background:var(--line2);font-weight:600}
td.attr{font-weight:600}
tr.known td.attr{background:var(--accent-bg);color:var(--accent)}
tr.unknown td.attr{color:var(--faint)}
th.known{background:var(--accent-bg);color:var(--accent)}
th.unknown{color:var(--faint)}
.q{font:11px/1 var(--mono);color:var(--dim);margin-left:6px}
.legend{font-size:12px;color:var(--dim);margin-top:10px}
.dot{display:inline-block;width:9px;height:9px;border-radius:3px;
  background:var(--accent);margin-right:4px;vertical-align:middle}
.dot.g{background:var(--faint)}
.judge{padding:11px 14px;border-top:1px solid var(--line2);display:flex;
  gap:8px;align-items:center;flex-wrap:wrap}
.judge .st{margin-left:auto;font-size:13px;color:var(--dim)}
button.ok.on{background:var(--accent);border-color:var(--accent);color:#fff}
button.bad.on{background:var(--bad);border-color:var(--bad);color:#fff}
button.hold.on{background:var(--warn);border-color:var(--warn);color:#fff}
dialog{border:none;border-radius:12px;padding:0;max-width:96vw;max-height:96vh;
  background:var(--panel)}
dialog::backdrop{background:rgba(0,0,0,.7)}
dialog img{display:block;max-width:96vw;max-height:92vh;width:auto}
.empty{color:var(--dim);padding:40px;text-align:center}
</style>
<header>
  <h1>원문 대조 — 정격 표</h1>
  <div class="sub" id="sub"></div>
  <div class="bar">
    <button id="f-all" class="on">전체</button>
    <button id="f-todo">미판정만</button>
    <button id="f-bad">틀림·보류만</button>
    <button id="export">판정 내보내기 (JSON)</button>
    <button id="reset">판정 지우기</button>
  </div>
</header>
<div class="wrap" id="list"></div>
<dialog id="zoom"><img id="zoomimg" alt=""></dialog>
<script>
const CARDS = __CARDS__;
const IMGS  = __IMGS__;
const KEY = "spec-verify-v1";
let verdicts = {};
try { verdicts = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch(e) {}
let filter = "all";

const esc = s => String(s==null?"":s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function ourTable(c){
  // 전치표는 첫 칸이 속성 → 행에 표시가 붙는다. 아니면 머리글에 붙는다.
  const isRow = c.orientation === "row";
  let h = "<thead><tr>";
  c.header.forEach((x,j) => {
    const k = !isRow && c.quantities[j] ? "known" : (!isRow ? "unknown" : "");
    const q = !isRow && c.quantities[j] ? '<span class="q">'+esc(c.quantities[j])+'</span>' : "";
    h += '<th class="'+k+'">'+esc(x)+q+'</th>';
  });
  h += "</tr></thead><tbody>";
  c.rows.forEach((r,i) => {
    const known = isRow && c.quantities[i];
    h += '<tr class="'+(isRow ? (known ? "known":"unknown") : "")+'">';
    r.forEach((x,j) => {
      const attr = (isRow && j===0) ? ' class="attr"' : "";
      const q = (isRow && j===0 && known) ? '<span class="q">'+esc(c.quantities[i])+'</span>' : "";
      h += "<td"+attr+">"+esc(x)+q+"</td>";
    });
    h += "</tr>";
  });
  return "<table>"+h+"</tbody></table>";
}

function card(c){
  const v = verdicts[c.id] || {};
  const cls = v.verdict==="ok" ? "done-ok" : (v.verdict==="bad" ? "done-bad" : "");
  const tags = [
    c.orientation==="row" ? '<span class="tag row">세로(전치)표</span>' : '<span class="tag">가로표</span>',
    c.kind==="rating" ? '<span class="tag rating">정격</span>' : '<span class="tag">'+esc(c.kind)+'</span>',
    c.located ? "" : '<span class="tag warn">표 위치 못 찾음 — 쪽 전체</span>'
  ].join("");
  return '<div class="card '+cls+'" data-id="'+esc(c.id)+'">'
    + '<div class="meta"><span class="m">'+esc(c.model)+'</span>'
    + '<span class="s">'+esc(c.vendor)+'</span>'
    + '<span class="s">'+esc(c.source)+' p'+esc(c.page)+'</span>'
    + tags + '</div>'
    + '<div class="cols">'
    +   '<div class="side"><div class="lab">원문</div>'
    +     '<img loading="lazy" src="'+IMGS[c.img]+'" alt="원문 표">'
    +     (c.title ? '<div class="legend">제목 인식: '+esc(c.title)+'</div>' : "")
    +   '</div>'
    +   '<div class="side"><div class="lab">우리가 읽은 값</div>'
    +     '<div class="tblbox">'+ourTable(c)+'</div>'
    +     '<div class="legend"><span class="dot"></span>물리량으로 알아본 항목'
    +     ' &nbsp; <span class="dot g"></span>못 알아본 항목 — 원문엔 있으나 값으로 쓰지 않는다</div>'
    +   '</div>'
    + '</div>'
    + '<div class="judge">'
    +   '<button class="ok'  +(v.verdict==="ok"?" on":"")  +'" data-v="ok">맞음</button>'
    +   '<button class="bad' +(v.verdict==="bad"?" on":"") +'" data-v="bad">틀림</button>'
    +   '<button class="hold'+(v.verdict==="hold"?" on":"")+'" data-v="hold">보류</button>'
    +   '<span class="st">'+(v.verdict ? "판정함" : "미판정")+'</span>'
    + '</div></div>';
}

function visible(){
  return CARDS.filter(c => {
    const v = (verdicts[c.id]||{}).verdict;
    if (filter==="todo") return !v;
    if (filter==="bad")  return v==="bad" || v==="hold";
    return true;
  });
}

function render(){
  const vs = visible();
  document.getElementById("list").innerHTML =
    vs.length ? vs.map(card).join("") : '<div class="empty">해당하는 표가 없다.</div>';
  const done = CARDS.filter(c => (verdicts[c.id]||{}).verdict).length;
  const bad  = CARDS.filter(c => (verdicts[c.id]||{}).verdict==="bad").length;
  document.getElementById("sub").textContent =
    CARDS.length + "건 중 " + done + "건 판정 · 틀림 " + bad + "건 · 보이는 것 " + vs.length + "건";
}

document.addEventListener("click", e => {
  const b = e.target.closest("button[data-v]");
  if (b) {
    const id = b.closest(".card").dataset.id;
    const cur = (verdicts[id]||{}).verdict;
    const nv = b.dataset.v;
    if (cur === nv) delete verdicts[id];
    else verdicts[id] = {verdict: nv, at: new Date().toISOString()};
    localStorage.setItem(KEY, JSON.stringify(verdicts));
    render();
    return;
  }
  const img = e.target.closest(".side img");
  if (img) {
    document.getElementById("zoomimg").src = img.src;
    document.getElementById("zoom").showModal();
  }
});
document.getElementById("zoom").addEventListener("click", e =>
  e.currentTarget.close());

function setFilter(f, el){
  filter = f;
  ["f-all","f-todo","f-bad"].forEach(i =>
    document.getElementById(i).classList.toggle("on", document.getElementById(i)===el));
  render();
}
document.getElementById("f-all").onclick  = e => setFilter("all", e.target);
document.getElementById("f-todo").onclick = e => setFilter("todo", e.target);
document.getElementById("f-bad").onclick  = e => setFilter("bad", e.target);

document.getElementById("export").onclick = () => {
  const rows = CARDS.filter(c => verdicts[c.id]).map(c => ({
    id: c.id, modelId: c.modelId, source: c.source, page: c.page,
    kind: c.kind, orientation: c.orientation, title: c.title,
    verdict: verdicts[c.id].verdict, at: verdicts[c.id].at
  }));
  const b = new Blob([JSON.stringify({checked: rows.length, rows}, null, 2)],
                     {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b);
  a.download = "spec-verdicts.json";
  a.click();
};
document.getElementById("reset").onclick = () => {
  if (!confirm("판정을 모두 지운다.")) return;
  verdicts = {}; localStorage.removeItem(KEY); render();
};
render();
</script>
"""


def main(argv):
    ap = argparse.ArgumentParser(description="원문 대조 화면 생성")
    ap.add_argument("--equip", help="장비 계열만 (예: e5)")
    ap.add_argument("--only", help="모델 ID 하나만")
    ap.add_argument("--all", action="store_true", help="전 사양표 (기본은 위험 상위)")
    ap.add_argument("--limit", type=int, help="앞에서 N건만")
    ap.add_argument("-o", "--out", help="출력 파일 경로")
    a = ap.parse_args(argv)

    models = load_models()
    picked = pick_tables(models, equip=a.equip, only=a.only, take_all=a.all)
    if a.limit:
        picked = picked[:a.limit]
    if not picked:
        print("대상 표가 없다.")
        return 1
    print("대상 %d건 — 원문에서 표 위치를 찾아 그림으로 자른다…" % len(picked))

    cards, imgs = build_cards(picked)
    if not cards:
        print("원문을 찾을 수 있는 표가 없다.")
        return 1

    page = (PAGE.replace("__CARDS__", json.dumps(cards, ensure_ascii=False))
                .replace("__IMGS__", json.dumps(imgs)))
    name = a.out or os.path.join(OUT, "spec-verify.html")
    with open(name, "w", encoding="utf-8") as f:
        f.write(page)

    located = sum(1 for c in cards if c["located"])
    mb = os.path.getsize(name) / 1024.0 / 1024.0
    print("  %s" % os.path.normpath(name))
    print("  표 %d건 · 그림 %d장 · %.1f MB" % (len(cards), len(imgs), mb))
    print("  표 위치 특정 %d / %d (나머지는 쪽 전체로 보여 준다)" % (located, len(cards)))
    skipped = len(picked) - len(cards)
    if skipped:
        print("  원문 없어 제외 %d건" % skipped)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
