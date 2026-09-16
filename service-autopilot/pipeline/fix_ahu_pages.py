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
        
    missing = [p for p in pts if (p.get('provenance') or {}).get('sourcePage') is None]
    if not missing:
        continue
        
    doc = m.get('sourceDoc')
    if not doc:
        print(f"Skipping {m['id']} - no sourceDoc")
        continue
        
    path = os.path.join(DATA, 'raw', doc)
    if not os.path.isfile(path):
        print(f"Skipping {m['id']} - PDF not found: {path}")
        continue
        
    print(f"Processing {m['id']} ({len(missing)} missing points)...")
    dd = fitz.open(path)
    
    # Extract names to search
    names = [p.get('name', '') for p in missing if p.get('name')]
    
    namemap = pages_by_name(dd, sorted(set(names)))
    dd.close()
    
    updated = 0
    for p in missing:
        name = p.get('name', '')
        if not name: continue
        
        pdf_page = namemap.get(name)
        if pdf_page is not None:
            if 'provenance' not in p:
                p['provenance'] = {}
            # Verify_points expects the 'printed' page in provenance.
            # But pages_by_name returns 1-based PDF page.
            # We will use PDF page as the sourcePage since we have no printed page logic for these.
            p['provenance']['sourcePage'] = pdf_page
            updated += 1
            
    if updated > 0:
        with open(f, 'w', encoding='utf-8') as file:
            json.dump(m, file, ensure_ascii=False, indent=1)
        print(f"  -> Updated {updated}/{len(missing)} points.")
        fixed += 1

print(f"Done. Fixed {fixed} AHU models.")
