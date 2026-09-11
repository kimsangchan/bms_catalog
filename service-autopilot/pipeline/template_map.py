# -*- coding: utf-8 -*-
"""BMS 기본화면 템플릿 검사대 → review/template-map.html

  PYTHONIOENCODING=utf-8 python template_map.py

왜 필요한가
  템플릿 행만 늘어놓으면 맞는지 알 수 없다. **모델을 붙여 봐야** '이 개념이 이 벤더에선
  어떤 이름으로 오나'가 보이고, 거기서 오답이 드러난다 — 실제로 이 대조를 스크립트로
  찍어 보고 오답 여덟을 잡았다(가스 적산을 전력 적산으로, 리모컨 잠금을 풍량 지령으로,
  'kWh Counter' 를 주파수 지령으로 …). 그 대조를 화면으로 옮긴 것이다.

  ⚠ 정규식은 이름만으로 뜻을 가르지 못한다. **집힌 결과를 사람이 봐야 한다.**
  이 페이지의 존재 이유가 그것이다.

무엇을 보여 주나
  ① 프로파일(계열·하위형식)별 템플릿 행 — 개념·종류·단위·등급·왜 필요한가·계산식·근거
  ② 모델과 판을 고르면 각 행에 **모델 원문에서 대응한 이름**이 채워진다
  ③ 덮개 표 — 모델 × 행 격자. 어느 행을 아무 모델도 안 내주는지 한눈에 본다

읽는 데이터 (화면이 목록을 정하지 않는다 — 데이터가 정한다)
  data/equip-templates.json      템플릿 행
  data/equip-requirements.json   계산식(energyModel)과 요구 항목
  data/datasets/model-mappings.json  모델·판별 매칭 결과
"""
import collections
import glob
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "..", "review", "template-map.html")
CATALOG = os.path.join(HERE, "..", "08-equip-spec-tag-catalog.md")


def equip_names():
    """계열 한글 이름을 **기준 문서에서 읽는다** — 두 벌을 만들지 않는다.
    '# 8. VRF (실내기 · 실외기)' -> e8. verify_points.py 와 같은 방식이다."""
    import re
    out = {}
    if os.path.exists(CATALOG):
        for line in io.open(CATALOG, encoding="utf-8"):
            m = re.match(r"^#\s+(\d+)\.\s+(.+?)\s*$", line)
            if m:
                out["e" + m.group(1)] = m.group(2)
    return out

# 공용 포인트는 **사전**이 정한다 — data/point-concepts.json.
# 예전엔 이 파일 안에 CANON 표를 두고 이름으로 묶었다. 그건 판단이 코드에 숨는 구조였고,
# 계열이 19개로 늘면 못 버틴다. 이제 행이 concept id 를 들고 다닌다.
CSS = """
:root{--bg:#F5F8F9;--panel:#fff;--ink:#0F1A1F;--dim:#4A6068;--faint:#7C949C;
 --line:#DAE3E7;--accent:#0E7A88;--soft:#DCEEF0;--warn:#9A6608;--bad:#A33;--ok:#1E7A44;
 --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
 --ui:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
 --bg:#0C1417;--panel:#111C20;--ink:#DCE7EA;--dim:#93A8AF;--faint:#6B838B;
 --line:#1E2C32;--accent:#3FB4C2;--soft:#10333A;--warn:#D9A441;--bad:#E08585;--ok:#5FBF8F}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:13px/1.5 var(--ui)}
.wrap{max-width:1460px;margin:0 auto;padding:16px 18px 28px}
h1{font-size:18px;margin:0 0 2px}
.sub{color:var(--faint);font-size:12px;margin:0 0 12px}
code{font-family:var(--mono);font-size:11px;color:var(--dim);word-break:break-all}

/* 탭 + 필터 바 — 위에 붙어 따라온다. 스크롤해도 조작부가 사라지지 않는다 */
.top{position:sticky;top:0;z-index:5;background:var(--bg);padding-top:2px;
 border-bottom:1px solid var(--line);margin-bottom:10px}
.tabs{display:flex;gap:4px;margin-bottom:8px;align-items:center}
.tabs .brand{font-weight:700;font-size:13px;margin-right:10px;white-space:nowrap}
.tabs button{background:none;border:0;border-bottom:2px solid transparent;
 padding:5px 12px;color:var(--dim);font:13px var(--ui);cursor:pointer}
.tabs button[aria-current=true]{color:var(--ink);border-bottom-color:var(--accent);
 font-weight:600}
.bar{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding-bottom:8px}
.bar input,.bar select{background:var(--panel);color:var(--ink);
 border:1px solid var(--line);border-radius:6px;padding:4px 7px;font:12px var(--ui)}
.bar input{width:170px}
.bar select{max-width:300px}
.bar .sp{flex:1}
.bar .cnt{font-family:var(--mono);font-size:11.5px;color:var(--dim);
 font-variant-numeric:tabular-nums;white-space:nowrap}
.bar .cnt b{color:var(--accent)}
.chip{border:1px solid var(--line);background:var(--panel);border-radius:999px;
 padding:3px 10px;font-size:11.5px;color:var(--dim);cursor:pointer}
.chip[aria-pressed=true]{border-color:var(--accent);background:var(--soft);
 color:var(--ink)}

table{border-collapse:collapse;width:100%;font-size:12px;background:var(--panel);
 border:1px solid var(--line);border-radius:8px;overflow:hidden}
th,td{padding:5px 8px;text-align:left;border-bottom:1px solid var(--line);
 vertical-align:middle}
th{background:var(--soft);font-weight:600;font-size:11px;white-space:nowrap;
 position:sticky;top:0}
tr:last-child td{border-bottom:0}
tr.sel td{background:var(--soft)}
tbody tr{cursor:pointer}
tbody tr:hover td{background:var(--soft)}
/* 이름은 자르지 않는다 — 무엇인지 못 알아보면 칸이 있으나 마나다.
   표는 이미 가로 스크롤 상자 안이라 넓어져도 오른쪽 패널을 안 덮는다 */
td.k{font-weight:600;white-space:nowrap}
td.mono{font-family:var(--mono);font-size:11px;font-variant-numeric:tabular-nums;
 white-space:nowrap}
td.hit{font-family:var(--mono);font-size:11px;color:var(--ok);
 white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:290px}
td.miss{color:var(--faint);font-size:11px;white-space:nowrap}
td.c{text-align:center;font-family:var(--mono)}
td.c.y b{color:var(--ok)}
td.c.n{color:var(--line)}
td.c .nm{display:block;font-size:9px;color:var(--faint);white-space:nowrap;
 overflow:hidden;text-overflow:ellipsis;max-width:88px;margin:0 auto}
th.pid{text-align:center;font-family:var(--mono);font-size:10px;padding:4px}
th.pid .e{display:block;color:var(--faint);font-size:9px}
.g{display:inline-block;border-radius:999px;padding:0 6px;font-size:10px;
 border:1px solid var(--line);white-space:nowrap}
.g.f{color:var(--bad);border-color:var(--bad)}
.g.r{color:var(--accent);border-color:var(--accent)}
.g.o{color:var(--faint)}
.g.w{color:var(--warn);border-color:var(--warn);margin-left:5px}

/* 페이저 — 표 바로 밑. 한 화면에 25행이면 스크롤이 거의 없다 */
.pager{display:flex;gap:6px;align-items:center;justify-content:flex-end;
 margin-top:7px;font-size:11.5px;color:var(--dim)}
.pager button{background:var(--panel);border:1px solid var(--line);border-radius:6px;
 padding:3px 9px;color:var(--ink);font:11.5px var(--mono);cursor:pointer}
.pager button[disabled]{opacity:.35;cursor:default}
.pager .pos{font-family:var(--mono);font-variant-numeric:tabular-nums}

/* 본문 + 상세. 상세는 옆에 붙어 스크롤을 만들지 않는다 */
/* 표는 프로파일마다 열이 하나씩 는다 — 칸을 넘기면 오른쪽 상세를 덮으므로
   가로 스크롤 상자에 담는다. th 의 sticky 는 이 상자 안에서 안 걸리지만
   25행 페이징이라 세로 스크롤이 거의 없어 손해가 없다 */
.tw{overflow-x:auto;border-radius:8px}
.split{display:grid;grid-template-columns:minmax(0,1fr) 330px;gap:14px;
 align-items:start}
@media(max-width:1120px){.split{grid-template-columns:1fr}}
aside{position:sticky;top:96px;max-height:calc(100dvh - 120px);overflow:auto}
aside h3{font-size:12.5px;margin:0 0 5px}
aside .ax{color:var(--faint);font-size:11px;margin:0 0 8px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:8px;
 padding:8px 10px;margin-bottom:7px}
.card>summary,.card>b{color:var(--accent);font-family:var(--mono);font-size:11px;
 cursor:pointer}
.card .f{font-size:11px;color:var(--dim);margin-top:5px;padding-top:5px;
 border-top:1px solid var(--line)}
.card .lbl{color:var(--faint);font-size:10px;display:block}
.card .pid2{display:inline-block;font-family:var(--mono);font-size:9px;
 color:var(--faint);margin-right:4px}
.empty{background:var(--panel);border:1px dashed var(--line);border-radius:8px;
 padding:18px;color:var(--faint);font-size:12px;text-align:center}
.nm{font-family:var(--mono);font-size:10px;color:var(--faint)}
td.grp{color:var(--faint);font-size:10.5px;white-space:nowrap;width:78px}
"""

JS = """
var D=DATA;
var S={tab:'shared', q:'', pid:'', grp:'', grade:'', hit:'', mdl:0, scp:null,
       page:0, size:25, sel:null, core:true};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function gcls(g){return g==='필수'?'f':g==='권장'?'r':'o';}
function el(id){return document.getElementById(id);}
/* 계열(equipId)로 묶은 드롭다운. 예전엔 e5.rtu 같은 id 를 그대로 늘어놓아
   무엇이 무엇인지 읽히지 않았다 — 계열 이름을 optgroup 으로 세운다. */
function optGrouped(cur,ph){
  var h=ph?'<option value="">'+ph+'</option>':'';
  Object.keys(D.families).forEach(function(eq){
    var ps=D.order.filter(function(p){return D.profiles[p].equipId===eq;});
    if(!ps.length) return;
    h+='<optgroup label="'+esc(eq+'  '+D.families[eq])+'">';
    ps.forEach(function(p){
      var t=D.profiles[p].title.replace(/ — BMS 기본화면$/,'');
      h+='<option value="'+p+'"'+(String(cur)===p?' selected':'')+'>'+esc(t)
        +' · '+D.profiles[p].rows.length+'행</option>';});
    h+='</optgroup>';
  });
  return h;
}
function opt(list,cur,ph){
  return '<option value="">'+ph+'</option>'+list.map(function(x){
    return '<option value="'+esc(x[0])+'"'+(String(cur)===String(x[0])?' selected':'')
      +'>'+esc(x[1])+'</option>';}).join('');}

/* ── 1) 공용 포인트 탭 ─────────────────────────────────────────────── */
function sharedRows(){
  var q=S.q.toLowerCase();
  return D.shared.filter(function(s){
    if(S.core && s.n<3) return false;
    if(S.pid && !s.cols[S.pid]) return false;
    if(S.grp && s.group!==S.grp) return false;
    if(!q) return true;
    return s.canon.toLowerCase().indexOf(q)>=0
      || s.raw.some(function(r){return r[1].toLowerCase().indexOf(q)>=0;});
  });
}
function drawShared(){
  var rows=sharedRows(), page=slice(rows);
  var h='<div class=tw><table><thead><tr><th>묶음</th><th>개념</th>'
    +'<th class="c" title="이 개념을 쓰는 계열 수">계열</th>';
  D.order.forEach(function(pid){
    var pp=D.profiles[pid];
    h+='<th class="pid" title="'+esc(pp.equipId+' '+pp.equipKo)+'">'
      +esc(pid.split('.')[1]||pid)+'<span class="e">'+esc(pp.equipKo.split(' ')[0])
      +'</span></th>';});
  h+='</tr></thead><tbody>';
  page.forEach(function(s,i){
    h+='<tr data-i="'+i+'"'+(S.sel===s.cid?' class="sel"':'')+'>'
      +'<td class="grp">'+esc(s.group)+'</td><td class="k">'
      +esc(s.canon)
      +(s.split?'<span class="g w" title="같은 개념인데 계열마다 이름 표기가 다르다">'
        +'표기 다름</span>':'')+'</td>'
      +'<td class="c y"><b>'+s.n+'</b></td>';
    D.order.forEach(function(pid){
      var g=s.cols[pid];
      var nm=(s.raw.filter(function(r){return r[0]===pid;})[0]||[])[1];
      h+='<td class="c '+(g?'y':'n')+'" title="'+esc(nm||'')+'">'
        +(g?'<b>●</b>'+(nm!==s.canon?'<span class="nm">'+esc(nm)+'</span>':''):'·')+'</td>';
    });
    h+='</tr>';
  });
  h+='</tbody></table></div>'+pager(rows.length);
  el('grid').innerHTML=h;
  bind(page,function(s){S.sel=s.cid;detailShared(s);drawShared();});
  if(!S.sel) detailShared(null);
}
function detailShared(s){
  var h='';
  if(s){
    var by={}; s.raw.forEach(function(r){(by[r[1]]=by[r[1]]||[]).push(r[0]);});
    h+='<div class="card"><b>'+esc(s.canon)+'</b> <span class="nm">'+esc(s.cid)
      +' · '+esc(s.group)+'</span>'
      +'<div class="f"><span class="lbl">계열마다 쓰는 이름</span>'
      +Object.keys(by).map(function(n){return '<code>'+esc(n)+'</code> <span class="nm">'
        +by[n].join(' ')+'</span>';}).join('<br>')+'</div>'
      +(s.split?'<div class="f"><span class="lbl">⚠ 표기가 계열마다 다르다</span>'
        +'같은 개념인데 계열마다 다른 이름으로 적혀 있다. 아직 통일하지 않았다 — '
        +'매칭 규칙이 이름에 매여 있어 함께 손봐야 한다.</div>':'')+'</div>';
  }
  h+='<h3>계산식</h3><p class="ax">각 계열 요구 프로파일의 <code>energyModel</code>. '
    +'템플릿 행의 <b>쓰임</b> 칸이 이 열쇠를 가리킨다.</p>';
  var byk={}; D.calc.forEach(function(c){(byk[c.key]=byk[c.key]||[]).push(c);});
  Object.keys(byk).forEach(function(k){
    h+='<details class="card"><summary>'+esc(k)+' <span class="nm">'+byk[k].length
      +'</span></summary>';
    byk[k].forEach(function(c){
      h+='<div class="f"><span class="pid2">'+esc(c.pid)+'</span>'+esc(c.text)+'</div>';});
    h+='</details>';
  });
  el('side').innerHTML=h;
}

/* ── 2) 템플릿 행 탭 ───────────────────────────────────────────────── */
function curProfile(){ return S.pid || D.order[0]; }
function curScope(){
  var p=D.profiles[curProfile()], m=p.models[S.mdl];
  if(!m||!m.scopes.length) return null;
  var i=(S.scp==null)?m.best:S.scp;
  return m.scopes[Math.min(i,m.scopes.length-1)];
}
function rowRows(){
  var p=D.profiles[curProfile()], sc=curScope(), by={};
  if(sc) sc.map.forEach(function(x){by[x.n]=x;});
  var q=S.q.toLowerCase();
  return p.rows.filter(function(r){
    if(S.grade && r.grade!==S.grade) return false;
    if(S.grp && r.group!==S.grp) return false;
    var g=by[r.name];
    if(S.hit==='y' && !(g&&g.hit)) return false;
    if(S.hit==='n' && (g&&g.hit)) return false;
    if(!q) return true;
    return (r.name+' '+(g&&g.hit||'')+' '+r.why).toLowerCase().indexOf(q)>=0;
  }).map(function(r){return {r:r, g:by[r.name]};});
}
function drawRows(){
  var p=D.profiles[curProfile()];
  if(!p.rows.length){
    el('grid').innerHTML='<div class="empty">이 계열은 행이 아직 없다 — 오른쪽에 사유가 있다.</div>';
    el('side').innerHTML='<div class="card"><b>'+esc(curProfile())+'</b><div class="f">'
      +esc(p.pending||'사유가 안 적혀 있다')+'</div></div>';
    return;
  }
  var rows=rowRows(), page=slice(rows);
  var h='<div class=tw><table><thead><tr><th>묶음</th><th>개념</th><th>종류</th><th>단위</th>'
    +'<th>등급</th><th title="고른 모델·판의 원문에서 이 행에 대응한 이름">'
    +'모델 원문 표기</th></tr></thead><tbody>';
  page.forEach(function(x,i){
    var r=x.r,g=x.g;
    h+='<tr data-i="'+i+'"'+(S.sel===r.name?' class="sel"':'')+'>'
      +'<td class="grp">'+esc(r.group)+'</td>'
      +'<td class="k">'+esc(r.name)+'</td><td class="mono">'+esc(r.objectType)+'</td>'
      +'<td class="mono">'+esc(r.unit)+'</td>'
      +'<td><span class="g '+gcls(r.grade)+'">'+esc(r.grade)+'</span></td>'
      +(g&&g.hit?'<td class="hit" title="'+esc(g.hit)+'">'+esc(g.hit)
          +(g.type?' <span class="nm">'+esc(g.type)+(g.inst!=null?' #'+g.inst:'')+'</span>':'')
          +'</td>'
        :'<td class="miss">— 원문에 없음</td>')+'</tr>';
  });
  h+='</tbody></table></div>'+pager(rows.length);
  el('grid').innerHTML=h;
  bind(page,function(x){S.sel=x.r.name;detailRow(x);drawRows();});
  if(!S.sel||!page.some(function(x){return x.r.name===S.sel;})) detailRow(page[0]||null);
}
function detailRow(x){
  var p=D.profiles[curProfile()], h='';
  if(x){
    var r=x.r;
    h+='<div class="card"><b>'+esc(r.name)+'</b> <span class="nm">'+esc(r.concept)
      +' · '+esc(r.group)+'</span>'
      +'<div class="f"><span class="lbl">왜 필요한가</span>'+esc(r.why)+'</div>'
      +'<div class="f"><span class="lbl">쓰임</span><code>'
        +esc((r.usedBy||[]).join(' ')||'—')+'</code></div>'
      +(r.haystack
        ?'<div class="f"><span class="lbl">Haystack 근거</span>'+esc(r.haystack)+'</div>'
        :'<div class="f"><span class="lbl">표준 proto 없음</span>'
          +esc(r.handMade||'사유가 안 적혀 있다 — 채워야 한다')+'</div>')
      +(r.exposure?'<div class="f"><span class="lbl">실측 노출</span>'
        +esc(r.exposure)+'</div>':'')
      +'<div class="f"><span class="lbl">매칭 규칙</span><code>include '+esc(r.include)
        +(r.exclude?'<br>exclude '+esc(r.exclude):'')+'</code></div>'
      +(r.matchNote?'<div class="f"><span class="lbl">주의</span>'+esc(r.matchNote)+'</div>':'')
      +(r.appliesWhen?'<div class="f"><span class="lbl">적용 조건</span>'
        +esc(r.appliesWhen)+'</div>':'')
      +'</div>';
  }
  var tot=p.rows.length;
  h+='<h3>모델별 덮개</h3><div class="card">';
  p.models.slice().sort(function(a,b){return b.any.length-a.any.length;})
   .forEach(function(m,i){
    h+='<div class="f"><span class="pid2">'+m.any.length+'/'+tot+'</span>'+esc(m.short)
      +'</div>';});
  if(!p.models.length) h+='<div class="f">붙는 모델이 아직 없다</div>';
  h+='</div>';
  var none=p.rows.filter(function(r){
    return !p.models.some(function(m){return m.any.indexOf(r.name)>=0;});});
  h+='<h3>아무 모델도 안 내주는 행 — '+none.length+'/'+tot+'</h3><div class="card">'
    +(none.length?none.map(function(r){return '<div class="f">'+esc(r.name)+'</div>';}).join('')
      :'<div class="f">없다. 모든 행을 최소 한 모델이 낸다.</div>')+'</div>';
  if(p.coverageNote) h+='<div class="card"><b>덮개 메모</b><div class="f">'
    +esc(p.coverageNote)+'</div></div>';
  el('side').innerHTML=h;
}

/* ── 공통: 페이징 · 필터 바 ────────────────────────────────────────── */
function slice(rows){
  var n=S.size==='all'?rows.length:+S.size;
  var max=Math.max(0,Math.ceil(rows.length/n)-1);
  if(S.page>max) S.page=max;
  return S.size==='all'?rows:rows.slice(S.page*n,(S.page+1)*n);
}
function pager(total){
  var n=S.size==='all'?total:+S.size;
  var pages=Math.max(1,Math.ceil(total/n)), from=total?S.page*n+1:0;
  var to=Math.min(total,(S.page+1)*n);
  return '<div class="pager"><span class="pos">'+from+'–'+to+' / '+total+'</span>'
    +'<button id="pp"'+(S.page<=0?' disabled':'')+'>‹</button>'
    +'<span class="pos">'+(S.page+1)+' / '+pages+'</span>'
    +'<button id="pn"'+(S.page>=pages-1?' disabled':'')+'>›</button>'
    +'<select id="ps">'+[25,50,100].map(function(v){
       return '<option'+(String(S.size)===String(v)?' selected':'')+'>'+v+'</option>';})
       .join('')+'<option value="all"'+(S.size==='all'?' selected':'')+'>전체</option>'
    +'</select><span>행</span></div>';
}
function bind(page,pick){
  [].forEach.call(document.querySelectorAll('#grid tbody tr'),function(tr){
    tr.onclick=function(){pick(page[+tr.dataset.i]);};});
  var pp=el('pp'),pn=el('pn'),ps=el('ps');
  if(pp) pp.onclick=function(){S.page--;draw();};
  if(pn) pn.onclick=function(){S.page++;draw();};
  if(ps) ps.onchange=function(){S.size=ps.value;S.page=0;draw();};
}
/* ⚠ 함수 이름을 top 으로 두면 안 된다 — 브라우저에서 window.top 은 **읽기 전용
   전역**이라 덮이지 않고, 호출하는 순간 'top is not a function' 으로 죽는다.
   페이지가 통째로 안 열렸다. node 검사에는 window.top 이 없어 통과했다. */
function drawBar(){
  var h='<div class="tabs"><span class="brand">템플릿 검사대</span>'
    +'<button data-t="shared" aria-current="'+(S.tab==='shared')+'">공용 포인트</button>'
    +'<button data-t="rows" aria-current="'+(S.tab==='rows')+'">템플릿 행</button></div>';
  h+='<div class="bar"><input id="q" placeholder="개념·포인트 이름 검색" value="'
    +esc(S.q)+'">'
    +'<select id="fgr">'+opt(D.groups.map(function(g){return [g,g];}),S.grp,'전 묶음')
    +'</select>';
  if(S.tab==='shared'){
    h+='<select id="fp">'+optGrouped(S.pid,'전 계열')+'</select>'
      +'<button class="chip" id="fc" aria-pressed="'+S.core+'">계열 3개 이상만</button>';
  }else{
    h+='<select id="fp">'+optGrouped(curProfile(),null)+'</select>';
    var p=D.profiles[curProfile()];
    if(p.models.length){
      h+='<select id="fm">'+p.models.map(function(m,i){
        return '<option value="'+i+'" title="'+esc(m.name)+'"'
          +(S.mdl===i?' selected':'')+'>'+esc(m.short)
          +'</option>';}).join('')+'</select>';
      var m=p.models[S.mdl], sc=curScope();
      if(m&&m.scopes.length>1) h+='<select id="fs">'+m.scopes.map(function(s,i){
        var n=s.map.filter(function(x){return x.hit;}).length;
        return '<option value="'+i+'"'+(sc===s?' selected':'')+'>'+esc(s.label)+' '
          +n+'/'+p.rows.length+'</option>';}).join('')+'</select>';
    }
    h+='<select id="fg">'+opt([['필수','필수'],['권장','권장'],['선택','선택']],
        S.grade,'전 등급')+'</select>'
      +'<select id="fh">'+opt([['y','원문에 있는 것만'],['n','원문에 없는 것만']],
        S.hit,'원문 대응 무관')
      +'</select>';
  }
  h+='<span class="sp"></span><span class="cnt" id="cnt"></span></div>';
  el('top').innerHTML=h;
  [].forEach.call(document.querySelectorAll('.tabs button'),function(b){
    b.onclick=function(){S.tab=b.dataset.t;S.page=0;S.sel=null;
      if(S.tab==='rows'&&!D.profiles[S.pid]) S.pid=D.order[0];
      if(S.tab==='shared') S.pid='';
      render();};});
  var q=el('q');
  q.oninput=function(){S.q=q.value;S.page=0;draw();cnt();};
  var fp=el('fp'); if(fp) fp.onchange=function(){S.pid=fp.value;S.page=0;S.mdl=0;
    S.scp=null;S.sel=null;render();};
  var fgr=el('fgr'); if(fgr) fgr.onchange=function(){S.grp=fgr.value;S.page=0;draw();cnt();};
  var fc=el('fc'); if(fc) fc.onclick=function(){S.core=!S.core;S.page=0;render();};
  var fm=el('fm'); if(fm) fm.onchange=function(){S.mdl=+fm.value;S.scp=null;render();};
  var fs=el('fs'); if(fs) fs.onchange=function(){S.scp=+fs.value;draw();cnt();};
  var fg=el('fg'); if(fg) fg.onchange=function(){S.grade=fg.value;S.page=0;draw();cnt();};
  var fh=el('fh'); if(fh) fh.onchange=function(){S.hit=fh.value;S.page=0;draw();cnt();};
}
function cnt(){
  var t=el('cnt'); if(!t) return;
  if(S.tab==='shared'){
    t.innerHTML='공용 개념 <b>'+sharedRows().length+'</b> / '+D.shared.length;
  }else{
    var p=D.profiles[curProfile()], sc=curScope();
    var n=sc?sc.map.filter(function(x){return x.hit;}).length:0;
    t.innerHTML='붙은 행 <b>'+n+'</b> / '+p.rows.length;
  }
}
function draw(){ S.tab==='shared'?drawShared():drawRows(); }
function render(){ drawBar(); draw(); cnt(); }
render();
"""


# 브라우저 전역과 부딪히면 안 되는 이름. window 의 이 속성들은 **읽기 전용**이라
# 같은 이름 함수를 만들어도 덮이지 않고, 호출하는 순간 죽는다.
# 실제로 `function top()` 하나 때문에 페이지가 통째로 안 열렸다 —
# node 로 돌린 검사는 window.top 이 없어 그냥 통과했다.
WINDOW_RESERVED = {
    "top", "parent", "self", "window", "frames", "length", "name", "status",
    "location", "history", "origin", "closed", "document", "navigator", "screen",
    "opener", "external", "print", "close", "open", "focus", "blur", "stop",
}


def check_globals(js):
    """JS 전역 함수·변수 이름이 브라우저 전역과 부딪히나 — 빌드 때마다 본다."""
    import re as _re
    bad = sorted({m for m in _re.findall(r"^function\s+([A-Za-z_$][\w$]*)\s*\(",
                                         js, _re.M)} & WINDOW_RESERVED)
    bad += sorted({m for m in _re.findall(r"^var\s+([A-Za-z_$][\w$]*)", js, _re.M)}
                  & WINDOW_RESERVED)
    if bad:
        raise SystemExit("브라우저 전역과 부딪히는 이름이다(페이지가 안 열린다): %s"
                         % ", ".join(bad))
    return len(bad)


def build():
    tpl = json.load(io.open(os.path.join(DATA, "equip-templates.json"),
                            encoding="utf-8"))["profiles"]
    req = json.load(io.open(os.path.join(DATA, "equip-requirements.json"),
                            encoding="utf-8"))["profiles"]
    # ⚠ 이 파일은 **미리 구운 것**이다(datasets.py 가 만든다). 라이브 계산이 아니라
    #   템플릿을 고쳐도 여기를 다시 안 구우면 화면이 조용히 옛 결과를 보여 준다.
    #   실제로 그랬다 — 매칭을 하루 종일 고치고 "덮개가 늘었다" 고 보고했는데
    #   화면의 모델별 덮개는 **사흘 전 것**이었다. 측정 스크립트로만 확인하고
    #   화면으로 확인하지 않아서 생긴 일이다(AGENTS 규칙 4).
    mmp = os.path.join(DATA, "datasets", "model-mappings.json")
    src = [os.path.join(DATA, "equip-templates.json"),
           os.path.join(DATA, "equip-requirements.json"),
           os.path.join(DATA, "point-concepts.json")]
    src += glob.glob(os.path.join(DATA, "models", "*.json"))
    newer = [f for f in src
             if os.path.exists(f) and os.path.getmtime(f) > os.path.getmtime(mmp)]
    if newer:
        raise SystemExit(
            "매칭 결과가 낡았다 — %s 보다 새 파일이 %d개 있다(예: %s). "
            "먼저 다시 구워라:  PYTHONIOENCODING=utf-8 python datasets.py"
            % (os.path.basename(mmp), len(newer),
               os.path.basename(sorted(newer, key=os.path.getmtime)[-1])))
    mm = json.load(io.open(mmp, encoding="utf-8"))
    cdoc = json.load(io.open(os.path.join(DATA, "point-concepts.json"),
                             encoding="utf-8"))
    concepts = cdoc["concepts"]

    per = collections.defaultdict(list)
    for mid, m in mm.items():
        pid = m.get("templateProfileId")
        if pid:
            per[pid].append((mid, m))

    profiles = collections.OrderedDict()
    for pid in sorted(tpl):
        p, rq = tpl[pid], req.get(pid) or {}
        rows = []
        for r in p.get("templatePoints") or []:
            mt = r.get("match") or {}
            rows.append({
                "name": r.get("name"), "objectType": r.get("objectType"),
                "unit": r.get("unit"), "grade": r.get("grade"),
                "why": r.get("why") or "", "usedBy": r.get("usedBy") or [],
                "haystack": r.get("haystack") or "", "appliesWhen": r.get("appliesWhen"),
                # ⚠ 근거 두 칸을 화면에 올린다. 데이터에만 적어 두었더니 모델이 0건인
                #   계열(냉각탑·보일러·열교환기·급배수·외조기 88행)의 행을 **볼 수는
                #   있는데 어디서 왔는지 확인할 길이 없었다.** 지어내지 않았다는 것을
                #   보이는 것이 이 화면의 일이다.
                "handMade": r.get("handMade") or "", "exposure": r.get("exposure") or "",
                "concept": r.get("concept") or "", "group": r.get("group") or "기타",
                "include": mt.get("include") or "", "exclude": mt.get("exclude") or "",
                "matchNote": r.get("matchNote") or "",
            })
        models = []
        for mid, m in sorted(per.get(pid, [])):
            scopes, any_hit = [], set()
            cands = list(m.get("interfaceMappings") or [])
            if not cands:
                cands = [{"interfaceId": None,
                          "templatePointMappings": m.get("templatePointMappings") or []}]
            for s in cands:
                mp = []
                for x in s.get("templatePointMappings") or []:
                    hit = x.get("matchedPoint") or None
                    if hit:
                        any_hit.add(x["templateName"])
                    mp.append({"n": x["templateName"],
                               "hit": (hit or {}).get("name"),
                               "type": (hit or {}).get("type"),
                               "inst": (hit or {}).get("instance")})
                scopes.append({"label": s.get("interfaceId") or "평면(옛 추출본)",
                               "map": mp})
            best = max(range(len(scopes)),
                       key=lambda i: sum(1 for x in scopes[i]["map"] if x["hit"])) \
                if scopes else 0
            models.append({
                "id": mid, "name": "%s — %s" % (m.get("vendor") or "", m.get("name") or mid),
                # ⚠ 자르지 않는다. 22자에서 자르니 'YKL Compact Low Profil' 이 되어
                #   어느 모델인지 알 수가 없었다. 고르는 칸에서 이름은 곧 신원이다.
                "short": (m.get("model") or mid),
                "scopes": scopes, "best": best, "any": sorted(any_hit)})
        profiles[pid] = {
            "title": p.get("title") or pid, "basis": p.get("basis") or "",
            "pending": p.get("pending") or "", "coverageNote": p.get("coverageNote") or "",
            "energyModel": rq.get("energyModel") or {},
            "rows": rows, "models": models,
        }

    order = sorted(profiles, key=lambda k: (-len(profiles[k]["rows"]), k))

    # ── 개요: 공용 포인트는 사전에서 바로 나온다 (묶는 판단이 데이터에 있다) ──
    used = collections.defaultdict(dict)      # cid → {pid: 등급}
    naming = collections.defaultdict(dict)    # cid → {pid: 그 계열의 표기}
    for pid, p in profiles.items():
        for r in p["rows"]:
            if not r["concept"]:
                continue
            used[r["concept"]][pid] = r["grade"]
            naming[r["concept"]][pid] = r["name"]
    shared = []
    for cid, c in concepts.items():
        cols = used.get(cid) or {}
        if not cols:
            continue
        names = naming.get(cid) or {}
        shared.append({"canon": c["ko"], "cid": cid, "group": c.get("group") or "기타",
                       "cols": cols, "raw": sorted(names.items()),
                       "n": len(cols),
                       "split": len(set(names.values())) > 1,
                       "haystack": c.get("haystack") or ""})
    shared.sort(key=lambda x: (-x["n"], x["group"], x["canon"]))

    calc = []
    for pid in order:
        for k, v in (profiles[pid]["energyModel"] or {}).items():
            calc.append({"pid": pid, "key": k, "text": v})

    fam = equip_names()
    for pid, pr in profiles.items():
        eq = pid.split(".")[0]
        pr["equipId"] = eq
        pr["equipKo"] = fam.get(eq, eq)
    data = {"order": order, "profiles": profiles,
            "families": collections.OrderedDict(
                (eq, fam.get(eq, eq)) for eq in
                sorted({pid.split(".")[0] for pid in profiles},
                       key=lambda x: int(x[1:]))),
            "shared": shared, "calc": calc,
            "groups": cdoc.get("groups") or [],
            "split": [s for s in shared if s["split"]]}
    nrow = sum(len(v["rows"]) for v in profiles.values())
    nmdl = sum(len(v["models"]) for v in profiles.values())

    check_globals(JS)
    html = ("<!doctype html><html lang=ko><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>BMS 기본화면 템플릿 검사대</title><style>%s</style>"
            "<div class=wrap>"
            "<div class=top id=top></div>"
            "<div class=split><div id=grid></div><aside id=side></aside></div></div>"
            "<script>var DATA=%s;\n%s</script></html>"
            % (CSS, json.dumps(data, ensure_ascii=False), JS))
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("→ %s  (%.2f MB · 프로파일 %d · 행 %d · 모델 %d)"
          % (os.path.relpath(OUT, HERE), len(html.encode("utf-8")) / 1e6,
             len(profiles), nrow, nmdl))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
