# -*- coding: utf-8 -*-
import glob, json

fixed = 0
for f in glob.glob('data/models/*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        m = json.load(file)
    
    pts = m.get('points', [])
    if not pts:
        continue
        
    original = [p.get('name') for p in pts]
    
    # Sort points by sourcePage, then type, then inst
    pts.sort(key=lambda p: (
        p.get('sourcePage') or (p.get('provenance') or {}).get('sourcePage') or 9999,
        p.get('type') or '',
        p.get('inst') if isinstance(p.get('inst'), int) else 999999
    ))
    
    sorted_names = [p.get('name') for p in pts]
    if original != sorted_names:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(m, file, ensure_ascii=False, indent=1)
        print(f"Sorted points in {m['id']}")
        fixed += 1

print(f"Done. Sorted {fixed} models.")
