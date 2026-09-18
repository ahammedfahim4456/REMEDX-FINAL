# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users
Biomedical researchers, translational scientists, academic clinicians, and pharmaceutical data scientists seeking rapid, evidence-grounded therapeutic candidates for drug repurposing without wading through disconnected biomedical silos.

## Product Purpose
Accelerate drug discovery from a decade-long, multi-billion-dollar endeavor to seconds. ReMedX connects genomic target associations, chemical ADMET feasibility, kinetic off-target bioactivities, and local LLM mechanistic reasoning to uncover viable secondary indications for approved and investigational molecules.

## Positioning
Unlike proprietary black-box AI drug engines, ReMedX operates transparently: every therapeutic lead is verifiable through Open Targets genetic scores, RDKit QSAR descriptors, ChEMBL bioassays, and Reactome pathways, accompanied by locally synthesized mechanistic rationales (Ollama Gemma 3) and instant publication-ready PDF dossiers.

## Operating Context
Used during early-stage hypothesis generation, target validation sprints, academic grant writing, and clinical trial feasibility reviews. Designed to run both with local backend services and as an offline-capable evidence explorer with pre-warmed SQLite caching.

## Capabilities and Constraints
- Search disease conditions with instant autocompletion and preset benchmarks (Alzheimer's, Parkinson's, Glioblastoma, Type 2 Diabetes, etc.).
- Multi-dimensional ranking by confidence score, clinical trial development phase (FDA Phase IV approved leads prioritized), and target gene.
- 2D chemical structure rendering via PubChem PUG REST and RDKit molecular descriptor metrics (MW, LogP, TPSA, HBD, HBA, RotB).
- Drug-likeness criteria compliance checks: Lipinski Rule of 5, Veber oral bioavailability, and PAINS toxicophore alerts.
- HTML5 Canvas Bioavailability Radar envelope with MPO desirability rating.
- ChEMBL reverse lookup mapping off-target binding affinities (IC50 / pChEMBL) to converted nanomolar potencies.
- Reactome signaling cascade modal with direct deep-links to official biological pathway diagrams.
- Sticky 4-lead comparison dock with side-by-side parametric matrix evaluation.
- Local AI mechanistic rationale generation with on-demand deepening via Ollama.
- Dynamic one-click scientific PDF dossier export.

## Brand Commitments
- Name: ReMedX
- Visual Identity: Living Organism aesthetic with porcelain white, soft mint, and bio-emerald hues.
- Voice: Empirical, precise, scientific, elegant, clear.

## Evidence on Hand
- Pre-warmed SQLite database caching 22 validated disease condition profiles.
- Integrated public APIs: Open Targets GraphQL (v4), ChEMBL REST (v33), Reactome REST, PubChem PUG REST.
- Test suites: test_endpoints.py, test_comprehensive_scale.py.

## Product Principles
1. Empirical primacy: Every clinical lead and AI explanation must tie directly to mapped genomic evidence and bioactivity data.
2. Clinical pragmatism: Highlight approved drugs with existing human safety records (FDA 505(b)(2) fast-track repurposing).
3. Zero-black-box cheminformatics: Show exact numbers for molecular weight, polar surface area, and rule violations.
4. Frictionless research workflow: Enable seamless cross-navigation from target genetics to chemical lab to off-target landscape.

## Accessibility & Inclusion
- Clear typography hierarchy with high-contrast text meeting WCAG AA requirements.
- Tactile interactive affordances with keyboard navigation across discovery chapters.
- Full support for prefers-reduced-motion to prevent motion discomfort in laboratory settings.
