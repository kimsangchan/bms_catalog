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
  ② 모델과 판을 고르면 각 행에 **실제로 붙은 포인트 이름**이 채워진다
  ③ 덮개 표 — 모델 × 행 격자. 어느 행을 아무 모델도 안 내주는지 한눈에 본다

읽는 데이터 (화면이 목록을 정하지 않는다 — 데이터가 정한다)
  data/equip-templates.json      템플릿 행
  data/equip-requirements.json   계산식(energyModel)과 요구 항목
  data/datasets/model-mappings.json  모델·판별 매칭 결과
"""
import collections
import io
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "..", "review", "template-map.html")

# 공용 포인트를 세려면 같은 개념의 다른 이름을 먼저 묶어야 한다.
# ⚠ 이건 **판단**이다 — 그래서 묶은 것과 원래 이름을 화면에 함께 보여 준다.
#   묶어 보니 이름이 프로파일마다 갈려 있다는 사실 자체가 드러났다(아래 '이름 통일 후보').
#   표기를 함부로 바꾸지 않은 이유: 행 순서와 match 규칙이 이름에 매여 있다(D-016 과 같은 결).
CANON = {
    "운전/정지 지령": ["운전/정지 지령", "기동/정지 지령"],
    "운전 상태": ["운전 상태"],
    "고장·경보": ["고장·경보", "트립·고장", "인버터 경보"],
    "고장 코드": ["에러 코드", "트립 코드"],
    "실내온도": ["실내온도"],
    "외기온도": ["외기온도"],
    "급기(토출) 온도": ["급기온도", "급기(토출) 온도"],
    "환기(리턴) 온도": ["환기온도", "환기(리턴) 온도"],
    "운전 모드": ["운전 모드"],
    "속도·주파수 지령": ["급기팬 주파수 지령", "환기팬 주파수 지령", "주파수 지령",
                  "풍량 단계"],
    "속도·주파수 실측": ["현재 주파수", "회전수", "인버터 출력"],
    "필터 차압·신호": ["필터 차압", "필터 청소 신호"],
    "소비전력": ["출력 전력", "소비전력"],
    "적산 전력량": ["적산 전력량"],
    "누적 운전시간": ["누적 운전시간"],
    "출력 전류": ["출력 전류"],
    "DC 링크 전압": ["DC 링크 전압"],
    "모듈·방열판 온도": ["모듈 온도", "방열판 온도"],
}

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
.tabs{display:flex;gap:4px;margin-bottom:8px}
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
td.k{font-weight:600;white-space:nowrap;max-width:230px;overflow:hidden;
 text-overflow:ellipsis}
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
"""

JS = """
var D=DATA;
var S={tab:'shared', q:'', pid:'', grade:'', hit:'', mdl:0, scp:null,
       page:0, size:25, sel:null, core:true};
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function gcls(g){return g==='필수'?'f':g==='권장'?'r':'o';}
function el(id){return document.getElementById(id);}
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
    if(!q) return true;
    return s.canon.toLowerCase().indexOf(q)>=0
      || s.raw.some(function(r){return r[1].toLowerCase().indexOf(q)>=0;});
  });
}
function drawShared(){
  var rows=sharedRows(), page=slice(rows);
  var h='<table><thead><tr><th>개념</th>';
  D.order.forEach(function(pid){h+='<th class="pid">'
    +esc(pid.split('.')[1]||pid)+'<span class="e">'+esc(pid.split('.')[0])+'</span></th>';});
  h+='<th>계열</th></tr></thead><tbody>';
  page.forEach(function(s,i){
    h+='<tr data-i="'+i+'"'+(S.sel===s.canon?' class="sel"':'')+'><td class="k">'
      +esc(s.canon)+(s.split?'<span class="g w">갈림</span>':'')+'</td>';
    D.order.forEach(function(pid){
      var g=s.cols[pid];
      var nm=(s.raw.filter(function(r){return r[0]===pid;})[0]||[])[1];
      h+='<td class="c '+(g?'y':'n')+'" title="'+esc(nm||'')+'">'
        +(g?'<b>●</b>'+(nm!==s.canon?'<span class="nm">'+esc(nm)+'</span>':''):'·')+'</td>';
    });
    h+='<td class="c y"><b>'+s.n+'</b></td></tr>';
  });
  h+='</tbody></table>'+pager(rows.length);
  el('grid').innerHTML=h;
  bind(page,function(s){S.sel=s.canon;detailShared(s);drawShared();});
  if(!S.sel) detailShared(null);
}
function detailShared(s){
  var h='';
  if(s){
    var by={}; s.raw.forEach(function(r){(by[r[1]]=by[r[1]]||[]).push(r[0]);});
    h+='<div class="card"><b>'+esc(s.canon)+'</b>'
      +'<div class="f"><span class="lbl">계열마다 쓰는 이름</span>'
      +Object.keys(by).map(function(n){return '<code>'+esc(n)+'</code> <span class="nm">'
        +by[n].join(' ')+'</span>';}).join('<br>')+'</div>'
      +(s.split?'<div class="f"><span class="lbl">⚠ 이름 갈림</span>표기를 아직 안 바꿨다 — '
        +'행 순서와 매칭 규칙이 이름에 매여 있어 함께 손봐야 한다.</div>':'')+'</div>';
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
  var h='<table><thead><tr><th>개념</th><th>종류</th><th>단위</th><th>등급</th>'
    +'<th>붙은 포인트</th></tr></thead><tbody>';
  page.forEach(function(x,i){
    var r=x.r,g=x.g;
    h+='<tr data-i="'+i+'"'+(S.sel===r.name?' class="sel"':'')+'>'
      +'<td class="k">'+esc(r.name)+'</td><td class="mono">'+esc(r.objectType)+'</td>'
      +'<td class="mono">'+esc(r.unit)+'</td>'
      +'<td><span class="g '+gcls(r.grade)+'">'+esc(r.grade)+'</span></td>'
      +(g&&g.hit?'<td class="hit" title="'+esc(g.hit)+'">'+esc(g.hit)
          +(g.type?' <span class="nm">'+esc(g.type)+(g.inst!=null?' #'+g.inst:'')+'</span>':'')
          +'</td>'
        :'<td class="miss">— 이 판에 없다</td>')+'</tr>';
  });
  h+='</tbody></table>'+pager(rows.length);
  el('grid').innerHTML=h;
  bind(page,function(x){S.sel=x.r.name;detailRow(x);drawRows();});
  if(!S.sel||!page.some(function(x){return x.r.name===S.sel;})) detailRow(page[0]||null);
}
function detailRow(x){
  var p=D.profiles[curProfile()], h='';
  if(x){
    var r=x.r;
    h+='<div class="card"><b>'+esc(r.name)+'</b>'
      +'<div class="f"><span class="lbl">왜 필요한가</span>'+esc(r.why)+'</div>'
      +'<div class="f"><span class="lbl">쓰임</span><code>'
        +esc((r.usedBy||[]).join(' ')||'—')+'</code></div>'
      +'<div class="f"><span class="lbl">Haystack 근거</span>'+esc(r.haystack||'—')+'</div>'
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
function top(){
  var h='<div class="tabs">'
    +'<button data-t="shared" aria-current="'+(S.tab==='shared')+'">공용 포인트</button>'
    +'<button data-t="rows" aria-current="'+(S.tab==='rows')+'">템플릿 행</button></div>';
  h+='<div class="bar"><input id="q" placeholder="개념·포인트 이름 검색" value="'
    +esc(S.q)+'">';
  if(S.tab==='shared'){
    h+='<select id="fp">'+opt(D.order.map(function(p){return [p,p];}),S.pid,'전 계열')
      +'</select>'
      +'<button class="chip" id="fc" aria-pressed="'+S.core+'">계열 3개 이상만</button>';
  }else{
    h+='<select id="fp">'+D.order.map(function(p){
        return '<option value="'+p+'"'+(curProfile()===p?' selected':'')+'>'
          +esc(D.profiles[p].title)+' ('+D.profiles[p].rows.length+')</option>';}).join('')
      +'</select>';
    var p=D.profiles[curProfile()];
    if(p.models.length){
      h+='<select id="fm">'+p.models.map(function(m,i){
        return '<option value="'+i+'"'+(S.mdl===i?' selected':'')+'>'+esc(m.short)
          +'</option>';}).join('')+'</select>';
      var m=p.models[S.mdl], sc=curScope();
      if(m&&m.scopes.length>1) h+='<select id="fs">'+m.scopes.map(function(s,i){
        var n=s.map.filter(function(x){return x.hit;}).length;
        return '<option value="'+i+'"'+(sc===s?' selected':'')+'>'+esc(s.label)+' '
          +n+'/'+p.rows.length+'</option>';}).join('')+'</select>';
    }
    h+='<select id="fg">'+opt([['필수','필수'],['권장','권장'],['선택','선택']],
        S.grade,'전 등급')+'</select>'
      +'<select id="fh">'+opt([['y','붙은 것만'],['n','안 붙은 것만']],S.hit,'붙음 무관')
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
function render(){ top(); draw(); cnt(); }
render();
"""


def build():
    tpl = json.load(io.open(os.path.join(DATA, "equip-templates.json"),
                            encoding="utf-8"))["profiles"]
    req = json.load(io.open(os.path.join(DATA, "equip-requirements.json"),
                            encoding="utf-8"))["profiles"]
    mm = json.load(io.open(os.path.join(DATA, "datasets", "model-mappings.json"),
                           encoding="utf-8"))

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
                "short": (m.get("model") or mid)[:22],
                "scopes": scopes, "best": best, "any": sorted(any_hit)})
        profiles[pid] = {
            "title": p.get("title") or pid, "basis": p.get("basis") or "",
            "pending": p.get("pending") or "", "coverageNote": p.get("coverageNote") or "",
            "energyModel": rq.get("energyModel") or {},
            "rows": rows, "models": models,
        }

    order = sorted(profiles, key=lambda k: (-len(profiles[k]["rows"]), k))

    # ── 개요: 공용 포인트 ────────────────────────────────────────────────
    where = collections.defaultdict(dict)      # 원래이름 → {pid: 등급}
    for pid, p in profiles.items():
        for r in p["rows"]:
            where[r["name"]][pid] = r["grade"]
    seen = set()
    shared = []
    for canon, names in CANON.items():
        cols, raw = {}, []
        for n in names:
            for pid, g in where.get(n, {}).items():
                cols[pid] = g
                raw.append((pid, n))
            seen.add(n)
        if cols:
            shared.append({"canon": canon, "cols": cols, "raw": raw,
                           "n": len(cols),
                           "split": len({n for _p, n in raw}) > 1})
    shared.sort(key=lambda x: (-x["n"], x["canon"]))
    solo = []
    for name, cols in sorted(where.items()):
        if name not in seen and len(cols) > 1:
            solo.append({"canon": name, "cols": cols,
                         "raw": [(p, name) for p in cols],
                         "n": len(cols), "split": False})
    solo.sort(key=lambda x: (-x["n"], x["canon"]))

    calc = []
    for pid in order:
        for k, v in (profiles[pid]["energyModel"] or {}).items():
            calc.append({"pid": pid, "key": k, "text": v})

    data = {"order": order, "profiles": profiles,
            "shared": shared + solo, "calc": calc,
            "split": [s for s in shared if s["split"]]}
    nrow = sum(len(v["rows"]) for v in profiles.values())
    nmdl = sum(len(v["models"]) for v in profiles.values())

    html = ("<!doctype html><html lang=ko><meta charset=utf-8>"
            "<meta name=viewport content='width=device-width,initial-scale=1'>"
            "<title>BMS 기본화면 템플릿 검사대</title><style>%s</style>"
            "<div class=wrap><h1>BMS 기본화면 템플릿 검사대</h1>"
            "<p class=sub>화면이 목록을 정하지 않는다 — <code>equip-templates.json</code> · "
            "<code>equip-requirements.json</code> · <code>model-mappings.json</code> 을 "
            "그대로 보여 준다. 프로파일 %d · 템플릿 행 %d · 붙는 모델 %d</p>"
            "<div class=top id=top></div>"
            "<div class=split><div id=grid></div><aside id=side></aside></div></div>"
            "<script>var DATA=%s;\n%s</script></html>"
            % (CSS, len(profiles), nrow, nmdl,
               json.dumps(data, ensure_ascii=False), JS))
    with io.open(OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("→ %s  (%.2f MB · 프로파일 %d · 행 %d · 모델 %d)"
          % (os.path.relpath(OUT, HERE), len(html.encode("utf-8")) / 1e6,
             len(profiles), nrow, nmdl))
    return 0


if __name__ == "__main__":
    raise SystemExit(build())
