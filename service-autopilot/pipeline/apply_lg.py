import sys
import os
import json
from specs import extract_specs

RAW = 'data/raw'
DATA = 'data'
fname = 'LG_Multi_V_5_Engineering_Data_Book.pdf'
mids = ['lg-multi-v-5-outdoor-unit']
path = os.path.join(RAW, fname)

print("Extracting LG specs...")
sys.stdout.flush()
ts = extract_specs(path)
print(f"Extracted {len(ts)} tables. Now dumping to JSON...")
sys.stdout.flush()

for mid in mids:
    mpath = os.path.join(DATA, "models", mid + ".json")
    if not os.path.exists(mpath):
        print(f"  Model not found: {mid}")
        continue
    m = json.load(open(mpath, encoding="utf-8"))
    keep = [t for t in m.get("specTables", []) if t.get("source") != fname]
    m["specTables"] = keep + [dict(t, source=fname) for t in ts]
    m["has"] = dict(m.get("has", {}), spec=True)
    json.dump(m, open(mpath, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"Dumped to {mpath}!")
    sys.stdout.flush()
