# -*- coding: utf-8 -*-
"""대조 화면의 틀 — 두 대조대(verify_lg · verify_points)가 함께 쓴다.

왜 한 틀인가
  대조대가 둘로 늘면서 같은 CSS·JS 450줄이 두 벌이 됐다. 한쪽만 고치면 다른 쪽이
  조용히 뒤처진다 — 확대 단추를 한쪽에만 달았다가 사용자가 그것을 먼저 만났다.

무엇을 주나
  ① 좌우 2단(팝업 없음) — 대조는 표와 원문을 **동시에** 봐야 되는 일이다.
  ② 왼쪽 트리 — 설비 → 벤더 → 모델 → 판. 벤더가 늘어도 화면이 안 무너진다.
  ③ 원문 쪽 확대/축소 — 휠·+/−·폭맞춤·쪽맞춤·더블클릭, 배율을 늘 숫자로 보여 준다.
  ④ 쪽이 눕혀 인쇄된 문서는 **재어서** 돌린다(글자 방향을 세지, 벤더로 가정하지 않는다).

payload 모양
  {title, subtitle, storeKey, tree[], sections[], pages{}, docs{}}
    tree     : {id,label,count,children[]}          — 노드 id 는 sections[].node 와 맞물린다
    sections : {id,node,path[],doc,printed,page,pageKey,addr?,points[]}
    points   : {n,t,i,nm,u,rw,d,s}                  — 없는 값은 그냥 빼면 열이 접힌다
    addr     : {label,ptype,rule,help}              — 있는 판에서만 주소 계산기가 뜬다
"""
import base64
import collections
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def printed_no(page, fallback, scan=5):
    """머리글의 인쇄 쪽번호. 오프셋을 **가정하지 않고 읽는다** —
    개정판에서 앞표지 장수가 바뀌면 'PDF 쪽 - 8' 같은 셈이 조용히 틀린다."""
    import re
    for line in page.get_text().splitlines()[:scan]:
        # 'E-73' 처럼 앞에 절 기호가 붙는 문서가 있다(삼성 설치설명서) — 숫자만 찾으면
        # 못 찾고 이름으로 되찾느라 경고가 뜬다.
        m = re.match(r"^[A-Za-z]{0,2}\s*-?\s*(\d{1,3})$", line.strip())
        if m and 1 <= int(m.group(1)) <= 999:
            return int(m.group(1))
    return fallback


def sideways(page):
    """이 쪽의 글자가 눕혀 있나 — 글줄 방향을 세어서 정한다.

    LG 문서는 표가 90도 돌려 인쇄돼 있고 LS 문서는 똑바르다. 벤더로 가정하면
    새 문서가 들어올 때마다 틀린다. get_text('dict') 의 line.dir 이 (0,±1) 이면
    세로쓰기다 — 재는 것이지 아는 것이 아니다.
    """
    c = collections.Counter()
    for b in page.get_text("dict")["blocks"]:
        for l in b.get("lines") or []:
            d = tuple(round(x) for x in l.get("dir", (1, 0)))
            c[d] += 1
    if not c:
        return False
    (dx, dy), _ = c.most_common(1)[0]
    return dy != 0


def page_images(doc, pages, dpi=140, quality=52):
    """회색조 WebP. 컬러 JPEG 는 같은 쪽에서 몇 배가 된다(저장소 실측).

    눕혀 인쇄된 쪽은 시계방향(-90)으로 돌려 담는다 — 그래야 표가 한 줄씩 가로로
    읽혀 왼쪽 목록과 눈높이가 맞는다. 화면의 '세로로' 단추가 원래대로 되돌린다.
    """
    import fitz
    from PIL import Image
    out = {}
    for p in sorted(pages):
        page = doc[p - 1]
        pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
        im = Image.open(io.BytesIO(pix.tobytes("png")))
        rot = sideways(page)
        if rot:
            im = im.rotate(-90, expand=True)
        buf = io.BytesIO()
        im.save(buf, "WEBP", quality=quality, method=4)
        out[p] = {"b": base64.b64encode(buf.getvalue()).decode("ascii"), "rot": rot}
    return out


def write(payload, out_path):
    """payload 를 틀에 넣어 파일로 굽는다. 크기(MB)를 돌려준다."""
    blob = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    # 데이터 안에 스크립트 닫는 표가 있으면 스크립트가 일찍 닫힌다. base64 라 없을 것이나 세운다.
    assert "</scr" + "ipt>" not in blob
    html = TEMPLATE.replace("__PAYLOAD__", blob)
    d = os.path.dirname(out_path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    io.open(out_path, "w", encoding="utf-8", newline="\n").write(html)
    return os.path.getsize(out_path) / 1048576.0


TEMPLATE = r"""
<meta charset="utf-8">
<title>오브젝트 대조대</title>
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
.top{display:flex;align-items:center;gap:9px;flex-wrap:wrap;
 padding:8px 13px;border-bottom:1px solid var(--line);background:var(--panel)}
.brand{font-size:14px;font-weight:650;letter-spacing:-.01em;white-space:nowrap}
.docmeta{font-size:11px;color:var(--faint);font-family:var(--mono);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:40ch}
/* 범위 배지 — 이 화면이 카탈로그 전체가 아님을 제목 옆에서 못 박는다 */
.scope{padding:2px 9px;border-radius:999px;font-size:11px;font-weight:650;
 background:var(--accent-soft);color:var(--accent);white-space:nowrap}
.top .sp{flex:1}
.seg{display:inline-flex;border:1px solid var(--line);border-radius:7px;overflow:hidden}
.seg button{padding:4px 10px;border:0;border-right:1px solid var(--line);background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer}
.seg button:last-child{border-right:0}
.seg button:hover{background:var(--accent-soft);color:var(--ink)}
.seg button[aria-pressed=true]{background:var(--accent);color:#fff;font-weight:600}
/* a 로도 쓴다(원문 PDF 열기) — 밑줄과 링크 색을 지워 단추와 같은 모양으로 세운다 */
.zbtn{padding:4px 9px;border:1px solid var(--line);border-radius:6px;background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer;white-space:nowrap;
 text-decoration:none;display:inline-block;line-height:1.35;font-family:inherit}
.zbtn:hover{background:var(--accent-soft);color:var(--ink)}
/* 배율 무리 — 클로드 웹의 확대 조작과 같은 자리(− 배율 +), 배율을 누르면 맞춤 */
.zoomer{display:inline-flex;align-items:center;border:1px solid var(--line);
 border-radius:7px;overflow:hidden;background:var(--bg)}
.zoomer button{border:0;background:transparent;color:var(--dim);cursor:pointer;
 padding:4px 9px;font-size:13px;line-height:1}
.zoomer button:hover{background:var(--accent-soft);color:var(--ink)}
.zoomer .pct{min-width:5.4ch;text-align:center;font-family:var(--mono);font-size:11.5px;
 font-variant-numeric:tabular-nums;border-left:1px solid var(--line);
 border-right:1px solid var(--line);color:var(--ink)}
.pgno{font-family:var(--mono);font-weight:700;color:var(--ink);white-space:nowrap}

/* ── 3단 작업대. 팝업을 쓰지 않는다 — 대조는 둘을 동시에 봐야 되는 일이다 ── */
.app{display:grid;grid-template-columns:var(--tw,224px) var(--lw,44%) 7px 1fr;
 height:calc(100dvh - 41px)}
.app.no-tree{grid-template-columns:0 var(--lw,44%) 7px 1fr}
.app.no-list{grid-template-columns:var(--tw,224px) 0 0 1fr}
.app.min-page{grid-template-columns:var(--tw,224px) 1fr 0 30px}
.app.no-tree.no-list{grid-template-columns:0 0 0 1fr}
.app.no-tree.min-page{grid-template-columns:0 1fr 0 30px}
.app.no-tree .tree,.app.no-list .left,
.app.no-list .grip,.app.min-page .grip{display:none}
.app.min-page .view{display:none}
.app.min-page .right{background:var(--panel);border-left:1px solid var(--line)}
.pane{min-width:0;display:flex;flex-direction:column;overflow:hidden}
.tree{border-right:1px solid var(--line);background:var(--panel);overflow:auto;padding:8px 0 20px}
.left{border-right:1px solid var(--line);background:var(--panel)}
.right{background:var(--rail)}
.grip{cursor:col-resize;background:var(--line)}
.grip:hover,.grip.on{background:var(--accent)}

/* ── 트리 ── */
.tree ul{list-style:none;margin:0;padding:0}
.tree li{margin:0}
.tnode{display:flex;align-items:center;gap:5px;width:100%;border:0;background:none;
 color:var(--ink);text-align:left;cursor:pointer;padding:4px 10px 4px 0;font-size:12px;
 border-radius:0}
.tnode:hover{background:var(--accent-soft)}
.tnode[aria-current=true]{background:var(--accent-soft);box-shadow:inset 3px 0 0 var(--accent);
 font-weight:650}
.tnode .tw{width:14px;flex:none;color:var(--faint);font-size:9px;text-align:center}
/* 잘라내지 않는다 — 잘리면 정작 다른 부분(실내기·ODU)이 사라진다. 접어 내린다 */
.tnode .tl{flex:1;min-width:0;white-space:normal;overflow-wrap:anywhere;line-height:1.35}
.tnode .tc{font-family:var(--mono);font-size:10.5px;color:var(--faint);
 font-variant-numeric:tabular-nums}
.tnode.d0{font-weight:650;letter-spacing:-.01em}
.tnode.d0 .tl{padding-left:2px}
.tnode.d1 .tl{padding-left:14px}
.tnode.d2 .tl{padding-left:28px}
.tnode.d3 .tl{padding-left:42px;color:var(--dim)}
li.closed>ul{display:none}

/* ── 왼쪽 머리 ── */
.head{padding:9px 13px;border-bottom:1px solid var(--line);background:var(--panel)}
.tools{display:flex;gap:6px;align-items:center;flex-wrap:wrap}
input[type=search],input.addr{padding:5px 9px;border:1px solid var(--line);
 border-radius:6px;background:var(--bg);color:var(--ink);font:inherit;font-size:12px}
input[type=search]{flex:1;min-width:110px}
input.addr{width:74px;font-family:var(--mono);text-align:right}
.chip{padding:3px 9px;border:1px solid var(--line);border-radius:999px;background:var(--bg);
 color:var(--dim);font-size:11.5px;cursor:pointer;white-space:nowrap}
.chip:hover{border-color:var(--accent);color:var(--ink)}
.addrbox{display:flex;align-items:center;gap:6px;margin-top:8px;padding:7px 9px;
 border:1px solid var(--line);border-radius:7px;background:var(--bg);font-size:11.5px}
.addrbox.off{display:none}
.addrbox label{color:var(--dim);white-space:nowrap}
.addrbox .why{color:var(--faint);font-size:11px;line-height:1.4}
.prog{display:flex;align-items:center;gap:8px;margin-top:8px;font-size:11.5px;color:var(--dim)}
.bar{flex:1;height:5px;border-radius:3px;background:var(--rail);overflow:hidden}
.bar i{display:block;height:100%;background:var(--ok);width:0}
.cnt{font-family:var(--mono);font-variant-numeric:tabular-nums}

/* ── 표 ── */
.scroll{flex:1;overflow:auto}
.gh{position:sticky;top:0;z-index:2;background:var(--panel);border-bottom:1px solid var(--line);
 padding:7px 13px 6px;font-size:11px;font-weight:700;letter-spacing:.05em;
 color:var(--faint);display:flex;gap:8px;align-items:baseline}
.gh b{color:var(--accent);font-weight:700}
.gh .pg{margin-left:auto;font-family:var(--mono);letter-spacing:0;white-space:nowrap}
table{border-collapse:collapse;width:100%;font-size:12px}
td,th{padding:5px 8px;border-bottom:1px solid var(--line);vertical-align:top}
/* 열 머리글 — 구역 머리글 바로 밑에 붙어 같이 따라온다 */
thead th{position:sticky;top:29px;z-index:1;background:var(--panel);text-align:left;
 font-size:10.5px;font-weight:700;letter-spacing:.03em;color:var(--faint);
 border-bottom:1px solid var(--line);white-space:nowrap}
thead th.ck{width:22px;padding-left:13px}
.c-n{width:56px;font-family:var(--mono);font-variant-numeric:tabular-nums;
 color:var(--faint);text-align:right;white-space:nowrap}
.c-t{width:42px}
.c-t span{display:inline-block;padding:1px 5px;border-radius:4px;font-family:var(--mono);
 font-size:10.5px;font-weight:700;background:var(--rail);color:var(--dim)}
.c-t span.o{background:var(--accent-soft);color:var(--accent)}
.c-nm{font-family:var(--mono);font-size:11.5px;word-break:break-all;min-width:14ch}
.c-nm em{font-style:normal;color:var(--accent);font-weight:700}
.c-u,.c-rw{width:62px;font-family:var(--mono);font-size:11px;color:var(--dim);white-space:nowrap}
.c-rw{width:44px}
.c-s{font-size:11px;color:var(--dim);font-family:var(--mono);min-width:12ch}
.c-d{color:var(--dim)}
.c-pg{width:38px;font-family:var(--mono);font-size:11px;color:var(--faint);text-align:right}
.c-inst{width:110px;font-family:var(--mono);font-size:11px;color:var(--dim);
 font-variant-numeric:tabular-nums;white-space:nowrap}
.c-inst b{color:var(--ink);font-weight:600}
/* 원문 칸(스키마 필드로 못 올린 것)은 열 이름을 그대로 쓰고 바탕을 옅게 깐다 */
.c-x{font-size:11px;color:var(--dim);background:color-mix(in srgb,var(--rail) 55%,transparent)}
thead th.c-x{background:var(--panel);color:var(--accent)}
tr.row{cursor:pointer}
tr.row:hover{background:var(--accent-soft)}
tr.row.sel{background:var(--accent-soft);box-shadow:inset 3px 0 0 var(--accent)}
tr.row.done td.c-nm{color:var(--faint)}
td.ck{width:22px;padding-left:13px;color:var(--faint);text-align:center;user-select:none}

tr.row.done td.ck{color:var(--ok)}







.none{padding:26px 13px;color:var(--faint);text-align:center}

/* ── 원문 쪽: 늘 보인다 ── */
/* 접었다 펴는 단추 — 원문창 안(접기)과 접힌 띠(펴기) 양쪽에 둔다 */
/* 접기 단추는 최상단 띠에 있다(#foldb). 원문창 안에 두었더니 setPointerCapture 가
   클릭을 가로채 눌러도 아무 일이 없었다 — 위치를 옮기고 잡아채기도 막았다. */
.unfold{display:none;width:100%;height:100%;border:0;background:none;color:var(--dim);
 cursor:pointer;font-size:11.5px;writing-mode:vertical-rl;padding:10px 0;letter-spacing:.08em}
.unfold:hover{background:var(--accent-soft);color:var(--ink)}
.app.min-page .unfold{display:block}
.view{flex:1;position:relative;overflow:hidden;background:var(--rail);cursor:grab;touch-action:none}
.view.drag{cursor:grabbing}
.view img{position:absolute;top:0;left:0;transform-origin:0 0;background:#fff;box-shadow:var(--shadow)}
.hint{position:absolute;left:0;right:0;bottom:0;padding:6px 12px;background:var(--panel);
 border-top:1px solid var(--line);font-size:11px;color:var(--faint)}
kbd{font-family:var(--mono);font-size:10.5px;border:1px solid var(--line);border-bottom-width:2px;
 border-radius:4px;padding:0 4px;color:var(--dim);background:var(--bg)}
@media (max-width:900px){
  body{overflow:auto}
  .app,.app.no-tree,.app.no-list,.app.min-page{grid-template-columns:1fr;height:auto}
  .app.min-page .view{display:block;height:0}   /* 좁은 화면에서도 접기가 먹는다 */
  .app.min-page .unfold{width:100%;height:auto;writing-mode:horizontal-tb;padding:6px 0}
  .grip{display:none}
  .tree{max-height:34vh;border-right:0;border-bottom:1px solid var(--line)}
  .left{border-right:0;border-bottom:1px solid var(--line)}
  .view{height:70vh}
  .docmeta{display:none}
}
</style>

<div class="top">
  <span class="brand" id="brand"></span>
  <span class="scope" id="scope" hidden></span>
  <span class="docmeta" id="meta"></span>
  <span class="seg" id="vseg">
    <button type="button" data-v="tree" aria-pressed="true">트리</button>
    <button type="button" data-v="list" aria-pressed="true">표</button>
    <button type="button" data-v="page" aria-pressed="true">원문</button>
  </span>
  <span class="sp"></span>
  <span>원문 <span class="pgno" id="rpg">—</span></span>
  <a class="zbtn" id="openpdf" target="_blank" rel="noopener"
     title="원문 PDF 를 새 탭에서 연다 (그 쪽으로 바로 간다)">원문 쪽 없음</a>
  <button class="zbtn" type="button" data-v="page" id="foldb"
          title="원문창 접기">─ 원문 접기</button>
  <button class="zbtn" type="button" id="csv" title="지금 보이는 행만 CSV 로">CSV</button>
  <button class="zbtn" type="button" data-z="rot" id="rotb">세로로</button>
  <button class="zbtn" type="button" data-z="fitw">폭맞춤</button>
  <span class="zoomer">
    <button type="button" data-z="-" aria-label="축소">−</button>
    <button type="button" class="pct" data-z="fit" id="pct" title="눌러서 쪽 맞춤">100%</button>
    <button type="button" data-z="+" aria-label="확대">+</button>
  </span>
</div>

<div class="app" id="app">
  <nav class="tree" id="tree" aria-label="설비 트리"></nav>

  <section class="pane left">
    <div class="head">
      <div class="tools">
        <input type="search" id="q" placeholder="이름·설명 찾기" aria-label="포인트 찾기">
        <button class="chip" id="reset" type="button">확인표시 초기화</button>
      </div>
      <div class="addrbox off" id="addrbox">
        <label for="addr" id="addrlab">유닛 주소</label>
        <input class="addr" id="addr" type="number" min="0" max="255" placeholder="—"
               aria-label="유닛 주소">
        <span class="why" id="why"></span>
      </div>
      <div class="prog">
        <span>확인</span>
        <span class="bar"><i id="pbar"></i></span>
        <span class="cnt" id="pcnt"></span>
      </div>
    </div>
    <div class="scroll" id="list"></div>
  </section>

  <div class="grip" id="grip" role="separator" aria-orientation="vertical" tabindex="0"
       aria-label="좌우 폭 조절"></div>

  <section class="pane right">
    <button class="unfold" type="button" data-v="page" title="원문 펼치기">원문 펼치기 ▸</button>
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

document.title = D.title;
document.getElementById("brand").textContent = D.title;
document.getElementById("meta").textContent = D.subtitle || "";
if (D.scope) {
  var sc = document.getElementById("scope");
  sc.textContent = D.scope; sc.hidden = false;
}
document.getElementById("hint").innerHTML = D.hint ||
  ('<kbd>↑</kbd><kbd>↓</kbd> 행 이동 · <kbd>Space</kbd> 확인 · 끌어서 이동 · 휠/'
   + '<kbd>+</kbd><kbd>−</kbd> 확대 · <kbd>0</kbd> 맞춤 · 더블클릭 확대');

/* 확인 표시는 브라우저에만 남는다. 저장이 막힌 환경에서도 화면은 돌아야 한다. */
var KEY = D.storeKey || "verify/v1", done = {};
try { done = JSON.parse(localStorage.getItem(KEY) || "{}") || {}; } catch (e) { done = {}; }
function save(){ try { localStorage.setItem(KEY, JSON.stringify(done)); } catch (e) {} }

var node = null, query = "", sel = null, addr = null;

/* ── 트리 ── */
var openSet = {};
function treeHTML(nodes, depth){
  return '<ul>' + nodes.map(function(n){
    var kids = n.children || [];
    var open = openSet[n.id] !== false;
    return '<li class="' + (kids.length && !open ? "closed" : "") + '" data-id="' + esc(n.id) + '">'
      + '<button class="tnode d' + depth + '" type="button" data-id="' + esc(n.id) + '"'
      + ' title="' + esc(n.full || n.label) + '"'
      + ' aria-current="false"><span class="tw">' + (kids.length ? (open ? "▾" : "▸") : "") + '</span>'
      + '<span class="tl">' + esc(n.label) + '</span>'
      + '<span class="tc">' + n.count + '</span></button>'
      + (kids.length ? treeHTML(kids, depth + 1) : "") + '</li>';
  }).join("") + '</ul>';
}
function drawTree(){
  document.getElementById("tree").innerHTML =
    '<ul><li><button class="tnode d0" type="button" data-id="" aria-current="'
    + (node === null) + '"><span class="tw"></span><span class="tl">전체</span>'
    + '<span class="tc">' + D.total + '</span></button></li></ul>'
    + treeHTML(D.tree, 0);
  var cur = document.querySelector('.tnode[data-id="' + (node || "") + '"]');
  if (cur) cur.setAttribute("aria-current", "true");
}
/* 노드 id → 그 아래 모든 노드 id (구역 고르기에 쓴다) */
var under = {};
(function walk(nodes, chain){
  nodes.forEach(function(n){
    var c = chain.concat([n.id]);
    c.forEach(function(a){ (under[a] = under[a] || {})[n.id] = 1; });
    if (n.children) walk(n.children, c);
  });
})(D.tree, []);

function inNode(s){
  if (!node) return true;
  return s.node === node || (under[node] && under[node][s.node]);
}

/* ── 인스턴스 번호(주소가 있어야 정해지는 판만) ──
   규칙은 원문이 준다 — payload 의 addr.rule 에 그대로 실려 온다. */
function instanceOf(a, ptype, point){
  if (a == null || ptype == null) return null;
  return ptype * 0x10000 + Math.floor(a / 16) * 0x1000 + (a % 16) * 0x100 + point;
}
function curAddr(){
  var s = shownSections();
  for (var i = 0; i < s.length; i++) { if (s[i].addr) return s[i].addr; }
  return null;
}
function why(){
  var box = document.getElementById("addrbox"), a = curAddr();
  box.classList.toggle("off", !a);
  if (!a) return;
  document.getElementById("addrlab").textContent = a.label;
  document.getElementById("why").innerHTML =
    addr == null ? a.help : ('Device <b>' + Math.floor(addr / 16) + '</b> · Product <b>'
      + (addr % 16) + '</b> — ' + esc(a.rule));
}

function match(p){
  if (!query) return true;
  var q = query.toLowerCase();
  return ((p.nm || "") + " " + (p.d || "") + " " + (p.t || "") + " " + (p.s || "")
          + " " + (p.n || "")).toLowerCase().indexOf(q) >= 0;
}
function shownSections(){ return D.sections.filter(inNode); }
function counts(){
  var n = 0, k;
  for (k in done) { if (done[k]) n++; }
  document.getElementById("pcnt").textContent = n + " / " + D.total;
  document.getElementById("pbar").style.width = (100 * n / D.total).toFixed(1) + "%";
}

/* 한 칸의 값을 꺼낸다. 원문 칸은 'x:<원문 열 이름>' 으로 온다 —
   벤더마다 열 이름이 달라 이름을 코드에 박지 않는다. */
function cell(t, p, c){
  if (c.k === "inst") {
    var v = t.addr ? instanceOf(addr, t.addr.ptype, p.i != null ? p.i : +p.n) : null;
    return v == null ? "" : '<b>0x' + v.toString(16).toUpperCase() + '</b><br>' + v;
  }
  if (c.k === "nm") {
    var nm = esc(p.nm);
    return addr == null ? nm : nm.replace(/_XXX/g, "_<em>" + addr + "</em>");
  }
  if (c.k === "t") {
    var isOut = p.rw ? p.rw.indexOf("W") >= 0 : /O$/.test(p.t || "");
    return '<span class="' + (isOut ? "o" : "") + '">' + esc(p.t || "—") + '</span>';
  }
  if (c.k.slice(0, 2) === "x:") return esc((p.x || {})[c.k.slice(2)] || "");
  return esc(p[c.k] == null ? "" : p[c.k]);
}

function render(){
  var out = [], shown = 0;
  shownSections().forEach(function(t){
    var pts = t.points.filter(match);
    if (!pts.length) return;
    /* 열은 구역마다 다르다 — 원문 표가 주는 칸이 다르기 때문이다.
       머리글을 세워야 어느 값이 어느 칸인지 눈으로 맞출 수 있다. */
    var cols = (t.cols || []).filter(function(c){
      return c.k !== "inst" || t.addr;
    });
    out.push('<div class="gh"><b>' + esc(t.path.join(" › ")) + '</b><span>'
           + pts.length + '점</span><span class="pg">원문 ' + esc(t.span)
           + '쪽</span></div><table><thead><tr><th class="ck"></th>'
           + cols.map(function(c){
               return '<th class="c-' + esc(c.k.replace(/[^a-zA-Z]/g, "")) + '">'
                    + esc(c.h) + '</th>';
             }).join("") + '</tr></thead><tbody>');
    pts.forEach(function(p){
      var k = t.id + ":" + (p.n || p.nm);
      shown++;
      out.push('<tr class="row' + (done[k] ? " done" : "") + (sel === k ? " sel" : "")
        + '" data-k="' + esc(k) + '" data-page="' + esc(p.pk)
        + '" data-printed="' + esc(p.pg) + '" data-pdf="' + esc(p.pdf) + '" tabindex="0">'
        + '<td class="ck">' + (done[k] ? "✓" : "○") + '</td>'
        + cols.map(function(c){
            return '<td class="c-' + esc(c.k.replace(/[^a-zA-Z]/g, "")) + '">'
                 + cell(t, p, c) + '</td>';
          }).join("") + '</tr>');
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
var mode = "fit", upright = true;   /* upright = 담긴 방향 그대로(표가 가로로 읽힌다) */

function boxW(){ return upright ? natural : naturalH; }
function boxH(){ return upright ? naturalH : natural; }
function showPct(){ document.getElementById("pct").textContent = Math.round(zoom * 100) + "%"; }
function fit(kind){
  if (!natural) return;
  var w = view.clientWidth - 24, h = view.clientHeight - 40;
  zoom = kind === "fitw" ? w / boxW() : Math.min(w / boxW(), h / boxH());
  if (!isFinite(zoom) || zoom <= 0) zoom = 1;
  ox = 12; oy = 12; mode = kind; apply();
}
function apply(){
  img.style.width = (natural * zoom) + "px";
  /* 세로 보기로 돌릴 때는 원래 방향(반시계 90도)으로 되돌린다 */
  var r = upright ? "" : " rotate(-90deg) translate(" + (-natural * zoom) + "px,0)";
  img.style.transform = "translate(" + ox + "px," + oy + "px)" + r;
  showPct();
}
function zoomAt(z2, mx, my){
  z2 = Math.max(0.05, Math.min(8, z2));
  ox = mx - (mx - ox) * (z2 / zoom); oy = my - (my - oy) * (z2 / zoom);
  zoom = z2; mode = "free"; apply();
}
function zoomCenter(f){
  zoomAt(zoom * f, view.clientWidth / 2, view.clientHeight / 2);
}
function show(key, printed, pdf){
  if (key === curPage) return;
  curPage = key;
  document.getElementById("rpg").innerHTML = printed
    + '쪽 <span style="color:var(--faint);font-weight:400">(PDF ' + pdf + ')</span>';
  /* 원문 PDF 를 통째로 여는 길. 쪽 그림은 한 장씩만 담기지만(용량) 앞뒤를 봐야
     할 때가 있다. key 는 '모델|파일#PDF쪽' 이라 파일 이름이 그 안에 있다.
     이 화면은 review/ 에 굽고 원문은 pipeline/data/raw/ 에 있다(저장소에 안 담긴다). */
  var link = document.getElementById("openpdf");
  var file = String(key || "").split("|").slice(1).join("|").split("#")[0];
  /* ⚠ 원문이 없을 때 단추를 **숨기지 않는다.** 숨겼더니 정격의 항목·통신 구역에서
     단추가 사라져 "링크가 안 된다" 로 읽혔다. 왜 없는지를 그 자리에 적어 둔다. */
  link.hidden = false;
  if (file) {
    link.href = "../pipeline/data/raw/" + encodeURIComponent(file)
              + (pdf && pdf !== "?" ? "#page=" + pdf : "");
    link.textContent = "PDF 전체" + (pdf && pdf !== "?" ? " (" + pdf + "쪽)" : "");
    link.title = file + " 를 새 탭에서 연다";
    link.removeAttribute("aria-disabled");
    link.style.opacity = "";
  } else {
    link.removeAttribute("href");
    link.textContent = "원문 쪽 없음";
    link.title = "이 줄은 원문 쪽을 안 갖고 있다 — 출처 칸에 문서 이름만 있거나"
               + "(예: 'Fact Sheet') 손으로 넣은 값이다";
    link.setAttribute("aria-disabled", "true");
    link.style.opacity = ".45";
  }
  var rec = D.pages[key];
  if (!rec) { img.removeAttribute("src"); return; }
  /* 눕혀 인쇄된 쪽만 돌려 담았다 — 담긴 그대로가 읽기 좋은 방향이다 */
  img.onload = function(){
    natural = img.naturalWidth; naturalH = img.naturalHeight;
    if (mode === "free") apply(); else fit(mode);
  };
  img.src = "data:image/webp;base64," + rec.b;
  document.getElementById("rotb").hidden = !rec.rot;
}

view.addEventListener("wheel", function(e){
  if (!natural) return;
  e.preventDefault();
  var r = view.getBoundingClientRect();
  zoomAt(zoom * (e.deltaY < 0 ? 1.12 : 1 / 1.12), e.clientX - r.left, e.clientY - r.top);
}, { passive: false });
view.addEventListener("dblclick", function(e){
  if (!natural) return;
  var r = view.getBoundingClientRect();
  zoomAt(zoom * (e.shiftKey ? 1 / 1.6 : 1.6), e.clientX - r.left, e.clientY - r.top);
});

var drag = null;
view.addEventListener("pointerdown", function(e){
  /* ⚠ 단추 위에서 시작한 누름은 잡지 않는다. setPointerCapture 가 뒤이은 click 의
     target 을 #view 로 돌려놓기 때문에, 원문창 안에 있던 '접기' 단추가 눌러도
     아무 일이 없었다(사용자가 '작동은 안 한다' 고 짚은 것이 이것이다). */
  if (e.target.closest && e.target.closest("button, a")) return;
  drag = { x: e.clientX - ox, y: e.clientY - oy };
  view.classList.add("drag"); view.setPointerCapture(e.pointerId);
});
view.addEventListener("pointermove", function(e){
  if (!drag) return;
  ox = e.clientX - drag.x; oy = e.clientY - drag.y; mode = "free"; apply();
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
    fit(mode === "free" ? "fit" : mode); return;
  }
  if (!natural) return;
  if (z === "fit" || z === "fitw") { fit(z); return; }
  zoomCenter(z === "+" ? 1.25 : 1 / 1.25);
});
addEventListener("resize", function(){ if (mode !== "free") fit(mode); });

/* ── 뷰 전환. 맨 위에 있어 어느 모드에서도 사라지지 않는다 ── */
var appEl = document.getElementById("app"), vseg = document.getElementById("vseg");
/* 원문창은 감추지 않고 **접는다**(min-page) — 되펴는 단추가 늘 띠에 남아 있어야
   "어디로 사라졌지" 가 안 생긴다. 트리·표는 그냥 감춘다(no-tree·no-list). */
function cls(v){ return v === "page" ? "min-page" : "no-" + v; }
function toggleView(v, force){
  var b = vseg.querySelector('button[data-v="' + v + '"]');
  var on = force == null ? b.getAttribute("aria-pressed") !== "true" : force;
  /* 셋 다 끄면 볼 것이 없어진다 — 마지막 하나는 못 끈다 */
  if (!on && vseg.querySelectorAll('button[aria-pressed=true]').length < 2) return;
  b.setAttribute("aria-pressed", String(on));
  appEl.classList.toggle(cls(v), !on);
  if (v === "page") {
    var fb = document.getElementById("foldb");
    if (fb) { fb.textContent = on ? "─ 원문 접기" : "▸ 원문 펼치기"; }
  }
  if (mode !== "free") setTimeout(function(){ fit(mode); }, 0);
}
/* 접기·펴기 단추가 뷰 전환 밖(원문창 안·접힌 띠)에도 있어 문서 전체에서 받는다 */
document.addEventListener("click", function(e){
  var b = e.target.closest("button[data-v]");
  if (b) toggleView(b.dataset.v);
});

/* ── 고르기 ── */
function pick(tr, scroll){
  if (!tr) return;
  var prev = document.querySelector("tr.sel");
  if (prev) prev.classList.remove("sel");
  tr.classList.add("sel"); sel = tr.dataset.k;
  show(tr.dataset.page, tr.dataset.printed, tr.dataset.pdf);
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
  if (e.key === "+" || e.key === "=") { e.preventDefault(); zoomCenter(1.25); return; }
  if (e.key === "-" || e.key === "_") { e.preventDefault(); zoomCenter(1 / 1.25); return; }
  if (e.key === "0") { e.preventDefault(); fit("fit"); return; }
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
document.getElementById("tree").addEventListener("click", function(e){
  var b = e.target.closest(".tnode");
  if (!b) return;
  var id = b.dataset.id || null;
  if (id && id === node) { openSet[id] = openSet[id] === false; drawTree(); return; }
  node = id; drawTree(); why(); render(); first();
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
  /* 트리를 접으면 --tw 값은 그대로라 셈이 어긋난다 — 실제로 그려진 폭을 잰다 */
  var tw = document.getElementById("tree").getBoundingClientRect().width;
  var pct = Math.max(18, Math.min(78, 100 * (e.clientX - tw) / (innerWidth - tw)));
  appEl.style.setProperty("--lw", pct + "%");
  if (mode !== "free") fit(mode);
});
addEventListener("pointerup", function(){ gd = false; grip.classList.remove("on"); });
grip.addEventListener("keydown", function(e){
  var cur = parseFloat(getComputedStyle(appEl).getPropertyValue("--lw")) || 44;
  if (e.key === "ArrowLeft") appEl.style.setProperty("--lw", Math.max(18, cur - 3) + "%");
  if (e.key === "ArrowRight") appEl.style.setProperty("--lw", Math.min(78, cur + 3) + "%");
  if (mode !== "free") fit(mode);
});

/* ── CSV 내보내기 ──
   지금 트리·찾기로 걸러 놓은 것 그대로 내보낸다 — 화면에 보이는 것과 파일이 같아야
   대조한 보람이 있다. 전 모델·전 열이 필요하면 pipeline/export_points.py 가 정본이다
   (프로토콜 주소를 접두 열로 펴고 판별 파일까지 낸다).
   ⚠ BOM 을 붙인다 — 없으면 Windows Excel 이 한글을 깨뜨린다. */
document.getElementById("csv").addEventListener("click", function(){
  /* 화면의 열을 그대로 쓴다 — 보이는 표와 파일이 달라지면 대조한 보람이 없다.
     전 모델·전 열(프로토콜 주소 접두 열까지)이 필요하면
     pipeline/export_points.py 가 정본이다. */
  var q = String.fromCharCode(34), lines = [], head = null;
  shownSections().forEach(function(t){
    var pts = t.points.filter(match);
    if (!pts.length) return;
    var cols = (t.cols || []).filter(function(c){ return c.k !== "inst" || t.addr; });
    var h = ["설비", "모델", "판", "구역"].concat(cols.map(function(c){ return c.h; }));
    if (!head || head.join("|") !== h.join("|")) { head = h; lines.push(h); }
    pts.forEach(function(p){
      lines.push([D.title, t.path[0] || "", t.path[1] || "", t.path[2] || ""]
        .concat(cols.map(function(c){
          if (c.k.slice(0, 2) === "x:") return (p.x || {})[c.k.slice(2)] || "";
          if (c.k === "inst") {
            var v = t.addr ? instanceOf(addr, t.addr.ptype, p.i != null ? p.i : +p.n) : null;
            return v == null ? "" : v;
          }
          return p[c.k] == null ? "" : p[c.k];
        })));
    });
  });
  var CRLF = String.fromCharCode(13, 10), BOM = String.fromCharCode(0xFEFF);
  var body = lines.map(function(r){
    return r.map(function(v){
      v = String(v == null ? "" : v);
      return q + v.split(q).join(q + q) + q;
    }).join(",");
  }).join(CRLF);
  /* BOM 을 붙인다 — 없으면 Windows Excel 이 한글을 깨뜨린다 */
  var blob = new Blob([BOM + body], { type: "text/csv;charset=utf-8" });
  var a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = (D.storeKey || "points").split("/")[0] + ".csv";
  document.body.appendChild(a); a.click();
  setTimeout(function(){ URL.revokeObjectURL(a.href); a.remove(); }, 0);
});

function first(){ pick(document.querySelector("tr.row"), true); }
drawTree(); why(); render(); first();
})();
</script>
"""
