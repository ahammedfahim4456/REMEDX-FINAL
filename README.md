# ReMedX (REMEDX FINAL) 🧬💊
> **AI-Powered Drug Repurposing Intelligence Platform**  
> *Accelerating therapeutic discovery from decades to seconds by connecting genomics, cheminformatics, and biological networks.*

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-3.0.3-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Hackathon%20Final%20Release-brightgreen.svg)]()

---

## 📖 Overview

Developing a new pharmaceutical drug typically requires **10–15 years** and over **$2.6 billion**, with failure rates exceeding 90% in clinical trials. 

**ReMedX** inverts this paradigm through algorithmic drug repurposing. By fusing genomic disease associations, clinical bioactivities, deep cheminformatics screening, and biological pathway networks, ReMedX uncovers non-obvious therapeutic hypotheses for established, clinically-validated molecules.

```
+---------------------------------------------------------------------------------------+
|                                    ReMedX Platform                                    |
|                                                                                       |
|   [ Disease Query ]                                                                   |
|          │                                                                            |
|          ▼                                                                            |
|   Open Targets GraphQL ──► Target Gene Scoring & Validation                           |
|          │                                                                            |
|          ├──────────────► ChEMBL Bioactivity & Drug Lookup                            |
|          │                                                                            |
|          ├──────────────► Reactome Biological Pathway Analysis                        |
|          │                                                                            |
|          ├──────────────► Cheminformatics Engine (Lipinski, Veber, PAINS, Brenk)      |
|          │                                                                            |
|          ▼                                                                            |
|   Ollama / LLM Reasoning Engine ──► "Living Story" Plain-English Clinical Hypotheses  |
|          │                                                                            |
|          ▼                                                                            |
|   Interactive Web UI & Instant Clinical PDF Dossier Generation                        |
+---------------------------------------------------------------------------------------+
```

---

## ✨ Core Features

- **🎯 Genomic Target Association Engine**:
  Queries the Open Targets Platform GraphQL API to rank high-confidence disease targets and maps them to approved or investigational drugs.
- **🔬 Real-Time Cheminformatics & ADMET**:
  Evaluates candidate chemical structures (SMILES) against:
  - **Lipinski's Rule of 5** (MW, LogP, HBD, HBA)
  - **Veber Rules** (Rotatable bonds, TPSA)
  - **Ghose Filter** (Molecular refractivity, atom count bounds)
  - **Structural Alerts**: Detects promiscuous binders and toxicophores using **PAINS A/B/C** and **Brenk** filters.
  - **ADMET Estimations**: Predicts human intestinal absorption (HIA) and blood-brain barrier (BBB) permeability.
- **🧬 Biological Pathway Enrichment**:
  Integrates Reactome to map affected pathways and downstream cascades.
- **💡 "Living Story" Clinical Explanations**:
  Employs local AI models (via Ollama `gemma3:latest` or rule-based fallback) to synthesize why an approved compound is mechanistically viable for an alternative pathology.
- **📄 One-Click Scientific PDF Export**:
  Dynamically compiles multi-page publication-ready PDF dossiers complete with chemical parameters, confidence metrics, and references.
- **✨ Fluid Modern UI & WebGL Atmosphere**:
  Featuring real-time search chips, chemical radar visualizations, responsive layouts, and interactive WebGL canvas animations via `<SoftAurora />`.

---

## 📂 Repository Structure

This repository is split into clean, modular components:

```text
REMEDX-FINAL/
├── .gitignore                      # Git configuration & secret prevention
├── README.md                       # Main repository overview (this document)
│
├── frontend/                       # Client Interface & Visualizations
│   ├── index.html                  # Full-featured ReMedX v3 Web Platform
│   ├── package.json                # Frontend package metadata (ogl, react)
│   ├── README.md                   # Frontend running and customization guide
│   ├── remedx-background.png       # Branding background asset
│   ├── assets/                     # Graphic assets
│   └── components/                 # UI components
│       └── SoftAurora/             # WebGL Shader Aurora React component
│
├── backend/                        # High-Performance Intelligence Engine
│   ├── app.py                      # Flask REST API server
│   ├── chembl_client.py            # ChEMBL REST reverse lookup client
│   ├── cheminformatics.py          # PAINS, Brenk, Lipinski, ADMET engine
│   ├── reactome_client.py          # Reactome pathway enrichment client
│   ├── prewarm_cache.py            # Cache pre-warming utility
│   ├── requirements.txt            # Python dependencies
│   ├── .env.example                # Safe environment variables template
│   ├── README.md                   # Backend documentation and API reference
│   └── tests/                      # Automated test suite
│       ├── test_endpoints.py       # API route verification
│       └── test_comprehensive_scale.py # Multi-threaded stress testing
│
└── docs/                           # Documentation, Literature & Media
    ├── README.md                   # Documentation guide
    ├── proposal/                   # Foundational proposal PDF
    ├── presentation/               # Slide decks and pitch documents
    ├── research/                   # Biomedical and cheminformatics research notes
    └── media/                      # Architecture mindmaps and pipeline workflows
```

---

## 🚀 Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/ahammedfahim4456/REMEDX-FINAL.git
cd REMEDX-FINAL
```

### 2. Backend Setup
```bash
cd backend
pip install -r requirements.txt
```

*(Optional)* Configure your environment:
```bash
cp .env.example .env
```

Start the Flask server:
```bash
python app.py
```
*The server will start on `http://localhost:5000`.*

### 3. Open the Frontend
Simply visit:
```
http://localhost:5000/
```
The Flask backend serves the frontend automatically. Alternatively, you can open `frontend/index.html` directly in any web browser.

---

## 📡 API Endpoints

| Endpoint | Method | Params | Description |
| :--- | :--- | :--- | :--- |
| `/` | `GET` | — | Serves the ReMedX frontend interface |
| `/api/repurpose` | `GET` | `disease` | Fetches prioritized repurposing candidates & AI hypotheses |
| `/api/compound/analyze` | `GET` | `smiles` | Runs cheminformatics rules (Lipinski, Veber, PAINS, Brenk) |
| `/api/reverse-lookup` | `GET` | `query` | Queries ChEMBL for drug bioactivity targets |
| `/api/pathways` | `GET` | `gene` | Returns Reactome biological pathways |
| `/api/export-pdf` | `GET` | `disease` | Generates a formatted scientific clinical dossier (PDF) |
| `/api/health` | `GET` | — | System health and service readiness check |
| `/api/cache-stats` | `GET` | — | SQLite caching performance and storage metrics |

---

## 🧪 Testing & Validation

Execute test suites from the project root:
```bash
# Verify API endpoints
python backend/tests/test_endpoints.py

# Stress test caching and concurrent requests
python backend/tests/test_comprehensive_scale.py
```

---

## 🛡️ Security & Integrity

- **Environment & Secrets**: Sensitive credentials (`.env`) are excluded via `.gitignore`; refer to `backend/.env.example`.
- **Database Caching**: Dynamic SQLite cache files (`repurpose_cache.db`) are auto-created on first run and excluded from source control.

---

## 👥 Contributors & Acknowledgements

- **Team ReMedX**
- Powered by [Open Targets Platform](https://platform.opentargets.org/), [ChEMBL](https://www.ebi.ac.uk/chembl/), [PubChem](https://pubchem.ncbi.nlm.nih.gov/), and [Reactome](https://reactome.org/).
