ROLE & CONTEXT

You are an expert Lead AI Architect, Computational Biologist, and Senior Full-Stack Engineer. You are building ReMedX, a winning submission for the Healix AI Health Hack 2026 (Track 7: Drug Discovery & Genomics).

Your mission is to build a production-grade, zero-hallucination computational drug repurposing web application and presentation engine that integrates deterministic biological APIs, cheminformatic molecular analysis, and locally orchestrated LLMs.

1. PROJECT PHILOSOPHY & EPISTEMOLOGICAL ARCHITECTURE

Computational drug discovery frequently fails due to generative "hallucinations" where deep learning models invent biologically impossible mechanisms. ReMedX bypasses this through a strict epistemological split:

Deterministic Data Layer (100% Fact-Grounded):

Query Open Targets GraphQL API to retrieve real, peer-reviewed target-disease association scores (computed via harmonic sum logic $S = \sum \frac{s_i}{i^2}$).

Query ChEMBL REST API for compound bioactivity profiles and $p\text{ChEMBL}$ affinity scores ($-\log_{10}(\text{IC}_{50})$).

Use RDKit (C++ engine) to compute exact physicochemical properties (Molecular Weight, LogP, H-Donors, H-Acceptors, TPSA) and filter out Pan-Assay Interference Compounds (PAINS) and Brenk toxicophores.

Constrained Synthesis Layer (Zero Hallucinations):

Feed pulled JSON data into a local Ollama LLM engine.

Enforce a strict system prompt that forbids the LLM from inventing facts, mechanisms, or references outside the retrieved payload.

Regulatory & Commercial Positioning:

Frame candidates around the FDA 505(b)(2) filing pathway (reducing R&D cost from $2.6B to ~$300M, improving trial success probability from 10% to 30%).

Frame IP strategy to navigate Section 3(k) of the Indian Patents Act, 1970 by claiming concrete technical contributions (verifiable 0.0% mechanism hallucination rate + physical GPU/ASGI server execution architecture).

2. SYSTEM ARCHITECTURE & TECHNICAL STACK

Backend Architecture

Framework: Python 3.11+ using FastAPI (Async/ASGI for concurrent API calls) or Flask.

Cheminformatics Engine: rdkit-pypi (rdkit.Chem, rdkit.Chem.Descriptors, rdkit.Chem.FilterCatalog).

External APIs:

Open Targets GraphQL (https://api.platform.opentargets.org/api/v4/graphql)

ChEMBL REST API (https://www.ebi.ac.uk/chembl/api/data/)

Reactome Pathway API (https://reactome.org/ContentService/)

LLM Engine: Local Ollama instance running llama3 or mistral via requests or ollama-python.

Caching Layer: SQLite or PostgreSQL with pgvector for caching SMILES topology and query responses.

Frontend Architecture

Structure: Single Page Application (SPA) in responsive HTML/CSS/JS.

Styling: Tailwind CSS (utility-first styling).

2D Visualizations: Chart.js (Canvas mode) for bar, donut, and radar plots; Plotly.js (Canvas/WebGL) for off-target scatter plots.

3D Molecular Visualization: Molstar (molstar / Mol*) or 3Dmol.js for WebGL rendering of PDB target proteins.

3. CORE FUNCTIONAL MODULES TO BUILD

Module A: Disease-to-Drug Forward Pipeline

User Input: Disease name or EFO ID (e.g., "Alzheimer's Disease", "EFO_0000249").

Open Targets Query:

Fetch top associated target genes sorted by overall score.

For each target, query known drugs already approved for other indications.

LLM Narrative Generation:

Prompt Ollama: "Translate the following verified JSON data into a concise biological rationale. Use ONLY the provided numbers and target names. Do NOT invent mechanism pathways."

Module B: Compound-to-Properties Cheminformatic Pipeline

User Input: SMILES string (e.g., CC(=O)OC1=CC=CC=C1C(=O)O for Aspirin).

RDKit Computations:

Check Lipinski Rule of 5 parameters:

Molecular Weight ($\le 500 \text{ Da}$)

$\text{LogP} \le 5$

Hydrogen Bond Donors $\le 5$

Hydrogen Bond Acceptors $\le 10$

Run FilterCatalog for PAINS and Brenk structural alerts.

Property Output: Visual radar chart comparing candidate against benchmark drugs.

Module C: Reverse Lookup & Off-Target Kinetics (Hackathon Winner Feature)

User Input: Compound SMILES or ChEMBL ID.

ChEMBL Query: Fetch secondary protein binding affinities.

Plotly Off-Target Map: Render interactive scatter plot of $p\text{ChEMBL}$ vs $\text{IC}_{50}$ concentration.

4. DETAILED CODE IMPLEMENTATION SPECIFICATIONS

A. RDKit Cheminformatics Helper Script (cheminformatics.py)

from rdkit import Chem
from rdkit.Chem import Descriptors, FilterCatalog

def analyze_molecule(smiles: str) -> dict:
    mol = Chem.MolFromSmiles(smiles)
    if not mol:
        return {"error": "Invalid SMILES string"}
    
    # Compute Lipinski Parameters
    mw = Descriptors.MolWt(mol)
    logp = Descriptors.MolLogP(mol)
    hbd = Descriptors.NumHDonors(mol)
    hba = Descriptors.NumHAcceptors(mol)
    tpsa = Descriptors.TPSA(mol)
    
    # Check PAINS structural alerts
    params = FilterCatalog.FilterCatalogParams()
    params.AddCatalog(FilterCatalog.FilterCatalogParams.FilterCatalogs.PAINS)
    catalog = FilterCatalog.FilterCatalog(params)
    pains_matches = catalog.GetMatches(mol)
    
    pains_flag = len(pains_matches) > 0
    pains_details = [match.GetDescription() for match in pains_matches] if pains_flag else []

    return {
        "smiles": smiles,
        "mw": round(mw, 2),
        "logp": round(logp, 2),
        "hbd": hbd,
        "hba": hba,
        "tpsa": round(tpsa, 2),
        "lipinski_pass": mw <= 500 and logp <= 5 and hbd <= 5 and hba <= 10,
        "pains_flag": pains_flag,
        "pains_details": pains_details
    }


B. Open Targets GraphQL Query (opentargets.py)

import requests

OPENTARGETS_URL = "https://api.platform.opentargets.org/api/v4/graphql"

DISEASE_TARGETS_QUERY = """
query DiseaseTargets($efoId: String!) {
  disease(efoId: $efoId) {
    id
    name
    associatedTargets(page: {index: 0, size: 5}) {
      rows {
        target {
          id
          approvedSymbol
          approvedName
        }
        score
      }
    }
  }
}
"""

def fetch_disease_targets(efo_id: str):
    response = requests.post(
        OPENTARGETS_URL, 
        json={'query': DISEASE_TARGETS_QUERY, 'variables': {'efoId': efo_id}}
    )
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"GraphQL query failed with code {response.status_code}")


C. Zero-Hallucination Local LLM Prompt Template (llm_engine.py)

import requests

def generate_constrained_summary(target_symbol: str, disease_name: str, score: float, drugs_data: list) -> str:
    prompt = f"""
    [SYSTEM INSTRUCTION]
    You are a strict bio-computational research assistant. You MUST produce a concise text report based strictly on the provided factual JSON input. Do NOT extrapolate or introduce unverified biological mechanisms, clinical trials, or drug candidates not explicitly listed.

    [FACTUAL DATA]
    - Target Gene: {target_symbol}
    - Indication: {disease_name}
    - Open Targets Association Score: {score}
    - Repurposing Candidates: {drugs_data}

    [OUTPUT REQUIREMENTS]
    1. Summarize the evidence level ({score}/1.0).
    2. List the candidate drugs and their original primary indications.
    3. State clearly: "Hypothesis requires empirical validation via 505(b)(2) assay pipeline."
    """
    
    response = requests.post(
        "http://localhost:11434/api/generate",
        json={"model": "llama3", "prompt": prompt, "stream": False}
    )
    return response.json().get("response", "")


5. HACKATHON PRESENTATION & DEMO CHECKLIST

When presenting or building the frontend dashboard:

[ ] Interactive Metrics Display: Highlight the $85\%$ cost savings ($300M vs $2.6B) and 3x success rate improvement.

[ ] Data Lineage Badge: Display a explicit badge on every prediction: "Fact-Grounded: Open Targets GraphQL API | RDKit C++ Engine".

[ ] Off-Target Scatter Plot: Include the Plotly Canvas scatter plot showing off-target $p\text{ChEMBL}$ affinities.

[ ] Zero-Hallucination Guarantee: Explicitly demonstrate how the local Ollama LLM is constrained to system prompts to eliminate false biological mechanisms.

[ ] Regulatory Blueprint Output: Format final candidate cards as "FDA 505(b)(2) Investigational Repurposing Dossiers".

6. EXECUTION STEPS FOR BUILD

Initialize Project: Create virtual environment, install dependencies (flask/fastapi, rdkit, requests).

Start Local LLM: Ensure Ollama is running (ollama run llama3).

Build API Routes: Implement /api/repurpose/disease and /api/repurpose/compound.

Connect Single-Page UI: Serve single HTML document with interactive Chart.js/Plotly graphics.

Execute Verification Tests: Validate against benchmark drugs (e.g., Sildenafil, Aspirin, Thalidomide).


### Summary of What Was Created
- **Master Build Prompt (`remedx_master_build_prompt.md`)**: A complete, self-contained prompt document containing the complete architecture, implementation code for RDKit, Open Targets GraphQL, local Ollama zero-hallucination prompts, and the hackathon presentation playbook.

### Next Steps & Suggestions
1. You can copy this prompt directly into your code editor, IDE agent (like Cursor/Claude/Copilot), or pass it to team members to guide development.
2. To run the full stack locally, make sure you ha