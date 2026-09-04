# -*- coding: utf-8 -*-
"""LG BACnet 오브젝트 목록 대조 화면 — review/lg-bacnet-verify.html

  PYTHONIOENCODING=utf-8 python verify_lg.py

**팝업을 쓰지 않는다.** 기존 검사대(ingest_jci.py)는 원문 쪽을 dialog 로 94vw x 92vh
띄워서, 뜨는 순간 뽑은 표가 가려졌다 — 값 대조는 둘을 **동시에** 봐야 되는 일이라
그 구조로는 눈이 왔다 갔다 한다. 여기서는 좌우 2단으로 나눠 둘 다 늘 보이게 하고,
행을 고르면 오른쪽이 그 쪽으로 따라간다.

⚠ 원문 표가 **전치돼 있다** — 행이 속성(Object Type·Object Name·Point No.)이고
   열이 포인트다. 세로로 세면 15점짜리 표가 10행으로 읽힌다.
⚠ 기기군은 **쪽 제목**('BACnet Point List : ODU')으로 정한다. 열 라벨보다 정확하고,
   제목이 없는 이어지는 쪽은 앞 제목을 승계한다.
⚠ 산출물은 쪽 그림을 담아 gitignore 된다. 이 스크립트가 정본이다 —
   원문은 대장에 있으므로 collect.py --run lg-bacnet-gateway 로 어디서든 다시 받는다.
"""
import base64
import io
import json
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
SRC_ID = "lg-bacnet-gateway"
OUT = os.path.join(HERE, "..", "review", "lg-bacnet-verify.html")

# 표가 실린 쪽. 쪽 제목이 기기군을 정하고, 제목 없는 쪽은 앞 제목을 승계한다.
PAGES = [34, 35, 36, 38, 39, 41, 42, 43, 44, 46, 47, 48, 49]
# 기기군 → (한글 이름, 제품유형). 제품유형은 원문 50쪽이 못 박았다:
#   "Product Type(Indoor:0, Vent:1, AHU:2, ODU:3, AWHP:4, GENERAL:5)"
#   "Device : Group of Product units(16EA)"
# 그래서 instance = 제품유형*0x10000 + Device*0x1000 + Product*0x100 + Point 이고
# 이름 끝 _XXX(= Unit address) = Device*16 + Product 다.
# 원문 50~52쪽 예시 42행에 맞춰 봤다 — 42/42 일치.
# ⚠ 이름은 원문 낱말만 쓴다. 원문은 HRV 가 아니라 **ERV** 라고 쓴다(5쪽 장치 목록).
KO = {"Indoor Unit": ("실내기", 0), "Ventilation": ("환기(ERV)", 1),
      "AHU": ("공조기(AHU)", 2), "ODU": ("실외기(ODU)", 3),
      "AWHP": ("AWHP", 4), "GENERAL": ("게이트웨이 공통", 5)}


def ledger_entry():
    """대장에서 원문을 찾는다 — 폴더를 훑으면 그 PC 에만 묶인다."""
    led = json.load(io.open(os.path.join(DATA, "collected.json"), encoding="utf-8"))
    for url, v in led.items():
        if v.get("source") == SRC_ID and v.get("file"):
            return url, v
    raise SystemExit("대장에 %s 가 없다 — 먼저 collect.py --run %s" % (SRC_ID, SRC_ID))


def printed_no(page, fallback):
    """머리글의 인쇄 쪽번호. 이 문서는 PDF 쪽 - 8 이지만 **가정하지 않고 읽는다** —
    개정판에서 앞표지 장수가 바뀌면 오프셋이 조용히 틀린다."""
    for line in page.get_text().splitlines()[:4]:
        s = line.strip()
        if s.isdigit() and 1 <= int(s) <= 999:
            return int(s)
    return fallback


def ident(s, txt):
    """오브젝트 이름의 조판 아티팩트를 지운다 — 빈칸 하나하나를 **원문에 물어본다.**

    ⚠ re.sub(r"\\s+", " ") 로 뭉개면 안 된다. 그렇게 했다가 165점 중 43점의 이름이
      'StartStopCommand_ XXX' 가 됐다 — 원문에 없는 빈칸이다.
    ⚠ 그렇다고 빈칸을 전부 지워도 안 된다. 원문이 정말 띄어 쓰는 이름이 있다.
      쪽 글자흐름을 세어 갈랐다(표 인식이 아닌 경로):
        '_XXX'                   붙음 236회 · **빈칸 0회** · 줄바꿈 34회 → 조판이다
        'Filter Sign'            빈칸 14회 · 줄바꿈 0회                 → 원문의 빈칸이다
        'InverterDischarge Temp' 빈칸  0회 · 줄바꿈 2회                 → 조판이다
    ⚠ 표 인식(find_tables)은 줄바꿈을 이미 빈칸으로 바꿔 놓아 셀만 봐서는 못 가른다.
      그래서 같은 쪽의 **글자흐름**에서 이름을 다시 찾아 빈칸 자리의 진짜 구분자를 본다.
      한 쪽에 여러 번 나오면 많이 나온 쪽을 따른다.
      원문 그대로는 provenance.sourceColumns['Object Name'] 에 남는다(artifactCleanupFirst).
    """
    toks = [t for t in s.split() if t]
    if len(toks) < 2:
        return "".join(toks)
    hits = list(re.finditer("(\\s*)".join(map(re.escape, toks)), txt))
    if not hits:
        return s.strip()
    out = toks[0]
    for i, t in enumerate(toks[1:]):
        joined = sum(1 for h in hits if "\n" in h.group(i + 1) or not h.group(i + 1))
        out += ("" if joined * 2 > len(hits) else " ") + t
    return out


def prose(s):
    """설명문은 반대다 — 줄바꿈이 낱말 사이를 자른 것이라 빈칸으로 바꾼다."""
    return re.sub(r"\s+", " ", s).strip()


def row_of(rows, key):
    for r in rows:
        if r and str(r[0] or "").strip().startswith(key):
            return r
    return None


def extract(doc):
    """전치된 표에서 포인트를 뽑는다 — 열 하나가 포인트 하나다."""
    group_of, cur = {}, None
    for p in PAGES:
        m = re.search(r"BACnet Point List\s*:?\s*([^\n]*)", doc[p - 1].get_text())
        if m and m.group(1).strip():
            cur = m.group(1).strip()
        group_of[p] = cur

    tables = []
    for p in PAGES:
        flow = doc[p - 1].get_text()         # 빈칸/줄바꿈을 가를 근거는 여기 있다
        for t in doc[p - 1].find_tables().tables:
            rows = t.extract()
            ot, on = row_of(rows, "Object Type"), row_of(rows, "Object Name")
            cm, pn = row_of(rows, "Control/monitoring"), row_of(rows, "Point No.")
            txt = [row_of(rows, "Text-%d" % i) for i in range(6)]
            if not (ot and on and pn):
                continue
            pts = []
            for c in range(len(pn)):
                num = str(pn[c] or "").strip()
                name = (str(on[c]) if c < len(on) else "").strip()
                if not num.isdigit() or not name or name in ("-", "None"):
                    continue
                states = []
                for i, tr in enumerate(txt):
                    v = (str(tr[c]).strip() if tr and c < len(tr) else "")
                    if v and v not in ("None", "-", ""):
                        states.append("%d=%s" % (i, v))
                pts.append({"no": int(num), "name": ident(name, flow), "nameRaw": name,
                            "type": (str(ot[c]).strip() if c < len(ot) else ""),
                            "desc": prose(str(cm[c]).strip()) if cm and c < len(cm) else "",
                            "states": ", ".join(states)})
            if pts:
                ko, ptype = KO.get(group_of[p], (group_of[p] or "?", None))
                tables.append({"page": p, "printed": printed_no(doc[p - 1], p),
                               "group": ko, "ptype": ptype, "points": pts})
    return tables


def page_images(doc, pages):
    """회색조 WebP. 컬러 JPEG 는 같은 쪽에서 몇 배가 된다(저장소 실측).

    ⚠ 표가 쪽 안에서 90도 눕혀 인쇄돼 있어 그대로 두면 고개를 돌려야 읽힌다.
    **시계방향(-90)** 으로 돌려 담는다 — 그러면 포인트가 한 줄씩 가로로 읽혀
    왼쪽 목록과 눈높이가 맞는다. 화면의 '세로로' 단추가 원래 방향으로 되돌린다.
    """
    import fitz
    from PIL import Image
    out = {}
    for p in sorted(pages):
        pix = doc[p - 1].get_pixmap(dpi=140, colorspace=fitz.csGRAY)
        im = Image.open(io.BytesIO(pix.tobytes("png"))).rotate(-90, expand=True)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=52, method=4)
        out[p] = base64.b64encode(buf.getvalue()).decode("ascii")
    return out


def main():
    import fitz
    url, meta = ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다: %s — collect.py --run %s" % (path, SRC_ID))
    doc = fitz.open(path)

    tables = extract(doc)
    total = sum(len(t["points"]) for t in tables)
    imgs = page_images(doc, {t["page"] for t in tables})
    payload = json.dumps({"doc": meta["file"], "sha": meta.get("sha256", ""), "url": url,
                          "source": SRC_ID, "total": total, "tables": tables, "pages": imgs},
                         ensure_ascii=False, separators=(",", ":"))
    # 데이터 안에 스크립트 닫는 표가 있으면 스크립트가 일찍 닫힌다. base64 라 없을 것이나 세운다.
    assert "</scr" + "ipt>" not in payload

    io.open(OUT, "w", encoding="utf-8", newline="\n").write(
        TEMPLATE.replace("__PAYLOAD__", payload))
    print("표 %d개 · 포인트 %d점 · 쪽 그림 %d장" % (len(tables), total, len(imgs)))
    for t in tables:
        print("   원문 %3d쪽(PDF %2d) %-14s %2d점"
              % (t["printed"], t["page"], t["group"], len(t["points"])))
    print("→ %s  (%.2f MB)" % (os.path.relpath(OUT, HERE), os.path.getsize(OUT) / 1048576))


TEMPLATE = r"""
<title>LG BACnet 대조대</title>
<style>
/* 토큰은 기존 검사대(ingest_jci.py)와 같은 것을 쓴다 — 한 세트로 보여야 한다.
   세 상태를 모두 정의한다: 기본(밝음) · OS 어두움 · 명시 선택. */
:root{
  --bg:#F5F8F9; --panel:#FFFFFF; --rail:#EDF2F4; --ink:#0F1A1F; --dim:#4A6068;
  --faint:#7C949C; --line:#DAE3E7; --accent:#0E7A88; --accent-soft:#DCEEF0;
  --warn:#9A6608; --ok:#1F6B4B; --shadow:0 1px 14px rgba(15,26,31,.16);
  --mono:ui-monospace,"Cascadia Mono",Consolas,"Noto Sans Mono",monospace;
  --ui:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic","Apple SD Gothic Neo",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --bg:#0C1417; --panel:#111C20; --rail:#0E181C; --ink:#DCE7EA; --dim:#93A8AF;
    --faint:#6B838B; --line:#1E2C32; --accent:#3FB4C2; --accent-soft:#10333A;
    --warn:#D9A441; --ok:#5FBF95; --shadow:0 1px 14px rgba(0,0,0,.45);
  }
}
:root[data-theme="dark"]{
  --bg:#0C1417; --panel:#111C20; --rail:#0E181C; --ink:#DCE7EA; --dim:#93A8AF;
  --faint:#6B838B; --line:#1E2C32; --accent:#3FB4C2; --accent-soft:#10333A;
  --warn:#D9A441; --ok:#5FBF95; --shadow:0 1px 14px rgba(0,0,0,.45);
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font-family:var(--ui);
 font-size:13px;line-height:1.5;overflow:hidden}
@media (prefers-reduced-motion:reduce){*{transition:none!important;animation:none!important}}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px;border-radius:3px}
button{font:inherit}

/* ── 맨 위 한 줄. 뷰 전환이 여기 있어야 어느 모드에서도 사라지지 않는다 ── */
.top{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
 padding:8px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
.brand{font-size:14px;font-weight:650;letter-spacing:-.01em;white-space:nowrap}
.docmeta{font-size:11px;color:var(--faint);font-family:var(--mono);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:36ch}
.top .sp{flex:1}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
.seg button{padding:4px 11px;border:0;border-right:1px solid var(--line);background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer}
.seg button:last-child{border-right:0}
.seg button:hover{background:var(--accent-soft);color:var(--ink)}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff;font-weight:600}
.zbtn{padding:4px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer;white-space:nowrap}
.zbtn:hover{background:var(--accent-soft);color:var(--ink)}
.pgno{font-family:var(--mono);font-weight:700;color:var(--ink);white-space:nowrap}

/* ── 2단 작업대. 팝업을 쓰지 않는다 — 대조는 둘을 동시에 봐야 되는 일이다 ── */
.app{display:grid;grid-template-columns:var(--lw,50%) 7px 1fr;height:calc(100dvh - 41px)}
.app.only-list{grid-template-columns:1fr 0 0}
.app.only-page{grid-template-columns:0 0 1fr}
.app.only-list .right,.app.only-page .left,
.app.only-list .grip,.app.only-page .grip{display:none}
.pane{min-width:0;display:flex;flex-direction:column;overflow:hidden}
.left{border-right:1px solid var(--line);background:var(--panel)}
.right{background:var(--rail)}
.grip{cursor:col-resize;background:var(--line)}
.grip:hover,.grip.on{background:var(--accent)}

/* ── 왼쪽 머리 ── */
.head{padding:10px 14px;border-bottom:1px solid var(--line);background:var(--panel)}
.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
input[type=search],input.addr{padding:5px 9px;border:1px solid var(--line);
 border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;font-size:12px}
input[type=search]{flex:1;min-width:120px}
input.addr{width:74px;font-family:var(--mono);text-align:right}
.chip{padding:3px 9px;border:1px solid var(--line);border-radius:999px;background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer;white-space:nowrap}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.chip[aria-pressed=true]{background:var(--accent-soft);border-color:var(--accent);
 color:var(--ink);font-weight:600}
.addrbox{display:flex;align-items:center;gap:6px;margin-top:9px;padding:7px 9px;
 border:1px solid var(--line);border-radius:7px;background:var(--bg);font-size:11.5px}
.addrbox label{color:var(--dim);white-space:nowrap}
.addrbox .why{color:var(--faint);font-size:11px;line-height:1.4}
.prog{display:flex;align-items:center;gap:8px;margin-top:9px;font-size:11.5px;color:var(--dim)}
.bar{flex:1;height:5px;border-radius:3px;background:var(--rail);overflow:hidden}
.bar i{display:block;height:100%;background:var(--ok);width:0}
.cnt{font-family:var(--mono);font-variant-numeric:tabular-nums}

/* ── 표 ── */
.scroll{flex:1;overflow:auto}
.gh{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--line);
 padding:7px 14px 6px;font-size:11px;font-weight:700;letter-spacing:.06em;
 text-transform:uppercase;color:var(--faint);display:flex;gap:8px;align-items:baseline}
.gh b{color:var(--accent);font-weight:700}
.gh .pg{margin-left:auto;font-family:var(--mono);text-transform:none;letter-spacing:0}
table{border-collapse:collapse;width:100%;font-size:12px}
td{padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
tr.row{cursor:pointer}
tr.row:hover{background:var(--accent-soft)}
tr.row.sel{background:var(--accent-soft);box-shadow:inset 3px 0 0 var(--accent)}
tr.row.done td.nm{color:var(--faint)}
td.ck{width:24px;padding-left:14px;color:var(--faint);text-align:center;user-select:none}
tr.row.done td.ck{color:var(--ok)}
td.no{width:30px;font-family:var(--mono);font-variant-numeric:tabular-nums;
 color:var(--faint);text-align:right}
td.ty{width:38px}
.ty span{display:inline-block;padding:1px 5px;border-radius:4px;font-family:var(--mono);
 font-size:10.5px;font-weight:700;background:var(--rail);color:var(--dim)}
.ty span.o{background:var(--accent-soft);color:var(--accent)}
td.nm{font-family:var(--mono);font-size:11.5px;word-break:break-all}
td.nm em{font-style:normal;color:var(--accent);font-weight:700}
td.inst{width:120px;font-family:var(--mono);font-size:11px;color:var(--dim);
 font-variant-numeric:tabular-nums;white-space:nowrap}
td.inst b{color:var(--ink);font-weight:600}
td.ds{color:var(--dim)}
.st{display:block;margin-top:2px;font-size:10.5px;color:var(--faint);font-family:var(--mono)}
.none{padding:26px 14px;color:var(--faint);text-align:center}

/* ── 원문 쪽: 늘 보인다 ── */
.view{flex:1;position:relative;overflow:hidden;background:var(--rail);cursor:grab;touch-action:none}
.view.drag{cursor:grabbing}
.view img{position:absolute;top:0;left:0;transform-origin:0 0;background:#fff;box-shadow:var(--shadow)}
.hint{position:absolute;left:0;right:0;bottom:0;padding:6px 12px;background:var(--panel);
 border-top:1px solid var(--line);font-size:11px;color:var(--faint)}
kbd{font-family:var(--mono);font-size:10.5px;border:1px solid var(--line);border-bottom-width:2px;
 border-radius:4px;padding:0 4px;color:var(--dim);background:var(--bg)}
@media (max-width:860px){
  body{overflow:auto}
  .app,.app.only-list,.app.only-page{grid-template-columns:1fr;height:auto}
  .grip{display:none}
  .left{border-right:0;border-bottom:1px solid var(--line)}
  .view{height:70vh}
  .docmeta{display:none}
}
</style>

<div class="top">
  <span class="brand">LG BACnet 대조대</span>
  <span class="docmeta" id="meta"></span>
  <span class="seg" id="vseg">
    <button type="button" data-v="list" aria-pressed="false">표만</button>
    <button type="button" data-v="both" aria-pressed="true">나란히</button>
    <button type="button" data-v="page" aria-pressed="false">원문만</button>
  </span>
  <span class="sp"></span>
  <span>원문 <span class="pgno" id="rpg">—</span></span>
  <button class="zbtn" type="button" data-z="rot" id="rotb">세로로</button>
  <button class="zbtn" type="button" data-z="fit">맞춤</button>
  <button class="zbtn" type="button" data-z="1">100%</button>
  <button class="zbtn" type="button" data-z="-">−</button>
  <button class="zbtn" type="button" data-z="+">+</button>
</div>

<div class="app" id="app">
  <section class="pane left">
    <div class="head">
      <div class="tools">
        <input type="search" id="q" placeholder="이름·설명 찾기" aria-label="포인트 찾기">
        <span id="chips"></span>
      </div>
      <div class="addrbox">
        <label for="addr">유닛 주소 <span class="cnt">XXX</span></label>
        <input class="addr" id="addr" type="number" min="0" max="255" placeholder="—"
               aria-label="유닛 주소">
        <span class="why" id="why"></span>
      </div>
      <div class="prog">
        <span>확인</span>
        <span class="bar"><i id="pbar"></i></span>
        <span class="cnt" id="pcnt"></span>
        <button class="chip" id="reset" type="button">초기화</button>
      </div>
    </div>
    <div class="scroll" id="list"></div>
  </section>

  <div class="grip" id="grip" role="separator" aria-orientation="vertical" tabindex="0"
       aria-label="좌우 폭 조절"></div>

  <section class="pane right">
    <div class="view" id="view">
      <img id="img" alt="원문 쪽">
      <div class="hint" id="hint"></div>
    </div>
  </section>
</div>

<script id="payload" type="application/json">__PAYLOAD__</script>
<script>
(function(){
"use strict";
var D = JSON.parse(document.getElementById("payload").textContent);
var MAP = {"&":"&amp;","<":"&lt;",">":"&gt;"};
MAP[String.fromCharCode(34)] = "&quot;";
function esc(s){
  return String(s == null ? "" : s).replace(/[&<>"]/g, function(c){ return MAP[c]; });
}

document.getElementById("meta").textContent =
  D.doc + " · sha " + D.sha.slice(0, 10) + "… · " + D.total + "점";

/* 확인 표시는 브라우저에만 남는다. 저장이 막힌 환경에서도 화면은 돌아야 한다. */
var KEY = "lg-bacnet-verify/v1", done = {};
try { done = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { done = {}; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (e) {} }

var groups = [];
D.tables.forEach(function(t){ if (groups.indexOf(t.group) < 0) groups.push(t.group); });
var filter = null, query = "", sel = null, addr = null;

var chips = document.getElementById("chips");
chips.innerHTML = ['<button class="chip" type="button" data-g="" aria-pressed="true">전체</button>']
  .concat(groups.map(function(g){
    var n = D.tables.filter(function(t){ return t.group === g; })
                    .reduce(function(a, t){ return a + t.points.length; }, 0);
    return '<button class="chip" type="button" data-g="' + esc(g) + '" aria-pressed="false">'
         + esc(g) + ' <span class="cnt">' + n + '</span></button>';
  })).join("");

/* ── 인스턴스 번호. 원문 50쪽이 규칙을 준다 ──
   Product Type(Indoor:0, Vent:1, AHU:2, ODU:3, AWHP:4, GENERAL:5)
   Device : Group of Product units(16EA)
   instance = 제품유형*0x10000 + Device*0x1000 + Product*0x100 + Point
   XXX(유닛 주소) = Device*16 + Product
   원문 예시 42행으로 맞춰 봤다 — 42/42 일치. */
function instanceOf(ptype, address, point){
  if (ptype == null || address == null) return null;
  return ptype * 0x10000 + Math.floor(address / 16) * 0x1000 + (address % 16) * 0x100 + point;
}
function why(){
  var el = document.getElementById("why");
  if (addr == null) {
    el.innerHTML = '이름 끝 <b>_XXX</b> 는 원문이 <b>(XXX : Unit address)</b> 라고 밝힌 '
                 + '유닛 주소다. 주소를 넣으면 실제 이름과 BACnet 인스턴스 번호가 나온다.';
  } else {
    el.innerHTML = 'Device <b>' + Math.floor(addr / 16) + '</b> · Product <b>'
      + (addr % 16) + '</b> — instance = 유형×0x10000 + Device×0x1000 + Product×0x100 + Point';
  }
}

function key(t, p){ return t.page + ":" + p.no + ":" + p.name; }
function match(p){
  if (!query) return true;
  var q = query.toLowerCase();
  return (p.name + " " + p.desc + " " + p.type + " " + p.states).toLowerCase().indexOf(q) >= 0;
}
function counts(){
  var n = 0, k;
  for (k in done) { if (done[k]) n++; }
  document.getElementById("pcnt").textContent = n + " / " + D.total;
  document.getElementById("pbar").style.width = (100 * n / D.total).toFixed(1) + "%";
}

function render(){
  var out = [], shown = 0;
  D.tables.forEach(function(t){
    if (filter && t.group !== filter) return;
    var pts = t.points.filter(match);
    if (!pts.length) return;
    out.push('<div class="gh"><b>' + esc(t.group) + '</b><span>' + pts.length + '점</span>'
           + '<span class="pg">원문 ' + t.printed + '쪽 <span style="color:var(--faint)">(PDF '
           + t.page + ')</span></span></div><table><tbody>');
    pts.forEach(function(p){
      var k = key(t, p), isOut = /O$/.test(p.type || "");
      var inst = instanceOf(t.ptype, addr, p.no);
      var nm = esc(p.name);
      if (addr != null) {
        nm = nm.replace(/_XXX\b/g, "_<em>" + addr + "</em>");
      }
      shown++;
      out.push('<tr class="row' + (done[k] ? " done" : "") + (sel === k ? " sel" : "")
        + '" data-k="' + esc(k) + '" data-page="' + t.page
        + '" data-printed="' + t.printed + '" tabindex="0">'
        + '<td class="ck">' + (done[k] ? "✓" : "○") + '</td>'
        + '<td class="no">' + p.no + '</td>'
        + '<td class="ty"><span class="' + (isOut ? "o" : "") + '">' + esc(p.type || "—") + '</span></td>'
        + '<td class="nm">' + nm + '</td>'
        + (inst == null ? "" : '<td class="inst"><b>0x' + inst.toString(16).toUpperCase()
            + '</b><br>' + inst + '</td>')
        + '<td class="ds">' + esc(p.desc || "")
        + (p.states ? '<span class="st">' + esc(p.states) + '</span>' : "") + '</td></tr>');
    });
    out.push('</tbody></table>');
  });
  document.getElementById("list").innerHTML =
    shown ? out.join("") : '<p class="none">찾는 포인트가 없다.</p>';
  counts();
}

/* ── 원문 쪽: 고른 행을 따라간다. 가리지 않는다 ── */
var img = document.getElementById("img"), view = document.getElementById("view");
var zoom = 1, ox = 12, oy = 12, natural = 0, naturalH = 0, curPage = null;
var fitMode = true, upright = true;   /* 기본은 표가 가로로 읽히는 방향 */

function boxW(){ return upright ? natural : naturalH; }
function boxH(){ return upright ? naturalH : natural; }
function fit(){
  if (!natural) return;
  var w = view.clientWidth - 24, h = view.clientHeight - 40;
  zoom = Math.min(w / boxW(), h / boxH());
  if (!isFinite(zoom) || zoom <= 0) zoom = 1;
  ox = 12; oy = 12; fitMode = true; apply();
}
function apply(){
  img.style.width = (natural * zoom) + "px";
  /* 세로 보기로 돌릴 때는 원래 방향(반시계 90도)으로 되돌린다 */
  var r = upright ? "" : " rotate(-90deg) translate(" + (-natural * zoom) + "px,0)";
  img.style.transform = "translate(" + ox + "px," + oy + "px)" + r;
}
function show(page, printed){
  if (page === curPage) return;
  curPage = page;
  document.getElementById("rpg").innerHTML = printed + "쪽 <span style=\"color:var(--faint);font-weight:400\">(PDF "
    + page + ")</span>";
  img.onload = function(){
    natural = img.naturalWidth; naturalH = img.naturalHeight;
    if (fitMode) fit(); else apply();
  };
  img.src = "data:image/webp;base64," + D.pages[page];
}
document.getElementById("hint").innerHTML =
  '원문 표를 <b>가로로 눕혀</b> 보여 준다 — 원문은 세로로 인쇄돼 있어 그대로는 읽기 어렵다. '
  + '<kbd>↑</kbd><kbd>↓</kbd> 행 이동 · <kbd>Space</kbd> 확인 · 끌어서 이동, 휠로 확대';

view.addEventListener("wheel", function(e){
  if (!natural) return;
  e.preventDefault();
  var r = view.getBoundingClientRect(), mx = e.clientX - r.left, my = e.clientY - r.top;
  var f = e.deltaY < 0 ? 1.12 : 1 / 1.12, z2 = Math.max(0.1, Math.min(6, zoom * f));
  ox = mx - (mx - ox) * (z2 / zoom); oy = my - (my - oy) * (z2 / zoom);
  zoom = z2; fitMode = false; apply();
}, { passive: false });

var drag = null;
view.addEventListener("pointerdown", function(e){
  drag = { x: e.clientX - ox, y: e.clientY - oy };
  view.classList.add("drag"); view.setPointerCapture(e.pointerId);
});
view.addEventListener("pointermove", function(e){
  if (!drag) return;
  ox = e.clientX - drag.x; oy = e.clientY - drag.y; fitMode = false; apply();
});
["pointerup", "pointercancel"].forEach(function(t){
  view.addEventListener(t, function(){ drag = null; view.classList.remove("drag"); });
});

document.querySelector(".top").addEventListener("click", function(e){
  var b = e.target.closest("button[data-z]");
  if (!b) return;
  var z = b.dataset.z;
  if (z === "rot") {
    upright = !upright;
    document.getElementById("rotb").textContent = upright ? "세로로" : "가로로";
    fitMode = true; fit(); return;
  }
  if (!natural) return;
  if (z === "fit") { fit(); return; }
  if (z === "1") { zoom = 1; ox = 12; oy = 12; fitMode = false; apply(); return; }
  zoom = Math.max(0.1, Math.min(6, zoom * (z === "+" ? 1.2 : 1 / 1.2)));
  fitMode = false; apply();
});
addEventListener("resize", function(){ if (fitMode) fit(); });

/* ── 뷰 전환. 맨 위에 있어 어느 모드에서도 사라지지 않는다 ── */
var appEl = document.getElementById("app"), vseg = document.getElementById("vseg");
vseg.addEventListener("click", function(e){
  var b = e.target.closest("button[data-v]");
  if (!b) return;
  appEl.classList.remove("only-list", "only-page");
  if (b.dataset.v === "list") appEl.classList.add("only-list");
  if (b.dataset.v === "page") appEl.classList.add("only-page");
  [].forEach.call(vseg.querySelectorAll("button"), function(x){
    x.setAttribute("aria-pressed", String(x === b));
  });
  if (fitMode) setTimeout(fit, 0);
});

/* ── 고르기 ── */
function pick(tr, scroll){
  if (!tr) return;
  var prev = document.querySelector("tr.sel");
  if (prev) prev.classList.remove("sel");
  tr.classList.add("sel"); sel = tr.dataset.k;
  show(+tr.dataset.page, tr.dataset.printed);
  if (scroll) tr.scrollIntoView({ block: "nearest" });
}
function toggle(tr){
  var k = tr.dataset.k;
  done[k] = !done[k]; save();
  tr.classList.toggle("done", !!done[k]);
  tr.querySelector(".ck").textContent = done[k] ? "✓" : "○";
  counts();
}
document.getElementById("list").addEventListener("click", function(e){
  var tr = e.target.closest("tr.row");
  if (!tr) return;
  if (e.target.classList.contains("ck")) { toggle(tr); return; }
  pick(tr, false);
});
addEventListener("keydown", function(e){
  if (/^(INPUT|TEXTAREA)$/.test(document.activeElement.tagName)) return;
  var rows = [].slice.call(document.querySelectorAll("tr.row"));
  if (!rows.length) return;
  var i = -1, n;
  for (n = 0; n < rows.length; n++) { if (rows[n].dataset.k === sel) { i = n; break; } }
  if (e.key === "ArrowDown" || e.key === "j") {
    e.preventDefault(); pick(rows[Math.min(rows.length - 1, i + 1)] || rows[0], true);
  } else if (e.key === "ArrowUp" || e.key === "k") {
    e.preventDefault(); pick(rows[Math.max(0, i - 1)] || rows[0], true);
  } else if (e.key === " " && i >= 0) {
    e.preventDefault(); toggle(rows[i]);
  }
});
chips.addEventListener("click", function(e){
  var b = e.target.closest(".chip");
  if (!b) return;
  filter = b.dataset.g || null;
  [].forEach.call(chips.querySelectorAll(".chip"), function(c){
    c.setAttribute("aria-pressed", String(c === b));
  });
  render(); first();
});
document.getElementById("q").addEventListener("input", function(e){
  query = e.target.value.trim(); render(); first();
});
document.getElementById("addr").addEventListener("input", function(e){
  var v = e.target.value.trim();
  addr = (v === "" || isNaN(+v)) ? null : Math.max(0, Math.min(255, parseInt(v, 10)));
  why(); render();
});
document.getElementById("reset").addEventListener("click", function(){
  done = {}; save(); render(); first();
});

/* ── 폭 조절 ── */
var grip = document.getElementById("grip"), gd = false;
grip.addEventListener("pointerdown", function(e){
  gd = true; grip.classList.add("on"); grip.setPointerCapture(e.pointerId);
});
addEventListener("pointermove", function(e){
  if (!gd) return;
  var pct = Math.max(20, Math.min(80, 100 * e.clientX / innerWidth));
  appEl.style.setProperty("--lw", pct + "%");
  if (fitMode) fit();
});
addEventListener("pointerup", function(){ gd = false; grip.classList.remove("on"); });
grip.addEventListener("keydown", function(e){
  var cur = parseFloat(getComputedStyle(appEl).getPropertyValue("--lw")) || 50;
  if (e.key === "ArrowLeft") { appEl.style.setProperty("--lw", Math.max(20, cur - 3) + "%"); if (fitMode) fit(); }
  if (e.key === "ArrowRight") { appEl.style.setProperty("--lw", Math.min(80, cur + 3) + "%"); if (fitMode) fit(); }
});

function first(){ pick(document.querySelector("tr.row"), true); }
why(); render(); first();
})();
</script>
"""


if __name__ == "__main__":
    main()
