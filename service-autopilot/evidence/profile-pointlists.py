# -*- coding: utf-8 -*-
import csv, io, os, re, json
from collections import Counter, defaultdict

ROOT = r"D:\DB\서울캠퍼스\포인트리스트_자동제어"

enc_stat = Counter()
def decode(path):
    raw = open(path, 'rb').read()
    if raw.startswith(b'\xef\xbb\xbf'):
        enc_stat['utf-8-bom'] += 1
        return raw[3:].decode('utf-8', errors='replace')
    if not any(b >= 0x80 for b in raw):
        enc_stat['ascii'] += 1
        return raw.decode('ascii')
    try:
        t = raw.decode('utf-8')
        enc_stat['utf-8'] += 1
        return t
    except UnicodeDecodeError:
        pass
    try:
        t = raw.decode('cp949')
        enc_stat['cp949'] += 1
        return t
    except UnicodeDecodeError:
        enc_stat['cp949-lossy'] += 1
        return raw.decode('cp949', errors='replace')

# --- accumulators
nia_objtype = Counter(); nia_writable = Counter(); nia_unit = Counter()
nia_desc_filled = 0; nia_rows = 0; nia_type = Counter(); nia_valstatus = Counter()
sh_rows = 0
key_dup = Counter()           # (SERVER,SYSTEM,DEVICE,SYSTEM_PT_ID)
objname_files = defaultdict(set)
model_cand = Counter()
equip_family = Counter()
kor_point = Counter()
unit_by_objtype = defaultdict(Counter)
panel_topology = Counter()    # SERVER/SYSTEM/DEVICE
desc_filled_sh = 0
name_len = Counter()

HVAC_KEY = {
    'AHU': ['AHU', 'AH-', '공조기', '공조'],
    'VAV': ['VAV', 'FP', 'AirFlow'],
    'FAN': ['SF', 'RF', 'EF', 'KEF', 'FAN', '송풍기', '팬'],
    'CHILLER': ['CHILLER', 'UC-800', 'TRANE', '냉동기', '터보', '흡수식', '칠러'],
    'COOLINGTOWER': ['CT-', 'CTCH', '냉각탑', 'COOLER'],
    'PUMP': ['PUMP', 'WPC', '펌프'],
    'BOILER': ['BOILER', 'HWG', '보일러', '온수'],
    'FCU': ['FCU', 'FC-', '팬코일'],
    'EHP': ['EHP', 'BIOT', 'AC_', '실내기', '항온항습'],
    'VFD': ['INV', 'FC101', '인버터'],
    'HEATEX': ['HV', 'HVU', '열교환', '전열교환'],
}
MODEL_RE = re.compile(r'\b([A-Z]{2,}[- ]?\d{2,4}[A-Z]?)\b')

for dirpath, dirnames, filenames in os.walk(ROOT):
    for fn in filenames:
        if not fn.lower().endswith('.csv'):
            continue
        p = os.path.join(dirpath, fn)
        txt = decode(p)
        rdr = csv.reader(io.StringIO(txt))
        try:
            hdr = [h.strip().lstrip('\ufeff') for h in next(rdr)]
        except StopIteration:
            continue
        idx = {h: i for i, h in enumerate(hdr)}
        shovel = 'OBJ_NAME' in hdr
        for r in rdr:
            if not r or len(r) < 3:
                continue
            def g(c):
                i = idx.get(c, -1)
                return r[i].strip() if 0 <= i < len(r) else ''
            if shovel:
                sh_rows += 1
                nm = g('OBJ_NAME'); ot = g('OBJ_TYPE'); un = g('OBJ_UNIT_NUM')
                unit_by_objtype[ot][un] += 1
                if g('OBJ_DESC'):
                    desc_filled_sh += 1
                key_dup[(g('SERVER_ID'), g('SYSTEM_ID'), g('DEVICE_ID'), g('SYSTEM_PT_ID'))] += 1
                objname_files[nm].add(os.path.basename(dirpath) + '/' + fn)
                panel_topology[(g('SERVER_ID'), g('SYSTEM_ID'), g('DEVICE_ID'))] += 1
                name_len[len(nm) // 20 * 20] += 1
                left = nm.split('.points.')[0] if '.points.' in nm else nm
                up = left.upper()
                hit = False
                for fam, keys in HVAC_KEY.items():
                    if any(k.upper() in up for k in keys):
                        equip_family[fam] += 1
                        hit = True
                if not hit:
                    equip_family['UNMATCHED'] += 1
                for m in MODEL_RE.findall(up):
                    model_cand[m] += 1
                if '.points.' in nm:
                    pn = nm.split('.points.', 1)[1]
                    if any(ord(ch) > 0x3000 for ch in pn):
                        kor_point[pn] += 1
            else:
                nia_rows += 1
                nia_objtype[g('Object Type')] += 1
                nia_type[g('Type')] += 1
                w = g('BACnet Writable')
                nia_writable[w if len(w) < 30 else w[:30] + '...'] += 1
                if g('Description'):
                    nia_desc_filled += 1
                v = g('Value')
                mu = re.match(r'^\s*[-\d.]+\s*([^\s{]+)?', v)
                nia_unit[(mu.group(1) or '(none)') if mu else '(nonnum)'] += 1
                ms = re.search(r'\{(\w+)\}', v)
                nia_valstatus[ms.group(1) if ms else '(none)'] += 1

dups = {k: v for k, v in key_dup.items() if v > 1}
multi_file_names = {k: len(v) for k, v in objname_files.items() if len(v) > 1}

out = {
  "encoding_per_file": enc_stat.most_common(),
  "shovel_rows": sh_rows, "niagara_rows": nia_rows,
  "shovel_desc_filled_pct": round(100.0 * desc_filled_sh / max(sh_rows, 1), 1),
  "shovel_pk_candidate": {
      "distinct_keys": len(key_dup), "keys_with_dup": len(dups),
      "dup_examples": list(dups.items())[:5],
  },
  "objname_in_multiple_files": {
      "distinct_objnames": len(objname_files),
      "appearing_in_2plus_files": len(multi_file_names),
      "max_files_for_one_name": max(multi_file_names.values()) if multi_file_names else 0,
  },
  "panel_topology_distinct": len(panel_topology),
  "panel_topology_top10": [[list(k), v] for k, v in panel_topology.most_common(10)],
  "equip_family": equip_family.most_common(),
  "model_candidates_top40": model_cand.most_common(40),
  "korean_point_names_top30": kor_point.most_common(30),
  "unit_by_objtype": {k: v.most_common(8) for k, v in sorted(unit_by_objtype.items())},
  "objname_len_bucket": sorted(name_len.items()),
  "niagara": {
     "object_type": nia_objtype.most_common(),
     "descriptor_type": nia_type.most_common(),
     "writable_patterns_top15": nia_writable.most_common(15),
     "unit_from_value_top20": nia_unit.most_common(20),
     "value_status": nia_valstatus.most_common(10),
     "desc_filled_pct": round(100.0 * nia_desc_filled / max(nia_rows, 1), 1),
  },
}
with open("profile2.json", "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("OK")
