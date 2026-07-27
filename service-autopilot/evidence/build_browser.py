# -*- coding: utf-8 -*-
"""08-equip-spec-tag-catalog.md → 카테고리 드릴다운 HTML 브라우저 생성"""
import re, json, os, html

SRC = r"D:\_solutions\Neuros\solution-planning\service-autopilot\08-equip-spec-tag-catalog.md"
OUT = r"D:\_solutions\Neuros\solution-planning\service-autopilot\review\equip-catalog.html"

DOMAIN = {
    5: "공기측 설비", 6: "공기측 설비", 7: "공기측 설비", 8: "공기측 설비",
    9: "열원·수측 설비", 10: "열원·수측 설비", 11: "열원·수측 설비", 12: "열원·수측 설비",
    13: "반송·구동", 14: "반송·구동", 15: "반송·구동",
    16: "계측·제어",
    19: "전력 설비", 20: "조명·차양", 21: "방재", 22: "승강", 23: "보안·출입",
    24: "환경·공기질", 25: "급배수·위생",
}

txt = open(SRC, encoding="utf-8").read()
lines = txt.split("\n")

# --- 섹션 분리
secs, cur = [], None
for ln in lines:
    m = re.match(r"^# (\d+)\.\s*(.+)$", ln)
    if m:
        cur = {"no": int(m.group(1)), "title": m.group(2).strip(), "body": []}
        secs.append(cur)
    elif re.match(r"^# ", ln):
        cur = None
    elif cur is not None:
        cur["body"].append(ln)

def parse_tables(body):
    """마크다운 표 블록들을 [{header:[], rows:[[]]}] 로"""
    tables, cur, prev_head = [], None, None
    for ln in body:
        if ln.startswith("|") and ln.rstrip().endswith("|"):
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            if cur is None:
                cur = {"header": cells, "rows": []}
            elif re.match(r"^[\s:\-|]+$", ln):
                pass
            else:
                cur["rows"].append(cells)
        else:
            if cur:
                cur["rows"] = [r for r in cur["rows"] if not all(re.match(r"^[:\-\s]*$", c) for c in r)]
                if cur["rows"]:
                    tables.append(cur)
                cur = None
    if cur and cur["rows"]:
        cur["rows"] = [r for r in cur["rows"] if not all(re.match(r"^[:\-\s]*$", c) for c in r)]
        if cur["rows"]:
            tables.append(cur)
    return tables

def md_inline(s):
    s = html.escape(s)
    s = re.sub(r"`([^`]+)`", r'<code>\1</code>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2" target="_blank">\1</a>', s)
    s = s.replace("✓", '<span class="ok">✓</span>').replace("★", '<span class="miss">★</span>')
    return s

equips = []
for s in secs:
    if s["no"] not in DOMAIN:
        continue
    body = s["body"]
    # 태그 요약 = 본문 앞부분에서 **태그** 또는 **식별** 로 시작하는 문단
    head = []
    for ln in body[:14]:
        if ln.strip().startswith("**") or ln.strip().startswith("구역 태그") or ln.strip().startswith("**Brick"):
            head.append(ln.strip())
        elif head and ln.strip() and not ln.startswith("|") and not ln.startswith("#") and not ln.startswith(">"):
            head.append(ln.strip())
        elif head and (ln.startswith("|") or ln.startswith("#") or not ln.strip()):
            if ln.startswith("|") or ln.startswith("#"):
                break
    notes = [ln.strip() for ln in body if ln.strip().startswith(">")]
    tabs = parse_tables(body)
    spec, points = [], []
    for t in tabs:
        h = " ".join(t["header"])
        if ("종류" in h and "역할" in h) or ("태그 조합" in h) or ("Haystack 마커셋" in h):
            points.append(t)
        elif "spec" in h.lower() or "항목" in h or "핵심 spec" in h:
            spec.append(t)
        else:
            spec.append(t)
    equips.append({
        "no": s["no"], "title": s["title"], "domain": DOMAIN[s["no"]],
        "head": " ".join(head), "notes": notes,
        "spec": spec, "points": points,
        "np": sum(len(t["rows"]) for t in points),
        "ns": sum(len(t["rows"]) for t in spec),
    })

print("장비 계열:", len(equips), "포인트 합:", sum(e["np"] for e in equips), "spec 합:", sum(e["ns"] for e in equips))
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(equips, open(os.path.join(os.path.dirname(__file__), "equips.json"), "w", encoding="utf-8"),
          ensure_ascii=False, indent=1)
print("→ equips.json 저장")
