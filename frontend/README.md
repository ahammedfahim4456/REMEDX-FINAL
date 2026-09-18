# ReMedX Frontend Interface

The ReMedX user interface is a responsive web application designed for biomedical researchers, clinicians, and pharmaceutical data scientists to explore drug repurposing candidates with ease and visual clarity.

---

## Architecture & Features

- **Interactive Search & Discovery**:
  - Live disease auto-querying with pre-warmed targets and quick-suggestion chips (Alzheimer's, Type 2 Diabetes, Parkinson's, etc.).
  - Real-time confidence metrics, clinical trial phase badges (Phase I-IV / Approved), and mechanism of action indicators.
- **Cheminformatics & Chemical Visualization**:
  - Interactive 2D chemical structure rendering directly from PubChem.
  - Live Lipinski Rule-of-5 radar, Veber criteria, and Ghose filter breakdowns.
  - PAINS / Brenk structural toxicity warnings with visual alert tags.
- **Living Story & Narrative Hypotheses**:
  - Evidence-backed AI summaries detailing why a drug originally intended for one pathology exhibits therapeutic promise for another.
- **Dynamic WebGL Atmosphere**:
  - Powered by the `<SoftAurora />` WebGL shader component (`ogl` library) for smooth, ambient visual immersion.
- **One-Click Dossier Export**:
  - Export comprehensive multi-page scientific PDF dossiers directly to the local system.

---

## Directory Structure

```text
frontend/
├── index.html                     # Main interactive application UI
├── package.json                   # UI package metadata and dependencies
├── remedx-background.png          # High-resolution platform graphic
├── assets/
│   └── remedx-background.png      # Assets directory
└── components/
    └── SoftAurora/                # React Bits WebGL Shader Aurora component
        ├── SoftAurora.jsx
        ├── SoftAurora.css
        └── index.js
```

---

## Running the Frontend

### Option 1: Served Automatically by the Backend (Recommended)
When the ReMedX Flask backend is running (`python backend/app.py`), navigate your browser directly to:
```
http://localhost:5000/
```
The backend automatically hosts and serves `frontend/index.html` and its associated assets.

### Option 2: Standalone Static File
You can also open `frontend/index.html` directly in any modern web browser (Chrome, Edge, Firefox, Safari). It communicates with `http://localhost:5000/api/...` via CORS.

### Option 3: Modern React / Vite Tooling
If developing additional React components alongside `SoftAurora`:
```bash
npm install
npm run dev
```
