# ReMedX Backend API & Intelligence Engine

The ReMedX backend is a high-performance Flask microservice delivering real-time biomedical intelligence, chemical profiling, drug repurposing target identification, and automated clinical hypothesis generation.

---

## Key Modules & Capabilities

1. **Disease Repurposing Engine (`/api/repurpose`)**:
   - Queries Open Targets Platform GraphQL API for disease-to-target associations.
   - Cross-references approved and clinical-stage drugs targeting associated genes.
   - Calculates target confidence scores, clinical phases, and mechanism of action.
   - Integrates local LLM (Ollama with `gemma3` or fallback) to generate plain-language biomedical rationales.
   - Built-in SQLite caching layer (`repurpose_cache.db`) with 24-hour TTL for instant query recall.

2. **Cheminformatics & ADMET Engine (`/api/compound/analyze`)**:
   - Evaluates chemical structures (SMILES) against standard drug-likeness rules:
     - **Lipinski's Rule of 5** (Molecular weight, LogP, H-bond donors, H-bond acceptors).
     - **Veber Rules** (Rotatable bonds, Topological polar surface area / TPSA).
     - **Ghose Filter** (Molar refractivity, atom count bounds).
   - Structural alert pattern detection (**PAINS A/B/C** and **Brenk filters** for toxic or promiscuous substructures).
   - ADMET estimations for human intestinal absorption (HIA) and blood-brain barrier (BBB) permeability.
   - Fetches exact 2D molecular structures and CIDs via PubChem PUG REST API.

3. **ChEMBL Reverse Lookup Engine (`/api/reverse-lookup`)**:
   - Resolves target mechanisms and bioactivities across ChEMBL databases for candidate drug molecules.

4. **Reactome Pathway Enrichment (`/api/pathways`)**:
   - Discovers biological pathways and functional cascades associated with target genes via Reactome API.

5. **Automated Clinical PDF Export (`/api/export-pdf`)**:
   - Dynamically compiles comprehensive drug repurposing dossiers and multi-page technical reports using ReportLab.

---

## Installation & Setup

### Prerequisites
- Python 3.10+
- (Optional) [Ollama](https://ollama.com/) with model `gemma3` pulled (`ollama pull gemma3`)

### Steps

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure Environment (Optional)**:
   Copy `.env.example` to `.env` and configure your API keys:
   ```bash
   cp .env.example .env
   ```

3. **Start the Backend Server**:
   ```bash
   python app.py
   ```
   The server will initialize SQLite caching tables and listen on `http://localhost:5000`.

---

## API Reference

| Method | Endpoint | Query Parameters | Description |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | None | Serves the ReMedX frontend interface |
| `GET` | `/api/repurpose` | `disease` (string) | Drug repurposing hypotheses and evidence candidates |
| `GET` | `/api/compound/analyze` | `smiles` (string) | ADMET, Lipinski, Veber, PAINS, and Brenk profiling |
| `GET` | `/api/reverse-lookup` | `query` (string) | Drug molecule bioactivity & target profile |
| `GET` | `/api/pathways` | `gene` (string) | Reactome biological pathways for a given gene |
| `GET` | `/api/export-pdf` | `disease` (string) | Downloads formatted PDF dossier of findings |
| `GET` | `/api/health` | None | System status and service health check |
| `GET` | `/api/cache-stats` | None | Statistics on cached queries and response latencies |

---

## Testing

Run the automated test suites:
```bash
# Run endpoint functionality verification
python tests/test_endpoints.py

# Run scale and stress verification test suite
python tests/test_comprehensive_scale.py
```
