# -*- coding: utf-8 -*-
"""실제 포인트리스트의 OBJ_NAME에 Haystack 태그가 걸리는지 실측.
NEUROS HaystackTagService 알고리즘(HAYSTACK_RECOMMEND_SPEC.md)을 그대로 재현한다."""
import csv, io, os, re, json
from collections import Counter, defaultdict

ROOT = r"D:\DB\서울캠퍼스\포인트리스트_자동제어"
DICT = r"D:\_solutions\Neuros\NEUROS\backend\src\main\resources\haystack-tags.json"

d = json.load(open(DICT, encoding="utf-8"))
TAGS = []                                     # (code, desc, category)
for cat in ("equip", "property", "role"):
    for code, desc in d.get(cat, {}).items():
        TAGS.append((code, desc or "", cat))

STOP = {"있는","있다","없는","관련","이상","기타","정보","데이터","시스템","사용","장치","상태"}
SPLIT = re.compile(r"[\s,./()\[\]_\-、，。·…:;+*#&']+")

def tokenize(s):
    out, seen = [], set()
    for t in SPLIT.split(s or ""):
        if not t:
            continue
        t = t.lower() if t.isascii() else t
        if len(t) < 2 or t in STOP or t in seen:
            continue
        seen.add(t); out.append(t)
    return out

# 토큰 -> [(tag_code, score, category)] 캐시
cache = {}
def tags_for_token(tok):
    if tok in cache:
        return cache[tok]
    hits = []
    ascii_tok = tok.isascii()
    pat = re.compile(r"\b" + re.escape(tok) + r"\b", re.I) if ascii_tok else None
    for code, desc, cat in TAGS:
        lc = code.lower()
        if lc == tok:
            hits.append((code, 3, cat)); continue
        parts = set(re.split(r"[-]", lc)) | set(re.findall(r"[a-z]+|[0-9]+", lc))
        if tok in parts:
            hits.append((code, 2, cat)); continue
        if desc:
            if (pat.search(desc) if ascii_tok else (tok in desc)):
                hits.append((code, 1, cat))
    cache[tok] = hits
    return hits

FAM = {
 "AHU": ["AHU","AH-","공조"], "VAV": ["VAV","FP","AIRFLOW"],
 "FAN": ["SF","RF","EF","KEF"], "CHILLER": ["UC-800","TRANE","냉동","터보","흡수"],
 "COOLTOWER": ["CTCH","CT-","냉각탑"], "PUMP": ["WPC","PUMP","펌프"],
 "BOILER": ["HWG","보일러"], "FCU": ["FC-","팬코일"],
 "EHP": ["BIOT","AC_","실내기","항온"], "VFD": ["INV","FC101","인버터"],
 "HEATEX": ["HVU","HV-","열교환","전열"],
}

def decode(p):
    raw = open(p, "rb").read()
    if raw.startswith(b"\xef\xbb\xbf"):
        return raw[3:].decode("utf-8", "replace")
    if not any(b >= 0x80 for b in raw):
        return raw.decode("ascii")
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp949", "replace")

names = {}          # obj_name -> desc (셔블 only)
for dp, _, fns in os.walk(ROOT):
    for fn in fns:
        if not fn.lower().endswith(".csv"):
            continue
        txt = decode(os.path.join(dp, fn))
        r = csv.reader(io.StringIO(txt))
        try:
            hdr = [h.strip().lstrip("\ufeff") for h in next(r)]
        except StopIteration:
            continue
        if "OBJ_NAME" not in hdr:
            continue
        i_n, i_d = hdr.index("OBJ_NAME"), (hdr.index("OBJ_DESC") if "OBJ_DESC" in hdr else -1)
        for row in r:
            if len(row) <= i_n:
                continue
            nm = row[i_n].strip()
            if nm:
                names.setdefault(nm, row[i_d].strip() if 0 <= i_d < len(row) else "")

def family(nm):
    up = nm.upper()
    for f, ks in FAM.items():
        if any(k in up for k in ks):
            return f
    return "OTHER"

stat = Counter(); fam_stat = defaultdict(Counter)
equip_tag_top = Counter(); prop_tag_top = Counter()
zero_examples = Counter(); point_only = Counter()
detail_rows = []

for nm, desc in names.items():
    fam = family(nm)
    toks = tokenize(nm + " " + desc)
    best = {}
    for t in toks:
        for code, sc, cat in tags_for_token(t):
            if best.get(code, (0, cat))[0] < sc:
                best[code] = (sc, cat)
    strong = {c: v for c, v in best.items() if v[0] >= 2}     # 코드 일치(사전 단어와 실제 매칭)
    any_hit = bool(best)
    equip_hit = any(v[1] == "equip" and v[0] >= 2 for v in best.values())
    prop_hit = any(v[1] == "property" and v[0] >= 2 for v in best.values())
    role_hit = any(v[1] == "role" for v in best.values())

    stat["total"] += 1
    stat["any_hit"] += any_hit
    stat["strong_hit"] += bool(strong)
    stat["equip_hit"] += equip_hit
    stat["prop_hit"] += prop_hit
    stat["role_hit"] += role_hit
    stat["desc_only"] += (any_hit and not strong)
    fam_stat[fam]["total"] += 1
    fam_stat[fam]["strong"] += bool(strong)
    fam_stat[fam]["equip"] += equip_hit
    fam_stat[fam]["prop"] += prop_hit
    for c, (sc, cat) in best.items():
        if sc >= 2:
            (equip_tag_top if cat == "equip" else prop_tag_top)[c] += 1
    if not strong:
        zero_examples[nm[:70]] += 1
    if ".points." in nm:
        pn = nm.split(".points.", 1)[1]
        pt = tokenize(pn)
        pb = {}
        for t in pt:
            for code, sc, cat in tags_for_token(t):
                pb[code] = max(pb.get(code, 0), sc)
        point_only["total"] += 1
        point_only["strong"] += any(v >= 2 for v in pb.values())

out = {
 "distinct_obj_names": stat["total"],
 "태그_1개이상_걸림(설명매칭 포함)": stat["any_hit"],
 "코드일치_태그_걸림(strong)": stat["strong_hit"],
 "설명만_걸림(약한 매칭)": stat["desc_only"],
 "equip태그_걸림": stat["equip_hit"],
 "property태그_걸림": stat["prop_hit"],
 "role태그_걸림": stat["role_hit"],
 "pct": {
   "any": round(100 * stat["any_hit"] / stat["total"], 1),
   "strong": round(100 * stat["strong_hit"] / stat["total"], 1),
   "equip": round(100 * stat["equip_hit"] / stat["total"], 1),
   "prop": round(100 * stat["prop_hit"] / stat["total"], 1),
 },
 "포인트명만_기준": {
   "total": point_only["total"], "strong": point_only["strong"],
   "pct": round(100 * point_only["strong"] / max(point_only["total"], 1), 1)},
 "장비군별": {f: {"총": c["total"], "코드일치%": round(100*c["strong"]/c["total"],1),
                  "equip%": round(100*c["equip"]/c["total"],1),
                  "property%": round(100*c["prop"]/c["total"],1)}
              for f, c in sorted(fam_stat.items(), key=lambda x: -x[1]["total"])},
 "가장_많이_걸린_equip태그": equip_tag_top.most_common(25),
 "가장_많이_걸린_property태그": prop_tag_top.most_common(30),
 "태그_0개_이름_예시": zero_examples.most_common(30),
 "태그_0개_이름_수": len(zero_examples),
}
open("nametag.json", "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1))
print("OK", stat["total"])
