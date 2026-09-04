# -*- coding: utf-8 -*-
"""취입 대조 화면 — review/lg-ingest-verify.html

  PYTHONIOENCODING=utf-8 python verify_lg_ingest.py

**오전의 대조대(verify_lg.py)와 무엇이 다른가**
  그쪽은 *원문에서 뽑은 것*을 원문과 맞춘다. 이쪽은 **모델에 실제로 들어간 것**을
  원문과 맞춘다 — 뽑기와 취입 사이에서 잃은 것이 있는지는 이 화면에서만 보인다.
  읽는 곳이 PDF 가 아니라 data/models/lg-ac-smart-bacnet-gateway.json 이다.

화면 방식은 오전 것을 그대로 쓴다(verify_lg.TEMPLATE 재사용):
  좌우 2단 · 팝업 없음 · 원문 쪽을 가로로 눕힘 · 표만/나란히/원문만 전환 ·
  유닛 주소를 넣으면 _XXX 와 인스턴스 번호가 나온다.

⚠ 산출물은 원문 쪽 그림을 담아 gitignore 된다. 이 스크립트가 정본이다.
"""
import base64
import collections
import io
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "data")
sys.path.insert(0, HERE)
import verify_lg as V  # noqa: E402  — 화면 틀과 원문 찾기를 함께 쓴다

MODEL_ID = "lg-ac-smart-bacnet-gateway"
OUT = os.path.join(HERE, "..", "review", "lg-ingest-verify.html")

# 판 → (보이는 이름, 제품유형). 제품유형은 원문 50쪽이 정한다.
IFACE_KO = {
    "indoor-unit": ("실내기", 0), "ventilation": ("환기(HRV)", 1),
    "ahu": ("공조기(AHU)", 2), "odu": ("실외기(ODU)", 3),
    "awhp": ("AWHP", 4), "gateway-general": ("게이트웨이 공통", 5),
}


def tables_from_model(model):
    """모델의 판·포인트를 화면이 쓰는 표 모양으로 되돌린다.

    ⚠ 여기서 **원문을 다시 읽지 않는다.** 화면에 뜨는 값은 전부 모델에 들어간 값이다 —
       그래야 '뽑은 것'이 아니라 '취입된 것'을 원문과 맞추는 화면이 된다.
    """
    out = []
    for iface in model.get("interfaces") or []:
        ko, ptype = IFACE_KO.get(iface["id"], (iface["id"], None))
        by_page = collections.defaultdict(list)
        for p in iface.get("points") or []:
            prov = p.get("provenance") or {}
            cols = prov.get("sourceColumns") or {}
            common = p.get("common") or {}
            bac = (p.get("blocks") or {}).get("bacnet") or {}
            states = ", ".join("%s=%s" % (s.get("code"), s.get("label"))
                               for s in (common.get("states") or []))
            by_page[prov.get("sourcePage")].append({
                "no": int(cols.get("Point No.") or 0),
                "name": common.get("name") or "",
                "type": bac.get("objectType") or "",
                "desc": common.get("note") or cols.get("Control/monitoring") or "",
                "states": states,
            })
        for printed, pts in sorted(by_page.items()):
            out.append({"page": printed + 8,        # 인쇄쪽 → PDF 쪽 (아래에서 실측으로 덮는다)
                        "printed": printed, "group": ko, "ptype": ptype,
                        "points": sorted(pts, key=lambda x: x["no"])})
    return out


def main():
    import fitz
    model_path = os.path.join(DATA, "models", MODEL_ID + ".json")
    if not os.path.exists(model_path):
        raise SystemExit("모델이 없다: %s — 먼저 ingest_lg.py --run" % MODEL_ID)
    model = json.load(io.open(model_path, encoding="utf-8"))

    url, meta = V.ledger_entry()
    path = os.path.join(DATA, "raw", meta["file"])
    if not os.path.exists(path):
        raise SystemExit("원문이 없다 — collect.py --run %s" % V.SRC_ID)
    doc = fitz.open(path)

    tables = tables_from_model(model)
    # 인쇄쪽 → PDF 쪽은 **가정하지 않고 문서에서 찾는다**(오프셋이 판마다 다를 수 있다)
    pdf_of = {}
    for p in V.PAGES:
        pdf_of[V.printed_no(doc[p - 1], p)] = p
    for t in tables:
        t["page"] = pdf_of.get(t["printed"], t["page"])

    imgs = V.page_images(doc, {t["page"] for t in tables})
    total = sum(len(t["points"]) for t in tables)
    payload = json.dumps({
        "doc": "%s → %s" % (meta["file"], MODEL_ID),
        "sha": meta.get("sha256", ""), "url": url, "source": V.SRC_ID,
        "total": total, "tables": tables, "pages": imgs,
    }, ensure_ascii=False, separators=(",", ":"))
    assert "</scr" + "ipt>" not in payload

    html = V.TEMPLATE.replace("__PAYLOAD__", payload)
    html = html.replace("<title>LG BACnet 대조대</title>",
                        "<title>LG 취입 대조대</title>")
    html = html.replace(">LG BACnet 대조대<", ">LG 취입 대조대<")
    html = html.replace(
        "원문 표를 <b>가로로 눕혀</b> 보여 준다",
        "왼쪽은 <b>모델에 실제로 들어간 값</b>이다(원문에서 다시 뽑은 것이 아니다). "
        "원문 표를 <b>가로로 눕혀</b> 보여 준다")
    io.open(OUT, "w", encoding="utf-8", newline="\n").write(html)

    print("모델 %s — 판 %d개 · %d점" % (MODEL_ID, len(model["interfaces"]), total))
    for t in tables:
        print("   원문 %3d쪽(PDF %2d) %-14s %2d점" % (t["printed"], t["page"], t["group"], len(t["points"])))
    print("→ %s  (%.2f MB)" % (os.path.relpath(OUT, HERE), os.path.getsize(OUT) / 1048576))


if __name__ == "__main__":
    main()
