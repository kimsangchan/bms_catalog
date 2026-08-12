# -*- coding: utf-8 -*-
"""요구항목 기준 육안검사 — 표가 아니라 **필요한 값**에서 출발한다.

verify.py 는 "우리가 읽은 표가 원문과 맞나"를 본다(표 기준). 이건 반대다.
**요구 항목마다** "그 값을 찾았나, 못 찾았으면 원문 어디에 있나"를 본다.

왜 반대 방향이 필요한가
  표 기준으로는 **없는 것을 볼 수 없다.** 기외정압을 한 번도 안 읽었으면 표 목록에
  아예 안 나타난다. 그런데 그게 팬 전력 계산의 필수 입력이다.
  요구 항목에서 출발해야 "이 값이 비었다 → 원문 어디에 있나 → 룰을 고친다"가 돈다.

무엇을 보여 주나
  · 찾은 값 — 어느 형번에서 얼마가 나왔는지, 근거 문서·쪽과 함께
  · 못 찾았으면 **후보 쪽** — 정의의 searchTerms 로 원문을 훑어 걸린 쪽을 잘라서 띄운다.
    걸린 낱말은 형광 표시한다.
  · 사람이 [여기 있다 / 여기 없다] 를 찍으면 그게 추출 룰 수정 과제가 된다.

실행
  PYTHONIOENCODING=utf-8 python verify_req.py --profile e5.rtu
  PYTHONIOENCODING=utf-8 python verify_req.py --profile e5.rtu --gaps   # 빈 항목만
"""
import argparse
import base64
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
RAW = os.path.join(DATA, "raw")
OUT = os.path.join(HERE, "..", "review")
sys.path.insert(0, HERE)
import requirements as RQ  # noqa: E402

CAND_DPI = 100
MAX_CAND_PER_MODEL = 2
MAX_CAND_PER_ITEM = 10
FILL_NEEDS_HELP = 60.0      # 이 밑이면 후보를 찾아 준다
SAMPLE_VALUES = 8


def source_pdfs(model):
    """모델이 근거로 쓰는 원문 파일 목록 (사양 표 + 형번 확정본)."""
    out = []
    for t in (model.get("specTables") or []):
        s = (t.get("source") or "").split("#")[0]
        if s and s not in out:
            out.append(s)
    for u in RQ.curated(model.get("id")):
        s = (u.get("source") or {})
        f = s.get("sourceFile") if isinstance(s, dict) else None
        f = f or u.get("sourceFile")
        if f and f not in out:
            out.append(f)
    return [f for f in out if os.path.exists(os.path.join(RAW, f))]


def found_values(models, item):
    """이 항목에 해당하는 값이 실제로 어디서 얼마나 나왔나."""
    feats = item.get("features") or []
    rows, hit, tot = [], 0, 0
    for m in models:
        for u in RQ.curated(m["id"]):
            tot += 1
            vals = RQ.field_values(u)
            got = {f: vals[f] for f in feats if f in vals}
            if got:
                hit += 1
                if len(rows) < SAMPLE_VALUES:
                    src = u.get("source") or {}
                    rows.append({
                        "model": m.get("model") or m["id"],
                        "unit": u.get("unitModelNumber"),
                        "vals": got,
                        "src": (src.get("sourceFile") if isinstance(src, dict)
                                else "") or "",
                        "page": (src.get("sourcePage") if isinstance(src, dict)
                                 else "") or "",
                    })
    fill = (100.0 * hit / tot) if tot else 0.0
    return rows, fill, hit, tot


# 낱말 경계로 찾는다. 부분문자열로 찾으면 'esp' 가 'especially' 에 걸려
# 브로슈어 쪽이 1순위로 올라온다 (2026-08-11 첫 육안검사에서 실제로 그랬다).
def term_re(t):
    return re.compile(r"(?<![a-z0-9])" + re.escape(t.lower()) + r"(?![a-z0-9])")


# 값이 실린 쪽에는 숫자가 빽빽하다. 홍보 문구 쪽은 낱말만 맞고 숫자가 없다.
MIN_DIGITS = 40


def find_candidates(models, item):
    """searchTerms 로 원문을 훑어 후보 쪽을 그림으로 만든다."""
    import fitz
    pats = [(t, term_re(t)) for t in (item.get("searchTerms") or [])]
    if not pats:
        return []
    cands = []
    for m in models:
        if len(cands) >= MAX_CAND_PER_ITEM:
            break
        got_for_model = 0
        for fname in source_pdfs(m):
            if got_for_model >= MAX_CAND_PER_MODEL:
                break
            path = os.path.join(RAW, fname)
            try:
                doc = fitz.open(path)
            except Exception:
                continue
            scored = []
            for pi in range(doc.page_count):
                try:
                    txt = doc[pi].get_text().lower()
                except Exception:
                    continue
                hits = [t for t, p in pats if p.search(txt)]
                digits = sum(1 for c in txt if c.isdigit())
                if len(hits) >= 2 and digits >= MIN_DIGITS:
                    scored.append((len(hits), digits, pi, hits))
            scored.sort(reverse=True)
            scored = [(h, pi, hs) for h, _d, pi, hs in scored]
            for _, pi, hits in scored[:MAX_CAND_PER_MODEL - got_for_model]:
                page = doc[pi]
                for t in hits[:3]:
                    try:
                        for r in page.search_for(t)[:6]:
                            page.add_highlight_annot(r)
                    except Exception:
                        pass
                pix = page.get_pixmap(dpi=CAND_DPI)
                cands.append({
                    "model": m.get("model") or m["id"],
                    "modelId": m["id"],
                    "file": fname,
                    "page": pi + 1,
                    "hits": hits[:5],
                    "img": "data:image/jpeg;base64," + base64.b64encode(
                        pix.tobytes("jpeg", jpg_quality=68)).decode("ascii"),
                })
                got_for_model += 1
                if len(cands) >= MAX_CAND_PER_ITEM:
                    break
            doc.close()
    return cands


PAGE = r"""<!doctype html>
<meta charset="utf-8">
<title>요구항목 육안검사 — __TITLE__</title>
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
.model{font-size:12px;color:var(--dim);margin-top:6px}
.wrap{padding:20px;max-width:1500px;margin:0 auto}
.eq{background:var(--panel);border:1px solid var(--line);border-radius:10px;
  padding:12px 16px;margin-bottom:18px;font-size:13px}
.eq b{font-weight:600}
.eq div{margin:3px 0;color:var(--dim)}
.eq code{font:12px var(--mono);color:var(--ink)}
.item{background:var(--panel);border:1px solid var(--line);border-radius:12px;
  margin-bottom:18px;overflow:hidden}
.item.ok{border-left:4px solid var(--accent)}
.item.gap{border-left:4px solid var(--bad)}
.item.part{border-left:4px solid var(--warn)}
.ih{padding:12px 16px;border-bottom:1px solid var(--line2)}
.ih h2{margin:0;font-size:15px;display:flex;gap:9px;align-items:baseline;flex-wrap:wrap}
.grade{font-size:11px;padding:2px 7px;border-radius:5px;border:1px solid var(--line);color:var(--dim)}
.grade.필수{background:var(--bad-bg);color:var(--bad);border-color:transparent}
.grade.권장{background:var(--warn-bg);color:var(--warn);border-color:transparent}
.fill{margin-left:auto;font:12px var(--mono);color:var(--dim)}
.why{font-size:13px;color:var(--dim);margin-top:5px}
.use{font:11px var(--mono);color:var(--faint)}
.body{padding:14px 16px}
.lab{font-size:11px;color:var(--faint);text-transform:uppercase;
  letter-spacing:.06em;margin:2px 0 8px}
table{border-collapse:collapse;font-size:13px;width:100%;margin-bottom:6px}
th,td{border:1px solid var(--line);padding:4px 8px;text-align:left;white-space:nowrap}
th{background:var(--line2);font-weight:600}
.none{color:var(--bad);font-size:13px;margin-bottom:10px}
.cands{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:14px}
.cand{border:1px solid var(--line);border-radius:9px;overflow:hidden;background:var(--bg)}
.cand img{width:100%;display:block;background:#fff;cursor:zoom-in}
.cm{padding:7px 10px;font-size:12px;color:var(--dim);border-bottom:1px solid var(--line2)}
.cm b{color:var(--ink);font-weight:600}
.hits{font:11px var(--mono);color:var(--accent)}
.cb{padding:8px 10px;display:flex;gap:6px;border-top:1px solid var(--line2)}
button{font:inherit;font-size:13px;padding:4px 10px;border:1px solid var(--line);
  border-radius:6px;background:var(--panel);color:var(--ink);cursor:pointer}
button:hover{background:var(--sel)}
button.yes.on{background:var(--accent);border-color:var(--accent);color:#fff}
button.no.on{background:var(--bad);border-color:var(--bad);color:#fff}
.bar{display:flex;gap:8px;margin-top:10px;flex-wrap:wrap}
.bar button.on{background:var(--ink);color:var(--bg);border-color:var(--ink)}
dialog{border:none;border-radius:12px;padding:0;background:var(--panel)}
dialog::backdrop{background:rgba(0,0,0,.7)}
dialog img{display:block;max-width:96vw;max-height:92vh}
</style>
<header>
  <h1>요구항목 육안검사 — __TITLE__</h1>
  <div class="sub" id="sub"></div>
  <div class="model" id="mods"></div>
  <div class="bar">
    <button id="f-all" class="on">전체</button>
    <button id="f-gap">빈 항목만</button>
    <button id="export">판정 내보내기 (JSON)</button>
  </div>
</header>
<div class="wrap">
  <div class="eq" id="eq"></div>
  <div id="list"></div>
</div>
<dialog id="zoom"><img id="zoomimg" alt=""></dialog>
<script>
const D = __DATA__;
const KEY = "req-verify-" + D.profileId;
let marks = {};
try { marks = JSON.parse(localStorage.getItem(KEY) || "{}"); } catch(e) {}
let onlyGap = false;
const esc = s => String(s==null?"":s).replace(/[&<>"]/g,
  c => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

function valTable(rows){
  if (!rows.length) return "";
  const keys = [...new Set(rows.flatMap(r => Object.keys(r.vals)))];
  let h = "<table><thead><tr><th>형번</th><th>모델</th>"
        + keys.map(k => "<th>"+esc(k)+"</th>").join("")
        + "<th>근거</th></tr></thead><tbody>";
  rows.forEach(r => {
    h += "<tr><td>"+esc(r.unit)+"</td><td>"+esc(r.model)+"</td>"
       + keys.map(k => "<td>"+esc(r.vals[k]==null?"":r.vals[k])+"</td>").join("")
       + "<td>"+esc(r.src)+(r.page?(" p"+esc(r.page)):"")+"</td></tr>";
  });
  return h+"</tbody></table>";
}

function cand(it, c, i){
  const id = it.id+"|"+c.modelId+"|"+c.file+"|"+c.page;
  const v = marks[id];
  return '<div class="cand">'
    + '<div class="cm"><b>'+esc(c.file)+'</b> p'+esc(c.page)
    + '<br>'+esc(c.model)
    + '<br><span class="hits">'+esc((c.hits||[]).join(" · "))+'</span></div>'
    + '<img loading="lazy" src="'+c.img+'" alt="후보 쪽">'
    + '<div class="cb" data-id="'+esc(id)+'">'
    +   '<button class="yes'+(v==="yes"?" on":"")+'" data-m="yes">여기 있다</button>'
    +   '<button class="no' +(v==="no" ?" on":"")+'" data-m="no">여기 없다</button>'
    + '</div></div>';
}

function item(it){
  const cls = it.fill >= 60 ? "ok" : (it.fill > 0 ? "part" : "gap");
  let body = "";
  if (it.found.length) {
    body += '<div class="lab">찾은 값 (표본 '+it.found.length+' / 채움 '
          + it.hit+'·'+it.tot+'건)</div>' + valTable(it.found);
  } else {
    body += '<div class="none">찾은 값이 없다.</div>';
  }
  if (it.candidates.length) {
    body += '<div class="lab" style="margin-top:14px">원문 후보 — 이 쪽에 값이 있나?</div>'
          + '<div class="cands">'
          + it.candidates.map((c,i) => cand(it,c,i)).join("") + '</div>';
  } else if (it.fill < 60) {
    body += '<div class="none">원문에서 후보를 못 찾았다 — 검색어를 넓히거나 문서가 없다.</div>';
  }
  return '<div class="item '+cls+'">'
    + '<div class="ih"><h2>'+esc(it.name)
    +   '<span class="grade '+esc(it.grade)+'">'+esc(it.grade)+'</span>'
    +   '<span class="use">'+esc((it.usedBy||[]).join(","))+'</span>'
    +   '<span class="fill">'+it.fill.toFixed(0)+'%</span></h2>'
    + '<div class="why">'+esc(it.why)+'</div>'
    + '<div class="use">찾을 곳: '+esc(it.sourceHint)+'</div></div>'
    + '<div class="body">'+body+'</div></div>';
}

function render(){
  const items = D.items.filter(i => !onlyGap || i.fill < 60);
  document.getElementById("list").innerHTML = items.map(item).join("");
  const gaps = D.items.filter(i => i.grade==="필수" && i.fill < 60).length;
  document.getElementById("sub").textContent =
    "요구 항목 " + D.items.length + "개 · 필수인데 빈 것 " + gaps
    + "개 · 형번 확정본 " + D.unitCount + "건";
  document.getElementById("mods").textContent = "대상 모델: " + D.models.join(" · ");
  document.getElementById("eq").innerHTML = "<b>계산식</b>"
    + Object.entries(D.energyModel).map(([k,v]) =>
        "<div><code>"+esc(k)+"</code> &nbsp;"+esc(v)+"</div>").join("");
}

document.addEventListener("click", e => {
  const b = e.target.closest("button[data-m]");
  if (b) {
    const id = b.parentNode.dataset.id, m = b.dataset.m;
    if (marks[id] === m) delete marks[id]; else marks[id] = m;
    localStorage.setItem(KEY, JSON.stringify(marks));
    render();
    return;
  }
  const img = e.target.closest(".cand img");
  if (img) {
    document.getElementById("zoomimg").src = img.src;
    document.getElementById("zoom").showModal();
  }
});
document.getElementById("zoom").addEventListener("click", e => e.currentTarget.close());
document.getElementById("f-all").onclick = e => {
  onlyGap=false; e.target.classList.add("on");
  document.getElementById("f-gap").classList.remove("on"); render(); };
document.getElementById("f-gap").onclick = e => {
  onlyGap=true; e.target.classList.add("on");
  document.getElementById("f-all").classList.remove("on"); render(); };
document.getElementById("export").onclick = () => {
  const rows = Object.entries(marks).map(([k,v]) => {
    const [item, modelId, file, page] = k.split("|");
    return {item, modelId, file, page: Number(page), mark: v};
  });
  const b = new Blob([JSON.stringify({profile: D.profileId, rows}, null, 2)],
                     {type:"application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b);
  a.download = "req-marks-" + D.profileId + ".json";
  a.click();
};
render();
</script>
"""


def main(argv):
    ap = argparse.ArgumentParser(description="요구항목 기준 육안검사 화면")
    ap.add_argument("--profile", default="e5.rtu")
    ap.add_argument("--gaps", action="store_true",
                    help="빈 항목만 (후보 탐색도 그것만)")
    ap.add_argument("-o", "--out")
    a = ap.parse_args(argv)

    profs = RQ.profiles()
    p = profs.get(a.profile)
    if not p:
        print("그런 프로파일이 없다: %s (있는 것: %s)"
              % (a.profile, ", ".join(profs)))
        return 1
    models = [m for m in RQ.models() if RQ.profile_for(m) == a.profile]
    if not models:
        print("해당 모델이 없다.")
        return 1
    print("%s — 모델 %d개. 요구 항목별로 값과 원문 후보를 모은다…"
          % (a.profile, len(models)))

    items, ucount = [], 0
    for m in models:
        ucount += len(RQ.curated(m["id"]))
    for it in (p.get("items") or []):
        rows, fill, hit, tot = found_values(models, it)
        cands = []
        need = fill < FILL_NEEDS_HELP and it.get("grade") in ("필수", "권장")
        if need and (not a.gaps or fill < FILL_NEEDS_HELP):
            print("   후보 탐색: %s (채움 %.0f%%)" % (it["name"], fill))
            cands = find_candidates(models, it)
        items.append({
            "id": it["id"], "name": it["name"], "grade": it.get("grade"),
            "usedBy": it.get("usedBy") or [], "why": it.get("why") or "",
            "sourceHint": it.get("sourceHint") or "",
            "found": rows, "fill": fill, "hit": hit, "tot": tot,
            "candidates": cands,
        })

    data = {
        "profileId": a.profile, "title": p.get("title"),
        "energyModel": p.get("energyModel") or {},
        "models": [m.get("model") or m["id"] for m in models],
        "unitCount": ucount, "items": items,
    }
    page = (PAGE.replace("__DATA__", json.dumps(data, ensure_ascii=False))
                .replace("__TITLE__", p.get("title") or a.profile))
    name = a.out or os.path.join(OUT, "req-verify-%s.html" % a.profile)
    with open(name, "w", encoding="utf-8") as f:
        f.write(page)
    ncand = sum(len(i["candidates"]) for i in items)
    print("  %s" % os.path.normpath(name))
    print("  항목 %d · 원문 후보 %d장 · %.1f MB"
          % (len(items), ncand, os.path.getsize(name) / 1024.0 / 1024.0))
    gaps = [i for i in items if i["grade"] == "필수" and i["fill"] < 60]
    if gaps:
        print("  필수인데 빈 항목 %d개: %s"
              % (len(gaps), ", ".join(i["name"][:20] for i in gaps)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
