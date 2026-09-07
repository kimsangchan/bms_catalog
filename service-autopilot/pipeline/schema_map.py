# -*- coding: utf-8 -*-
"""데이터 지도 — review/data-map.html

  PYTHONIOENCODING=utf-8 python schema_map.py

무엇을 보여 주나
  벤더 원문이 어떤 층을 거쳐 시뮬레이터·BMS 가 읽는 모양이 되는지, 그리고 각 층의
  **표 구조(스키마)와 층끼리 잇는 열쇠(조인 키)** 를 한 화면에 편다.
  사용자 질문: "sql 에서 db 테이블 구조 연결해 둔 것 같은 게 있다는 건가?" — 맞다.
  다만 그림을 그려 두면 데이터와 어긋나므로 **실제 파일에서 세어 그린다.**
"""
import collections
import glob
import io
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
OUT = os.path.join(HERE, "..", "review", "data-map.html")
sys.path.insert(0, HERE)


def jload(p):
    return json.load(io.open(p, encoding="utf-8"))


def counts():
    """실측 — 층마다 지금 몇 건인지."""
    models = [jload(f) for f in sorted(glob.glob(os.path.join(DATA, "models", "*.json")))]
    pts_flat = sum(len(m.get("points") or []) for m in models)
    ifaces = [i for m in models for i in (m.get("interfaces") or [])]
    pts_if = sum(len(i.get("points") or []) for i in ifaces)
    spec_rows = sum(len(t.get("rows") or []) for m in models
                    for t in (m.get("specTables") or []))
    units = [jload(f) for f in glob.glob(os.path.join(DATA, "units", "*.json"))]
    raw = len(glob.glob(os.path.join(DATA, "raw", "*.pdf"))) + \
        len(glob.glob(os.path.join(DATA, "raw", "*.PDF")))
    ds = {}
    dsp = os.path.join(DATA, "datasets", "catalog-dataset.json")
    if os.path.exists(dsp):
        d = jload(dsp)
        mm = d.get("modelMappings") or {}
        ds = {"모델": len(mm),
              "템플릿 매핑된 모델": sum(1 for m in mm.values()
                                if m.get("templatePointMappings")),
              "매핑된 포인트": sum(len(m.get("templatePointMappings") or [])
                             for m in mm.values()),
              "설비 계열": len(d.get("equipmentTemplates") or {}),
              "계열 표준 포인트": sum(len(v.get("templatePoints") or [])
                              for v in (d.get("equipmentTemplates") or {}).values())}
    return {
        "models": models, "ifaces": ifaces, "units": units,
        "n": {"원문 PDF": raw, "모델": len(models), "판(인터페이스)": len(ifaces),
              "오브젝트(판)": pts_if, "오브젝트(옛 평면)": pts_flat,
              "정격 표 행": spec_rows, "확정본 모델": len(units),
              "확정본 형번": sum(len(u.get("units") or []) for u in units)},
        "ds": ds,
    }


def schema_rows():
    """사전 파일에서 필드 목록을 그대로 읽어 온다 — 손으로 옮겨 적지 않는다."""
    ps = jload(os.path.join(DATA, "point-schema.json"))
    us = jload(os.path.join(DATA, "unit-schema.json"))
    out = {"point": [], "blocks": [], "prov": [], "feat": [], "cls": []}
    for k, v in (ps.get("common") or {}).items():
        out["point"].append([k, v.get("ko") or "", v.get("shape") or "",
                             (v.get("note") or "")[:150]])
    for bk, bv in (ps.get("blocks") or {}).items():
        fields = ", ".join((bv.get("fields") or {}).keys())
        out["blocks"].append([bk, bv.get("ko") or "", fields[:120],
                              (bv.get("description") or "")[:110]])
    for k, v in (ps.get("provenance") or {}).items():
        ko = v.get("ko") if isinstance(v, dict) else ""
        note = (v.get("note") if isinstance(v, dict) else "") or ""
        out["prov"].append([k, ko or "", "", note[:150]])
    for k, v in (us.get("features") or {}).items():
        out["feat"].append([k, v.get("ko") or "", v.get("convUnit") or "—", ""])
    for k, v in (us.get("classes") or {}).items():
        out["cls"].append([k, v.get("ko") or "",
                           ", ".join(v.get("table") or [])[:120],
                           ", ".join(v.get("detailExtra") or [])[:90]])
    return out


def sample():
    """한 건이 층을 따라 어떻게 바뀌는지 — 실제 레코드에서 뽑는다."""
    out = {}
    mp = os.path.join(DATA, "models", "ls-electric-h100-vfd.json")
    if os.path.exists(mp):
        m = jload(mp)
        ifc = (m.get("interfaces") or [None])[0]
        if ifc and ifc.get("points"):
            out["point"] = ifc["points"][0]
        for t in m.get("specTables") or []:
            if t.get("kind") == "rating":
                out["specRow"] = {"title": t.get("title"), "header": t.get("header"),
                                  "row": (t.get("rows") or [[]])[0],
                                  "quantities": t.get("quantities")}
                break
    up = os.path.join(DATA, "units", "ls-electric-h100-vfd.json")
    if os.path.exists(up):
        u = jload(up)
        if u.get("units"):
            out["unit"] = u["units"][0]
    return out


# 층끼리 잇는 열쇠 — 여기가 'DB 로 치면 외래키' 다
JOINS = [
    ["modelId", "data/models/&lt;id&gt;.json", "data/units/&lt;id&gt;.json · 데이터셋 modelMappings",
     "모델 하나가 정격 확정본·매핑과 같은 이름으로 이어진다"],
    ["equipId", "모델.equipId (e5·e8·e15 …)", "unit-schema.classes · equipmentTemplates",
     "설비 계열이 **무엇을 뽑을지**와 **어떤 표준 포인트를 갖는지**를 정한다"],
    ["interfaceId", "모델.interfaces[].id", "포인트.provenance.interfaceId",
     "포인트가 어느 판(문서 리비전)에서 왔는지. 판이 다르면 주소가 다르다"],
    ["unitModelNumber", "확정본.units[].unitModelNumber", "정격 표의 머리글 형번",
     "형번 하나 = 확정본 한 줄. 시뮬레이터가 고르는 단위"],
    ["feature id", "unit-schema.features (ratedOutputCurrent …)",
     "확정본.units[].fields.&lt;feature&gt;",
     "속성 이름이 곧 열 이름이다. 단위는 features.convUnit 이 정본"],
    ["templateName", "equipmentTemplates[].templatePoints[].name",
     "modelMappings[].templatePointMappings[].matchedPoint",
     "설비 표준 포인트 ↔ 벤더 포인트를 잇는다. '모델만 고르면 매핑' 이 여기서 난다"],
]

LAYERS = [
    ("① 원문", "data/raw/*.pdf", "벤더가 낸 PDF 그대로. 저장소엔 안 담고 경로·SHA-256 만 대장에",
     "collect.py · sources.py"),
    ("② 취입", "ingest_*.py · specs.py", "**벤더 차이를 여기서만 흡수한다.** 전치표·좌표·격자·식 — 원문 모양이 제각각이라 읽는 법이 다르다",
     "ingest_lg · ingest_samsung · ingest_ls_rs485 · ingest_danfoss_fc101 · ingest_ls_ratings"),
    ("③ 모델 레코드", "data/models/&lt;id&gt;.json", "여기서부터 **모양이 하나다**. 오브젝트는 point-schema, 정격은 specTables(원문 그대로 = 제안)",
     "validate.py 가 사전 밖 필드를 오류로 잡는다"),
    ("④ 확정본", "data/units/&lt;id&gt;.json", "형번별 **골든 레코드**. 값과 단위가 갈려 있다. 사람이 확인하면 verified 로 굳어 재추출이 못 덮는다",
     "units.py --sync / --verify"),
    ("⑤ 데이터셋", "data/datasets/catalog-dataset.json", "설비 표준 포인트 + 모델별 매핑 + 시뮬레이터 입력을 한 파일로",
     "datasets.py"),
    ("⑥ 소비자", "review/*.html · review/export/*.csv", "BMS 는 46열 CSV(행=판, 프로토콜=열), 시뮬레이터는 확정본·시뮬레이터 입력",
     "export_points.py · build.py · verify_points.py"),
]

CSS = """
:root{--bg:#F5F8F9;--panel:#fff;--ink:#0F1A1F;--dim:#4A6068;--faint:#7C949C;
 --line:#DAE3E7;--accent:#0E7A88;--soft:#DCEEF0;--warn:#9A6608;
 --mono:ui-monospace,"Cascadia Mono",Consolas,monospace;
 --ui:-apple-system,BlinkMacSystemFont,"Segoe UI","Malgun Gothic",sans-serif}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){
 --bg:#0C1417;--panel:#111C20;--ink:#DCE7EA;--dim:#93A8AF;--faint:#6B838B;
 --line:#1E2C32;--accent:#3FB4C2;--soft:#10333A;--warn:#D9A441}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.65 var(--ui)}
.wrap{max-width:1180px;margin:0 auto;padding:30px 22px 70px}
h1{font-size:22px;margin:0 0 4px}
.sub{color:var(--faint);font-size:12.5px;margin-bottom:26px}
h2{font-size:15px;margin:34px 0 10px;padding-bottom:6px;border-bottom:1px solid var(--line)}
p.note{color:var(--dim);font-size:13px;margin:0 0 14px}
.flow{display:grid;gap:10px}
.step{background:var(--panel);border:1px solid var(--line);border-radius:10px;
 padding:12px 14px;display:grid;grid-template-columns:96px 1fr;gap:14px;align-items:start}
.step b{color:var(--accent);font-size:13px}
.step .path{font-family:var(--mono);font-size:11.5px;color:var(--dim);word-break:break-all}
.step .who{font-family:var(--mono);font-size:11px;color:var(--faint);margin-top:4px}
.n{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 8px}
.n span{background:var(--panel);border:1px solid var(--line);border-radius:999px;
 padding:3px 11px;font-size:12px}
.n b{color:var(--accent);font-variant-numeric:tabular-nums}
table{border-collapse:collapse;width:100%;font-size:12.5px;background:var(--panel);
 border:1px solid var(--line);border-radius:10px;overflow:hidden}
th,td{padding:7px 10px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:var(--soft);color:var(--ink);font-weight:600;font-size:11.5px}
tr:last-child td{border-bottom:0}
td.k{font-family:var(--mono);color:var(--accent);white-space:nowrap}
td.d{color:var(--dim)}
pre{background:var(--panel);border:1px solid var(--line);border-radius:10px;
 padding:12px 14px;overflow:auto;font-family:var(--mono);font-size:11.5px;color:var(--dim)}
.two{display:grid;grid-template-columns:1fr 1fr;gap:16px}
@media(max-width:860px){.two{grid-template-columns:1fr}.step{grid-template-columns:1fr}}
"""


def esc(x):
    return (str(x).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if x is not None else "")


def table(head, rows):
    h = "".join("<th>%s</th>" % esc(x) for x in head)
    body = ""
    for r in rows:
        cells = "".join('<td class="%s">%s</td>'
                        % ("k" if i == 0 else ("d" if i >= 2 else ""),
                           r[i] if i == 0 and "&" in str(r[i]) else esc(r[i]))
                        for i in range(len(r)))
        body += "<tr>%s</tr>" % cells
    return "<table><thead><tr>%s</tr></thead><tbody>%s</tbody></table>" % (h, body)


def main():
    c = counts()
    sc = schema_rows()
    sp = sample()
    h = ['<meta charset="utf-8"><title>데이터 지도</title><style>%s</style>' % CSS,
         '<div class="wrap"><h1>데이터 지도</h1>',
         '<div class="sub">벤더 원문이 어떤 층을 거쳐 시뮬레이터·BMS 가 읽는 모양이 '
         '되는지. 숫자는 <b>지금 저장소를 세어</b> 그린 것이다 — 그림이 데이터와 '
         '어긋나지 않게. 다시 만들기: <code>python schema_map.py</code></div>']

    h.append('<div class="n">%s</div>' % "".join(
        "<span>%s <b>%s</b></span>" % (esc(k), format(v, ",")) for k, v in c["n"].items()))

    h.append("<h2>층 — 원문에서 소비자까지</h2>")
    h.append('<p class="note">핵심은 <b>② 취입</b>이다. 벤더마다 원문 모양이 달라도 '
             '다른 것은 거기까지고, ③부터는 모든 벤더가 <b>같은 모양</b>이다. '
             '그래서 소비자(시뮬레이터·BMS)는 벤더를 몰라도 된다.</p>')
    h.append('<div class="flow">')
    for name, path, what, who in LAYERS:
        h.append('<div class="step"><div><b>%s</b><div class="path">%s</div></div>'
                 '<div>%s<div class="who">%s</div></div></div>'
                 % (esc(name), path, what, esc(who)))
    h.append("</div>")

    if c["ds"]:
        h.append("<h2>지금 이어진 정도</h2>")
        h.append('<div class="n">%s</div>' % "".join(
            "<span>%s <b>%s</b></span>" % (esc(k), format(v, ",")) for k, v in c["ds"].items()))

    h.append("<h2>층끼리 잇는 열쇠 (DB 로 치면 외래키)</h2>")
    h.append(table(["열쇠", "어디에 있나", "무엇과 이어지나", "뜻"], JOINS))

    h.append("<h2>오브젝트 스키마 — point-schema.json</h2>")
    h.append('<p class="note">한 포인트는 <b>common</b>(사람이 읽는 것) + '
             '<b>blocks</b>(프로토콜별 주소) + <b>provenance</b>(어느 원문 어느 쪽) '
             '세 덩어리다. 사전 밖 필드는 <code>validate.py</code> 가 오류로 잡는다.</p>')
    h.append(table(["common", "뜻", "모양", "메모"], sc["point"]))
    h.append("<h2>프로토콜 블록 — 벤더가 주는 주소가 여기 들어간다</h2>")
    h.append(table(["block", "뜻", "필드", "메모"], sc["blocks"]))
    h.append("<h2>출처(provenance) — 되짚을 수 있어야 한다</h2>")
    h.append(table(["provenance", "뜻", "", "메모"], sc["prov"]))

    h.append("<h2>정격 스키마 — unit-schema.json</h2>")
    h.append('<p class="note">설비 계열(<b>classes</b>)이 <b>무엇을 뽑을지</b>를 정하고, '
             '속성(<b>features</b>)이 <b>이름과 단위</b>를 정한다. 사전에 없는 설비는 '
             '확정본을 만들지 않는다 — 그래서 인버터는 e15 를 등재하고서야 열렸다.</p>')
    h.append(table(["class", "설비", "표에 세우는 속성", "상세에만"], sc["cls"]))
    h.append(table(["feature", "뜻", "단위(convUnit)", ""], sc["feat"]))

    if sp:
        h.append("<h2>한 건이 층을 따라 어떻게 바뀌나 (LS H100)</h2>")
        h.append('<div class="two">')
        if sp.get("point"):
            h.append("<div><b>오브젝트 한 점 — ③ 모델 레코드</b><pre>%s</pre></div>"
                     % esc(json.dumps(sp["point"], ensure_ascii=False, indent=1)[:1100]))
        if sp.get("specRow"):
            h.append("<div><b>정격 한 줄 — ③ 원문 그대로(제안)</b><pre>%s</pre></div>"
                     % esc(json.dumps(sp["specRow"], ensure_ascii=False, indent=1)[:1100]))
        h.append("</div>")
        if sp.get("unit"):
            h.append("<div><b>같은 형번 — ④ 확정본(값·단위가 갈린 뒤)</b><pre>%s</pre></div>"
                     % esc(json.dumps(sp["unit"], ensure_ascii=False, indent=1)[:1400]))
    h.append("</div>")

    d = os.path.dirname(OUT)
    if not os.path.isdir(d):
        os.makedirs(d)
    io.open(OUT, "w", encoding="utf-8", newline="\n").write("\n".join(h))
    print("→ %s  (%.2f MB)" % (os.path.relpath(OUT, HERE),
                               os.path.getsize(OUT) / 1048576.0))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
