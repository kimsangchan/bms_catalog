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
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.6 var(--ui)}
.wrap{max-width:1420px;margin:0 auto;padding:24px 20px 70px}
h1{font-size:21px;margin:0 0 3px}
.sub{color:var(--faint);font-size:12.5px;margin-bottom:16px}
.n{display:flex;gap:7px;flex-wrap:wrap;margin-bottom:18px}
.n span{background:var(--panel);border:1px solid var(--line);border-radius:999px;
 padding:3px 11px;font-size:12px;color:var(--dim)}
.n b{color:var(--accent);font-family:var(--mono);font-variant-numeric:tabular-nums}
.cols{display:grid;grid-template-columns:210px minmax(0,1fr);gap:18px;align-items:start}
@media(max-width:900px){.cols{grid-template-columns:1fr}}
.rail{position:sticky;top:14px}
.rail button{display:block;width:100%;text-align:left;background:var(--panel);
 border:1px solid var(--line);border-radius:8px;padding:7px 10px;margin-bottom:5px;
 color:var(--ink);font:12.5px/1.35 var(--ui);cursor:pointer}
.rail button:hover{border-color:var(--accent)}
.rail button[aria-current=true]{border-color:var(--accent);background:var(--soft)}
.rail .m{display:block;color:var(--faint);font-family:var(--mono);font-size:10.5px;
 font-variant-numeric:tabular-nums}
.head{background:var(--panel);border:1px solid var(--line);border-radius:10px;
 padding:12px 14px;margin-bottom:12px}
.head h2{font-size:15px;margin:0 0 6px}
.head p{margin:0 0 6px;color:var(--dim);font-size:12.5px}
.head .warn{color:var(--warn)}
.calc{border-top:1px solid var(--line);margin-top:8px;padding-top:8px}
.calc div{font-size:12px;color:var(--dim);margin-bottom:3px}
.calc b{color:var(--accent);font-family:var(--mono);font-size:11px}
.pick{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:10px}
.pick select{background:var(--panel);color:var(--ink);border:1px solid var(--line);
 border-radius:7px;padding:5px 8px;font:12.5px var(--ui);max-width:420px}
.pick .cov{font-family:var(--mono);font-size:12px;color:var(--dim);
 font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--panel);
 border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:6px 9px;text-align:left;border-bottom:1px solid var(--line);
 vertical-align:top}
th{background:var(--soft);font-weight:600;font-size:11.5px;white-space:nowrap}
tr:last-child td{border-bottom:0}
td.k{font-weight:600;white-space:nowrap}
td.mono,td.num{font-family:var(--mono);font-size:11.5px;
 font-variant-numeric:tabular-nums}
td.d{color:var(--dim);font-size:12px}
td.hit{font-family:var(--mono);font-size:11.5px;color:var(--ok);word-break:break-all}
td.miss{color:var(--faint);font-size:11.5px}
.g{display:inline-block;border-radius:999px;padding:1px 7px;font-size:10.5px;
 border:1px solid var(--line);white-space:nowrap}
.g.f{color:var(--bad);border-color:var(--bad)}
.g.r{color:var(--accent);border-color:var(--accent)}
.g.o{color:var(--faint)}
details{margin-top:3px}
summary{cursor:pointer;color:var(--faint);font-size:11px}
code{font-family:var(--mono);font-size:11px;color:var(--dim);word-break:break-all}
.matrix{overflow:auto;margin-top:14px}
.matrix table{font-size:11.5px}
h3.mh{font-size:12.5px;margin:16px 0 7px;color:var(--dim)}
p.ax{color:var(--faint);font-size:11.5px;margin:0 0 10px}
table.cov2 td{vertical-align:middle}
table.cov2 td.k{max-width:420px;white-space:normal;font-weight:500}
table.cov2 td.bar{width:38%;padding:6px 9px}
table.cov2 td.bar span{display:block;height:7px;border-radius:4px;
 background:var(--accent);min-width:2px}
table.cov2 td.num{font-family:var(--mono);font-size:11.5px;text-align:right;
 font-variant-numeric:tabular-nums;white-space:nowrap;color:var(--dim)}
table.cov2 td.pct{color:var(--ink);width:52px}
.empty{background:var(--panel);border:1px dashed var(--line);border-radius:10px;
 padding:22px;color:var(--faint);font-size:12.5px;text-align:center}
.rail .sep{color:var(--faint);font-size:10.5px;margin:12px 0 5px 2px;
 text-transform:uppercase;letter-spacing:.06em}
/* 개요 — 본문 + 계산식 사이드. 좁아지면 사이드가 아래로 내려간다 */
.ov{display:grid;grid-template-columns:minmax(0,1fr) 310px;gap:16px;align-items:start}
@media(max-width:1080px){.ov{grid-template-columns:1fr}}
.ov th.pid{font-family:var(--mono);font-size:10.5px;font-weight:500;
 padding:8px 5px;text-align:center;white-space:nowrap}
.ov td.c{text-align:center;font-family:var(--mono);line-height:1.25}
.ov td.c.y b{color:var(--ok);font-size:13px}
.ov td.c.n{color:var(--line)}
.ov td.c .nm{display:block;font-size:9.5px;color:var(--faint);max-width:74px;
 margin:0 auto;word-break:keep-all}
.ov td.c b{font-variant-numeric:tabular-nums}
.g.w{color:var(--warn);border-color:var(--warn)}
.ov tr.core td{background:var(--soft)}
.ov tr.core td.k{font-weight:700}
aside{position:sticky;top:14px}
aside h3{font-size:13px;margin:0 0 6px}
aside .ax{color:var(--faint);font-size:11.5px;margin:0 0 10px}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;
 padding:9px 11px;margin-bottom:8px}
.card>b{color:var(--accent);font-family:var(--mono);font-size:11.5px}
.card .f{font-size:11.5px;color:var(--dim);margin-top:5px;padding-top:5px;
 border-top:1px solid var(--line)}
.card .f:first-of-type{border-top:0;padding-top:0}
.card .pid{display:inline-block;font-family:var(--mono);font-size:9.5px;
 color:var(--faint);margin-right:5px}
"""

JS = """
var D=DATA, cur=null;
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function gcls(g){return g==='필수'?'f':g==='권장'?'r':'o';}

function rail(){
  var h='<button data-pid="_" aria-current="'+(cur==='_')+'">개요 — 공용 포인트'
    +'<span class="m">개념 '+D.shared.length+' · 계산식 '+D.calc.length+'</span></button>'
    +'<div class="sep">계열별 화면</div>';
  D.order.forEach(function(pid){
    var p=D.profiles[pid];
    h+='<button data-pid="'+pid+'" aria-current="'+(pid===cur)+'">'+esc(p.title)
      +'<span class="m">'+pid+' · '+p.rows.length+'행 · 모델 '+p.models.length+'</span></button>';
  });
  document.getElementById('rail').innerHTML=h;
  [].forEach.call(document.querySelectorAll('#rail button'),function(b){
    b.onclick=function(){cur=b.dataset.pid;rail();
      window.scrollTo(0,0); cur==='_'?overview():body();};});
}

/* 개요 — 계열을 가로질러 되풀이되는 개념을 한 화면에. 옆에 계산식을 붙인다. */
function overview(){
  var el=document.getElementById('body');
  var h='<div class="ov">';

  h+='<div><div class="head"><h2>공용 포인트 — 계열을 가로질러 되풀이되는 개념</h2>'
    +'<p>같은 개념이 여러 계열에 나온다. <b>그래서 화면은 모델을 몰라도 설계된다</b> — '
    +'모델은 주소를 붙일 때만 필요하다. 아래 표의 ● 은 그 계열 템플릿에 그 개념이 '
    +'있다는 뜻이고, 칸에 뜨는 글자는 <b>그 계열이 실제로 쓰는 이름</b>이다.</p>'
    +'<p class="ax">⚠ <code>e5.rtu</code> 와 <code>e5.ahu</code> 는 같은 계열의 형제라 '
    +'둘만 겹치는 것은 당연하다. <b>계열 3개 이상</b>에 나오는 개념(굵게)이 진짜 공용이다.</p></div>';
  h+='<table><thead><tr><th>개념</th>';
  D.order.forEach(function(pid){h+='<th class="pid">'+esc(pid)+'</th>';});
  h+='<th>계열</th></tr></thead><tbody>';
  D.shared.forEach(function(s){
    h+='<tr'+(s.n>=3?' class="core"':'')+'><td class="k">'+esc(s.canon)
      +(s.split?' <span class="g w" title="계열마다 이름이 다르다">이름 갈림</span>':'')
      +'</td>';
    D.order.forEach(function(pid){
      var g=s.cols[pid];
      var nm=(s.raw.filter(function(r){return r[0]===pid;})[0]||[])[1];
      h+='<td class="c '+(g?'y':'n')+'" title="'+esc(nm||'')+'">'
        +(g?'<b>●</b><span class="nm">'+esc(nm===s.canon?'':nm)+'</span>':'·')+'</td>';
    });
    h+='<td class="c '+(s.n>1?'y':'n')+'"><b>'+s.n+'</b></td></tr>';
  });
  h+='</tbody></table>';

  if(D.split.length){
    h+='<div class="head" style="margin-top:16px"><h2>이름 통일 후보 — '
      +D.split.length+'건</h2><p class="warn">같은 개념인데 계열마다 다르게 적혀 있다. '
      +'표기를 함부로 바꾸지 않은 이유는 <b>행 순서와 매칭 규칙이 이름에 매여</b> 있어서다 '
      +'— 바꾸려면 그 둘을 같이 손봐야 한다.</p>';
    h+='<table><thead><tr><th>개념</th><th>계열마다 쓰는 이름</th></tr></thead><tbody>';
    D.split.forEach(function(s){
      var by={};
      s.raw.forEach(function(r){ (by[r[1]]=by[r[1]]||[]).push(r[0]); });
      var parts=Object.keys(by).map(function(n){
        return '<code>'+esc(n)+'</code> <span class="nm">'+by[n].join(' ')+'</span>';});
      h+='<tr><td class="k">'+esc(s.canon)+'</td><td>'+parts.join(' &nbsp;/&nbsp; ')
        +'</td></tr>';
    });
    h+='</tbody></table></div>';
  }
  h+='</div>';

  h+='<aside><h3>계산식 — 이 포인트들이 무엇에 쓰이나</h3>'
    +'<p class="ax">각 계열 요구 프로파일의 <code>energyModel</code> 을 그대로 옮긴 것이다. '
    +'템플릿 행의 <b>쓰임</b> 칸이 이 열쇠를 가리킨다.</p>';
  var byk={};
  D.calc.forEach(function(c){ (byk[c.key]=byk[c.key]||[]).push(c); });
  Object.keys(byk).forEach(function(k){
    h+='<div class="card"><b>'+esc(k)+'</b>';
    byk[k].forEach(function(c){
      h+='<div class="f"><span class="pid">'+esc(c.pid)+'</span>'+esc(c.text)+'</div>';});
    h+='</div>';
  });
  h+='</aside></div>';
  el.innerHTML=h;
}

function body(){
  var p=D.profiles[cur], el=document.getElementById('body');
  var h='<div class="head"><h2>'+esc(p.title)+' <code>'+cur+'</code></h2>';
  if(p.basis) h+='<p>'+esc(p.basis)+'</p>';
  if(p.pending) h+='<p class="warn">'+esc(p.pending)+'</p>';
  if(p.coverageNote) h+='<p class="warn">'+esc(p.coverageNote)+'</p>';
  if(p.energyModel && Object.keys(p.energyModel).length){
    h+='<div class="calc">';
    Object.keys(p.energyModel).forEach(function(k){
      h+='<div><b>'+esc(k)+'</b> — '+esc(p.energyModel[k])+'</div>';});
    h+='</div>';
  }
  h+='</div>';

  if(!p.rows.length){
    el.innerHTML=h+'<div class="empty">행이 아직 없다. 위 사유를 보라 — '
      +'빈 채로 두는 것은 규칙 ④ 가 허용하지만 <b>사유 없이 비면 잊힌다</b>.</div>';
    return;
  }
  if(!p.models.length){
    h+='<div class="empty">이 프로파일에 붙는 모델이 아직 없다 — '
      +'행은 표준·계산식으로 세웠고, 모델이 들어오면 여기서 붙는다.</div>';
  }else{
    h+='<div class="pick"><label>모델 <select id="mdl"></select></label>'
      +'<label>판 <select id="scp"></select></label>'
      +'<span class="cov" id="cov"></span></div>';
  }
  h+='<table><thead><tr><th>개념</th><th>종류</th><th>단위</th><th>등급</th>'
    +'<th>붙은 포인트</th><th>왜 필요한가</th><th>쓰임</th><th>Haystack 근거</th>'
    +'</tr></thead><tbody id="rows"></tbody></table>';
  h+='<div class="matrix" id="mx"></div>';
  el.innerHTML=h;

  if(p.models.length){
    var ms=document.getElementById('mdl');
    ms.innerHTML=p.models.map(function(m,i){
      return '<option value="'+i+'">'+esc(m.name||m.id)+'</option>';}).join('');
    ms.onchange=scopes; scopes();
  }else{ rows(null); }
  matrix();
}

function scopes(){
  var p=D.profiles[cur], m=p.models[+document.getElementById('mdl').value];
  var ss=document.getElementById('scp');
  ss.innerHTML=m.scopes.map(function(s,i){
    var n=s.map.filter(function(x){return x.hit;}).length;
    return '<option value="'+i+'">'+esc(s.label)+' — '+n+'/'+p.rows.length+'</option>';
  }).join('');
  ss.onchange=function(){rows(m.scopes[+ss.value]);};
  ss.value=String(m.best);
  rows(m.scopes[m.best]);
}

function rows(scope){
  var p=D.profiles[cur], by={};
  if(scope) scope.map.forEach(function(x){by[x.n]=x;});
  var h='';
  p.rows.forEach(function(r){
    var g=by[r.name];
    h+='<tr><td class="k">'+esc(r.name)+'</td><td class="mono">'+esc(r.objectType)
      +'</td><td class="mono">'+esc(r.unit)+'</td>'
      +'<td><span class="g '+gcls(r.grade)+'">'+esc(r.grade)+'</span></td>';
    if(!scope){ h+='<td class="miss">모델 미선택</td>'; }
    else if(g && g.hit){
      h+='<td class="hit">'+esc(g.hit)
        +(g.type?' <span style="color:var(--faint)">'+esc(g.type)+(g.inst!=null?' #'+g.inst:'')+'</span>':'')
        +'</td>';
    } else {
      h+='<td class="miss">— 이 판에 없다'+(r.appliesWhen?' <details><summary>왜</summary><code>'
        +esc(r.appliesWhen)+'</code></details>':'')+'</td>';
    }
    h+='<td class="d">'+esc(r.why)+'</td>'
      +'<td class="mono">'+esc((r.usedBy||[]).join(' '))+'</td>'
      +'<td class="d">'+esc(r.haystack)
      +'<details><summary>매칭 규칙</summary><code>include '+esc(r.include)
      +(r.exclude?'<br>exclude '+esc(r.exclude):'')+'</code>'
      +(r.matchNote?'<br><code>'+esc(r.matchNote)+'</code>':'')+'</details></td></tr>';
  });
  document.getElementById('rows').innerHTML=h;
  if(scope){
    var n=scope.map.filter(function(x){return x.hit;}).length;
    document.getElementById('cov').textContent=n+' / '+p.rows.length+' 행이 붙었다';
  }
}

function matrix(){
  var p=D.profiles[cur], el=document.getElementById('mx');
  if(!p.models.length){el.innerHTML='';return;}
  /* 모델명을 세로로 세운 격자였다 — 글자가 세로로 서면 읽을 수가 없다.
     묻는 것은 둘뿐이다: (1) 모델마다 얼마나 덮나 (2) 아무도 안 내주는 행은 무엇인가.
     그래서 모델을 **행**으로 눕히고, 빈 행은 따로 목록으로 뺀다. */
  var tot=p.rows.length;
  var h='<h3 class="mh">모델별 덮개</h3><table class="cov2"><tbody>';
  p.models.slice().sort(function(a,b){return b.any.length-a.any.length;})
   .forEach(function(m){
    var n=m.any.length, pct=tot?Math.round(n*100/tot):0;
    h+='<tr><td class="k">'+esc(m.name)+'</td>'
      +'<td class="bar"><span style="width:'+pct+'%"></span></td>'
      +'<td class="num">'+n+' / '+tot+'</td>'
      +'<td class="num pct">'+pct+'%</td></tr>';
  });
  h+='</tbody></table>';
  var none=p.rows.filter(function(r){
    return !p.models.some(function(m){return m.any.indexOf(r.name)>=0;});});
  h+='<h3 class="mh">아무 모델도 안 내주는 행 — '+none.length+' / '+tot+'</h3>';
  if(!none.length){
    h+='<p class="ax">없다. 모든 행을 최소 한 모델이 낸다.</p>';
  }else{
    h+='<table class="cov2"><tbody>';
    none.forEach(function(r){
      h+='<tr><td class="k">'+esc(r.name)+'</td>'
        +'<td><span class="g '+gcls(r.grade)+'">'+esc(r.grade)+'</span></td>'
        +'<td class="d">'+esc(r.appliesWhen||'카탈로그 모델에 이 점이 없다 — 문서가 없는 것인지 그 기기에 원래 없는 것인지 가려야 한다')+'</td></tr>';
    });
    h+='</tbody></table>';
  }
  el.innerHTML=h;
}

cur='_'; rail(); overview();
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
            "<p class=sub>템플릿 행만으로는 맞는지 알 수 없다 — <b>모델을 붙여 봐야</b> "
            "그 개념이 벤더마다 어떤 이름으로 오는지 보이고, 거기서 오답이 드러난다. "
            "화면이 목록을 정하지 않는다: <code>equip-templates.json</code> · "
            "<code>equip-requirements.json</code> · <code>model-mappings.json</code> 을 "
            "그대로 보여 준다.</p>"
            "<div class=n><span>프로파일 <b>%d</b></span><span>템플릿 행 <b>%d</b></span>"
            "<span>붙는 모델 <b>%d</b></span></div>"
            "<div class=cols><div><div class=rail id=rail></div></div>"
            "<div id=body></div></div></div>"
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
