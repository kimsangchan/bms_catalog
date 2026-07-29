# -*- coding: utf-8 -*-
"""카탈로그 브라우저 재설계 — 관제/대시보드 프로파일 (밀도 8 · 모션 2 · 편차 3)
데이터는 JSON으로 심고 화면은 JS가 그린다(탭·필터로 한 패널 한 목적)."""
import json, os, importlib.util as il

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = r"D:\_solutions\Neuros\solution-planning\service-autopilot\review\equip-catalog.html"

equips = json.load(open(os.path.join(HERE, "equips.json"), encoding="utf-8"))
_s = il.spec_from_file_location("models", os.path.join(HERE, "models.py"))
_m = il.module_from_spec(_s); _s.loader.exec_module(_m)

DOM_ORDER = ["공기측 설비", "열원·수측 설비", "반송·구동", "계측·제어", "전력 설비",
             "조명·차양", "방재", "승강", "보안·출입", "환경·공기질", "급배수·위생"]

def clean(t):
    return {"header": t["header"], "rows": t["rows"]}

DATA = {
    "equips": [{
        "id": "e%d" % e["no"], "no": e["no"], "title": e["title"], "domain": e["domain"],
        "head": e["head"], "notes": e["notes"],
        "spec": [clean(t) for t in e["spec"]],
        "points": [clean(t) for t in e["points"]],
        "np": e["np"], "ns": e["ns"],
    } for e in equips],
    "models": {("e%d" % k): v for k, v in _m.MODELS.items()},
    "l3": {("e%d" % k): v for k, v in _m.L3_STATUS.items()},
    "domOrder": DOM_ORDER,
}
TOTP = sum(e["np"] for e in equips)
TOTS = sum(e["ns"] for e in equips)
NMODEL = sum(len(v) for v in _m.MODELS.values())
NMPTS = sum(len([p for p in md["points"] if p.get("inst")]) for v in _m.MODELS.values() for md in v)

HTML = r"""<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>BMS 장비 카탈로그</title>
<style>
:root{
  --bg:#fafaf9; --panel:#fff; --ink:#18181b; --dim:#71717a; --faint:#a1a1aa;
  --line:#e4e4e7; --line2:#f4f4f5; --accent:#15803d; --accent-bg:#f0fdf4;
  --warn:#b45309; --warn-bg:#fffbeb; --sel:#f4f4f5;
  --mono:ui-monospace,"SF Mono",SFMono-Regular,"Cascadia Mono",Consolas,monospace;
}
@media (prefers-color-scheme:dark){:root{
  --bg:#18181b; --panel:#1f1f23; --ink:#f4f4f5; --dim:#a1a1aa; --faint:#71717a;
  --line:#3f3f46; --line2:#27272a; --accent:#4ade80; --accent-bg:#14251a;
  --warn:#fbbf24; --warn-bg:#2a2113; --sel:#27272a;}}
*{box-sizing:border-box;margin:0;padding:0}
body{min-height:100dvh;background:var(--bg);color:var(--ink);
 font:13px/1.55 -apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif;
 -webkit-font-smoothing:antialiased}
.num,code,td.n{font-family:var(--mono);font-variant-numeric:tabular-nums}
code{font-size:11.5px;background:var(--line2);padding:1px 4px;border-radius:3px;color:var(--dim)}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
button{font:inherit;color:inherit;background:none;border:0;cursor:pointer}

/* 헤더 */
.top{display:grid;grid-template-columns:auto 1fr auto;gap:16px;align-items:center;
 padding:10px 16px;border-bottom:1px solid var(--line);background:var(--panel);
 position:sticky;top:0;z-index:10}
.brand{font-size:13.5px;font-weight:650;letter-spacing:-.01em}
.brand span{color:var(--faint);font-weight:400;margin-left:8px;font-size:11.5px}
#q{width:100%;max-width:340px;padding:6px 10px;border:1px solid var(--line);border-radius:6px;
 background:var(--bg);color:var(--ink);font-size:12.5px;outline:none}
#q:focus{border-color:var(--accent)}
.tot{display:flex;gap:14px;font-size:11.5px;color:var(--dim);white-space:nowrap}
.tot b{color:var(--ink);font-family:var(--mono)}

/* 3분할 */
.app{display:grid;grid-template-columns:212px minmax(0,1fr);min-height:calc(100dvh - 45px)}
aside{border-right:1px solid var(--line);overflow-y:auto;max-height:calc(100dvh - 45px);
 position:sticky;top:45px;padding-bottom:24px}
.gh{padding:12px 12px 4px;font-size:10.5px;font-weight:700;letter-spacing:.07em;color:var(--faint)}
aside button{display:grid;grid-template-columns:1fr auto;gap:6px;width:100%;text-align:left;
 padding:5px 12px;font-size:12.5px;align-items:center;border-left:2px solid transparent}
aside button:hover{background:var(--sel)}
aside button[aria-current="true"]{background:var(--sel);border-left-color:var(--accent);font-weight:600}
aside button i{font-style:normal;font-family:var(--mono);font-size:11px;color:var(--faint)}

main{min-width:0;display:flex;flex-direction:column}
.hd{padding:14px 18px 0}
.hd .dom{font-size:10.5px;letter-spacing:.07em;color:var(--faint);font-weight:700}
.hd h1{font-size:19px;letter-spacing:-.02em;margin:3px 0 6px;font-weight:650}
.hd .tag{font-size:12px;color:var(--dim);line-height:1.85}
.hd .tag .ok{color:var(--accent)}
.hd .tag .no{color:var(--warn)}

/* 탭 */
.tabs{display:flex;gap:2px;padding:12px 18px 0;border-bottom:1px solid var(--line)}
.tabs button{padding:7px 12px;font-size:12.5px;color:var(--dim);border-bottom:2px solid transparent;
 margin-bottom:-1px}
.tabs button[aria-selected="true"]{color:var(--ink);font-weight:650;border-bottom-color:var(--accent)}
.tabs button i{font-style:normal;font-family:var(--mono);font-size:11px;color:var(--faint);margin-left:5px}

/* 필터 */
.bar{display:flex;gap:5px;flex-wrap:wrap;align-items:center;padding:9px 18px;
 border-bottom:1px solid var(--line2)}
.chip{padding:3px 9px;border:1px solid var(--line);border-radius:99px;font-size:11.5px;color:var(--dim)}
.chip[aria-pressed="true"]{background:var(--accent-bg);border-color:var(--accent);color:var(--accent);font-weight:600}
.bar .sp{margin-left:auto;font-size:11.5px;color:var(--faint);font-family:var(--mono)}

/* 표 — 카드 없이 선으로만 */
.wrap{padding:0 0 60px;min-width:0}
/* 표는 **자기 안에서만** 가로로 넘긴다. 바깥이 넘치면 화면 전체가 밀린다 */
.tw{overflow-x:auto;-webkit-overflow-scrolling:touch}
table{min-width:max-content}
table{width:100%;border-collapse:collapse;font-size:12.3px}
th{position:sticky;top:45px;background:var(--bg);text-align:left;padding:7px 10px;
 font-size:10.5px;font-weight:700;letter-spacing:.04em;color:var(--faint);
 border-bottom:1px solid var(--line);white-space:nowrap;z-index:2}
th:first-child,td:first-child{padding-left:18px}
th:last-child,td:last-child{padding-right:18px}
td{padding:6px 10px;border-bottom:1px solid var(--line2);vertical-align:top}
tbody tr:hover{background:var(--sel)}
td.n{color:var(--dim);white-space:nowrap;font-size:11.5px}
.ok{color:var(--accent);font-weight:600}
.no{color:var(--warn);font-weight:600}

/* 섹션 제목 */
.sec{padding:18px 18px 7px;font-size:11px;font-weight:700;letter-spacing:.06em;color:var(--faint)}
.sec b{color:var(--ink);font-family:var(--mono);font-weight:700}

/* 모델 */
.mlist{display:flex;gap:5px;flex-wrap:wrap;padding:9px 18px;border-bottom:1px solid var(--line2)}
.mlist button{padding:5px 11px;border:1px solid var(--line);border-radius:6px;font-size:12px}
.mlist button[aria-pressed="true"]{background:var(--sel);border-color:var(--accent);font-weight:650}
.mlist button{display:inline-flex;align-items:center;gap:6px}
.mpre{padding:9px 18px 0;font-size:11px;letter-spacing:.05em;color:var(--faint);font-weight:700}
.mpr{font-size:10px;letter-spacing:.04em;color:var(--faint);font-weight:700}
.slist{display:flex;gap:5px;flex-wrap:wrap;padding:0 18px 10px;max-height:132px;overflow:auto}
.slist button{display:inline-flex;align-items:center;gap:6px;padding:4px 9px;
 border:1px solid var(--line);border-radius:6px;font-size:11.5px}
.slist button[aria-pressed="true"]{background:var(--sel);border-color:var(--accent);font-weight:650}
th.srt{cursor:pointer;user-select:none}
th.srt:hover{color:var(--accent)}
.sa{font-style:normal;font-size:9px;color:var(--accent)}
.pg{display:flex;gap:6px;align-items:center;padding:6px 18px;font-size:11.5px}
.pgb{padding:3px 9px;border:1px solid var(--line);border-radius:5px;font-size:11px}
.pgb[disabled]{opacity:.35;cursor:default}
.pgn{font-family:var(--mono);color:var(--dim);margin-left:4px}
thead th{position:sticky;top:0;background:var(--bg);z-index:2}
.ms{font-size:10px;letter-spacing:.03em;padding:1px 5px;border-radius:3px;
 background:var(--sel);color:var(--accent);font-weight:700}
nav .sm{color:var(--accent)}
.vlist{display:flex;gap:5px;flex-wrap:wrap;padding:0 18px 10px}
.vlist button{padding:4px 10px;border:1px solid var(--line);border-radius:6px;
 font-family:var(--mono);font-size:11.5px}
.vlist button[aria-pressed="true"]{background:var(--sel);border-color:var(--accent);font-weight:650}
.qrow{display:flex;gap:5px;flex-wrap:wrap;align-items:center;padding:0 18px 8px}
.qtag{font-size:10.5px;letter-spacing:.03em;padding:2px 7px;border:1px solid var(--line);
 border-radius:4px;color:var(--dim)}
.qtag.alt{border-color:var(--accent);color:var(--ink)}
.qsrc{margin-left:auto;font-family:var(--mono);font-size:10.5px;color:var(--faint)}
.mn{font-family:var(--mono);font-size:10.5px;color:var(--dim);border-left:1px solid var(--line2);padding-left:6px}
.mtop{display:flex;gap:16px;align-items:flex-start;padding:14px 18px 0}
.mtxt{min-width:0;flex:1}
.mpic{width:132px;height:132px;object-fit:contain;background:var(--sel);
 border:1px solid var(--line2);border-radius:8px;padding:6px;flex:none}
.psrc{margin-top:6px;font-family:var(--mono);font-size:10.5px;color:var(--faint)}
.mth{width:22px;height:22px;object-fit:contain;border-radius:3px;background:var(--sel)}
.vth{width:20px;height:20px;object-fit:contain;border-radius:3px;background:var(--sel)}
@media(max-width:640px){.mtop{flex-direction:column}.mpic{width:108px;height:108px}}
.mtop h2{font-size:15.5px;font-weight:650;letter-spacing:-.01em}
.mtop .vd{font-size:11px;letter-spacing:.06em;color:var(--faint);font-weight:700}
.mtop p{font-size:12.3px;color:var(--dim);margin-top:5px;max-width:74ch}
.meta{display:flex;gap:16px;flex-wrap:wrap;padding:10px 18px;margin-top:10px;
 border-top:1px solid var(--line2);border-bottom:1px solid var(--line2);font-size:11.5px;color:var(--dim)}

/* 안내 상태 */
.msg{margin:18px;padding:16px 18px;border:1px dashed var(--line);border-radius:8px}
.msg b{display:block;font-size:13.5px;margin-bottom:4px}
.msg p{font-size:12.3px;color:var(--dim)}
.msg .nx{margin-top:8px;font-size:12px;color:var(--warn)}

/* 홈 */
.home{padding:20px 18px 60px;max-width:960px}
.home h1{font-size:21px;font-weight:650;letter-spacing:-.02em;margin-bottom:6px}
.home .lead{font-size:13px;color:var(--dim);max-width:70ch;margin-bottom:20px}
.rows{border-top:1px solid var(--line)}
.rows>div{display:grid;grid-template-columns:96px 1fr 132px;gap:14px;padding:11px 0;
 border-bottom:1px solid var(--line2);align-items:baseline}
.rows .k{font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--faint)}
.rows .v b{font-size:13px}
.rows .v p{font-size:12.2px;color:var(--dim);margin-top:2px}
.rows .r{text-align:right;font-size:11.5px;color:var(--faint);font-family:var(--mono)}
@media(max-width:860px){
 /* 상단이 3열 고정이라 좁은 화면에서 지표가 밀려 화면 전체가 가로로 넘쳤다 → 2줄로 */
 .top{grid-template-columns:1fr auto;gap:8px;padding:8px 12px}
 #q{grid-column:1/-1;max-width:none;order:3}
 .tot{flex-wrap:wrap;gap:8px;justify-content:flex-end}
 .app{grid-template-columns:1fr;min-width:0}
 main,.wrap{min-width:0;max-width:100vw}
 .mlist button,.slist button{max-width:100%}
 aside{position:static;max-height:none;border-right:0;border-bottom:1px solid var(--line);
  display:flex;overflow-x:auto;gap:2px;padding:6px}
 aside .gh{display:none}
 aside button{width:auto;white-space:nowrap;border-left:0;border-bottom:2px solid transparent}
 aside button[aria-current="true"]{border-left:0;border-bottom-color:var(--accent)}
 th{top:0}
 .rows>div{grid-template-columns:1fr}
}
</style></head><body>
<div class="top">
  <div class="brand">BMS 장비 카탈로그<span>Haystack 4 기준 · 2026-07-27</span></div>
  <input id="q" placeholder="장비 · 포인트 · 태그 · 모델 검색" autocomplete="off">
  <div class="tot"><span>장비 <b>__NEQ__</b></span><span>포인트 <b>__TOTP__</b></span>
   <span>모델 <b>__NMODEL__</b></span><span>모델 포인트 <b>__NMPTS__</b></span>
   <span>정격 사양 <b>__NSPEC__</b><small>모델</small></span></div>
</div>
<div class="app">
  <aside id="nav"></aside>
  <main id="main"></main>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
(function(){
"use strict";
var D = JSON.parse(document.getElementById('data').textContent);
var nav = document.getElementById('nav'), main = document.getElementById('main'), q = document.getElementById('q');
var cur = 'home', tab = 'pt', mi = 0, kindF = '', gradeF = '', term = '';
var vsel = 0;   // 고른 형번 (variants) — 모델을 바꾸면 0 으로 되돌린다
var ssel = 0;   // 고른 사양 표

function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function fmt(s){ // 마크다운 조각 → HTML
  s = esc(s);
  s = s.replace(/`([^`]+)`/g,'<code>$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g,'<b>$1</b>');
  s = s.replace(/\[([^\]]+)\]\(([^)]+)\)/g,'<a href="$2" target="_blank" rel="noopener">$1</a>');
  s = s.replace(/✓/g,'<span class="ok">✓</span>').replace(/★/g,'<span class="no">★</span>');
  return s;
}
var NUMCOL = /^(인스턴스|종류|단위|등급|수량|값)$/;

// ── 좌측 목록
function buildNav(){
  var h = '<div class="gh">시작</div><button data-id="home">홈 — 현업은 이렇게 봐요<i></i></button>';
  D.domOrder.forEach(function(dm){
    var list = D.equips.filter(function(e){return e.domain===dm;});
    if(!list.length) return;
    if(list.length>1) h += '<div class="gh">'+esc(dm)+'</div>';
    else h += '<div class="gh" style="height:6px"></div>';
    list.forEach(function(e){
      var nm = (D.models[e.id]||[]).length;
      // 사양이 있는 모델 수까지 보여 준다 — 없으면 어느 계열을 눌러야 할지 알 수 없다
      var ns = (D.models[e.id]||[]).filter(hasSpec).length;
      h += '<button data-id="'+e.id+'">'+esc(e.title)+'<i>'+e.np+(nm?' · M'+nm:'')
         + (ns?' · <b class="sm">S'+ns+'</b>':'')+'</i></button>';
    });
  });
  nav.innerHTML = h;
  nav.querySelectorAll('button').forEach(function(b){
    b.addEventListener('click',function(){ cur=b.dataset.id; tab='pt'; mi=0; vsel=0; ssel=0; pageOf={}; kindF=''; gradeF=''; render(); });
  });
}
function markNav(){ nav.querySelectorAll('button').forEach(function(b){
  b.setAttribute('aria-current', b.dataset.id===cur ? 'true':'false'); }); }

// ── 표
// 표가 길면 나눠 그린다. 1,537행짜리 오브젝트 목록을 한 번에 그리면
// 화면이 끝없이 늘어나고 원하는 줄을 찾을 수 없다 (밀러의 법칙 — 덩어리로 끊는다).
var PAGE = 60;
var sortOf = {};        // 표 키 → {col, dir}
// 맨 앞의 수를 값으로 본다. '13 W' 와 '2 W' 는 단위가 붙어 있어도 13 > 2 다 —
// 문자열로 견주면 '13' 이 '2' 보다 앞서 정렬이 뒤집힌다.
function numOf(x){
  var m = String(x).replace(/,/g,'').match(/-?\d+(\.\d+)?/);
  return m ? parseFloat(m[0]) : NaN;
}
function cmpCell(a,b){
  var na = numOf(a), nb = numOf(b);
  var ae = String(a).trim(), be = String(b).trim();
  var empty = function(v){ return !v || v === '—' || v === '-'; };
  if(empty(ae) !== empty(be)) return empty(ae) ? 1 : -1;   // 빈 칸은 항상 뒤로
  if(!isNaN(na) && !isNaN(nb) && na !== nb) return na - nb;
  return ae.localeCompare(be, 'ko');
}
var pageOf = {};        // 표 키 → 현재 쪽
function pageKey(t){ return (t.key || (t.header||[]).join('|')).slice(0,80); }

function pager(key, total, page, pages){
  if(pages < 2) return '';
  var from = page*PAGE+1, to = Math.min(total, (page+1)*PAGE);
  return '<div class="pg" data-pk="'+esc(key)+'">'
    + '<button class="pgb" data-go="0" '+(page?'':'disabled')+'>처음</button>'
    + '<button class="pgb" data-go="'+(page-1)+'" '+(page?'':'disabled')+'>이전</button>'
    + '<span class="pgn"><b>'+from+'–'+to+'</b> / '+total+'행 · '+(page+1)+'/'+pages+'쪽</span>'
    + '<button class="pgb" data-go="'+(page+1)+'" '+(page<pages-1?'':'disabled')+'>다음</button>'
    + '<button class="pgb" data-go="'+(pages-1)+'" '+(page<pages-1?'':'disabled')+'>끝</button>'
    + '</div>';
}

function table(t, opts){
  opts = opts||{};
  var ki = t.header.findIndex(function(c){return /종류/.test(c);});
  var gi = t.header.findIndex(function(c){return /등급/.test(c);});
  var rows = t.rows.filter(function(r){
    if(kindF && ki>=0 && String(r[ki]).indexOf(kindF)<0) return false;
    if(gradeF && gi>=0 && String(r[gi]).indexOf(gradeF)<0) return false;
    if(term && r.join(' ').toLowerCase().indexOf(term)<0) return false;
    return true;
  });
  if(!rows.length) return '';
  // 긴 표만 쪽으로 나눈다. 짧은 표까지 나누면 오히려 손이 더 간다.
  var key = pageKey(t), total = rows.length, pages = 1, page = 0, ctrl = '';
  var rowsAll = rows;
  if(!opts.nopage && total > PAGE){
    pages = Math.ceil(total/PAGE);
    page = Math.min(pageOf[key]||0, pages-1);
    ctrl = pager(key, total, page, pages);
    rows = rows.slice(page*PAGE, (page+1)*PAGE);
  }
  var so = sortOf[key];
  if(so){
    rowsAll.sort(function(x,y){ return cmpCell(x[so.col], y[so.col]) * so.dir; });
    rows = (!opts.nopage && total > PAGE) ? rowsAll.slice(page*PAGE,(page+1)*PAGE) : rowsAll;
  }
  var h = ctrl + '<div class="tw"><table data-tk="'+esc(key)+'"><thead><tr>';
  t.header.forEach(function(c,i){
    var mark = so && so.col===i ? (so.dir>0?' ▲':' ▼') : '';
    h += '<th class="srt" data-col="'+i+'">'+fmt(c)+'<i class="sa">'+mark+'</i></th>';
  });
  h += '</tr></thead><tbody>';
  rows.forEach(function(r){
    h += '<tr>';
    r.forEach(function(c,i){
      var cls = NUMCOL.test(t.header[i]) || /^\d/.test(String(c)) ? ' class="n"' : '';
      h += '<td'+cls+'>'+fmt(c)+'</td>';
    });
    h += '</tr>';
  });
  return h + '</tbody></table></div>' + (pages>1 ? ctrl : '');
}
function counted(tabs){ return tabs.reduce(function(a,t){return a+t.rows.length;},0); }

// ── 필터 바
function kindChips(tabs){
  var ki=-1, set={};
  tabs.forEach(function(t){
    var i = t.header.findIndex(function(c){return /종류/.test(c);});
    if(i<0) return; ki=i;
    t.rows.forEach(function(r){ String(r[i]).split('/').forEach(function(k){
      k=k.trim(); if(k && k!=='—') set[k]=1; }); });
  });
  if(ki<0) return '';
  var ks = Object.keys(set).sort();
  if(ks.length<2) return '';
  var h = '<div class="bar"><button class="chip" data-kind="" aria-pressed="'+(!kindF)+'">전체</button>';
  ks.forEach(function(k){ h += '<button class="chip" data-kind="'+esc(k)+'" aria-pressed="'+(kindF===k)+'">'+esc(k)+'</button>'; });
  var gset = {};
  tabs.forEach(function(t){
    var i = t.header.findIndex(function(c){return /등급/.test(c);});
    if(i<0) return;
    t.rows.forEach(function(r){ var g=String(r[i]).trim(); if(g) gset[g]=1; });
  });
  Object.keys(gset).forEach(function(g){
    h += '<button class="chip" data-grade="'+esc(g)+'" aria-pressed="'+(gradeF===g)+'">'+esc(g)+'</button>';
  });
  return h + '<span class="sp" id="cnt"></span></div>';
}

// ── 화면
function renderHome(){
  return '<div class="home"><h1>현업은 장비 정보를 이렇게 봐요</h1>'
   + '<p class="lead">건설·설비 현장은 장비 정보를 단계마다 다른 문서로 나눠서 봐요. '
   + '다섯 문서가 공통으로 지키는 규칙이 있는데, 이 카탈로그도 그 규칙을 따라요.</p>'
   + '<div class="rows">'
   + row('설계','장비일람표','도면 안의 표예요. 태그(<code>AHU-1</code>)가 도면 그림과 표의 한 줄을 이어줘요.','1장비 = 1행')
   + row('시공','자재승인원','“이 모델 쓸게요”라고 내는 문서예요. 일람표가 요구한 값과 제품 실제 값을 맞춰봐요.','값 대조')
   + row('관제','포인트 리스트','장비마다 <code>AI/AO/DI/DO</code>가 몇 점인지 적어요. 이름 규칙이 따로 있어요.','오브젝트 목록')
   + row('준공','O&amp;M 매뉴얼','데이터시트와 매뉴얼에 <b>그 현장의 실제 값</b>(명판·설정값·위치)을 더해요.','현장 실측값')
   + row('운영','COBie','엑셀 탭 하나가 데이터베이스 표 하나예요. 유지보수 시스템에 그대로 넣어요.','국제 표준')
   + row('국내','유지관리기준','국토부 고시 제2023-695호. <b>장비일람표의 모델명·용량·위치가 최신인지</b>를 점검해요.','법정 요구')
   + '</div>'
   + '<h1 style="margin-top:28px;font-size:16px">다섯 문서의 공통 규칙</h1>'
   + '<div class="rows">'
   + row('규칙 1','표 한 장으로 봐요','장비일람표도 포인트 리스트도 COBie도 전부 스프레드시트예요.','1행 = 1항목')
   + row('규칙 2','태그가 문서를 이어요','<code>AHU-1</code> 하나가 도면·일람표·승인원·포인트리스트·유지보수대장에 다 나와요.','연결 키')
   + row('규칙 3','모델과 현장 1대를 나눠요','COBie도 Type 탭(모델)과 Component 탭(설치된 개체)을 나눠요.','우리와 같은 구조')
   + '</div>'
   + '<h1 style="margin-top:28px;font-size:16px">포인트 수가 층마다 달라요</h1>'
   + '<div class="rows">'
   + row('공통','장비 종류의 최소 공통','모델이 무엇이든 항상 있는 포인트예요. 왼쪽에서 장비를 고르면 이게 나와요.','계열당 10~35')
   + row('부속 포함','부속까지 펼친 것','공조기 1대 = 급기팬 + 환기팬 + 코일 + 댐퍼 4개 + 필터 + 인버터 2대예요.','1대당 30~120')
   + row('모델','그 모델이 내보내는 전부','제조사 문서가 있어야 채워져요. <b>냉동기 원심 기종은 217점</b>이에요.','모델당 30~300')
   + '</div>'
   + '<p class="lead" style="margin-top:18px">왼쪽에서 장비를 고르고, 위쪽 <b>모델</b> 탭을 누르면 실제 오브젝트 목록을 볼 수 있어요.</p>'
   + '</div>';
}
function row(k,t,d,r){
  return '<div><div class="k">'+k+'</div><div class="v"><b>'+t+'</b><p>'+d+'</p></div>'
       + '<div class="r">'+r+'</div></div>';
}

function renderEquip(e){
  var models = D.models[e.id]||[], l3 = D.l3[e.id];
  var h = '<div class="hd"><div class="dom">'+esc(e.domain)+'</div><h1>'+esc(e.title)+'</h1>'
        + '<div class="tag">'+fmt(e.head)+'</div></div>';
  h += '<div class="tabs">'
     + tb('pt','포인트',e.np) + tb('sp','사양',e.ns) + tb('md','모델',models.length) + '</div>';
  if(tab==='pt'){
    h += kindChips(e.points);
    h += '<div class="wrap">' + e.points.map(function(t){return table(t);}).join('');
    h += emptyIf(e.points) + '</div>';
  } else if(tab==='sp'){
    h += '<div class="wrap">' + e.spec.map(function(t){return table(t);}).join('') + emptyIf(e.spec) + '</div>';
    if(e.notes.length) h += '<div class="msg"><b>참고</b><p>'+fmt(e.notes.map(function(n){
      return n.replace(/^>\s*/,'');}).join(' '))+'</p></div>';
  } else {
    h += renderModels(models, l3);
  }
  return h;
}
function tb(id,label,n){
  return '<button data-tab="'+id+'" aria-selected="'+(tab===id)+'">'+label
       + (n?'<i>'+n+'</i>':'')+'</button>';
}
function emptyIf(tabs){
  var n = tabs.reduce(function(a,t){return a+t.rows.length;},0);
  if(!n) return '<div class="msg"><b>아직 없어요</b><p>이 항목은 채워지지 않았어요.</p></div>';
  return '';
}
function renderModels(models, l3){
  if(!models.length){
    return '<div class="msg"><b>확보한 모델이 아직 없어요</b>'
      + '<p>앞의 사양 탭은 <b>무엇을 채울지</b>만 정해둔 목록이에요. 값은 제조사 문서에서 와요.</p>'
      + '<div class="nx">다음에 받을 문서 — '+esc(l3?l3[1]:'제조사 통신 문서')+'</div></div>';
  }
  var m = models[Math.min(mi, models.length-1)];
  var h = '';
  if(models.length>1){
    // 모델이 20건을 넘으면 이름 전체가 길어 고르기 어렵다.
    // 공통 앞머리(제조사·컨트롤러)를 떼고 **다른 부분만** 보이게 한다.
    var pre = models.length > 1 ? commonPrefix(models.map(function(x){return x.model;})) : '';
    h += (pre ? '<div class="mpre">'+esc(pre.replace(/[\s—·-]+$/,''))+'</div>' : '')
       + '<div class="mlist">' + models.map(function(x,i){
      // 프로토콜은 오른쪽 배지로 따로 보여주므로 이름에서는 뺀다 (중복 표기 방지)
      var lbl = x.model.slice(pre.length).replace(/^[\s—·-]+/,'')
                 .replace(/\s*\((BACnet|LonTalk|Modbus)\)\s*$/i,'') || x.model;
      var pr = (x.comm||[]).map(function(c){return c[0];});
      var tail = pr.length ? '<span class="mpr">'+esc(pr.join('·'))+'</span>' : '';
      var n = (x.points||[]).length, sn = specCount(x);
      var th = x.photo ? '<img class="mth" src="'+x.photo+'" alt="">' : '';
      return '<button data-mi="'+i+'" aria-pressed="'+(i===mi)+'">'+th+esc(lbl)+tail
           + (n ? '<span class="mn">'+n+'</span>' : '')
           + (sn ? '<span class="ms">사양 '+sn+'</span>' : '') + '</button>';
    }).join('') + '</div>';
  }
  // 형번을 골랐으면 그 형번 사진을, 아니면 제품군 사진을 보여 준다.
  var vphoto = (m.variants||[])[Math.min(vsel,(m.variants||[]).length-1)];
  var photo = (vphoto && vphoto.photo) || m.photo;
  var psrc  = (vphoto && vphoto.photo) ? (vphoto.source+' p'+(vphoto.photoPage||1)) : m.photoSource;
  h += '<div class="mtop">'
     + (photo ? '<img class="mpic" src="'+photo+'" alt="" title="'+esc(psrc||'')+'">' : '')
     + '<div class="mtxt"><div class="vd">'+esc(m.vendor)+'</div><h2>'+esc(m.name)+'</h2>'
     + '<p>'+fmt(m.summary)+'</p>'
     + (psrc ? '<div class="psrc">사진 출처 '+esc(psrc)+'</div>' : '')
     + '</div></div>';
  h += '<div class="meta"><span>모델 <code>'+esc(m.model)+'</code></span>'
     + '<span>분류 <code>'+esc(m.cat)+'</code></span><span>태그 <code>'+esc(m.tag)+'</code></span>'
     + '<span>사양값 '+badge(m.has.spec)+'</span><span>오브젝트 목록 '+badge(m.has.points)+'</span></div>';
  h += '<div class="wrap">';
  if(m.spec.length) h += sec('정격 사양', m.spec.length)
    + table({header:['항목','값','단위','조건·비고','근거'], rows:m.spec});
  if(m.comm.length) h += sec('통신', m.comm.length)
    + table({header:['프로토콜','제공','물리계층','근거'], rows:m.comm});
  if(m.io.length) h += sec('하드웨어 입출력 · 레지스터 구성', m.io.length)
    + table({header:['항목','수량·위치','내용','근거'], rows:m.io});
  if(m.elec) h += sec('전기 데이터 — 용량별 전류 · 손실 · 효율', m.elec.rows.length)
    + '<div class="msg" style="margin:0 18px 10px"><p>'+fmt(m.elec.note)+'</p></div>'
    + table({header:m.elec.header, rows:m.elec.rows});
  // 형번별 정격 — 데이터시트 한 장이 형번 하나다. 제품군을 고른 뒤 형번을 고르면
  // 그 형번의 정격이 나온다. 시뮬레이터가 쓰는 값이 여기 있다.
  if((m.variants||[]).length){
    var vs = m.variants, vi = Math.min(vsel, vs.length-1);
    // 형번을 고르기 전에 **나란히 비교**할 수 있어야 한다. 하나씩 눌러 보며
    // 외우게 하면 안 된다 (테슬러 — 복잡함은 도구가 떠안는다).
    var KEYS = [['정격전압', /nominal voltage$/i], ['운전 전력', /power consumption in operation/i],
                ['유지 전력', /power consumption.*(rest|holding)/i], ['토크', /torque motor/i],
                ['구동시간', /running time/i], ['소음', /sound power/i], ['중량', /^weight$/i]];
    var used = KEYS.filter(function(k){
      return vs.some(function(v){ return (v.spec||[]).some(function(r){ return k[1].test(r[0]); }); });
    });
    if(used.length){
      var crows = vs.map(function(v){
        return [v.code].concat(used.map(function(k){
          var r = (v.spec||[]).find(function(x){ return k[1].test(x[0]); });
          if(!r) return '—';
          // 값에 이미 단위가 붙어 있으면 또 붙이지 않는다 ('180 in-lb [20 Nm] in-lb')
          var val = String(r[1]), u = r[2];
          var dup = u && u!=='—' && val.toLowerCase().indexOf(String(u).toLowerCase()) >= 0;
          // 비교표는 한눈에 봐야 하므로 괄호 안 환산값·부연은 잘라낸다
          val = val.replace(/\s*\[[^\]]*\]/g,'').replace(/,\s*(end stop|.*fuse).*$/i,'')
                   .replace(/\s*@.*$/,'').trim();
          return val + (u && u!=='—' && !dup ? ' '+u : '');
        }));
      });
      h += sec('형번 비교 — 핵심 정격', vs.length)
         + table({header:['형번'].concat(used.map(function(k){return k[0];})),
                  rows:crows, key:'vcmp'+m.id});
    }
    h += sec('형번별 상세', vs.length)
       + '<div class="vlist">' + vs.map(function(v,i){
           return '<button data-vi="'+i+'" aria-pressed="'+(i===vi)+'">'
                + (v.photo ? '<img class="vth" src="'+v.photo+'" alt="">' : '')
                + esc(v.code)+'</button>';
         }).join('') + '</div>'
       + table({header:['항목','값','단위','구역','근거'], rows:vs[vi].spec});
  }
  // 카탈로그·설계 가이드에서 뽑은 정격 사양 행렬. 한 줄이 형번 하나이고
  // 열이 속성이라 포인트 표와 구조가 다르다 — 표마다 따로 그린다.
  // 사양 표는 모델 하나에 수십 개까지 붙는다(Ascend 38개). 전부 펼치면 스크롤이
  // 끝나지 않아 원하는 표를 못 찾는다 → **목록에서 골라 하나씩** 본다 (힉의 법칙).
  var sts = m.specTables || [];
  if(sts.length){
    var si = Math.min(ssel, sts.length-1), t = sts[si];
    h += sec('정격 사양', sts.length)
       + '<div class="slist">' + sts.map(function(x,i){
           var qq = (x.quantities||[]).filter(Boolean);
           var lbl = (x.title||'표 '+(i+1)).replace(/^Table\s*\d+\.\s*/,'');
           // 같은 제목이 여러 개면 쪽수로 가른다 — 'General Information' 이 세 개다
           if(sts.filter(function(z){return (z.title||'')===(x.title||'');}).length>1)
             lbl += ' (p'+x.page+')';
           return '<button data-si="'+i+'" aria-pressed="'+(i===si)+'">'
                + esc(lbl.slice(0,34))
                + '<span class="mn">'+x.rows.length+'</span>'
                + (qq.length?'<span class="ms">'+esc(QLABEL[qq[0]]||qq[0])+'</span>':'')
                + '</button>';
         }).join('') + '</div>';
    var uq = [];
    (t.quantities||[]).forEach(function(x){ if(x && uq.indexOf(x)<0) uq.push(x); });
    h += '<div class="qrow">'
       + (t.orientation==='row' ? '<span class="qtag alt">행=항목 · 열=형번</span>' : '')
       + uq.map(function(x){ return '<span class="qtag">'+esc(QLABEL[x]||x)+'</span>'; }).join('')
       + '<span class="qsrc">' + esc(t.source||'') + ' p'+t.page+'</span></div>'
       + table({header:t.header, rows:t.rows, key:'st'+si+(t.source||'')});
  }
  if(m.points.length){
    var pts = m.points.filter(function(p){return p.inst;});
    var hasNote = m.points.some(function(p){return p.note;});
    var head = hasNote ? ['인스턴스','종류','단위','오브젝트명','값 범위 · 상태']
                       : ['인스턴스','종류','단위','오브젝트명'];
    var rows = m.points.map(function(p){
      return hasNote ? [p.inst||'', p.type, p.unitDisp, p.name, p.note||'']
                     : [p.inst, p.type, p.unitDisp, p.name];
    });
    h += sec('오브젝트 목록 — BMS에 이대로 만들어져요', pts.length)
       + kindChips([{header:head, rows:rows}])
       + table({header:head, rows:rows});
  }
  h += sec('근거 문서', m.docs.length)
     + table({header:['종류','제목','발행자','문서번호','발행','경로','상태'],
              rows:m.docs.map(function(d){
                return [d[0],d[1],d[2],d[3],d[4],'['+'열기'+']('+d[5]+')',d[6]];})});
  h += '</div>';
  if(m.gap) h += '<div class="msg"><b>아직 못 채운 것</b><p>'+fmt(m.gap)+'</p></div>';
  return h;
}
function badge(ok){ return ok ? '<span class="ok">있어요</span>' : '<span class="no">아직 없어요</span>'; }
function commonPrefix(a){
  if(a.length<2) return '';
  var p = a[0];
  for(var i=1;i<a.length;i++){
    var j=0; while(j<p.length && j<a[i].length && p[j]===a[i][j]) j++;
    p = p.slice(0,j);
    if(!p) return '';
  }
  return p;
}

var QLABEL = {power:'전력', current:'전류', voltage:'전압', frequency:'주파수',
  efficiency:'효율', loss:'손실', capacity:'용량', airflow:'풍량', pressure:'압력',
  speed:'회전수', torque:'토크', temperature:'온도', weight:'중량',
  dimension:'치수', noise:'소음', protection:'보호등급'};

function specCount(m){
  return (m.specTables||[]).length + (m.variants||[]).length + ((m.spec||[]).length?1:0);
}
function hasSpec(m){ return specCount(m) > 0; }

function sec(t,n){ return '<div class="sec">'+esc(t)+(n?' <b>'+n+'</b>':'')+'</div>'; }

function render(){
  markNav();
  if(cur==='home'){ main.innerHTML = renderHome(); return; }
  var e = D.equips.filter(function(x){return x.id===cur;})[0];
  main.innerHTML = renderEquip(e);
  main.querySelectorAll('.tabs button').forEach(function(b){
    b.addEventListener('click',function(){ tab=b.dataset.tab; kindF=''; gradeF=''; render(); });});
  main.querySelectorAll('.mlist button').forEach(function(b){
    b.addEventListener('click',function(){ mi=+b.dataset.mi; vsel=0; ssel=0; pageOf={}; render(); });});
  main.querySelectorAll('.vlist button').forEach(function(b){
    b.addEventListener('click',function(){ vsel=+b.dataset.vi; render(); });});
  main.querySelectorAll('.slist button').forEach(function(b){
    b.addEventListener('click',function(){ ssel=+b.dataset.si; pageOf={}; render(); });});
  main.querySelectorAll('th.srt').forEach(function(th){
    th.addEventListener('click',function(){
      var k = th.closest('table').dataset.tk, c = +th.dataset.col;
      var cur = sortOf[k];
      sortOf[k] = (cur && cur.col===c) ? {col:c, dir:-cur.dir} : {col:c, dir:1};
      var y = window.scrollY; render(); window.scrollTo(0,y);
    });});
  main.querySelectorAll('.pgb').forEach(function(b){
    b.addEventListener('click',function(){
      if(b.disabled) return;
      var y = window.scrollY;
      pageOf[b.parentNode.dataset.pk] = +b.dataset.go;
      render(); window.scrollTo(0, y);   // 쪽만 바뀌고 보던 자리는 그대로
    });});
  main.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click',function(){
      if(b.dataset.kind!==undefined) kindF = (kindF===b.dataset.kind)?'':b.dataset.kind;
      if(b.dataset.grade!==undefined) gradeF = (gradeF===b.dataset.grade)?'':b.dataset.grade;
      render();});});
  // 행 수는 **필터 칩 바로 다음 표**만 센다. main 전체를 세다가 통신표·근거문서표
  // 행까지 더해져 550점이 553행으로 보였다.
  var c = main.querySelector('#cnt');
  if(c){
    var bar = c.closest('.chips') || c.parentNode;
    var t = bar.nextElementSibling;
    while(t && t.tagName !== 'TABLE') t = t.querySelector ? t.querySelector('table') : null;
    c.textContent = (t ? t.querySelectorAll('tbody tr').length : 0) + '행';
  }
}

var t0;
q.addEventListener('input', function(){
  clearTimeout(t0);
  t0 = setTimeout(function(){ term = q.value.trim().toLowerCase(); render(); }, 120);
});
buildNav(); render();
})();
</script>
</body></html>"""

out = (HTML.replace("__DATA__", json.dumps(DATA, ensure_ascii=False).replace("</", "<\\/"))
           .replace("__NEQ__", str(len(equips))).replace("__TOTP__", str(TOTP))
           .replace("__NMODEL__", str(NMODEL)).replace("__NMPTS__", str(NMPTS))
           .replace("__NSPEC__", str(NSPEC)))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8").write(out)
print("생성:", OUT, "%.0f KB" % (len(out.encode("utf-8")) / 1024))
print("장비 %d · 포인트 %d · 사양 %d · 모델 %d · 모델포인트 %d" % (len(equips), TOTP, TOTS, NMODEL, NMPTS))
