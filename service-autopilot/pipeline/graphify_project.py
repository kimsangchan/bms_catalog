# -*- coding: utf-8 -*-
import os, json, glob, shutil

VAULT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'obsidian_vault'))

def reset_vault():
    if os.path.exists(VAULT_DIR):
        shutil.rmtree(VAULT_DIR)
    os.makedirs(VAULT_DIR)
    os.makedirs(os.path.join(VAULT_DIR, 'Models'))
    os.makedirs(os.path.join(VAULT_DIR, 'PDFs'))
    os.makedirs(os.path.join(VAULT_DIR, 'Categories'))
    os.makedirs(os.path.join(VAULT_DIR, 'Vendors'))
    os.makedirs(os.path.join(VAULT_DIR, 'Pipeline'))

def write_md(folder, filename, content):
    filepath = os.path.join(VAULT_DIR, folder, str(filename).replace('/', '_') + '.md')
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)

def generate_vault():
    reset_vault()
    
    models = []
    pdf_to_models = {}
    vendor_to_models = {}
    cat_to_models = {}
    
    # Read all models
    for f in glob.glob('data/models/*.json'):
        try:
            with open(f, 'r', encoding='utf-8') as file:
                m = json.load(file)
                models.append(m)
        except Exception as e:
            pass
            
    # Process models
    for m in models:
        mid = m.get('id', 'unknown')
        vendor = m.get('vendor') or 'Unknown'
        cat = m.get('equipId') or 'Unknown'
        doc = m.get('sourceDoc') or 'Unknown'
        
        pdf_to_models.setdefault(doc, []).append(m)
        vendor_to_models.setdefault(vendor, []).append(m)
        cat_to_models.setdefault(cat, []).append(m)
        
        # Model Markdown
        pts_count = len(m.get('points', []))
        interfaces_count = sum(len(i.get('points', [])) for i in m.get('interfaces', []))
        total_pts = max(pts_count, interfaces_count)
        
        content = f"""# {mid}

## Overview
- **Vendor**: [[{vendor}]]
- **Equipment Category**: [[{cat}]]
- **Source PDF**: [[{doc}]]
- **Total Points**: {total_pts}

## Context Graph
`mermaid
graph LR
    PDF["?? {doc}"] --> Model("{mid}")
    Model --> Cat["?? {cat}"]
    Model --> Vendor["?? {vendor}"]
`
"""
        write_md('Models', mid, content)
        
    # PDFs Markdown
    for doc, mods in pdf_to_models.items():
        if doc == 'Unknown': continue
        
        pdf_path = os.path.join(os.path.dirname(__file__), 'data', 'raw', doc)
        exists = os.path.isfile(pdf_path)
        
        links = "\n".join(f"- [[{m.get('id')}]]" for m in mods)
        
        content = f"""# {doc}

## File Info
- **Location**: service-autopilot/pipeline/data/raw/{doc}
- **Exists Locally**: {exists}

## Models Extracted from this PDF
{links}

## Context Graph
`mermaid
graph TD
    PDF["?? {doc}"]
"""
        for m in mods:
            safe_mid = m.get("id").replace("-", "_").replace(".", "_")
            content += f'    PDF --> Model_{safe_mid}("{m.get("id")}")\n'
        content += "`\n"
        write_md('PDFs', doc, content)
        
    # Vendors Markdown
    for vendor, mods in vendor_to_models.items():
        if vendor == 'Unknown': continue
        links = "\n".join(f"- [[{m.get('id')}]]" for m in mods)
        content = f"# {vendor}\n\n## Models\n{links}\n"
        write_md('Vendors', vendor, content)
        
    # Categories Markdown
    for cat, mods in cat_to_models.items():
        if cat == 'Unknown': continue
        links = "\n".join(f"- [[{m.get('id')}]]" for m in mods)
        content = f"# {cat}\n\n## Models\n{links}\n"
        write_md('Categories', cat, content)
        
    # Home Dashboard
    home = f"""# Project Dashboard

Welcome to the Service Autopilot extraction pipeline knowledge base.
This vault automatically maps the relationships between Raw PDFs, JSON Models, and Equipment Categories.

## Quick Links
- **Total Models**: {len(models)}
- **Total PDFs mapped**: {len(pdf_to_models)}
- **Vendors**: {len(vendor_to_models)}

### Views
- [[Pipeline Architecture]]
"""
    write_md('', 'Home', home)
    
    # Pipeline Architecture
    arch = """# Pipeline Architecture

`mermaid
graph TD
    subgraph Data Sources
        Raw[data/raw/*.pdf]
    end
    
    subgraph Extraction Pipeline
        Extract[extract.py\nRead PDF text & tables]
        Register[register.py\nCreate Models]
        Crosscheck[crosscheck.py\nValidate extractions]
    end
    
    subgraph Output
        Models[data/models/*.json\nEquipment Models]
    end
    
    subgraph Review & Generation
        Datasets[datasets.py\nJoin with schemas]
        Build[build.py\nGenerate Catalogs]
        Verify[verify_points.py\nCross-reference raw PDF images]
    end
    
    Raw --> Extract
    Extract --> Register
    Register --> Models
    Models --> Crosscheck
    
    Models --> Datasets
    Datasets --> Build
    Datasets --> Verify
    Raw -.->|Page Images| Verify
`
"""
    write_md('Pipeline', 'Pipeline Architecture', arch)
    print(f"Vault generated at {VAULT_DIR}")

if __name__ == '__main__':
    generate_vault()
