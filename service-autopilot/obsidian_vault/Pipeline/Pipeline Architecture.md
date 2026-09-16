# Pipeline Architecture

`mermaid
graph TD
    subgraph Data Sources
        Raw[data/raw/*.pdf]
    end
    
    subgraph Extraction Pipeline
        Extract[extract.py
Read PDF text & tables]
        Register[register.py
Create Models]
        Crosscheck[crosscheck.py
Validate extractions]
    end
    
    subgraph Output
        Models[data/models/*.json
Equipment Models]
    end
    
    subgraph Review & Generation
        Datasets[datasets.py
Join with schemas]
        Build[build.py
Generate Catalogs]
        Verify[verify_points.py
Cross-reference raw PDF images]
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
