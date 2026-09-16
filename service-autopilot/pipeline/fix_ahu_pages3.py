# -*- coding: utf-8 -*-
import glob, json, os, fitz
from verify_points import pages_by_name

DATA = 'data'
fixed = 0

for f in glob.glob('data/models/*.json'):
    with open(f, 'r', encoding='utf-8') as file:
        m = json.load(file)
    
    if not ('ahu' in m.get('id', '').lower() or 'ahu' in m.get('cat', '').lower()):
        continue
    
    pts = m.get('points', [])
    if not pts:
        continue
        
    # We want ALL AHU models to have flat sourcePage
    doc = m.get('sourceDoc')
    if not doc:
        continue
        
    path = os.path.join(DATA, 'raw', doc)
    if not os.path.isfile(path):
        continue
        
    print(f"Processing {m['id']}...")
    dd = fitz.open(path)
    
    names = [p.get('name', '') for p in pts if p.get('name')]
    namemap = pages_by_name(dd, sorted(set(names)))
    dd.close()
    
    updated = 0
    for p in pts:
        name = p.get('name', '')
        if not name: continue
        
        pdf_page = namemap.get(name)
        if pdf_page is not None:
            p['sourcePage'] = pdf_page
            if 'provenance' in p:
                del p['provenance']
            updated += 1
            
    if updated > 0:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(m, file, ensure_ascii=False, indent=1)
        print(f"  -> Updated {updated}/{len(pts)} points with flat sourcePage.")
        fixed += 1

print(f"Done. Fixed {fixed} AHU models.")
