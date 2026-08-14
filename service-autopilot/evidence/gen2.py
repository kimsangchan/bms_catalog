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
.qbox{display:flex;gap:6px;align-items:center}
#qall{padding:6px 10px;border:1px solid var(--line);border-radius:6px;font-size:11.5px;
 color:var(--dim);white-space:nowrap}
#qall:hover{border-color:var(--accent);color:var(--accent)}
.jump{color:var(--accent);text-decoration:underline;text-underline-offset:2px;font-size:12px}
.tot{display:flex;gap:14px;font-size:11.5px;color:var(--dim);white-space:nowrap}
.tot b{color:var(--ink);font-family:var(--mono)}

/* 3분할 */
.app{display:grid;grid-template-columns:212px minmax(0,1fr);min-height:calc(100dvh - 45px)}
aside{border-right:1px solid var(--line);overflow-y:auto;max-height:calc(100dvh - 45px);
 position:sticky;top:45px;padding-bottom:24px}
.gh{padding:12px 12px 4px;font-size:10.5px;font-weight:700;letter-spacing:.07em;color:var(--faint)}
/* 축 전환 — 같은 데이터에 입구를 둘 둔다 (설비 기준 · 제조사 기준) */
.axis{display:flex;gap:4px;padding:8px 10px 2px;border-bottom:1px solid var(--line)}
.axis button{flex:1;padding:5px 0;font-size:11.5px;font-weight:650;border:1px solid var(--line);
 border-radius:6px;color:var(--dim);text-align:center}
.axis button[aria-pressed="true"]{background:var(--sel);border-color:var(--accent);color:var(--ink)}
/* 모델 목록의 제조사 구분 — 한 줄로 늘어놓으면 어느 회사 것인지 이름을 읽어야 안다 */
.mvd{display:flex;align-items:baseline;gap:6px;padding:10px 18px 4px;font-size:11px;
 font-weight:700;letter-spacing:.04em;color:var(--dim)}
.mvd i{font-style:normal;font-size:10px;color:var(--faint)}
/* 인터페이스(판) 고르기 */
.iflist{display:flex;gap:6px;flex-wrap:wrap;padding:0 18px 10px}
.iflist button{display:inline-flex;align-items:center;gap:7px;padding:6px 11px;
 border:1px solid var(--line);border-radius:6px;font-size:12px}
.iflist button[aria-pressed="true"]{background:var(--sel);border-color:var(--accent);font-weight:650}
.ifr{font-size:10.5px;color:var(--dim);font-family:var(--mono)}
.ifmeta{padding:0 18px 8px;font-size:11.5px;color:var(--dim)}
.ifmeta .dot{margin:0 7px;color:var(--faint)}
.vclr{margin-left:8px;padding:1px 7px;border:1px solid var(--line);border-radius:4px;font-size:10.5px}
aside button{display:grid;grid-template-columns:1fr auto;gap:6px;width:100%;text-align:left;
 padding:5px 12px;font-size:12.5px;align-items:center;border-left:2px solid transparent}
aside button:hover{background:var(--sel)}
aside button[aria-current="true"]{background:var(--sel);border-left-color:var(--accent);font-weight:600}
aside button i{font-style:normal;font-family:var(--mono);font-size:11px;color:var(--faint)}
aside button.sub{padding-left:24px;font-size:11.7px;color:var(--dim)}
aside button.sub[aria-current="true"]{color:var(--ink)}

main{min-width:0;display:flex;flex-direction:column}
.hd{padding:14px 18px 0}
.hd .dom{font-size:10.5px;letter-spacing:.07em;color:var(--faint);font-weight:700}
.hd h1{font-size:19px;letter-spacing:-.02em;margin:3px 0 6px;font-weight:650}
.hd .subttl{font-size:12px;color:var(--accent);font-weight:650;margin:-2px 0 6px}
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
.tw.compact table{min-width:980px;table-layout:fixed}
.tw.compact th,.tw.compact td{white-space:normal;overflow-wrap:anywhere;line-height:1.45}
.tw.compact td.n{white-space:normal}
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
.slist button{white-space:normal;text-align:left;line-height:1.35;max-width:360px}
.sgroups{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:10px;
 padding:0 18px 10px}
.sgroup{border-top:1px solid var(--line2);padding-top:8px}
.sgroup h4{font-size:10.5px;font-weight:700;letter-spacing:.06em;color:var(--faint);margin-bottom:6px}
.sgroup .slist{padding:0;max-height:none}
.slist .stxt{display:flex;flex-direction:column;gap:2px;min-width:0}
.slist .stxt b{font-size:11.8px;font-weight:650;overflow-wrap:anywhere}
.slist .stxt i{font-style:normal;font-size:10.5px;color:var(--faint);overflow-wrap:anywhere}
/* 표의 성격을 먼저 고른다 — 정격/성능/치수는 쓰임이 다르다 */
.klist{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:2px 18px 9px}
.klist button{display:inline-flex;align-items:center;gap:6px;padding:5px 12px;
 border:1px solid var(--line);border-radius:16px;font-size:12px}
.klist button[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);
 color:#fff;font-weight:650}
.klist button[aria-pressed="true"] .mn{color:#fff;opacity:.75}
.khint{font-size:11.5px;color:var(--dim);margin-left:6px}
/* 내보내기 — 화면에서 보는 것과 별개로 뽑아 쓰는 길 */
.csv{margin-left:8px;padding:3px 9px;border:1px solid var(--line);border-radius:5px;
 font-size:10.5px;font-family:var(--mono);color:var(--dim);white-space:nowrap}
.csv:hover{border-color:var(--accent);color:var(--accent)}
th.srt{cursor:pointer;user-select:none}
th.srt:hover{color:var(--accent)}
.sa{font-style:normal;font-size:9px;color:var(--accent)}
.pg{display:flex;gap:6px;align-items:center;padding:6px 18px;font-size:11.5px}
.pgb{padding:3px 9px;border:1px solid var(--line);border-radius:5px;font-size:11px}
.pgb[disabled]{opacity:.35;cursor:default}
.pgn{font-family:var(--mono);color:var(--dim);margin-left:4px}
thead th{position:sticky;top:0;background:var(--bg);z-index:2}
.lgd{display:flex;gap:6px;flex-wrap:wrap;align-items:center;padding:0 18px 8px;
 font-size:11px;color:var(--faint)}
.lgd .sim{margin-left:6px}
/* 중요도는 **색**으로 가른다. 별표를 달면 표가 어수선해지고 눈에 덜 띈다 */
.lbl{cursor:help;border-bottom:1px dotted var(--line);display:inline-block}
.lbl i{display:block;font-style:normal;font-size:10.5px;color:var(--faint);
 font-family:var(--mono);margin-top:1px}
.lbl.k3{color:var(--accent);font-weight:650}
.lbl.k2{color:var(--ink)}
.lbl.k1{color:var(--faint)}
.val.k3{color:var(--accent);font-weight:650;font-family:var(--mono)}
.val.k2{font-family:var(--mono)}
.val.k1{color:var(--dim);font-family:var(--mono)}
th .lbl{border-bottom:0}
th .lbl.k3{color:var(--accent)}
/* 마우스를 올렸을 때만 뜨는 설명 — 늘 펼쳐 두면 값이 안 보인다 */
#tip{position:fixed;z-index:99;max-width:320px;padding:8px 11px;border-radius:7px;
 background:var(--ink);color:var(--bg);font-size:11.5px;line-height:1.6;
 box-shadow:0 6px 22px rgba(0,0,0,.22);pointer-events:none;opacity:0;
 transition:opacity .09s;white-space:pre-line}
#tip.on{opacity:1}
.tiles{display:grid;grid-template-columns:repeat(auto-fill,minmax(148px,1fr));
 gap:1px;background:var(--line2);border-top:1px solid var(--line2);
 border-bottom:1px solid var(--line2);margin-bottom:4px}
.tile{background:var(--bg);padding:9px 14px}
.tk{font-size:10.5px;font-weight:700;letter-spacing:.03em;color:var(--accent)}
.tv{font-family:var(--mono);font-size:17px;font-weight:650;letter-spacing:-.02em;margin-top:2px}
/* 벤더가 값 칸에 '12 to 15 VDC at 5.2 W maximum' 처럼 길게 적어 두면 큰 글씨로는
   타일 안에서 한 글자씩 세로로 늘어진다. 긴 값만 작게 — 읽히는 쪽이 우선이다. */
.tv.tvl{font-size:12px;font-weight:600;letter-spacing:0;line-height:1.35}
.tv small{font-size:11px;font-weight:400;color:var(--dim);margin-left:3px}
.tn{font-size:10px;color:var(--faint);margin-top:2px;overflow:hidden;text-overflow:ellipsis;
 white-space:nowrap}
.cath{padding:16px 18px 4px;font-size:11px;font-weight:700;letter-spacing:.06em;color:var(--dim)}
.cath b{font-family:var(--mono);color:var(--faint);margin-left:5px;font-weight:700}
.more{margin:14px 18px 0;border-top:1px solid var(--line2);padding-top:8px}
.more summary{cursor:pointer;font-size:11.5px;color:var(--dim);padding:4px 0}
.more summary i{font-style:normal;color:var(--faint);font-size:11px}
.more[open] summary{color:var(--ink);font-weight:600}
.tdesc{display:block;font-style:normal;font-size:11px;color:var(--dim);margin-top:2px;
 line-height:1.5;max-width:46ch}
.sim{font-size:10px;font-weight:700;letter-spacing:.03em;padding:1px 6px;border-radius:3px;
 white-space:nowrap}
.sim.s3{background:var(--accent-bg);color:var(--accent)}
.sim.s2{background:var(--sel);color:var(--dim)}
.sim.s1{background:transparent;color:var(--faint)}
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
.srclink{color:inherit;text-decoration:underline dotted;text-underline-offset:2px}
.srclink:hover{color:var(--accent);text-decoration-style:solid}
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
.purpose{border-top:1px solid var(--line2);border-bottom:1px solid var(--line2);
 margin:10px 0 4px;padding:12px 18px;background:var(--panel)}
.purpose h3{font-size:13px;font-weight:650;margin-bottom:4px}
.purpose p{font-size:12px;color:var(--dim);max-width:86ch}
.pstat{display:flex;gap:14px;flex-wrap:wrap;margin-top:9px;font-size:11.5px;color:var(--dim)}
.pstat b{font-family:var(--mono);color:var(--ink)}
.mini{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;
 padding:8px 18px 4px}
.mini h4{font-size:11px;font-weight:700;letter-spacing:.05em;color:var(--faint);margin-bottom:6px}
.pill{display:inline-flex;align-items:center;gap:5px;padding:1px 6px;border-radius:4px;
 font-size:10.5px;font-weight:700;letter-spacing:.03em}
.pill.y{background:var(--accent-bg);color:var(--accent)}
.pill.c{background:var(--sel);color:var(--dim)}
.pill.n{background:var(--warn-bg);color:var(--warn)}
.guide{margin:0 18px 10px;padding:10px 12px;border-left:3px solid var(--accent);
 background:var(--panel)}
.guide b{display:block;font-size:12.5px;margin-bottom:3px}
.guide p{font-size:12px;color:var(--dim);max-width:92ch}
.guide .why{display:flex;gap:6px;flex-wrap:wrap;margin-top:7px}
.guide .why span{font-size:10.5px;padding:2px 7px;border-radius:4px;background:var(--sel);color:var(--dim)}
.mtabs{display:flex;gap:2px;padding:10px 18px 0;border-bottom:1px solid var(--line2)}
.mtabs button{padding:7px 10px;font-size:12px;color:var(--dim);border-bottom:2px solid transparent;margin-bottom:-1px}
.mtabs button[aria-selected="true"]{color:var(--ink);font-weight:650;border-bottom-color:var(--accent)}
.mtabs i{font-style:normal;font-family:var(--mono);font-size:10.5px;color:var(--faint);margin-left:4px}
.unitpick{padding:0 18px 8px;display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:6px}
.ucard{border:1px solid var(--line);border-radius:6px;padding:8px 10px;text-align:left;background:var(--bg)}
.ucard:hover{border-color:var(--accent)}
.ucard[aria-pressed="true"]{border-color:var(--accent);background:var(--accent-bg)}
.ucard b{display:block;font-size:12px;margin-bottom:2px}
.ucard span{display:block;font-size:11px;color:var(--dim);line-height:1.35}
.udetail{margin:0 18px 12px;border-top:1px solid var(--line2);border-bottom:1px solid var(--line2);
 padding:10px 0}
.udetail h4{font-size:13px;font-weight:650;margin-bottom:8px}
.uvals{display:grid;grid-template-columns:repeat(auto-fit,minmax(132px,1fr));gap:1px;background:var(--line2)}
.uval{background:var(--bg);padding:8px 10px;min-height:58px}
.uval .k{font-size:10.5px;color:var(--faint);font-weight:700;letter-spacing:.04em}
.uval .v{font-family:var(--mono);font-size:13px;font-weight:650;margin-top:2px;overflow-wrap:anywhere}
.ustat{display:inline-block;font-size:10px;font-weight:700;letter-spacing:.04em;
 padding:1px 7px;border-radius:999px;border:1px solid var(--line);color:var(--dim)}
.ustat.ok{border-color:var(--accent);color:var(--accent)}
.ustat.man{border-style:dashed;color:var(--ink)}
.uvwt{display:flex;gap:6px;align-items:center;padding:0 18px 8px}
.uvwt button{font-size:11px;padding:4px 12px;border:1px solid var(--line);border-radius:999px;
 background:var(--bg);color:var(--dim)}
.uvwt button[aria-pressed="true"]{border-color:var(--accent);color:var(--ink);background:var(--accent-bg)}
.uvwn{font-size:10.5px;color:var(--faint)}
.ugrid{padding:0 18px 14px;display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:8px}
.gcard{display:flex;flex-direction:column;gap:3px;padding:10px}
.gimg{position:relative;margin:-4px -4px 4px;border-radius:4px;overflow:hidden;background:var(--line2)}
.gimg img{display:block;width:100%;height:96px;object-fit:contain}
.gimg i{position:absolute;right:4px;bottom:4px;font-size:9px;font-style:normal;
 padding:1px 5px;border-radius:3px;background:rgba(0,0,0,.55);color:#fff}
.gcard b{font-size:12.5px}
.gcard .grole{font-size:10.5px;color:var(--faint)}
.gcard .gvals{font-size:11px;color:var(--dim);line-height:1.4}
.gcard .ustat{align-self:flex-start;margin:2px 0}

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
  <div class="qbox">
   <input id="q" placeholder="장비 · 포인트 · 태그 · 모델 검색" autocomplete="off">
   <button id="qall" title="모든 모델을 가로질러 찾아요">전체에서 찾기</button>
  </div>
  <div class="tot"><span>장비 <b>__NEQ__</b></span><span>포인트 <b>__TOTP__</b></span>
   <span>모델 <b>__NMODEL__</b></span><span>모델 포인트 <b>__NMPTS__</b></span>
   <span>정격 사양 <b>__NSPEC__</b><small>모델</small></span></div>
</div>
<div id="tip"></div>
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
var cur = 'home', tab = 'md', mi = 0, kindF = '', gradeF = '', term = '', subF = '';
var vsel = 0;   // 고른 형번 (variants) — 모델을 바꾸면 0 으로 되돌린다
var ssel = 0;   // 고른 사양 표
var usel = {};  // 모델 ID → 고른 Unit Model Number 후보
var uvw = {};   // 모델 ID → 형번 목록 보기 방식 (table 표 | cards 카드)
var mview = 'unit'; // 모델 상세 안의 작업 탭
var axis = 'eq';    // 좌측 레일의 축 — 'eq' 설비 기준 · 'vn' 제조사 기준
var vnF = '';       // 제조사 축에서 들어왔을 때의 제조사 좁히기
var isel = {};      // 모델 ID → 고른 인터페이스(포인트 리스트의 판)
// 프로토콜 블록 이름 → 화면 표기. 사전(point-schema blocks)의 키를 그대로 받는다.
var PROTO_KO = {bacnet:'BACnet', modbus:'Modbus', n2:'N2', lon:'LON',
                yorktalk:'York Talk', logix:'Logix', elink:'E-Link'};
var ksel = 'rating';  // 고른 표 성격 — 모델을 바꾸면 모델별 기본 정격표로 되돌린다
// 표의 성격. rating은 사용자가 바로 입력하는 값이 아니라 모델별 정격값을 찾는 원문표다.
var KIND_ORDER = ['rating','perf','dim','etc'];
var KIND_KO = {rating:'모델별 기본 정격표', perf:'조건별 성능표', dim:'치수·중량', etc:'부속·참고'};
var KIND_HINT = {
  rating:'선택한 Unit Model Number와 같은 행/열만 보면 됩니다',
  perf:'조건을 넣고 찾아보는 표 — 온도별 능력, 풍량×정압별 축동력',
  dim:'설치용 치수와 중량 — 계산에는 쓰지 않아요',
  etc:'부속 호환, 배선, 선정 참고표 — 기본 화면에서는 접어 둬요'
};
var searchAll_on = false;   // 전체 검색 화면인가

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
  // 입구를 둘 둔다 — 설비 기준과 제조사 기준. 업계 카탈로그(BTL·AHRI)가 같은 집합에
  // 입구를 둘 두는 이유는 물어보는 것이 두 가지라서다. "이 제조사가 뭘 갖고 있나"와
  // "이 설비를 누가 만드나"는 다른 질문이고, 트리 하나로는 한쪽만 답한다.
  var h = '<div class="axis">'
        + '<button class="axb" data-axis="eq" aria-pressed="'+(axis==='eq')+'">설비</button>'
        + '<button class="axb" data-axis="vn" aria-pressed="'+(axis==='vn')+'">제조사</button>'
        + '</div>';
  h += '<div class="gh">시작</div><button data-id="home">홈 — 현업은 이렇게 봐요<i></i></button>';
  if(axis==='eq'){
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
        if(e.id==='e5' && nm){
          modelSubtypes(e.id).forEach(function(g){
            h += '<button class="sub" data-id="'+e.id+'" data-sub="'+esc(g.name)+'">└ '
               + esc(g.name)+'<i>M'+g.count+'</i></button>';
          });
        }
      });
    });
  } else {
    var vx = vendorIndex();
    h += '<div class="gh">제조사 '+Object.keys(vx).length+'곳</div>';
    Object.keys(vx).sort().forEach(function(vn){
      var v = vx[vn];
      h += '<button data-id="v:'+esc(vn)+'">'+esc(vn)+'<i>M'+v.n
         + (v.ni?' · <b class="sm">'+v.ni+'판</b>':'')+'</i></button>';
      Object.keys(v.eqs).forEach(function(eq){
        var e = eqById(eq);
        if(!e) return;
        h += '<button class="sub" data-id="'+eq+'" data-vendor="'+esc(vn)+'">└ '
           + esc(e.title)+'<i>M'+v.eqs[eq].length+'</i></button>';
      });
    });
  }
  nav.innerHTML = h;
  nav.querySelectorAll('button:not(.axb)').forEach(function(b){
    b.addEventListener('click',function(){ cur=b.dataset.id; subF=b.dataset.sub||'';
      vnF=b.dataset.vendor||''; tab=defaultTab(cur); mi=0; vsel=0; ssel=0; mview='unit';
      pageOf={}; kindF=''; gradeF=''; render(); });
  });
  nav.querySelectorAll('.axb').forEach(function(b){
    b.addEventListener('click',function(){ axis=b.dataset.axis; buildNav(); markNav(); });
  });
}

// 제조사 → {모델 수, 판 수, 계열별 모델 번호}. 번호는 D.models[계열] 기준이라 기존
// 이동 단추([[계열|번호|이름]])와 그대로 맞물린다.
function vendorIndex(){
  var map = {};
  Object.keys(D.models).forEach(function(eq){
    (D.models[eq]||[]).forEach(function(m,i){
      var v = map[m.vendor] = map[m.vendor] || {n:0, ni:0, eqs:{}};
      v.n++;
      v.ni += (m.interfaces||[]).length;
      (v.eqs[eq] = v.eqs[eq] || []).push(i);
    });
  });
  return map;
}
function eqById(id){ return D.equips.filter(function(x){return x.id===id;})[0]; }

function markNav(){ nav.querySelectorAll('button:not(.axb)').forEach(function(b){
  b.setAttribute('aria-current', b.dataset.id===cur && (b.dataset.sub||'')===subF
    && (b.dataset.vendor||'')===vnF ? 'true':'false'); }); }
function defaultTab(eid){
  return (D.models[eid]||[]).length ? 'md' : 'pt';
}

function modelSubtypes(eid){
  var groups = {};
  (D.models[eid]||[]).forEach(function(m){
    var name = m.modelSubtype || '기타';
    groups[name] = (groups[name]||0) + 1;
  });
  return Object.keys(groups).map(function(name){return {name:name, count:groups[name]};});
}
function visibleModels(eid){
  var allModels = D.models[eid] || [];
  if(subF) allModels = allModels.filter(function(m){ return (m.modelSubtype||'기타')===subF; });
  // 제조사 축에서 들어오면 그 제조사만 남긴다 — 축을 바꿔도 화면이 같으면 축을 바꾼
  // 의미가 없다. 'Trane 의 냉동기'가 곧 답이어야 한다.
  if(vnF) allModels = allModels.filter(function(m){ return m.vendor===vnF; });
  return allModels;
}

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
  if(t.raw) opts.raw = true;
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
  var cls = opts.compact ? 'tw compact' : 'tw';
  var h = ctrl + '<div class="'+cls+'"><table data-tk="'+esc(key)+'"><thead><tr>';
  t.header.forEach(function(c,i){
    var mark = so && so.col===i ? (so.dir>0?' ▲':' ▼') : '';
    // raw 표는 머리글에도 미리 만든 조각(배지)이 들어온다 — 이스케이프하면 글자로 샌다
    h += '<th class="srt" data-col="'+i+'">'+(opts.raw ? String(c) : fmt(c))
       + '<i class="sa">'+mark+'</i></th>';
  });
  h += '</tr></thead><tbody>';
  rows.forEach(function(r){
    h += '<tr>';
    r.forEach(function(c,i){
      var cls = NUMCOL.test(t.header[i]) || /^\d/.test(String(c)) ? ' class="n"' : '';
      // raw 로 표시된 표는 셀에 이미 만들어 둔 조각(배지·설명)을 그대로 낸다
      h += '<td'+cls+'>'+(opts.raw ? String(c) : fmt(c))+'</td>';
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
// 모든 모델을 가로질러 찾는다. 표 안 필터만으로는 '이 오브젝트명이 어느 모델에
// 있나'를 알 수 없다 — 모델을 하나씩 열어 봐야 했다.
function searchAll(t){
  var hitEq = [], hitMd = [], hitPt = [], hitSp = [];
  D.equips.forEach(function(e){
    if((e.title+' '+e.domain+' '+(e.head||'')).toLowerCase().indexOf(t)>=0)
      hitEq.push({eq:e});
  });
  Object.keys(D.models).forEach(function(eid){
    var e = D.equips.filter(function(x){return x.id===eid;})[0];
    (D.models[eid]||[]).forEach(function(m, mi){
      if((m.name+' '+m.model+' '+m.vendor+' '+m.cat+' '+m.tag).toLowerCase().indexOf(t)>=0)
        hitMd.push({eq:e, m:m, mi:mi});
      (m.points||[]).forEach(function(p){
        if(hitPt.length>400) return;
        if((p.name+' '+(p.note||'')).toLowerCase().indexOf(t)>=0)
          hitPt.push({eq:e, m:m, mi:mi, p:p});
      });
      (m.variants||[]).forEach(function(v){
        (v.spec||[]).forEach(function(r){
          if(hitSp.length>200) return;
          if((r[0]+' '+r[1]).toLowerCase().indexOf(t)>=0)
            hitSp.push({eq:e, m:m, mi:mi, code:v.code, r:r});
        });
      });
      (m.specTables||[]).forEach(function(st){
        if(hitSp.length>200) return;
        if((st.title||'').toLowerCase().indexOf(t)>=0)
          hitSp.push({eq:e, m:m, mi:mi, code:'', r:[st.title, st.rows.length+'행', '', st.source||'']});
      });
    });
  });
  return {eq:hitEq, md:hitMd, pt:hitPt, sp:hitSp};
}

function renderSearch(){
  var r = searchAll(term), n = r.eq.length+r.md.length+r.pt.length+r.sp.length;
  var h = '<div class="hd"><div class="dom">전체 검색</div><h1>'+esc(q.value.trim())+'</h1>'
        + '<div class="tag">모든 모델을 가로질러 찾았어요 — 결과 <b class="num">'+n+'</b>건'
        + (r.pt.length>400?' (포인트는 400건까지)':'')+'</div></div><div class="wrap">';
  if(!n) return h + '<div class="sec">찾은 게 없어요</div></div>';
  if(r.md.length) h += sec('모델', r.md.length)
    + table({header:['장비','모델','제조사','포인트','사양'],
             rows:r.md.map(function(x){ return [
               '[['+x.eq.id+'|'+x.mi+'|'+esc(x.eq.title)+']]', x.m.name, x.m.vendor,
               (x.m.points||[]).length, specCount(x.m)]; }), key:'srchmd', nopage:true});
  if(r.pt.length) h += sec('오브젝트', r.pt.length)
    + table({header:['장비','모델','종류','인스턴스','오브젝트명'],
             rows:r.pt.map(function(x){ return [
               '[['+x.eq.id+'|'+x.mi+'|'+esc(x.eq.title)+']]', x.m.name,
               x.p.type, x.p.inst, x.p.name]; }), key:'srchpt'});
  if(r.sp.length) h += sec('사양', r.sp.length)
    + table({header:['장비','모델','형번','항목','값'],
             rows:r.sp.map(function(x){ return [
               '[['+x.eq.id+'|'+x.mi+'|'+esc(x.eq.title)+']]', x.m.name, x.code||'—',
               x.r[0], x.r[1]]; }), key:'srchsp'});
  if(r.eq.length) h += sec('장비 계열', r.eq.length)
    + table({header:['계열','도메인'], rows:r.eq.map(function(x){ return [
        '[['+x.eq.id+'|0|'+esc(x.eq.title)+']]', x.eq.domain]; }), key:'srcheq', nopage:true});
  return h + '</div>';
}

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
   + row('L2','장비 종류의 기본 화면','모델이 무엇이든 항상 있는 포인트예요. 공조기라면 급기온도, 밸브 개도, 팬 지령 같은 관제용 목록이에요.','계열당 10~35')
   + row('L2.5','부속까지 펼친 화면','공조기 1대 = 급기팬 + 환기팬 + 코일 + 댐퍼 4개 + 필터 + 인버터 2대예요. 부속 수만큼 포인트가 늘어요.','1대당 30~120')
   + row('L3','제조사 원문 전체','통신 문서가 내보내는 전체 오브젝트예요. 매핑·시운전에는 필요하지만 운영자 화면에 전부 올리지는 않아요.','모델당 30~300')
   + '</div>'
   + '<p class="lead" style="margin-top:18px">왼쪽에서 장비를 고르고, 위쪽 <b>모델</b> 탭을 누르면 실제 오브젝트 목록을 볼 수 있어요.</p>'
   + '</div>';
}
function row(k,t,d,r){
  return '<div><div class="k">'+k+'</div><div class="v"><b>'+t+'</b><p>'+d+'</p></div>'
       + '<div class="r">'+r+'</div></div>';
}

function renderEquip(e){
  var l3 = D.l3[e.id];
  var models = visibleModels(e.id);
  if(tab==='md' && !models.length) tab = 'pt';
  var h = '<div class="hd"><div class="dom">'+esc(e.domain)+'</div><h1>'+esc(e.title)+'</h1>'
        + (subF ? '<div class="subttl">'+esc(subF)+'</div>' : '')
        + (vnF ? '<div class="subttl">'+esc(vnF)+' 만 <button class="vclr">전체 보기</button></div>' : '')
        + '<div class="tag">'+fmt(e.head)+'</div></div>';
  h += '<div class="tabs">'
     + tb('md','모델',models.length) + tb('pt','포인트',e.np) + tb('sp','사양',e.ns) + '</div>';
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
    var pre = models.length > 1 ? commonPrefix(models.map(function(x){return x.selectorLabel || x.model;})) : '';
    // 제조사로 묶는다 — 한 줄로 늘어놓으면 어느 회사 것인지 이름을 읽어야 안다.
    // (models 는 build 에서 (제조사, 모델) 순으로 정렬돼 이어 붙이면 그대로 묶인다)
    var vgroups = [];
    models.forEach(function(x,i){
      var g = vgroups[vgroups.length-1];
      if(!g || g.v !== x.vendor) vgroups.push(g = {v:x.vendor, items:[]});
      g.items.push({x:x, i:i});
    });
    h += (pre ? '<div class="mpre">'+esc(pre.replace(/[\s—·-]+$/,''))+'</div>' : '')
       + vgroups.map(function(g){
           return (vgroups.length>1 ? '<div class="mvd">'+esc(g.v)+'<i>'+g.items.length+'</i></div>' : '')
             + '<div class="mlist">'
             + g.items.map(function(o){ return modelButton(o.x, o.i, pre); }).join('')
             + '</div>';
         }).join('');
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
  // 별칭 모델 — 이 제품은 자기 목록이 없고 다른 모델의 판이 덮는다. 그 판으로 가는
  // 길을 안 주면 화면이 '아무것도 없는 모델'로 보인다.
  if(m.aliasOf){
    var pj = null;
    Object.keys(D.models).forEach(function(eq){
      (D.models[eq]||[]).forEach(function(x,i){ if(x.id===m.aliasOf) pj = [eq,i,x.name]; }); });
    h += '<div class="msg"><b>이 제품은 목록을 다른 모델과 함께 쓴다</b><p>'
       + fmt(m.summary) + '</p>'
       + (pj ? '<p>[['+pj[0]+'|'+pj[1]+'|'+esc(pj[2])+' 로 가기]]</p>' : '') + '</div>';
  }
  h += '<div class="meta"><span>프로파일 <code>'+esc(m.model)+'</code></span>'
     + '<span>분류 <code>'+esc(m.cat)+'</code></span><span>태그 <code>'+esc(m.tag)+'</code></span>'
     + '<span>사양값 '+badge(m.has.spec)+'</span><span>오브젝트 목록 '+badge(m.has.points)+'</span></div>';
  h += '<div class="wrap">';
  if(hasUnitWorkspace(m)){
    h += renderAhuPurposeWorkspace(m);
    h += '</div>';
    if(m.gap) h += '<div class="msg"><b>아직 못 채운 것</b><p>'+fmt(m.gap)+'</p></div>';
    return h;
  }
  // 정격 사양은 형번별(variants)과 같은 사양 시트로 그린다 — 한글 이름·설명·
  // 시뮬레이터 중요도가 용어 사전에서 붙는다. 전에는 원문 영문 그대로 나열됐다.
  if(m.spec.length){
    var srcs = {};
    m.spec.forEach(function(r){ if(r[4]) srcs[String(r[4]).replace(/\s+p\d+$/,'')] = 1; });
    h += sec('정격 사양', m.spec.length)
       + renderSpecSheet(m.spec, 'f'+m.id)
       + '<div class="msg" style="margin:0 18px 14px"><p>근거 '
       + esc(Object.keys(srcs).join(' · ')) + '</p></div>';
  }
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
    var KEYS = [['정격전압', /nominal voltage$/i, 'Nominal voltage'],
                ['운전 전력', /power consumption in operation/i, 'Power consumption in operation'],
                ['유지 전력', /power consumption.*(rest|holding)/i, 'Power consumption in rest position'],
                ['토크', /torque motor/i, 'Torque motor'],
                ['구동시간', /running time/i, 'Running Time (Motor)'],
                ['소음', /sound power/i, 'Sound power level'],
                ['중량', /^weight$/i, 'Weight']];
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
      if(m.specFromName) h += '<div class="msg" style="margin:0 18px 8px"><p>'
       + '사양은 같은 제품의 <b>'+esc(m.specFromName)+'</b> 문서에서 가져왔어요 — '
       + '프로토콜만 다르고 기기는 같아요.</p></div>';
    h += sec('형번 비교 — 핵심 정격', vs.length)
         + '<div class="lgd">항목 이름에 마우스를 올리면 뜻이 나와요 · '
         + '<span class="lbl k3">진한 색</span> 계산에 직접 · '
         + '<span class="lbl k2">보통</span> 한계·조건 · '
         + '<span class="lbl k1">흐린 색</span> 선정에만</div>'
         + table({header:['형번'].concat(used.map(function(k){
                    var t = termOf(k[2] || k[0]);
                    return t ? '<span class="lbl '+simCls(t.sim)+'"'+tipAttr(t)+'>'
                               + esc(k[0])+'</span>' : esc(k[0]);
                  })), rows:crows, key:'vcmp'+m.id, raw:true});
    }
    h += sec('형번별 상세', vs.length)
       + '<div class="vlist">' + vs.map(function(v,i){
           return '<button data-vi="'+i+'" aria-pressed="'+(i===vi)+'">'
                + (v.photo ? '<img class="vth" src="'+v.photo+'" alt="">' : '')
                + esc(v.code)+'</button>';
         }).join('') + '</div>'
       + renderSpecSheet(vs[vi].spec, 'v'+vi+m.id);
  }
  // 카탈로그·설계 가이드에서 뽑은 정격 사양 행렬. 한 줄이 형번 하나이고
  // 열이 속성이라 포인트 표와 구조가 다르다 — 표마다 따로 그린다.
  // 사양 표는 모델 하나에 수십 개까지 붙는다(Ascend 38개). 전부 펼치면 스크롤이
  // 끝나지 않아 원하는 표를 못 찾는다 → **목록에서 골라 하나씩** 본다 (힉의 법칙).
  var sts = (m.specTables || []).slice();
  if(sts.length){
    // 표는 성격이 섞여 있다 — '이 제품이 늘 갖는 값(정격)' 과 '조건을 넣고
    // 찾아보는 표(성능)' 와 '치수' 는 쓰임이 다르다. 한 덩어리로 늘어놓으면
    // 무슨 표인지 알 수 없다(실측: 모델 하나에 148개).
    // 성격을 먼저 고르고, 그 안에서 표를 고른다.
    sts.forEach(function(x,i){ x._i = i; });
    var kinds = KIND_ORDER.filter(function(k){
      return sts.some(function(x){ return (x.kind||'etc')===k; }); });
    var kk = kinds.indexOf(ksel) >= 0 ? ksel : kinds[0];
    sts = sts.filter(function(x){ return (x.kind||'etc')===kk; });
    // 시뮬레이터가 쓰는 열이 많은 표를 앞에 둔다 — 'General Data 1' 부터 보여 주면
    // 정작 필요한 전기 데이터 표를 한참 찾아야 한다
    sts.sort(function(a,b){ return summarizeMatrix(b).length - summarizeMatrix(a).length; });
    var si = Math.min(ssel, sts.length-1), t = sts[si];
    if(isAhuModel(m)){
      h += '<details class="more rawspec"><summary>제조사 원문표 상세 '
        + (m.specTables||[]).length + '개 <i>(확정 기본값이 아니라 근거 확인용 후보표예요)</i></summary>';
    }
    h += sec('제조사 원문표', (m.specTables||[]).length)
       + '<div class="klist">' + kinds.map(function(k){
           var n = (m.specTables||[]).filter(function(x){ return (x.kind||'etc')===k; }).length;
           return '<button data-kk="'+k+'" aria-pressed="'+(k===kk)+'">'
                + esc(KIND_KO[k]) + '<span class="mn">' + n + '개</span></button>';
         }).join('')
       + '<span class="khint">' + esc(KIND_HINT[kk]||'') + '</span></div>'
       + specKindGuide(kk)
       + '<div class="slist">' + sts.map(function(x,i){
           var qq = (x.quantities||[]).filter(Boolean);
           var lbl = (x.title||'표 '+(i+1)).replace(/^Table\s*\d+\.\s*/,'');
           // 같은 제목이 여러 개면 쪽수로 가른다 — 'General Information' 이 세 개다
           if(sts.filter(function(z){return (z.title||'')===(x.title||'');}).length>1)
             lbl += ' (p'+x.page+')';
           return '<button data-si="'+i+'" aria-pressed="'+(i===si)+'">'
                + esc(lbl)
                + (qq.length?'<span class="ms">포함값: '+esc(QLABEL[qq[0]]||qq[0])+'</span>':'')
                + '</button>';
         }).join('') + '</div>';
    var uq = [];
    (t.quantities||[]).forEach(function(x){ if(x && uq.indexOf(x)<0) uq.push(x); });
    h += rawSpecGuide(t, kk)
       + '<div class="qrow">'
       + (t.orientation==='row' ? '<span class="qtag alt">행=항목 · 열=형번</span>' : '')
       + uq.map(function(x){ return '<span class="qtag">'+esc(QLABEL[x]||x)+'</span>'; }).join('')
       + '<span class="qsrc">' + srcLink(t.source, t.page, (t.source||'') + ' p'+t.page) + '</span>'
       + csvBtn('st'+m.id+t._i,
                safeName(m.model+'_'+(t.title||'표')+'_p'+t.page)+'.csv',
                t.header, t.rows, '이 표 CSV')
       // 여러 표를 한 파일로 낼 때는 가로로 이어 붙이면 안 된다 — 표마다 열 구성이
       // 달라 '열1…열16' 이 되고 무엇인지 알 수 없다. 한 줄에 값 하나씩 두는
       // 세로형으로 낸다. 열 이름이 값과 함께 붙어 있어 그대로 처리할 수 있다.
       + csvBtn('stall'+m.id+kk, safeName(m.model+'_'+KIND_KO[kk])+'_전체.csv',
                ['표','쪽','근거','행','열','값'],
                sts.reduce(function(acc,x){
                  x.rows.forEach(function(r, ri){
                    r.forEach(function(v, ci){
                      if(v===''||v===null||v===undefined) return;
                      acc.push([x.title||'', x.page, x.source||'', ri+1,
                                x.header[ci]||('열'+(ci+1)), v]);
                    });
                  });
                  return acc;
                }, []),
                KIND_KO[kk]+' 전체 CSV')
       + '</div>'
       + (isAhuModel(m) ? '' : matrixTiles(t))
       + table({header:t.orientation==='row' ? t.header : t.header.map(function(hh){
                  var tt = termOf(hh);
                  return tt ? '<span class="lbl '+simCls(tt.sim)+'"'+tipAttr(tt)+'>'
                              + esc(hh)+'</span>' : esc(hh);
                }),
                rows:(t.orientation==='row' ? t.rows.map(function(r){
                        var tt = termOf(r[0]);
                        return [tt ? '<span class="lbl '+simCls(tt.sim)+'"'+tipAttr(tt)+'>'
                                     + esc(tt.ko)+'<i>'+esc(r[0])+'</i></span>'
                                   : esc(r[0])].concat(r.slice(1).map(esc));
                      }) : t.rows.map(function(r){ return r.map(esc); })),
                key:'st'+si+(t.source||''), raw:true});
    if(isAhuModel(m)) h += '</details>';
  }
  h += renderInterfaces(m);
  if(m.points.length){
    var pts = m.points.filter(function(p){return p.inst;});
    var hasNote = m.points.some(function(p){return p.note;});
    var hasSrc = m.points.some(function(p){return p.sourceFile && p.sourcePage;});
    var hasModbusMeta = m.points.some(function(p){return p.bacOid || p.modbusScaleFactor || p.modbusSignedFlag || p.modbusWritableFlag !== undefined;});
    var head = ['인스턴스','종류','단위','오브젝트명'];
    if(hasModbusMeta) head = head.concat(['BACOid','Scale','Signed','Writable']);
    if(hasNote) head.push('값 범위 · 상태');
    if(hasSrc) head.push('출처');
    var rows = m.points.map(function(p){
      var r = [esc(p.inst||''), esc(p.type), esc(p.unitDisp), esc(p.name)];
      if(hasModbusMeta) r = r.concat([
        esc(p.bacOid||''), esc(p.modbusScaleFactor||''),
        esc(p.modbusSignedFlag||''), esc(p.modbusWritableFlag === undefined ? '' : p.modbusWritableFlag)
      ]);
      if(hasNote) r.push(esc(p.note||''));
      if(hasSrc) r.push(srcLink(p.sourceFile, p.sourcePage,
        p.sourceFile ? (p.sourceFile + (p.sourcePage ? ' p'+p.sourcePage : '')) : ''));
      return r;
    });
    // 매핑 자동화에 실제로 쓰이는 건 이 표다 — 뽑아 갈 수 있어야 한다.
    // 화면 표기(unitDisp)가 아니라 원문 단위와 정규 단위를 함께 넣는다.
    h += sec('제조사 원문 오브젝트 목록', pts.length)
       + '<div class="qrow"><span class="qsrc">인스턴스 번호까지 문서에 확정된 L3 전체 목록</span>'
       + csvBtn('pt'+m.id, safeName(m.vendor+'_'+m.model)+'_오브젝트목록.csv',
                ['type','instance','name','unit','unitRaw','bacOid','modbusRegister','modbusScaleFactor','modbusBooleanFlag','modbusSignedFlag','modbusOffset','modbusWritableFlag','sourceFile','sourcePage','note'],
                m.points.map(function(p){
                  return [p.type, p.inst||'', p.name, p.unit||'', p.unitRaw||'',
                          p.bacOid||'', p.modbusRegister||'', p.modbusScaleFactor||'',
                          p.modbusBooleanFlag||'', p.modbusSignedFlag||'',
                          p.modbusOffset||'', p.modbusWritableFlag === undefined ? '' : p.modbusWritableFlag,
                          p.sourceFile||'', p.sourcePage||'', p.note||'']; }),
                '오브젝트 목록 CSV')
       + '</div>'
       + kindChips([{header:head, rows:rows}])
       + table({header:head, rows:rows, raw:true});
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

function isAhuModel(m){
  return m.equipId === 'e5' || /HVAC\.AIR\.(AHU|RTU)/i.test(m.cat||'')
      || /\b(ahu|rtu|rooftop)\b/i.test(m.tag||'');
}

// 형번·정격 작업 화면을 열 수 있는가 — 공조기이거나, 형번 후보가 실제로 뽑힌 모델
// (냉동기 카탈로그의 Physical/General data 도 같은 구조라 형번이 나온다)
function hasUnitWorkspace(m){
  var p = (D.purpose||{})[m.id];
  return isAhuModel(m) || !!(p && (p.unitModels||[]).length);
}

// 공조기 운영 화면은 L3 원문 전체가 아니라 L2 기본 화면에서 시작한다.
// 아래 규칙은 "화면 후보를 먼저 보여 주는" 얇은 계층이고, 원문 목록은 그대로 보존한다.
//
// ⚠ 이 목록은 renderAhuOperatorView() 전용 폴백이고 **지금은 도달하지 않는다** —
//   e5 모델은 purpose 데이터가 항상 있어 renderAhuPurposeWorkspace 가 먼저 돌아간다.
//   그래서 옛 목록(냉수·온수 밸브 포함)을 그대로 두었다. 되살릴 때는 여기 규칙을 베끼지
//   말고 pipeline/data/equip-templates.json 의 하위형식 프로파일(e5.rtu·e5.ahu)을 써라.
//   RTU 에는 냉수·온수 밸브가 없다 (2026-08-11 사고, pipeline/README.md 참고).
var VIEW_PROFILES = {
  ahu: [
    ['급기온도', /(?:supply|discharge).*air.*temp|discharge.*temp/i],
    ['환기온도', /return.*air.*temp/i],
    ['외기온도', /outdoor|outside.*air.*temp/i],
    ['급기정압', /(?:supply|discharge).*static.*pressure|duct.*static/i],
    ['급기온도 설정값', /(?:supply|discharge).*temp.*setpoint|discharge.*cooling.*setpoint/i],
    ['급기정압 설정값', /static.*pressure.*setpoint/i],
    ['팬 지령/상태', /fan.*(?:command|status|speed|frequency)|(?:supply|return).*fan/i],
    ['외기댐퍼', /outdoor.*air.*damper|outside.*air.*damper/i],
    ['냉수·냉방 밸브/능력', /cool(?:ing)?|chilled.*water|cooling.*capacity/i],
    ['온수·난방 밸브/능력', /heat(?:ing)?|hot.*water/i],
    ['필터/차압', /filter|differential.*pressure/i],
    ['경보/고장', /alarm|fault|emergency|freeze|lockout/i]
  ]
};

function renderAhuPurposeWorkspace(m){
  var p = (D.purpose||{})[m.id];
  if(!p) return renderAhuOperatorView(m);
  var views = availableModelViews(m, p);
  if(!views.some(function(x){return x.id===mview;})) mview = views[0].id;
  var h = '<div class="purpose"><h3>이 모델 문서를 이렇게 쓰면 돼요</h3>'
    + '<p>먼저 <b>Unit Model Number</b>를 고릅니다. '
    + '이 화면의 모델명은 물리 장비 1대가 아니라 통신 프로파일/제품군 문서인 경우가 많습니다. '
    + '원문표는 선택한 형번 값이 PDF 어디에서 왔는지 확인할 때만 봅니다.</p>'
    + '<div class="pstat"><span>Unit Model Number <b>'+((p.unitModels||[]).length||0)+'</b>개</span>'
    + '<span>제조사 원문 포인트 <b>'+((p.counts||{}).l3MappingPoints||0)+'</b>개 보존</span>'
    + '<span>원문표 <b>'+((m.specTables||[]).length||0)+'</b>개</span></div></div>';
  h += '<div class="mtabs">' + views.map(function(v){
      return '<button data-mview="'+v.id+'" aria-selected="'+(mview===v.id)+'">'
        + esc(v.label) + '<i>'+v.count+'</i></button>';
    }).join('') + '</div>';
  return h + renderModelViewPanel(m, p);
}

function availableModelViews(m, p){
  var views = [];
  if((p.unitModels||[]).length) views.push({id:'unit', label:'형번·정격', count:p.unitModels.length});
  views.push({id:'points', label:'오브젝트 목록', count:ptCount(m)});
  if((m.specTables||[]).length) views.push({id:'raw', label:'원문표', count:(m.specTables||[]).length});
  if((m.docs||[]).length) views.push({id:'docs', label:'근거', count:(m.docs||[]).length});
  return views;
}

function renderModelViewPanel(m, p){
  if(mview === 'unit') return renderAhuUnitModelCandidates(m);
  if(mview === 'bms') return renderBmsTemplatePanel(m, p);
  if(mview === 'sim') return renderSimulatorInputPanel(m, p);
  if(mview === 'points') return renderObjectPointPanel(m);
  if(mview === 'raw') return renderRawSpecPanel(m);
  if(mview === 'docs') return renderDocsPanel(m);
  return '';
}

function renderBmsTemplatePanel(m, p){
  var tm = p.templatePointMappings || [];
  return sec('BMS 기본화면', tm.length)
    + '<div class="guide"><b>운영 화면에 먼저 올릴 포인트예요</b>'
    + '<p>장비별 템플릿 데이터에서 온 항목입니다. 화면 코드가 목록을 정하는 것이 아니라 데이터셋의 <code>templatePointMappings</code>를 그대로 보여줍니다.</p></div>'
    + table({header:['상태','화면 이름','원문 포인트','종류','단위'],
             rows:tm.map(function(x){
               var mp = x.matchedPoint || {};
               return [statusPill(x.status), esc(x.templateName),
                       mp.name ? esc(mp.name) : '—', mp.type || x.objectType || '—',
                       esc(mp.unit || x.unit || '—')];
             }), key:'ahu-purpose-template'+m.id, raw:true, nopage:true});
}

function renderSimulatorInputPanel(m, p){
  var sm = p.simulatorRequirementMappings || [];
  return sec('시뮬레이터 입력', sm.length)
    + '<div class="guide"><b>계산에 필요한 정격 항목이에요</b>'
    + '<p>장비별 사양 요구사항 데이터에서 온 항목입니다. <b>후보</b>는 제품군 원문표에서 찾은 값이라 Unit Model Number·전원·옵션을 골라야 확정됩니다.</p></div>'
    + table({header:['상태','필요 정격','찾은 값','단위'],
             rows:sm.map(function(x){
               var mi = (x.matchedInputs || [])[0] || {};
               var label = mi.label ? mi.label + ' · ' : '';
               var note = x.status === 'candidate' ? '<br><span class="tdesc">형번·전원·옵션을 더 골라야 확정</span>' : '';
               return [statusPill(x.status), esc(x.requirementName),
                       mi.name ? esc(label + mi.name + ' = ' + (mi.value || '')) + note : '—',
                       esc(mi.unit || x.unit || '—')];
             }), key:'ahu-purpose-sim'+m.id, raw:true, nopage:true});
}

// ── 제조사 화면 ──────────────────────────────────────────────────────────────
// 제조사를 고르면 그 회사가 가진 것을 설비별로 본다. 표 첫 칸이 이동 단추라
// 거기서 바로 그 계열 화면의 그 모델로 넘어간다.
function protoOf(m){
  var s = {};
  (m.comm||[]).forEach(function(c){ if(c[0]) s[c[0]]=1; });
  (m.interfaces||[]).forEach(function(it){
    (it.protocols||[]).forEach(function(x){ s[PROTO_KO[x]||x]=1; }); });
  return Object.keys(s).join('·');
}
function ptCount(m){
  return (m.points||[]).length
       + (m.interfaces||[]).reduce(function(a,it){ return a + (it.pointCount||0); }, 0);
}
function renderVendor(vn){
  var v = vendorIndex()[vn];
  if(!v) return '<div class="msg"><b>제조사를 못 찾았어요</b></div>';
  var nm = 0, np = 0;
  Object.keys(v.eqs).forEach(function(eq){ v.eqs[eq].forEach(function(i){
    nm++; np += ptCount(D.models[eq][i]); }); });
  var h = '<div class="hd"><div class="dom">제조사</div><h1>'+esc(vn)+'</h1>'
        + '<div class="tag">모델 <b class="num">'+nm+'</b> · 설비 계열 '
        + Object.keys(v.eqs).length + ' · 오브젝트 <b class="num">'+np+'</b>'
        + (v.ni?' · 포인트 리스트 판 <b class="num">'+v.ni+'</b>':'')+'</div></div><div class="wrap">';
  Object.keys(v.eqs).forEach(function(eq){
    var e = eqById(eq);
    if(!e) return;
    var rows = v.eqs[eq].map(function(i){
      var m = D.models[eq][i];
      return ['[['+eq+'|'+i+'|'+esc(e.title)+']]', esc(m.name)
              + (m.aliasOf ? '<span class="mpr"> 별칭</span>' : ''),
              esc(protoOf(m)), (m.interfaces||[]).length || '',
              ptCount(m) || '', specCount(m) || ''];
    });
    h += sec(e.title, rows.length)
       + table({header:['계열','모델','프로토콜','판','오브젝트','원문표'],
                rows:rows, key:'vn'+vn+eq, nopage:true, raw:true});
  });
  return h + '</div>';
}

// ── 인터페이스(포인트 리스트의 판) ────────────────────────────────────────────
// 한 제품이 게이트웨이·펌웨어·개정에 따라 다른 목록을 낸다. 문서가 가른 대로 나눠
// 두지 않으면 주소 체계가 다른 목록이 한 표에 섞여 되돌릴 수 없다(D-016).
function ifCell(v){
  if(v===null || v===undefined) return '';
  if(Array.isArray(v)) return v.map(ifCell).join(', ');
  if(typeof v === 'object'){
    if(v.raw!==undefined && v.raw!==null) return String(v.raw);
    return Object.keys(v).map(function(k){ return k+'='+ifCell(v[k]); }).join(' · ');
  }
  return String(v);
}
var IFCOLS = [['n','오브젝트명'],['s','짧은 이름'],['b','BACnet'],['m','Modbus'],['d','N2'],
              ['l','LON'],['y','York Talk'],['k','YT 종별'],['g','Logix'],['u','단위'],
              ['w','R/W'],['a','적용 조건'],['t','상태·열거'],['o','비고'],['p','쪽']];
function renderInterfaces(m){
  var ifs = m.interfaces || [];
  if(!ifs.length) return '';
  var k = Math.min(isel[m.id]||0, ifs.length-1), it = ifs[k];
  var tot = ifs.reduce(function(a,x){ return a + (x.pointCount||0); }, 0);
  var h = sec('오브젝트 목록 — 판 '+ifs.length+'개', tot);
  if(ifs.length>1) h += '<div class="guide"><b>같은 제품인데 목록이 여러 판이에요</b>'
    + '<p>게이트웨이·펌웨어·문서 개정에 따라 주소가 달라집니다. 문서가 가른 대로 나눠 두었어요 '
    + '— 판을 고르면 그 판의 목록만 봅니다.</p></div>';
  h += '<div class="iflist">' + ifs.map(function(x,i){
      // 계통+개정만으로는 안 갈린다 — YK 는 EM/SSS 판과 VSD 판이 같은 'Rev K 04d' 다.
      // 문서 이름이 유일한 구분자라 함께 보인다.
      var rv = [x.revision&&x.revision.doc, x.revision&&x.revision.block,
                x.revision&&x.revision.firmware,
                x.id.replace(/^[a-z0-9]+-/,'')].filter(Boolean).join(' · ');
      return '<button data-if="'+i+'" aria-pressed="'+(i===k)+'">'
        + esc(x.family||'계통 미상')
        + (rv ? '<span class="ifr">'+esc(rv)+'</span>' : '')
        + '<span class="mpr">'+esc((x.protocols||[]).map(function(pp){
            return PROTO_KO[pp]||pp; }).join('·'))+'</span>'
        + '<span class="mn">'+(x.pointCount||0)+'</span></button>';
    }).join('') + '</div>';
  var meta = [];
  if(it.appliesTo && it.appliesTo.length)
    meta.push('이 목록이 덮는 제품 <b>'+esc(it.appliesTo.join(' · '))+'</b>');
  meta.push('출처 ' + srcLink(it.sourceFile, (it.sourcePages||[])[0],
            it.sourceFile + (it.sourcePages ? ' p'+it.sourcePages.join('~') : '')));
  h += '<div class="ifmeta">' + meta.join('<span class="dot">·</span>') + '</div>';
  if(it.note) h += '<div class="ifmeta">'+esc(it.note)+'</div>';
  // 뺀 행과 못 채운 것은 표 앞에 둔다 — 조용히 빼면 '문서에 그것뿐'으로 읽힌다
  if(it.excluded) h += '<div class="msg"><b>포인트로 세지 않은 행</b><p>'
    + esc(Object.keys(it.excluded).map(function(r){ return r+' '+it.excluded[r]+'행'; }).join(' · '))
    + '</p></div>';
  if(it.gaps && it.gaps.length) h += '<div class="msg"><b>남은 판단</b><p>'
    + esc(it.gaps.join(' / ')) + '</p></div>';
  var use = IFCOLS.filter(function(c){
    return (it.points||[]).some(function(pp){ return pp[c[0]]!==undefined && pp[c[0]]!==''; }); });
  var rows = (it.points||[]).map(function(pp){
    return use.map(function(c){ return esc(ifCell(pp[c[0]])); }); });
  h += '<div class="qrow"><span class="qsrc">'+esc(it.label||'')+'</span>'
     + csvBtn('if'+m.id+k, safeName(m.vendor+'_'+m.model+'_'+it.id)+'.csv',
              use.map(function(c){ return c[1]; }), rows, '이 판 CSV')
     + '</div>'
     + table({header:use.map(function(c){ return c[1]; }), rows:rows, raw:true,
              key:'if'+m.id+k});
  return h;
}

function renderObjectPointPanel(m){
  // 새 형식(판별 목록)이 있으면 그것이 본체다. 옛 평면 목록이 함께 있으면 뒤에 잇는다.
  var ifh = renderInterfaces(m);
  if(ifh && !(m.points||[]).length) return ifh;
  var pts = (m.points||[]).filter(function(p){return p.inst;});
  var hasNote = (m.points||[]).some(function(p){return p.note;});
  var hasSrc = (m.points||[]).some(function(p){return p.sourceFile && p.sourcePage;});
  var hasModbusMeta = (m.points||[]).some(function(p){return p.bacOid || p.modbusScaleFactor || p.modbusSignedFlag || p.modbusWritableFlag !== undefined;});
  var head = ['인스턴스','종류','단위','오브젝트명'];
  if(hasModbusMeta) head = head.concat(['BACOid','Scale','Signed','Writable']);
  if(hasNote) head.push('값 범위 · 상태');
  if(hasSrc) head.push('출처');
  var rows = (m.points||[]).map(function(p){
    var r = [esc(p.inst||''), esc(p.type), esc(p.unitDisp), esc(p.name)];
    if(hasModbusMeta) r = r.concat([
      esc(p.bacOid||''), esc(p.modbusScaleFactor||''),
      esc(p.modbusSignedFlag||''), esc(p.modbusWritableFlag === undefined ? '' : p.modbusWritableFlag)
    ]);
    if(hasNote) r.push(esc(p.note||''));
    if(hasSrc) r.push(srcLink(p.sourceFile, p.sourcePage,
      p.sourceFile ? (p.sourceFile + (p.sourcePage ? ' p'+p.sourcePage : '')) : ''));
    return r;
  });
  return ifh + sec('제조사 원문 오브젝트 목록', pts.length)
    + '<div class="guide"><b>L3 전체 포인트예요</b>'
    + '<p>BMS 자동 매핑과 시운전에 필요한 제조사 원문 오브젝트 목록입니다. 운영 화면에 전부 올리는 목록이 아니라, 상세 매핑의 원천입니다.</p></div>'
    + '<div class="qrow"><span class="qsrc">인스턴스 번호까지 문서에 확정된 L3 전체 목록</span>'
    + csvBtn('pt'+m.id, safeName(m.vendor+'_'+m.model)+'_오브젝트목록.csv',
             ['type','instance','name','unit','unitRaw','bacOid','modbusRegister','modbusScaleFactor','modbusBooleanFlag','modbusSignedFlag','modbusOffset','modbusWritableFlag','sourceFile','sourcePage','note'],
             (m.points||[]).map(function(p){
               return [p.type, p.inst||'', p.name, p.unit||'', p.unitRaw||'',
                       p.bacOid||'', p.modbusRegister||'', p.modbusScaleFactor||'',
                       p.modbusBooleanFlag||'', p.modbusSignedFlag||'',
                       p.modbusOffset||'', p.modbusWritableFlag === undefined ? '' : p.modbusWritableFlag,
                       p.sourceFile||'', p.sourcePage||'', p.note||'']; }),
             '오브젝트 목록 CSV')
    + '</div>'
    + kindChips([{header:head, rows:rows}])
    + table({header:head, rows:rows, raw:true});
}

function renderDocsPanel(m){
  return sec('근거 문서', (m.docs||[]).length)
    + table({header:['종류','제목','발행자','문서번호','발행','경로','상태'],
             rows:(m.docs||[]).map(function(d){
               return [d[0],d[1],d[2],d[3],d[4],'['+'열기'+']('+d[5]+')',d[6]];})});
}

function renderRawSpecPanel(m){
  var sts = (m.specTables || []).slice();
  if(!sts.length) return '<div class="msg"><b>원문표가 없어요</b><p>이 모델 문서에서는 사양 표를 찾지 못했어요.</p></div>';
  sts.forEach(function(x,i){ x._i = i; });
  var purpose = (D.purpose||{})[m.id] || {};
  var units = purpose.unitModels || [];
  var selectedUnit = units.length ? units[Math.min(usel[m.id] || 0, units.length-1)] : null;
  var kinds = KIND_ORDER.filter(function(k){
    return sts.some(function(x){ return (x.kind||'etc')===k; });
  });
  var kk = kinds.indexOf(ksel) >= 0 ? ksel : kinds[0];
  sts = sts.filter(function(x){ return (x.kind||'etc')===kk; });
  sts.sort(function(a,b){
    return rawTableRelevance(b, selectedUnit) - rawTableRelevance(a, selectedUnit)
        || summarizeMatrix(b).length - summarizeMatrix(a).length;
  });
  var si = Math.min(ssel, sts.length-1), t = sts[si];
  var h = sec('원문표', (m.specTables||[]).length)
    + rawBlindSpotGuide(selectedUnit)
    + '<div class="klist">' + kinds.map(function(k){
        var n = (m.specTables||[]).filter(function(x){ return (x.kind||'etc')===k; }).length;
        return '<button data-kk="'+k+'" aria-pressed="'+(k===kk)+'">'
          + esc(KIND_KO[k]) + '<span class="mn">' + n + '개</span></button>';
      }).join('')
    + '<span class="khint">' + esc(KIND_HINT[kk]||'') + '</span></div>'
    + specKindGuide(kk)
    + rawTableList(sts, si, selectedUnit);
  var uq = [];
  (t.quantities||[]).forEach(function(x){ if(x && uq.indexOf(x)<0) uq.push(x); });
  h += rawSpecGuide(t, kk)
    + '<div class="qrow">'
    + (t.orientation==='row' ? '<span class="qtag alt">행=항목 · 열=형번</span>' : '')
    + uq.map(function(x){ return '<span class="qtag">'+esc(QLABEL[x]||x)+'</span>'; }).join('')
    + '<span class="qsrc">' + srcLink(t.source, t.page, (t.source||'') + ' p'+t.page) + '</span>'
    + csvBtn('st'+m.id+t._i, safeName(m.model+'_'+(t.title||'표')+'_p'+t.page)+'.csv',
             t.header, t.rows, '이 표 CSV')
    + csvBtn('stall'+m.id+kk, safeName(m.model+'_'+KIND_KO[kk])+'_전체.csv',
             ['표','쪽','근거','행','열','값'],
             sts.reduce(function(acc,x){
               x.rows.forEach(function(r, ri){
                 r.forEach(function(v, ci){
                   if(v===''||v===null||v===undefined) return;
                   acc.push([x.title||'', x.page, x.source||'', ri+1,
                             x.header[ci]||('열'+(ci+1)), v]);
                 });
               });
               return acc;
             }, []),
             KIND_KO[kk]+' 전체 CSV')
    + '</div>'
    + table({header:t.orientation==='row' ? t.header : t.header.map(function(hh){
             var tt = termOf(hh);
             return tt ? '<span class="lbl '+simCls(tt.sim)+'"'+tipAttr(tt)+'>'
                         + esc(hh)+'</span>' : esc(hh);
           }),
           rows:(t.orientation==='row' ? t.rows.map(function(r){
             var tt = termOf(r[0]);
             return [tt ? '<span class="lbl '+simCls(tt.sim)+'"'+tipAttr(tt)+'>'
                          + esc(tt.ko)+'<i>'+esc(r[0])+'</i></span>'
                        : esc(r[0])].concat(r.slice(1).map(esc));
           }) : t.rows.map(function(r){ return r.map(esc); })),
           key:'st'+si+(t.source||''), raw:true});
  return h;
}

function renderAhuUnitModelCandidates(m){
  var purpose = (D.purpose||{})[m.id] || {};
  var rows = purpose.unitModels || extractAhuUnitModels(m);
  if(!rows.length) return '';
  var idx = Math.min(usel[m.id] || 0, rows.length-1);
  var curUnit = rows[idx];
  var view = uvw[m.id] || 'table';
  return sec('Unit Model Number별 정격 후보', rows.length)
    + '<div class="guide"><b>여기서 실제 장비 형번을 골라야 해요</b>'
    + '<p>제품군 문서에는 여러 형번의 값이 한꺼번에 들어 있습니다. 실제 현장 장비가 아래 형번 중 무엇인지 정해지면 그 형번의 풍량·냉방능력·조합 공조기를 한 줄로 좁힐 수 있습니다. 전압은 별도 전기 특성표에서 전원 코드와 함께 다시 확정해야 합니다.</p>'
    + '<p>단위는 원문표 라벨·단위 열에 적힌 것을 그대로 씁니다. 라벨에 단위가 없는 AHRI 정격(냉방능력·풍량)은 미국 카탈로그(I-P 단위계) 관례인 Btu/h·CFM으로 표기했습니다 — 환산: CFM×1.699=㎥/h · Btu/h×0.293=W.</p></div>'
    + '<div class="unitpick">' + rows.map(function(r,i){
        var line = unitRoleLabel(r);
        if(unitCapacity(r) !== '—') line += ' · ' + unitCapacity(r);
        if(unitAirflow(r) !== '—') line += ' · 풍량 ' + unitAirflow(r);
        var metric = unitCardMetric(r);
        return '<button class="ucard" data-ui="'+i+'" aria-pressed="'+(i===idx)+'">'
          + '<b>'+esc(unitCode(r))+'</b>'
          + '<span>'+esc(line)+'</span>'
          + (metric ? '<span>'+esc(metric)+'</span>' : '') + '</button>';
      }).join('') + '</div>'
    + renderAhuUnitDetail(curUnit, purpose.electricalRows || [], m)
    + sec('전체 Unit Model Number 표', rows.length)
    + '<div class="guide"><b>실제 장비를 고르는 기준표예요</b>'
    + '<p>현장 장비일람표나 자재승인원에 적힌 형번을 이 표에서 찾아 선택합니다. 선택한 형번의 정격값을 기본값 후보로 쓰고, 오브젝트 목록은 같은 프로파일 문서의 L3 매핑 근거로 씁니다. 문서에 없는 항목의 열은 표시하지 않고, <b>척도가 다른 단위는 열을 가릅니다</b> — 단위는 머리글에 있고 열 안은 같은 척도라 그대로 비교·정렬하면 됩니다. 상태 배지: <b>자동 추출</b>=문서에서 기계가 옮긴 제안값, <b>확인됨</b>=사람이 원문과 대조해 확정, <b>수기 입력</b>=문서 한계로 직접 채움.</p></div>'
    + '<div class="qrow"><span class="qsrc">Unit Model Number rating CSV: wide = simulator/BMS defaults, long = field QA/mapping</span>'
    + csvBtn('unitwide'+m.id, safeName(m.vendor+'_'+m.model)+'_unit-model-ratings_wide.csv',
             unitWideCsvHeader(m, rows), unitWideCsvRows(m, rows), 'Unit ratings wide CSV')
    + csvBtn('unitlong'+m.id, safeName(m.vendor+'_'+m.model)+'_unit-model-ratings_long.csv',
             unitLongCsvHeader(), unitLongCsvRows(m, rows), 'Unit ratings long CSV')
    + '</div>'
    + '<div class="uvwt">'
    +   '<button data-uvw="table" aria-pressed="'+(view!=='cards')+'">표로 보기</button>'
    +   '<button data-uvw="cards" aria-pressed="'+(view==='cards')+'">카드로 보기</button>'
    +   (view==='cards' ? '<span class="uvwn">카드는 훑어보며 고르는 용도예요 — 값 비교·정렬은 표가 정확합니다</span>' : '')
    + '</div>'
    + (view==='cards' ? unitCardGrid(rows, m, idx) : unitTable(rows, m))
}

// 전체 형번 표 — 열 구성·순서·라벨은 속성 사전(unit-schema.json)의 설비 클래스가 정본이고,
// 값이 하나도 없는 열은 만들지 않는다 (벤더마다 문서에 싣는 항목이 다르다)
function unitClassOf(m){
  var sch = D.unitSchema || {};
  return (sch.classes||{})[m.equipId] || {table: Object.keys(sch.features||{}), roles:{}};
}
function unitFeature(fid){ return ((D.unitSchema||{}).features||{})[fid] || {}; }
function unitFieldKo(fid, cls){
  // 설비별 라벨 오버라이드가 1순위 — 같은 속성이라도 설비마다 뜻이 다르다
  // (냉동기의 코일·팬 = 응축기 쪽 값)
  return ((cls||{}).labels||{})[fid] || unitFeature(fid).ko || fid;
}
var UNIT_STATUS = {verified:['확인됨','ok'], manual:['수기 입력','man'], extracted:['자동 추출','ext']};
function unitStatusBadge(r){
  var s = UNIT_STATUS[r.status||'extracted'] || [r.status, 'ext'];
  return '<span class="ustat '+s[1]+'">'+esc(s[0])+'</span>';
}
// 행에서 그 필드의 유효 단위 — 문서 단위(r.units)가 1순위, 없으면 관례 단위(convUnit)
function unitEffectiveUnit(r, fid){
  var v = r[fid];
  if(!v || v === '—') return null;
  return (r.units||{})[fid] || unitFeature(fid).convUnit || '';
}
function unitCsvFeatureOrder(m){
  var cls = unitClassOf(m);
  var features = (D.unitSchema||{}).features || {};
  var out = [];
  function add(fid){
    if(features[fid] && out.indexOf(fid) < 0) out.push(fid);
  }
  (cls.table||[]).forEach(add);
  (cls.detailExtra||[]).forEach(add);
  Object.keys(features).forEach(add);
  return out;
}
function unitCsvBaseHeader(){
  return ['modelId','equipmentId','vendor','model','unitModelNumber','unitNumberKind',
          'unitRole','status','sourceFile','sourcePage','sourceTable'];
}
function unitCsvBaseRow(m, r){
  return [m.id||'', m.equipId||'', m.vendor||'', m.model||'', unitCode(r),
          r.unitNumberKind||'', unitRole(r), r.status||'', r.sourceFile||'',
          r.sourcePage||'', r.sourceTable||''];
}
function unitWideCsvHeader(m, rows){
  var h = unitCsvBaseHeader();
  unitCsvFeatureOrder(m).forEach(function(fid){
    h.push(fid);
    h.push(fid+'Unit');
  });
  return h;
}

function modelButton(x, i, pre){
  // 프로토콜은 오른쪽 배지로 따로 보여주므로 이름에서는 뺀다 (중복 표기 방지)
  var base = x.selectorLabel || x.model;
  var lbl = base.slice(pre.length).replace(/^[\s—·-]+/,'')
             .replace(/\s*\((BACnet|LonTalk|Modbus)\)\s*$/i,'') || base;
  var pr = (x.comm||[]).map(function(c){return c[0];});
  var tail = pr.length ? '<span class="mpr">'+esc(pr.join('·'))+'</span>' : '';
  var n = (x.points||[]).length, sn = specCount(x);
  var th = x.photo ? '<img class="mth" src="'+x.photo+'" alt="">' : '';
  return '<button data-mi="'+i+'" aria-pressed="'+(i===mi)+'">'+th+esc(lbl)+tail
       + (n ? '<span class="mn">'+n+'</span>' : '')
       + (sn ? '<span class="ms">원문표 '+sn+'</span>' : '') + '</button>';
}

function unitWideCsvRows(m, rows){
  var fids = unitCsvFeatureOrder(m);
  return rows.map(function(r){
    var row = unitCsvBaseRow(m, r);
    fids.forEach(function(fid){
      var v = r[fid];
      row.push((v && v !== '—') ? v : '');
      row.push((v && v !== '—') ? ((r.units||{})[fid] || unitFeature(fid).convUnit || '') : '');
    });
    return row;
  });
}
function unitLongCsvHeader(){
  return unitCsvBaseHeader().concat(['fieldId','fieldKo','value','unit']);
}
function unitLongCsvRows(m, rows){
  var fids = unitCsvFeatureOrder(m);
  var out = [];
  rows.forEach(function(r){
    fids.forEach(function(fid){
      var v = r[fid];
      if(!v || v === '—') return;
      out.push(unitCsvBaseRow(m, r).concat([
        fid,
        unitFieldKo(fid, unitClassOf(m)),
        v,
        (r.units||{})[fid] || unitFeature(fid).convUnit || ''
      ]));
    });
  });
  return out;
}
function unitCols(m, rows){
  var cls = unitClassOf(m);
  var cols = [
    ['용량대', unitCapacity],
    ['Unit Model Number', unitCode],
    ['구분', function(r){ return unitRoleLabel(r, cls); }],
    ['상태', unitStatusBadge, true],
  ];
  (cls.table||[]).forEach(function(fid){
    if(fid === 'capacityClass') return;   // 첫 열(용량대)로 특별 취급
    // 척도가 다른 값(MBh·Btu/h·kW, CFM·m³/s·m³/h)은 한 열에 섞지 않는다 —
    // 행에 실제로 나온 단위마다 열을 가르고, 단위는 셀이 아니라 머리글에 올린다
    // (ETIM 원칙: 속성 하나 = 단위 하나. 열 안은 같은 척도라 비교·정렬이 성립)
    var units = [];
    rows.forEach(function(r){
      var u = unitEffectiveUnit(r, fid);
      if(u !== null && units.indexOf(u) < 0) units.push(u);
    });
    units.forEach(function(u){
      cols.push([unitFieldKo(fid, cls) + (u ? ' ('+esc(u)+')' : ''),
                 function(r){
                   return unitEffectiveUnit(r, fid) === u ? r[fid] : '—';
                 }]);
    });
  });
  cols.push(['근거표', unitSourceLink, true]);
  return cols;
}
function unitTable(rows, m){
  // 값 없는 열 제거는 unitCols 가 이미 한다 — 단위가 안 나온 필드는 열 자체가 없다
  var active = unitCols(m, rows);
  return table({header:active.map(function(c){ return c[0]; }),
                // 세 번째 원소가 true 인 열(상태·근거표)은 조각을 이미 만들어 와서 그대로 낸다
                rows:rows.map(function(r){ return active.map(function(c){
                  var v = c[1](r) || '—';
                  return c[2] ? v : esc(v);
                }); }),
                key:'ahu-unit-models'+m.id, raw:true, nopage:false, compact:true});
}

// 카드 보기 — 사진과 핵심 값으로 훑어보며 고르는 용도. 문서에 형번별 사진은 없어서
// 시리즈 대표 사진을 상속해 붙인다 (지어내지 않는다는 원칙 그대로).
function unitCardGrid(rows, m, idx){
  var cls = unitClassOf(m);
  return '<div class="ugrid">' + rows.map(function(r, i){
    var vals = [];
    if(unitCapacity(r) !== '—') vals.push(unitCapacity(r));
    if(unitAirflow(r) !== '—') vals.push('풍량 ' + unitAirflow(r));
    var metric = unitCardMetric(r);
    if(metric) vals.push(metric);
    return '<button class="ucard gcard" data-ui="'+i+'" aria-pressed="'+(i===idx)+'">'
      + (m.photo ? '<span class="gimg"><img src="'+m.photo+'" alt="" loading="lazy">'
                   + '<i>시리즈 대표 사진</i></span>' : '')
      + '<b>'+esc(unitCode(r))+'</b>'
      + '<span class="grole">'+esc(unitRoleLabel(r, cls))+'</span>'
      + unitStatusBadge(r)
      + '<span class="gvals">'+esc(vals.join(' · ')||'문서에 정격 없음')+'</span>'
      + '</button>';
  }).join('') + '</div>';
}

function renderAhuUnitDetail(r, electricalRows, m){
  if(!r) return '';
  var cls = unitClassOf(m);
  var items = [
    ['구분', unitRoleLabel(r, cls)],
    ['상태', unitStatusBadge(r), true],
    ['용량대', unitCapacity(r)],
    ['Unit Model Number', unitCode(r)],
    ['정격 풍량', unitAirflow(r)],
    ['근거', unitSourceLink(r), true],
  ];
  // 역할별 앞세울 속성 → 클래스 공통 부가 속성 순 — 구성은 스키마
  // (classes.roles.detail / detailExtra)가 정본이고, 값이 있을 때만 칸을 만든다
  var seen = {};
  items.forEach(function(x){ seen[x[0]] = 1; });
  var order = (((cls.roles||{})[unitRole(r)]||{}).detail || []).concat(cls.detailExtra||[]);
  order.forEach(function(fid){
    var ko = unitFieldKo(fid, cls);
    if(seen[ko]) return;
    seen[ko] = 1;
    var v = valueWithUnit(r, fid, unitFeature(fid).convUnit||'');
    if(v && v !== '—') items.push([ko, v]);
  });
  if(r.unitNumberKind === 'capacityClass')
    items.push(['형번 표기', '문서가 이 유닛을 형번 없이 톤수로만 구분해요']);
  // 문서에 없는 값('—')은 칸을 만들지 않는다 — 신원 항목만 항상 남긴다
  var KEEP = {'구분':1, '상태':1, 'Unit Model Number':1, '근거':1, '형번 표기':1};
  items = items.filter(function(x){ return KEEP[x[0]] || (x[1] && x[1] !== '—'); });
  return '<div class="udetail"><h4>'+esc(unitCode(r))+'</h4><div class="uvals">'
    + items.map(function(x){
      // 세 번째 원소가 true 인 항목(근거)은 링크 조각을 이미 만들어 와서 그대로 낸다
      return '<div class="uval"><div class="k">'+esc(x[0])+'</div><div class="v">'
        + (x[2] ? String(x[1]||'—') : esc(x[1]||'—'))+'</div></div>';
    }).join('') + '</div></div>'
    + renderUnitElectricalRows(r, electricalRows);
}


function unitCode(r){ return r.unitModelNumber || r.unitModel || '—'; }
function unitRole(r){ return r.unitRole || (/TWE/i.test(unitCode(r)) ? 'airHandler' : 'condensingUnit'); }
function unitRoleLabel(r, cls){
  // 역할 이름도 스키마 클래스(classes.roles[].ko)가 1순위 — 설비마다 부르는 말이 다르다
  var role = unitRole(r);
  var d = ((cls||{}).roles||{})[role];
  if(d && d.ko) return d.ko;
  return {airHandler:'공기측 유닛', condensingUnit:'실외/응축 유닛',
          packagedUnit:'일체형(패키지) 유닛', chillerUnit:'냉동기 유닛'}[role]
      || '실외/응축 유닛';
}
function unitCapacity(r){ return r.capacityClass || r.tons || '—'; }
function unitAirflow(r){ return valueWithUnit(r, 'ratedAirflow', 'CFM') !== '—'
  ? valueWithUnit(r, 'ratedAirflow', 'CFM') : (r.airflow || '—'); }
function unitCooling(r){
  var v = r.grossCoolingCapacity || r.cooling || '—';
  if(v === '—') v = r.ahriNetCoolingCapacity || '—';
  return v;
}
// 값 + 단위. 단위는 ① 문서 라벨/단위 열에서 가져온 것(r.units) ② 라벨에 단위가 없는
// AHRI 정격의 I-P 관례(conv — 냉방 Btu/h·풍량 CFM, 안내문에 근거 표기) 순서다.
function valueWithUnit(r, field, conv){
  var v = r[field];
  if(!v || v === '—') return '—';
  var u = (r.units||{})[field] || conv || '';
  return u ? v + ' ' + u : v;
}
function coolingWithUnit(r){
  if(r.grossCoolingCapacity && r.grossCoolingCapacity !== '—')
    return valueWithUnit(r, 'grossCoolingCapacity', 'Btu/h');
  if(r.ahriNetCoolingCapacity && r.ahriNetCoolingCapacity !== '—')
    return valueWithUnit(r, 'ahriNetCoolingCapacity', 'Btu/h');
  return r.cooling || '—';
}
function unitCardMetric(r){
  if(unitRole(r) === 'airHandler'){
    return '팬 ' + valueWithUnit(r, 'fanMotorHp', 'HP')
      + ' · 코일 ' + (r.coilRowsFpi || '—');
  }
  // 문서에 있는 값만 보여준다 — 냉방 → 용량 단계 → 효율 순. 다 없으면 줄 자체를 뺀다.
  if(coolingWithUnit(r) !== '—') return '냉방 ' + coolingWithUnit(r);
  if(r.capacitySteps && r.capacitySteps !== '—')
    return '용량 단계 ' + valueWithUnit(r, 'capacitySteps', '%');
  if(r.eer && r.eer !== '—') return 'EER ' + r.eer;
  if(r.ieer && r.ieer !== '—') return 'IEER ' + r.ieer;
  return '';
}
function unitSource(r){
  if(r.source) return r.source;
  return (r.sourceTable || '').replace(/^Table\s*\d+\.\s*/,'') + (r.sourcePage ? ' p'+r.sourcePage : '');
}
// 출처 클릭 → 수집 원본 PDF(pipeline/data/raw)의 해당 쪽을 새 탭으로 연다.
// source 의 '#…' 조각은 파이프라인이 표 구분용으로 붙인 것이라 파일명에서 뗀다.
// data/raw 는 gitignore 라 수집을 돌린 PC에서만 열린다 — 파일이 없으면 404 다.
function srcHref(file, page){
  if(!file || !/\.pdf/i.test(String(file))) return '';
  return '../pipeline/data/raw/' + encodeURIComponent(String(file).split('#')[0])
    + (page ? '#page='+page : '');
}
function srcLink(file, page, text){
  var h = srcHref(file, page);
  if(!h) return esc(text);
  return '<a class="srclink" href="'+h+'" target="_blank" rel="noopener" '
    + 'title="원문 PDF 해당 쪽 열기">'+esc(text)+'</a>';
}
function unitSourceLink(r){
  return srcLink(r.sourceFile, r.sourcePage || r.page, unitSource(r));
}

function renderUnitElectricalRows(unit, rows){
  var picked = electricalRowsForUnit(unit, rows);
  if(!picked.length) return '';
  return sec('선택 형번 전기 특성', picked.length)
    + '<div class="guide"><b>전기 약어는 이렇게 읽으면 돼요</b>'
    + '<p><b>RLA</b>는 압축기가 운전 중 먹는 전류, <b>LRA</b>는 기동 순간 전류, '
    + '<b>FLA</b>는 팬 모터 정격전류, <b>MCA</b>는 최소 전선 용량, <b>MOP</b>는 최대 차단기 용량 — '
    + '전압(V) 열을 뺀 값은 전부 전류(A)입니다. '
    + '원문표의 여러 모델/전압 묶음을 한 행씩 쪼개서 보여줍니다.</p></div>'
    + table({header:['유닛','전압','상','모터 구분','압축기1 RLA','압축기1 LRA','압축기2 RLA','압축기2 LRA','팬 FLA','팬 LRA','MCA','MOP','근거'],
             rows:picked.map(electricalRow), key:'ahu-electrical'+unitCode(unit), raw:true, nopage:true, compact:true});
}

function electricalRowsForUnit(unit, rows){
  if(!unit || !rows) return [];
  var re = unitElectricalRegex(unit);
  return rows.filter(function(r){ return re.test(r.unitModelNumber||''); }).slice(0, 12);
}

function unitElectricalRegex(unit){
  var code = unitCode(unit);
  var tta = code.match(/\bTTA(\d{4})\*([A-Z])\*/i);
  if(tta) return new RegExp('^TTA' + tta[1] + '.*' + tta[2] + '$', 'i');
  var exact = code.match(/\b(TTA|TWE)\d{4}[A-Z0-9]*/i);
  if(exact) return new RegExp('^' + exact[0].replace(/([.*+?^${}()|\[\]\\])/g,'\\$1'), 'i');
  // 일반형: 계열 끝 2글자+숫자 (T/YSC036G3,4,W → SC036, WHJ150 → HJ150).
  // 전기표는 T/YSC·W/DHJ처럼 첫 글자만 다른 병기 표기를 쓰므로 뒷부분으로 맞춘다.
  var generic = code.match(/([A-Z]{2})(\d{2,})/i);
  if(generic) return new RegExp(generic[1] + generic[2], 'i');
  return /$^/;
}

function electricalRow(r){
  var cells = [
    r.unitModelNumber,
    r.voltage,
    r.phase,
    motorSetLabel(r.motorSet),
    cleanElecValue(r.compressor1Rla),
    cleanElecValue(r.compressor1Lra),
    cleanElecValue(r.compressor2Rla),
    cleanElecValue(r.compressor2Lra),
    cleanElecValue(r.fanFla),
    cleanElecValue(r.fanLra),
    cleanElecValue(r.mca),
    cleanElecValue(r.mop),
  ].map(esc);
  cells.push(srcLink(r.sourceFile, r.sourcePage,
    (r.sourceTable || '').replace(/^Table\s*\d+\.\s*/,'') + (r.sourcePage ? ' p'+r.sourcePage : '')));
  return cells;
}

function cleanElecValue(x){
  return x && x !== 'N/A' && x !== '—' ? x : '—';
}

function motorSetLabel(x){
  return {
    compressorAndCondenserFan:'압축기/응축팬',
    standardEvaporatorFan:'표준 공기측 팬',
    oversizedEvaporatorFan:'대형 공기측 팬'
  }[x] || (x || '—');
}

function rawTableList(sts, si, selectedUnit){
  var groups = [
    ['selected', '현재 선택한 형번'],
    ['condensing', '실외/응축 유닛'],
    ['airHandler', '공기측 유닛'],
    ['electrical', '전기 특성'],
    ['performance', '조건별 성능'],
    ['dimension', '치수·설치'],
    ['accessory', '부속·참고']
  ];
  var grouped = {};
  groups.forEach(function(g){ grouped[g[0]] = []; });
  sts.forEach(function(t, i){
    var rel = rawTableHasSelectedUnit(t, selectedUnit);
    var key = rel ? 'selected' : rawTableCategory(t);
    if(!grouped[key]) grouped[key] = [];
    grouped[key].push({table:t, index:i, rel:rel});
  });
  return '<div class="sgroups">' + groups.map(function(g){
    var list = grouped[g[0]] || [];
    if(!list.length) return '';
    return '<div class="sgroup"><h4>'+esc(g[1])+'</h4><div class="slist">'
      + list.map(function(item){
        var x = item.table;
        var title = rawTableDisplayTitle(x);
        var raw = (x.title||'표 '+(item.index+1)).replace(/^Table\s*\d+\.\s*/,'');
        var qty = firstQuantityLabel(x);
        return '<button data-si="'+item.index+'" aria-pressed="'+(item.index===si)+'">'
          + '<span class="stxt"><b>'+esc(title)+'</b><i>'+esc(raw)+'</i></span>'
          + (item.rel?'<span class="ms">현재 형번 포함</span>':'')
          + (qty?'<span class="ms">'+esc(qty)+'</span>':'')
          + '</button>';
      }).join('') + '</div></div>';
  }).join('') + '</div>';
}

function rawTableHasSelectedUnit(t, unit){
  if(!unit) return false;
  var compact = compactModelCode(unitCode(unit));
  var source = unit.sourceTable || unit.source || '';
  var text = ((t.title||'') + ' ' + (t.header||[]).join(' ') + ' '
           + (t.rows||[]).slice(0,12).map(function(r){ return (r||[]).join(' '); }).join(' '));
  if(source && (t.title||'') === source) return true;
  if(compact && text.indexOf(compact) >= 0) return true;
  return !!(compact && fuzzyModelRegex(compact).test(text));
}

function rawTableCategory(t){
  var text = ((t.title||'') + ' ' + (t.header||[]).join(' ')).toLowerCase();
  if(/electrical|voltage|motor|mca|mop|rla|fla|compressor.*fan/.test(text)) return 'electrical';
  if(/air handler|twe|szvav|evaporator fan/.test(text)) return 'airHandler';
  if(/condensing unit|tta|compressor/.test(text)) return 'condensing';
  if((t.kind||'') === 'perf' || /performance|capacity correction|airflow|static pressure/.test(text)) return 'performance';
  if((t.kind||'') === 'dim' || /dimension|clearance|curb|weight|shipping/.test(text)) return 'dimension';
  return 'accessory';
}

function rawTableDisplayTitle(t){
  var raw = (t.title||'').replace(/^Table\s*\d+\.\s*/,'');
  var cap = capacityRangeFromTitle(raw);
  var text = raw.toLowerCase();
  if(/electrical|voltage|mca|mop|rla|fla/.test(text)) return (cap ? cap + ' ' : '') + '전기 특성';
  if(/air handler|twe|szvav|evaporator fan/.test(text)) return (cap ? cap + ' ' : '') + '공기측 유닛 기본 정격';
  if(/condensing unit|tta|compressor/.test(text)) return (cap ? cap + ' ' : '') + '실외/응축 유닛 기본 정격';
  if(/performance/.test(text)) return (cap ? cap + ' ' : '') + '조건별 성능표';
  if(/dimension|clearance|curb|weight|shipping/.test(text)) return (cap ? cap + ' ' : '') + '치수·설치 표';
  return raw || '원문표';
}

function capacityRangeFromTitle(title){
  var m = String(title||'').match(/(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*tons?/i);
  if(m) return m[1] + '-' + m[2] + '톤';
  m = String(title||'').match(/(\d+(?:\.\d+)?)\s*tons?/i);
  return m ? m[1] + '톤' : '';
}

function firstQuantityLabel(t){
  var qs = (t.quantities||[]).filter(Boolean);
  return qs.length ? '포함값: ' + (QLABEL[qs[0]] || qs[0]) : '';
}

function rawBlindSpotGuide(unit){
  var target = unit ? unitCode(unit) : '선택한 Unit Model Number';
  return '<div class="guide"><b>여기는 값을 고르는 화면이 아니라 근거를 확인하는 화면이에요</b>'
    + '<p>블라인드 스팟은 세 가지입니다. 첫째, 프로파일 모델과 실제 장비 형번이 다릅니다. '
    + '둘째, 원문표 한 장에는 여러 형번·전원·옵션이 함께 들어갑니다. '
    + '셋째, 실외/응축 유닛과 공기측 유닛은 보는 정격이 다릅니다. '
    + '따라서 먼저 <b>형번·정격</b> 탭에서 <code>'+esc(target)+'</code>를 고르고, 여기서는 그 값이 어느 원문표에서 왔는지만 확인합니다.</p></div>';
}

function rawTableRelevance(t, unit){
  if(!unit) return 0;
  var code = unitCode(unit);
  var compact = compactModelCode(code);
  var source = unit.sourceTable || unit.source || '';
  var text = ((t.title||'') + ' ' + (t.header||[]).join(' ') + ' '
           + (t.rows||[]).slice(0,12).map(function(r){ return (r||[]).join(' '); }).join(' '));
  var score = 0;
  if(source && (t.title||'') === source) score += 50;
  if(compact && text.indexOf(compact) >= 0) score += 30;
  if(compact && fuzzyModelRegex(compact).test(text)) score += 20;
  if(unitRole(unit) === 'airHandler' && /air handler|TWE|evaporator fan|SZVAV/i.test(text)) score += 6;
  if(unitRole(unit) !== 'airHandler' && /condensing unit|TTA|compressor/i.test(text)) score += 6;
  return score;
}

function compactModelCode(code){
  var m = String(code||'').match(/\b(TTA|TWE)\d{4}[A-Z0-9*\/-]*/i);
  return m ? m[0].replace(/[*,\/-].*$/,'') : '';
}

function fuzzyModelRegex(code){
  var s = String(code||'').replace(/([.*+?^${}()|\[\]\\])/g,'\\$1');
  if(!s) return /$^/;
  return new RegExp(s.replace(/\\\*/g,'.*').replace(/[A-Z]$/i,'.*'), 'i');
}

function extractAhuUnitModels(m){
  var out = [];
  (m.specTables||[]).forEach(function(t){
    if((t.kind||'etc') !== 'rating' || t.orientation !== 'row') return;
    if(!/general data/i.test(t.title||'')) return;
    var first = (t.rows||[])[0] || [];
    var rows = t.rows || [];
    for(var c=1;c<(t.header||[]).length;c++){
      var unit = cleanModelLabel(first[c]);
      if(!unit) continue;
      out.push({
        tons: t.header[c] || '—',
        unitModel: unit,
        airHandler: valueForLabel(rows, /matched air handler$/i, c) || '—',
        airflow: valueForLabel(rows, /AHRI Rated Airflow/i, c) || valueForLabel(rows, /^CFM$/i, c) || '—',
        cooling: valueForLabel(rows, /Gross Cooling Capacity - System/i, c) || '—',
        ahriCooling: valueForLabel(rows, /AHRI Net Cooling Capacity/i, c) || '—',
        eer: valueForLabel(rows, /Matched Air Handler \(EER\)|System \(EER\)/i, c) || '—',
        source: (t.title||'').replace(/^Table\s*\d+\.\s*/,'') + ' p' + (t.page||''),
      });
    }
  });
  return out;
}

function cleanModelLabel(s){
  s = String(s||'').replace(/\s+/g,' ').trim();
  if(!s || /^system data|cooling performance|efficiency$/i.test(s)) return '';
  return s;
}

function valueForLabel(rows, re, col){
  for(var i=0;i<rows.length;i++){
    var r = rows[i] || [];
    if(re.test(String(r[0]||''))) return String(r[col]||'').trim();
  }
  return '';
}

function statusPill(s){
  if(s === 'matched') return '<span class="pill y">확정</span>';
  if(s === 'candidate') return '<span class="pill c">후보</span>';
  return '<span class="pill n">없음</span>';
}

function renderAhuOperatorView(m){
  var picked = [], seen = {};
  VIEW_PROFILES.ahu.forEach(function(rule){
    var p = (m.points||[]).find(function(x){ return !seen[x.name] && rule[1].test(x.name||''); });
    if(!p) return;
    seen[p.name] = 1;
    picked.push([rule[0], p.type, p.unitDisp, p.name, p.inst||'']);
  });
  var h = sec('관제 화면 우선 후보', picked.length)
    + '<div class="msg" style="margin:0 18px 10px"><p>'
    + '<b>L2</b>는 운영자가 보는 기본 화면, <b>L3</b>는 제조사 통신문서 전체예요. '
    + '아래 표는 L3 전체 목록에서 공조기 화면에 먼저 올릴 만한 것만 골라 본 후보예요. '
    + '나머지 원문 오브젝트는 아래 상세 목록에 그대로 남겨 둡니다.</p></div>';
  if(!picked.length) return h;
  return h + table({header:['화면 이름','종류','단위','원문 오브젝트명','인스턴스'],
                    rows:picked, key:'ahuop'+m.id, nopage:true});
}

function specKindGuide(kind){
  var title = {
    rating:'모델별 기본 정격표예요',
    perf:'성능표는 운전 조건을 넣고 찾아보는 표예요',
    dim:'치수·중량은 설치와 반입 검토용이에요',
    etc:'부속·참고는 선정·배선·호환 확인용이에요'
  }[kind] || '원문 표';
  var body = {
    rating:'제조사 PDF에서 Unit Model Number별 풍량, 냉방능력, 효율 같은 기본값을 적어 둔 표입니다. 여러 형번이나 전원 옵션이 함께 보이면 전체를 읽지 말고 선택한 형번과 같은 열/행만 따라가면 됩니다.',
    perf:'예: 외기온도별 냉방능력, 풍량별 압력손실처럼 조건에 따라 값이 바뀝니다. “정답 하나”가 아니라 조건을 선택해서 읽는 표입니다.',
    dim:'예: 폭, 깊이, 높이, 중량입니다. BMS 제어나 에너지 계산보다 설치 공간, 반입, 유지보수 동선 확인에 씁니다.',
    etc:'예: 부속품, 배선, 호환표입니다. 자동 매핑과 시뮬레이터에는 보통 바로 쓰지 않고, 시운전·구매 확인 때 참고합니다.'
  }[kind] || '';
  return '<div class="guide"><b>'+esc(title)+'</b><p>'+esc(body)+'</p></div>';
}

function rawSpecGuide(t, kind){
  var evidence = rawSpecEvidence(t);
  if(!evidence.length && kind !== 'rating') return '';
  var title = kind === 'rating'
    ? '선택한 형번의 열/행만 보면 돼요'
    : '이 표를 읽는 기준';
  var body = kind === 'rating'
    ? '원문표에는 여러 모델명, 용량대, 전원 옵션이 함께 들어갑니다. 형번·정격 탭에서 고른 Unit Model Number와 같은 열 또는 같은 행만 근거로 보면 됩니다.'
    : '조건별 성능표와 치수표는 시뮬레이터 기본값을 바로 확정하는 표가 아닙니다. 필요한 조건이나 설치 조건을 정한 뒤 근거로 확인합니다.';
  return '<div class="guide"><b>'+esc(title)+'</b><p>'+esc(body)+'</p>'
       + (evidence.length ? '<div class="why">'+evidence.map(function(x){
           return '<span>'+esc(x)+'</span>';
         }).join('')+'</div>' : '') + '</div>';
}

function rawSpecEvidence(t){
  var text = ((t.title||'') + ' ' + (t.header||[]).join(' ') + ' '
           + (t.rows||[]).slice(0,6).map(function(r){ return (r||[]).join(' '); }).join(' '));
  var out = [];
  var modelHits = text.match(/\b[A-Z]{2,5}\d{3,5}[A-Z0-9*\/-]*/g) || [];
  var voltHits = text.match(/\b(?:200|208|230|380|460|575)(?:-\d+)?\b/g) || [];
  var tonHits = text.match(/\b\d+(?:\.\d+)?\s*(?:Tons?|ton)\b/gi) || [];
  if(unique(modelHits).length >= 2) out.push('여러 형번');
  if(unique(voltHits).length >= 2) out.push('여러 전원 옵션');
  if(unique(tonHits).length >= 2 || /\b\d+(?:\.\d+)?\s*[-–]\s*\d+(?:\.\d+)?\s*tons?\b/i.test(text))
    out.push('여러 용량대');
  if(/standard|high static|oversized|electric heat|steam|hot water|option/i.test(text))
    out.push('옵션별 값');
  return out;
}

function unique(list){
  var seen = {}, out = [];
  list.forEach(function(x){ var k=String(x).toLowerCase(); if(!seen[k]){seen[k]=1; out.push(x);} });
  return out;
}

var QLABEL = {power:'전력', current:'전류', voltage:'전압', frequency:'주파수',
  efficiency:'효율', loss:'손실', capacity:'용량', airflow:'풍량', pressure:'압력',
  speed:'회전수', torque:'토크', temperature:'온도', weight:'중량',
  dimension:'치수', noise:'소음', protection:'보호등급'};

// 영문 사양 이름 → {한글, 설명, 시뮬레이터 쓰임새}. 못 알아본 것은 null 을 준다
// (지어내지 않는다). 사전은 data/spec-terms.json 에 있다.
var TERMS = (D.terms||[]).map(function(t){
  return {re:new RegExp(t[0],'i'), ko:t[1], desc:t[2], sim:t[3], cat:t[4]||'기타'};
});
function termOf(label){
  var s = String(label||'').trim();
  for(var i=0;i<TERMS.length;i++) if(TERMS[i].re.test(s)) return TERMS[i];
  return null;
}
var SIMLBL = {3:'시뮬레이터 계산에 직접 들어가요', 2:'한계·조건으로 쓰여요',
              1:'선정에만 쓰여요 — 계산에는 안 써요'};
// 별표 대신 **색**으로 가른다. 뜻은 마우스를 올렸을 때만 띄운다 —
// 설명을 늘 펼쳐 두면 줄이 길어져 값이 눈에 안 들어온다.
function tipAttr(term, orig){
  if(!term) return ' data-tip="' + esc('사전에 없는 항목이라 원문 그대로 둡니다') + '"';
  return ' data-tip="' + esc(term.ko + ' — ' + term.desc + '\n' + SIMLBL[term.sim]) + '"';
}
function simCls(n){ return n===3 ? 'k3' : (n===2 ? 'k2' : 'k1'); }

// 제품 데이터시트의 관례 구성으로 낸다: **핵심 요약 → 분류별 상세 → 참고는 접기**.
// 앞서는 수십 줄을 한 표에 그냥 늘어놓아 무엇부터 봐야 할지 알 수 없었다.
var CATORD = ['전기','성능','제어·동작','물리','설치·환경','기타'];

// 행렬형 사양 표(행=형번, 열=속성)는 값이 여러 줄이라 타일 하나로 못 줄인다.
// 대신 **열마다 숫자 범위**를 뽑아 '이 표가 무엇을 담고 있는지'를 한 줄로 보여 준다.
// 카탈로그에서 하이픈은 거의 언제나 '범위'나 '구분'이지 음수 부호가 아니다.
// '208-230 460 575'(전압 선택지)를 -230 으로 읽어 전압 범위가 '−230 ~ 575' 로
// 나왔다. 숫자 바로 뒤에 붙은 하이픈은 부호로 보지 않는다.
function numsIn(list){
  var out = [];
  list.forEach(function(v){
    var s = String(v).replace(/,/g,'').replace(/(\d)\s*[-–]\s*(?=\d)/g, '$1 ');
    var m = s.match(/-?\d+(\.\d+)?/g);
    if(m) m.forEach(function(x){ var n=parseFloat(x); if(isFinite(n)) out.push(n); });
  });
  return out;
}
function fmtNum(n){
  return (Math.abs(n)>=100 || n===Math.round(n)) ? String(Math.round(n)) : String(n);
}
function summarizeMatrix(t){
  var out = [];
  var isRow = t.orientation === 'row';
  var n = isRow ? t.rows.length : t.header.length;
  for(var i=0;i<n;i++){
    var label = isRow ? (t.rows[i]||[])[0] : t.header[i];
    var term = termOf(label);
    if(!term || term.sim !== 3) continue;
    var vals = isRow ? (t.rows[i]||[]).slice(1)
                     : t.rows.map(function(r){ return r[i]; });
    var ns = numsIn(vals.filter(Boolean));
    if(!ns.length) continue;
    var lo = Math.min.apply(null, ns), hi = Math.max.apply(null, ns);
    out.push({ko:term.ko, orig:label, desc:term.desc,
              val: lo===hi ? fmtNum(lo) : fmtNum(lo)+' – '+fmtNum(hi)});
    if(out.length >= 8) break;
  }
  return out;
}
function matrixTiles(t){
  var sum = summarizeMatrix(t);
  if(!sum.length) return '';
  return '<div class="tiles">' + sum.map(function(x){
    return '<div class="tile" title="'+esc(x.orig+' — '+x.desc)+'">'
         + '<div class="tk">'+esc(x.ko)+'</div>'
         + '<div class="tv">'+esc(x.val)+'</div>'
         + '<div class="tn">'+esc(x.orig)+'</div></div>';
  }).join('') + '</div>';
}

function renderSpecSheet(spec, key){
  var rows = spec.map(function(r){ return {r:r, t:termOf(r[0])}; });
  var core = rows.filter(function(x){ return x.t && x.t.sim===3; });
  var h = '';

  // 1) 핵심 요약 — 시뮬레이터가 바로 쓰는 값만 큰 글씨로
  if(core.length){
    // 같은 뜻이 여러 항목으로 잡히면 첫 것만 (구동 시간이 두 줄로 나왔다)
    var seen = {}, pick = [];
    core.forEach(function(x){
      if(seen[x.t.ko]) return;
      seen[x.t.ko] = 1; pick.push(x);
    });
    h += '<div class="tiles">' + pick.slice(0,8).map(function(x){
      // 괄호 환산값·조건은 잘라 큰 글씨를 짧게. 값에 이미 단위가 있으면 또 붙이지 않는다
      var val = String(x.r[1]).replace(/\s*\[[^\]]*\]/g,'')
                  .replace(/\s*@.*$/,'').replace(/\s*,.*$/,'')
                  .replace(/\s*\bNote:.*$/i,'').replace(/\s*\(.*$/,'').trim();
      // 벤더가 값 칸에 문장을 넣어 두면 타입 타일이 한 글자씩 세로로 늘어진다.
      // 요약은 짧아야 요약이다 — 넘치면 자르고 전문은 아래 상세 표에 그대로 있다.
      if(val.length > 30) val = val.slice(0,29).trim() + '…';
      var u = (x.r[2]==='—'||!x.r[2]) ? ''
            : (val.toLowerCase().indexOf(String(x.r[2]).toLowerCase())>=0 ? '' : x.r[2]);
      return '<div class="tile" title="'+esc(x.r[0]+' — '+x.t.desc)+'">'
           + '<div class="tk">'+esc(x.t.ko)+'</div>'
           + '<div class="tv'+(val.length>13?' tvl':'')+'">'
           + esc(val)+(u?'<small>'+esc(u)+'</small>':'')+'</div>'
           + '<div class="tn">'+esc(x.r[0])+'</div></div>';
    }).join('') + '</div>';
  }

  // 2) 분류별 상세 — 참고(sim=1)와 사전에 없는 항목은 아래로 내린다
  var main = rows.filter(function(x){ return x.t && x.t.sim>=2; });
  var rest = rows.filter(function(x){ return !x.t || x.t.sim<2; });
  var byCat = {};
  main.forEach(function(x){ (byCat[x.t.cat] = byCat[x.t.cat]||[]).push(x); });
  CATORD.forEach(function(c){
    if(!byCat[c]) return;
    h += '<div class="cath">'+esc(c)+'<b>'+byCat[c].length+'</b></div>'
       + table({header:['항목','값','단위'],
                rows:byCat[c].map(function(x){
                  return ['<span class="lbl '+simCls(x.t.sim)+'"'+tipAttr(x.t)+'>'
                          + esc(x.t.ko)+'<i>'+esc(x.r[0])+'</i></span>',
                          '<span class="val '+simCls(x.t.sim)+'">'+esc(x.r[1])+'</span>',
                          esc(x.r[2])];
                }), key:key+c, raw:true, nopage:true});
  });

  // 3) 참고·미등록 — 접어 둔다. 필요할 때만 편다
  if(rest.length){
    h += '<details class="more"><summary>설치·인증 등 참고 항목 '
       + rest.length + '개 <i>(시뮬레이터 계산에는 쓰지 않아요)</i></summary>'
       + table({header:['항목','값','단위'],
                rows:rest.map(function(x){
                  return ['<span class="lbl k1"'+tipAttr(x.t)+'>'
                          + esc(x.t ? x.t.ko : x.r[0]) + (x.t?'<i>'+esc(x.r[0])+'</i>':'')
                          + '</span>',
                          '<span class="val k1">'+esc(x.r[1])+'</span>', esc(x.r[2])];
                }), key:key+'rest', raw:true, nopage:true})
       + '</details>';
  }
  return h;
}

function specCount(m){
  return (m.specTables||[]).length + (m.variants||[]).length + ((m.spec||[]).length?1:0);
}
function hasSpec(m){ return specCount(m) > 0; }

function sec(t,n){ return '<div class="sec">'+esc(t)+(n?' <b>'+n+'</b>':'')+'</div>'; }

function render(){
  markNav();
  var html;
  if(searchAll_on && term.length>=2) html = renderSearch();
  else if(cur==='home') html = renderHome();
  else if(String(cur).indexOf('v:')===0) html = renderVendor(String(cur).slice(2));
  else html = renderEquip(eqById(cur));
  // 링크 표기 [[계열|모델|이름]] → 이동 버튼. **이벤트를 붙이기 전에** 바꿔야 한다.
  // 예전엔 붙인 뒤 innerHTML 을 다시 넣어 앞서 건 이벤트가 전부 날아갔다.
  main.innerHTML = html.replace(/\[\[([^|]+)\|(\d+)\|([^\]]+)\]\]/g,
    '<button class="jump" data-eq="$1" data-mi="$2">$3</button>');
  wire();
}

// ── CSV 내보내기 ─────────────────────────────────────────────────────────────
// 화면에서 눈으로 보는 것과 별개로, 뽑아서 쓰는 길이 있어야 한다.
// 오프라인 단일 HTML 이라 서버가 없다 → Blob 으로 만들어 바로 내려받는다.
var CSVSRC = {};   // 버튼이 가리키는 표를 여기 담아 둔다

function csvCell(v){
  var s = (v===null||v===undefined) ? '' : String(v);
  // 화면용 태그가 섞여 들어오면 글자만 남긴다
  if(s.indexOf('<')>=0){ var d=document.createElement('div'); d.innerHTML=s; s=d.textContent; }
  s = s.replace(/\s+/g,' ').trim();
  return /[",\n]/.test(s) ? '"' + s.replace(/"/g,'""') + '"' : s;
}

function toCsv(header, rows){
  return [header.map(csvCell).join(',')]
    .concat(rows.map(function(r){ return r.map(csvCell).join(','); })).join('\r\n');
}

function downloadCsv(key){
  var d = CSVSRC[key];
  if(!d) return;
  // BOM 을 붙인다 — 안 붙이면 엑셀이 한글을 깨서 연다
  var blob = new Blob(['﻿' + toCsv(d.header, d.rows)],
                      {type:'text/csv;charset=utf-8;'});
  var url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = d.name;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 1000);
}

function csvBtn(key, name, header, rows, label){
  CSVSRC[key] = {name:name, header:header, rows:rows};
  return '<button class="csv" data-csv="'+esc(key)+'" title="'+esc(name)+'">'
       + '↓ ' + esc(label||'CSV') + '</button>';
}

function safeName(s){
  return String(s||'data').replace(/[\\/:*?"<>|]+/g,'-').replace(/\s+/g,'_').slice(0,80);
}

function wire(){
  var re = function(){ var y=window.scrollY; render(); window.scrollTo(0,y); };
  main.querySelectorAll('.tabs button').forEach(function(b){
    b.addEventListener('click',function(){ tab=b.dataset.tab; kindF=''; gradeF=''; render(); });});
  main.querySelectorAll('.mlist button').forEach(function(b){
    b.addEventListener('click',function(){ mi=+b.dataset.mi; vsel=0; ssel=0; mview='unit'; ksel='rating'; pageOf={}; render(); });});
  main.querySelectorAll('.iflist button').forEach(function(b){
    b.addEventListener('click',function(){
      var models = visibleModels(cur), m = models[Math.min(mi, models.length-1)];
      if(m) isel[m.id] = +b.dataset.if;
      re();
    });});
  main.querySelectorAll('.vclr').forEach(function(b){
    b.addEventListener('click',function(){ vnF=''; mi=0; render(); });});
  main.querySelectorAll('.mtabs button').forEach(function(b){
    b.addEventListener('click',function(){ mview=b.dataset.mview; pageOf={}; render(); });});
  main.querySelectorAll('.ucard').forEach(function(b){
    b.addEventListener('click',function(){
      var models = visibleModels(cur), m = models[Math.min(mi, models.length-1)];
      if(m) usel[m.id] = +b.dataset.ui;
      render();
    });});
  main.querySelectorAll('.uvwt button').forEach(function(b){
    b.addEventListener('click',function(){
      var models = visibleModels(cur), m = models[Math.min(mi, models.length-1)];
      if(m) uvw[m.id] = b.dataset.uvw;
      re();   // 보기 방식만 바뀌고 보던 자리는 그대로
    });});
  main.querySelectorAll('.vlist button').forEach(function(b){
    b.addEventListener('click',function(){ vsel=+b.dataset.vi; render(); });});
  main.querySelectorAll('.klist button').forEach(function(b){
    b.addEventListener('click',function(){ ksel=b.dataset.kk; ssel=0; pageOf={}; render(); });});
  main.querySelectorAll('.slist button').forEach(function(b){
    b.addEventListener('click',function(){ ssel=+b.dataset.si; pageOf={}; render(); });});
  main.querySelectorAll('.csv').forEach(function(b){
    b.addEventListener('click',function(){ downloadCsv(b.dataset.csv); });});
  main.querySelectorAll('th.srt').forEach(function(th){
    th.addEventListener('click',function(){
      var k = th.closest('table').dataset.tk, c = +th.dataset.col, cu = sortOf[k];
      sortOf[k] = (cu && cu.col===c) ? {col:c, dir:-cu.dir} : {col:c, dir:1};
      re();
    });});
  main.querySelectorAll('.pgb').forEach(function(b){
    b.addEventListener('click',function(){
      if(b.disabled) return;
      pageOf[b.parentNode.dataset.pk] = +b.dataset.go;
      re();   // 쪽만 바뀌고 보던 자리는 그대로
    });});
  main.querySelectorAll('.chip').forEach(function(b){
    b.addEventListener('click',function(){
      if(b.dataset.kind!==undefined) kindF = (kindF===b.dataset.kind)?'':b.dataset.kind;
      if(b.dataset.grade!==undefined) gradeF = (gradeF===b.dataset.grade)?'':b.dataset.grade;
      render();});});
  main.querySelectorAll('.jump').forEach(function(b){
    b.addEventListener('click', function(){
      cur = b.dataset.eq; mi = +b.dataset.mi; tab='md';
      vsel=0; ssel=0; pageOf={}; sortOf={};
      q.value=''; term=''; searchAll_on=false; render(); window.scrollTo(0,0);
    });});
  // 행 수는 **필터 칩 바로 다음 표**만 센다 (통신표·근거문서표까지 세던 것 수정)
  var c = main.querySelector('#cnt');
  if(c){
    var bar = c.closest('.chips') || c.parentNode;
    var t = bar.nextElementSibling;
    while(t && t.tagName !== 'TABLE') t = t.querySelector ? t.querySelector('table') : null;
    c.textContent = (t ? t.querySelectorAll('tbody tr').length : 0) + '행';
  }
}

// 툴팁 — data-tip 이 있는 요소에 올리면 뜬다. 브라우저 기본 title 은 느리고
// 줄바꿈·서식을 못 준다.
var tipEl = document.getElementById('tip');
document.addEventListener('mouseover', function(ev){
  var el = ev.target.closest && ev.target.closest('[data-tip]');
  if(!el){ tipEl.classList.remove('on'); return; }
  tipEl.textContent = el.dataset.tip;
  tipEl.classList.add('on');
  // position:fixed 는 화면 좌표를 쓴다. getBoundingClientRect 도 화면 기준이라
  // 그대로 쓰면 되지만, 아래로 넘치면 위로 뒤집고 화면 밖으로 나가지 않게 가둔다.
  var r = el.getBoundingClientRect(), th = tipEl.offsetHeight, tw = tipEl.offsetWidth;
  var top = r.bottom + 8;
  if(top + th > innerHeight - 8) top = Math.max(8, r.top - th - 8);
  var left = Math.max(8, Math.min(r.left, innerWidth - tw - 8));
  tipEl.style.top = Math.round(top) + 'px';
  tipEl.style.left = Math.round(left) + 'px';
});
document.addEventListener('mouseout', function(ev){
  if(!ev.relatedTarget || !ev.relatedTarget.closest || !ev.relatedTarget.closest('[data-tip]'))
    tipEl.classList.remove('on');
});

var t0;
q.addEventListener('input', function(){
  clearTimeout(t0);
  t0 = setTimeout(function(){ term = q.value.trim().toLowerCase(); render(); }, 120);
});
q.addEventListener('keydown', function(ev){
  if(ev.key === 'Enter'){ searchAll_on = true; term = q.value.trim().toLowerCase(); render(); }
  if(ev.key === 'Escape'){ q.value=''; term=''; searchAll_on=false; render(); }
});
document.getElementById('qall').addEventListener('click', function(){
  term = q.value.trim().toLowerCase();
  if(term.length < 2){ q.focus(); return; }
  searchAll_on = true; render();
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
