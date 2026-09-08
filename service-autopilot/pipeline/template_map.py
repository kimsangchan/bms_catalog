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
.matrix th.rot{writing-mode:vertical-rl;text-orientation:mixed;padding:6px 3px;
 font-weight:500;font-size:10.5px;max-height:150px}
.matrix td.c{text-align:center;font-family:var(--mono)}
.matrix td.c.y{color:var(--ok)}
.matrix td.c.n{color:var(--faint)}
.empty{background:var(--panel);border:1px dashed var(--line);border-radius:10px;
 padding:22px;color:var(--faint);font-size:12.5px;text-align:center}
"""

JS = """
var D=DATA, cur=null;
function esc(s){return String(s==null?'':s).replace(/[&<>]/g,function(c){
  return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];});}
function gcls(g){return g==='필수'?'f':g==='권장'?'r':'o';}

function rail(){
  var h='';
  D.order.forEach(function(pid){
    var p=D.profiles[pid];
    h+='<button data-pid="'+pid+'" aria-current="'+(pid===cur)+'">'+esc(p.title)
      +'<span class="m">'+pid+' · '+p.rows.length+'행 · 모델 '+p.models.length+'</span></button>';
  });
  document.getElementById('rail').innerHTML=h;
  [].forEach.call(document.querySelectorAll('#rail button'),function(b){
    b.onclick=function(){cur=b.dataset.pid;rail();body();};});
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
  var p=D.profiles[cur];
  if(!p.models.length){document.getElementById('mx').innerHTML='';return;}
  var h='<table><thead><tr><th>행 \\\\ 모델</th>';
  p.models.forEach(function(m){h+='<th class="rot">'+esc(m.short)+'</th>';});
  h+='<th>덮개</th></tr></thead><tbody>';
  p.rows.forEach(function(r){
    var c=0,cells='';
    p.models.forEach(function(m){
      var y=m.any.indexOf(r.name)>=0; if(y)c++;
      cells+='<td class="c '+(y?'y':'n')+'">'+(y?'●':'·')+'</td>';
    });
    h+='<tr><td class="k">'+esc(r.name)+'</td>'+cells
      +'<td class="c '+(c?'y':'n')+'">'+c+'/'+p.models.length+'</td></tr>';
  });
  h+='</tbody></table>';
  document.getElementById('mx').innerHTML=h;
}

cur=D.order[0]; rail(); body();
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
    data = {"order": order, "profiles": profiles}
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
