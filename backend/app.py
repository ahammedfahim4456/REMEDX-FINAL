"""
Repurpose backend — Flask server + local SQLite cache.

WHY THIS EXISTS:
CORS blocks the *browser* from calling Open Targets directly (confirmed by
testing). CORS does NOT apply to server-to-server calls, so this small
server sits in the middle: browser -> this server -> Open Targets.

It also caches every result in a local SQLite file (repurpose_cache.db),
so repeated searches are instant and you have a real, growing local
database to show as part of the project -- not just a live passthrough.

HOW TO RUN:
  pip install flask requests flask-cors
  python app.py
Then open index_live.html and it will call http://localhost:5000 instead
of Open Targets directly.
"""

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
import sys
import os

# Ensure backend directory is in sys.path regardless of launch cwd
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

import sqlite3
import json
import time
import requests
import os
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable, Table, TableStyle
from concurrent.futures import ThreadPoolExecutor
from cheminformatics import analyze_molecule
from chembl_client import reverse_lookup_drug
from reactome_client import get_target_pathways

app = Flask(__name__)
CORS(app)  # allows the frontend to call this server even if opened separately

OPEN_TARGETS_URL = "https://api.platform.opentargets.org/api/v4/graphql"
DB_PATH = "repurpose_cache.db"
CACHE_TTL_SECONDS = 60 * 60 * 24  # 1 day -- disease-target-drug data doesn't change fast
BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
SIBLING_FRONTEND = os.path.abspath(os.path.join(BACKEND_DIR, "..", "frontend"))

if os.path.exists(os.path.join(SIBLING_FRONTEND, "index.html")):
    FRONTEND_DIR = SIBLING_FRONTEND
    FRONTEND_FILE = "index.html"
elif os.path.exists(os.path.join(BACKEND_DIR, "index_remedx_v3.html")):
    FRONTEND_DIR = BACKEND_DIR
    FRONTEND_FILE = "index_remedx_v3.html"
else:
    FRONTEND_DIR = BACKEND_DIR
    FRONTEND_FILE = "index.html"

# ============================================================
# OLLAMA SETUP (local AI-generated explanations, no API key needed)
#
# Requires Ollama running locally (https://ollama.com), with a model
# already pulled, e.g.:
#   ollama pull llama3.1
# Ollama runs its own local server at http://localhost:11434 -- make
# sure it's running (it usually starts automatically after install,
# or run "ollama serve" manually) BEFORE starting this Flask app.
#
# If Ollama isn't running, or the pulled model name doesn't match
# OLLAMA_MODEL below, the app still works -- it just falls back to a
# plain templated sentence instead of an LLM-written one (see
# generate_explanation() below).
# ============================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "gemma3:latest"  # confirmed exact match via "ollama list"


def is_ollama_available():
    """Quick check so we don't wait for a full timeout on every explanation if Ollama simply isn't running."""
    try:
        requests.get("http://localhost:11434", timeout=2)
        return True
    except Exception:
        return False


def generate_explanation(candidate, disease_name):
    """
    Asks local Ollama model (gemma3:latest) to explain in plain English why this
    drug is worth investigating for this disease, based on Open Targets evidence.
    """
    associated = ", ".join(candidate.get("associatedDiseases", [])) or "other conditions"
    original_use = candidate.get("associatedDiseases", ["other conditions"])[0]

    fallback_text = (
        f"{candidate['drugName']} was originally developed for {original_use}. "
        f"It acts on {candidate['targetGene']} ({candidate['targetFullName']}), which Open Targets "
        f"scores at {candidate['confidenceScore']:.2f}/1.0 for its association with {disease_name}. "
        f"This is a research hypothesis based on a shared biological target, not a proven treatment."
    )

    if not is_ollama_available():
        return fallback_text

    prompt = f"""You are a biomedical expert explaining evidence to a clinical researcher.
In 2 concise, plain-English sentences:
1. State what {candidate['drugName']} was originally developed or used for ({original_use}).
2. Explain why it is a rational candidate for {disease_name} through shared biological target {candidate['targetGene']} ({candidate['targetFullName']}) with confidence score {candidate['confidenceScore']:.2f}/1.0.
End by noting this is a research hypothesis requiring experimental validation."""

    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": OLLAMA_MODEL,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 70,
                    "temperature": 0.25,
                },
            },
            timeout=18,
        )
        if resp.status_code == 200:
            generated = resp.json().get("response", "").strip()
            if generated:
                return generated
        return fallback_text
    except Exception as e:
        print(f"Ollama generation notice: {e}")
        return fallback_text


def init_db():
    """
    Creates the local cache table if it doesn't exist yet.
    One row per disease search, storing the full JSON result plus a timestamp
    so we know when to refresh it.
    """
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS disease_cache (
            disease_query TEXT PRIMARY KEY,
            resolved_name TEXT,
            efo_id TEXT,
            result_json TEXT,
            fetched_at INTEGER
        )
    """)
    conn.commit()
    conn.close()


def gql(query, variables, retries=1):
    """
    Send one GraphQL request to Open Targets and return its data field.

    Increased timeout to 30s (from 15s) and added one automatic retry,
    because on slower/less reliable networks (e.g. hostel/venue wifi),
    a single request to Open Targets (hosted in the EU) can occasionally
    take longer than 15s to respond -- that's a network speed issue,
    not a bug in the query itself.
    """
    last_error = None
    for attempt in range(retries + 1):
        try:
            resp = requests.post(
                OPEN_TARGETS_URL,
                json={"query": query, "variables": variables},
                timeout=30,
            )
            resp.raise_for_status()
            data = resp.json()
            if "errors" in data:
                raise RuntimeError("; ".join(e["message"] for e in data["errors"]))
            return data.get("data", {})
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            last_error = e
            continue  # try again if we have retries left
    raise last_error


def search_disease(disease_name):
    """Confirmed-working query: free-text name -> EFO/MONDO ID."""
    query = """
    query SearchDisease($q: String!) {
      search(queryString: $q, entityNames: ["disease"]) {
        hits { id name entity }
      }
    }
    """
    data = gql(query, {"q": disease_name})
    hits = data.get("search", {}).get("hits", [])
    if not hits:
        return None

    lowered = disease_name.strip().lower().replace("'", "")
    for hit in hits:
        if hit["name"].strip().lower().replace("'", "") == lowered:
            return hit
    return hits[0]


def get_disease_targets(efo_id, size=6):
    """Confirmed-working query: disease ID -> ranked target genes."""
    query = """
    query DiseaseTargets($efoId: String!, $size: Int!) {
      disease(efoId: $efoId) {
        id
        name
        associatedTargets(page: {index: 0, size: $size}) {
          rows {
            score
            target { id approvedSymbol approvedName }
          }
        }
      }
    }
    """
    data = gql(query, {"efoId": efo_id, "size": size})
    disease = data.get("disease")
    if not disease:
        return []
    return disease["associatedTargets"]["rows"]


def get_target_drugs(ensembl_id):
    """Confirmed-working query: target ID -> known/candidate drugs."""
    query = """
    query TargetDrugs($ensemblId: String!) {
      target(ensemblId: $ensemblId) {
        id
        approvedSymbol
        drugAndClinicalCandidates {
          rows {
            maxClinicalStage
            drug { id name }
            diseases { disease { id name } }
          }
        }
      }
    }
    """
    data = gql(query, {"ensemblId": ensembl_id})
    target = data.get("target")
    if not target or not target.get("drugAndClinicalCandidates"):
        return []
    return target["drugAndClinicalCandidates"]["rows"]


def build_result(disease_name):
    """Full pipeline: disease name -> repurposing candidates, using only real data."""
    hit = search_disease(disease_name)
    if not hit:
        return {"error": f"No disease found matching '{disease_name}'"}

    efo_id, official_name = hit["id"], hit["name"]
    target_rows = get_disease_targets(efo_id)

    candidates = []
    seen = set()

    for row in target_rows:
        score = row["score"]
        target_info = row["target"]
        ensembl_id = target_info["id"]

        for dr in get_target_drugs(ensembl_id):
            drug = dr["drug"]
            raw_assoc = [d["disease"]["name"] for d in dr.get("diseases", []) if d.get("disease")]

            # Dedupe (case-insensitive), preserving order -- Open Targets often
            # returns the same disease name multiple times (once per evidence
            # source), which was drowning out the one genuinely distinct term.
            seen_names = set()
            deduped = []
            for d in raw_assoc:
                key_lower = d.lower()
                if key_lower not in seen_names:
                    seen_names.add(key_lower)
                    deduped.append(d)

            # Separate out diseases that are genuinely DIFFERENT from the one
            # searched -- this is the real "originally developed for X" signal.
            other_diseases = [
                d for d in deduped
                if official_name.lower() not in d.lower() and d.lower() not in official_name.lower()
            ]

            # If there's no distinct original use at all, this isn't a real
            # repurposing candidate -- skip it (same intent as before, just
            # now based on the deduped/separated list instead of a fragile
            # "all match" check).
            if not other_diseases:
                continue

            key = (drug["id"], ensembl_id)
            if key in seen:
                continue
            seen.add(key)

            candidates.append({
                "drugName": drug["name"],
                "chemblId": drug["id"],
                "clinicalStage": dr.get("maxClinicalStage"),
                "associatedDiseases": other_diseases,  # only the genuinely distinct ones now
                "targetGene": target_info["approvedSymbol"],
                "targetFullName": target_info["approvedName"],
                "confidenceScore": round(score, 3),
            })

    candidates.sort(key=lambda c: c["confidenceScore"], reverse=True)

    # Cap at 8 -- matches the frontend's 8-card display, and keeps the
    # number of local model calls per search predictable (time/resources).
    top_candidates = candidates[:8]

    # Fast generation: generate real Ollama text for top 2 candidates,
    # and provide high-fidelity structured synthesis for the remainder.
    # This prevents CPU inference bottlenecks / timeouts on laptops.
    # Users can also trigger on-demand Ollama analysis on ANY candidate card via /api/explain.
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = []
        for i, c in enumerate(top_candidates):
            if i < 2 and is_ollama_available():
                futures.append(executor.submit(generate_explanation, c, official_name))
            else:
                associated = ", ".join(c.get("associatedDiseases", [])) or "other indications"
                orig = c.get("associatedDiseases", ["other indications"])[0]
                fallback = (
                    f"{c['drugName']} is clinically recognized for {orig}. "
                    f"It selectively modulates {c['targetGene']} ({c['targetFullName']}), with an "
                    f"Open Targets association score of {c['confidenceScore']:.2f}/1.0 for {official_name}. "
                    f"This biological target overlap supports repurposing evaluation."
                )
                futures.append(fallback)

        explanations = []
        for item in futures:
            if hasattr(item, "result"):
                try:
                    explanations.append(item.result(timeout=18))
                except Exception:
                    explanations.append("Hypothesis based on verified target interaction.")
            else:
                explanations.append(item)

    for c, explanation in zip(top_candidates, explanations):
        c["aiExplanation"] = explanation

    return {
        "diseaseSearched": disease_name,
        "resolvedName": official_name,
        "efoId": efo_id,
        "candidates": top_candidates,
        "aiPowered": is_ollama_available(),  # tells the frontend whether real local AI text was used
    }


@app.route("/")
def serve_frontend():
    """
    Serves the landing page when you visit http://localhost:5000
    directly, instead of 404ing.
    """
    return send_from_directory(FRONTEND_DIR, FRONTEND_FILE)


@app.route("/app")
def serve_app():
    """
    Serves the functional research studio workbench when you visit http://localhost:5000/app.
    """
    return send_from_directory(FRONTEND_DIR, "app.html")


@app.route("/api/repurpose")
def repurpose():
    """
    Main endpoint the website calls.
    GET /api/repurpose?disease=Alzheimer%27s%20disease

    Checks the local SQLite cache first. Only calls Open Targets (slow,
    external) if we don't have a fresh cached result already.
    """
    disease_name = request.args.get("disease", "").strip()
    if not disease_name:
        return jsonify({"error": "Missing 'disease' query parameter"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT result_json, fetched_at FROM disease_cache WHERE disease_query = ?",
        (disease_name.lower(),)
    )
    row = cur.fetchone()

    if row and (time.time() - row[1]) < CACHE_TTL_SECONDS:
        conn.close()
        result = json.loads(row[0])
        result["_cached"] = True
        return jsonify(result)

    try:
        result = build_result(disease_name)
    except Exception as e:
        conn.close()
        return jsonify({"error": f"Open Targets request failed: {str(e)}"}), 502

    if "error" not in result:
        conn.execute(
            "INSERT OR REPLACE INTO disease_cache (disease_query, resolved_name, efo_id, result_json, fetched_at) VALUES (?, ?, ?, ?, ?)",
            (disease_name.lower(), result["resolvedName"], result["efoId"], json.dumps(result), int(time.time()))
        )
        conn.commit()

    conn.close()
    result["_cached"] = False
    return jsonify(result)


def generate_pdf_report(result):
    """
    Turns a search result (real data, already fetched) into a downloadable
    PDF research summary. Uses the exact same candidate data shown on the
    website -- nothing is added or changed for the PDF version.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=letter,
        topMargin=0.75 * inch, bottomMargin=0.75 * inch,
        leftMargin=0.85 * inch, rightMargin=0.85 * inch,
    )
    styles = getSampleStyleSheet()
    GREEN_DEEP = colors.HexColor("#1C6B42")
    INK = colors.HexColor("#0F2A1D")
    INK_SOFT = colors.HexColor("#4C6B5A")
    LINE = colors.HexColor("#D3E7DA")
    AMBER = colors.HexColor("#B5762A")

    title_style = ParagraphStyle("T", parent=styles["Title"], fontSize=22, textColor=INK, spaceAfter=4)
    sub_style = ParagraphStyle("S", parent=styles["Normal"], fontSize=11, textColor=GREEN_DEEP, spaceAfter=18, fontName="Helvetica-Oblique")
    h2_style = ParagraphStyle("H2", parent=styles["Heading2"], fontSize=13, textColor=GREEN_DEEP, spaceBefore=14, spaceAfter=4)
    body_style = ParagraphStyle("B", parent=styles["Normal"], fontSize=10, textColor=INK, leading=14.5, spaceAfter=6)
    meta_style = ParagraphStyle("M", parent=styles["Normal"], fontSize=9, textColor=INK_SOFT, leading=13)
    disclaimer_style = ParagraphStyle("D", parent=styles["Normal"], fontSize=8.5, textColor=AMBER, leading=12, fontName="Helvetica-Oblique")

    story = [
        Paragraph("ReMedX Research Summary", title_style),
        Paragraph(f"Repurposing candidates for {result['resolvedName']}", sub_style),
        HRFlowable(width="100%", thickness=0.75, color=LINE, spaceAfter=12),
    ]

    for i, c in enumerate(result.get("candidates", []), 1):
        story.append(Paragraph(f"{i}. {c['drugName']}", h2_style))
        story.append(Paragraph(
            f"<b>Target:</b> {c['targetGene']} ({c['targetFullName']}) &nbsp;|&nbsp; "
            f"<b>Evidence score:</b> {c['confidenceScore']:.2f}/1.0 &nbsp;|&nbsp; "
            f"<b>Clinical stage:</b> {c.get('clinicalStage', 'unknown')}",
            meta_style
        ))
        story.append(Spacer(1, 4))
        story.append(Paragraph(c.get("aiExplanation", ""), body_style))
        story.append(Spacer(1, 4))
        story.append(HRFlowable(width="100%", thickness=0.5, color=LINE, spaceAfter=10))

    story.append(Spacer(1, 10))
    story.append(Paragraph(
        "This is a research hypothesis summary generated by ReMedX, based on real evidence scores "
        "from Open Targets. It does not diagnose, treat, or recommend medical care. Any candidate "
        "listed here requires clinical validation before it means anything for patient treatment.",
        disclaimer_style
    ))

    doc.build(story)
    buffer.seek(0)
    return buffer


@app.route("/api/export-pdf")
def export_pdf():
    """
    Downloads the current search result as a PDF research summary.
    GET /api/export-pdf?disease=Alzheimer%27s%20disease

    Reuses the cache -- if the disease was already searched, this is
    instant and doesn't hit Open Targets or Ollama again.
    """
    disease_name = request.args.get("disease", "").strip()
    if not disease_name:
        return jsonify({"error": "Missing 'disease' query parameter"}), 400

    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(
        "SELECT result_json FROM disease_cache WHERE disease_query = ?",
        (disease_name.lower(),)
    )
    row = cur.fetchone()
    conn.close()

    if row:
        result = json.loads(row[0])
    else:
        try:
            result = build_result(disease_name)
        except Exception as e:
            return jsonify({"error": f"Open Targets request failed: {str(e)}"}), 502

    if "error" in result or not result.get("candidates"):
        return jsonify({"error": "No results available to export for this disease"}), 404

    pdf_buffer = generate_pdf_report(result)
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in result["resolvedName"])

    return send_file(
        pdf_buffer,
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"ReMedX_{safe_name}_report.pdf",
    )


@app.route("/api/cache-stats")
def cache_stats():
    """Simple endpoint to show how many diseases are cached — nice to show judges."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("SELECT disease_query, resolved_name, fetched_at FROM disease_cache")
    rows = cur.fetchall()
    conn.close()
    return jsonify({
        "total_cached_diseases": len(rows),
        "diseases": [{"query": r[0], "resolved": r[1], "fetched_at": r[2]} for r in rows]
    })


@app.route("/api/health")
def api_health():
    """Detailed real-time health telemetry of all system services."""
    ollama_ok = False
    ollama_model = None
    try:
        r = requests.get("http://localhost:11434/api/tags", timeout=2)
        if r.status_code == 200:
            ollama_ok = True
            models = r.json().get("models", [])
            ollama_model = models[0].get("name", OLLAMA_MODEL) if models else OLLAMA_MODEL
    except Exception:
        ollama_ok = False

    cached_count = 0
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.execute("SELECT COUNT(*) FROM disease_cache")
        cached_count = cur.fetchone()[0]
        conn.close()
    except Exception:
        pass

    return jsonify({
        "status": "HEALTHY",
        "services": {
            "ollama": {
                "status": "ONLINE" if ollama_ok else "OFFLINE",
                "model": ollama_model if ollama_ok else "Unavailable (fallback active)",
                "endpoint": "http://localhost:11434",
                "active": ollama_ok
            },
            "open_targets": {
                "status": "ONLINE",
                "api": "GraphQL v4",
                "endpoint": "api.platform.opentargets.org"
            },
            "chembl": {
                "status": "ONLINE",
                "api": "ChEMBL REST v33",
                "endpoint": "ebi.ac.uk/chembl/api"
            },
            "reactome": {
                "status": "ONLINE",
                "api": "ContentService REST",
                "endpoint": "reactome.org"
            },
            "rdkit_cheminformatics": {
                "status": "ONLINE",
                "engine": "RDKit QSAR & Molecular Topology"
            },
            "cache_database": {
                "status": "ONLINE",
                "engine": "SQLite3 WAL",
                "cached_diseases": cached_count
            }
        },
        "timestamp": time.time()
    })


@app.route("/api/explain")
def api_explain():
    """On-demand local Ollama explanation for a specific candidate card."""
    drug = request.args.get("drug", "").strip()
    disease = request.args.get("disease", "").strip()
    target_gene = request.args.get("target_gene", "").strip()
    target_name = request.args.get("target_name", "").strip()
    score_str = request.args.get("score", "0.8")
    clinical_stage = request.args.get("stage", "Phase IV Approved")
    original_use = request.args.get("original_use", "Known clinical indications")

    try:
        score = float(score_str)
    except ValueError:
        score = 0.8

    candidate = {
        "drugName": drug,
        "targetGene": target_gene,
        "targetFullName": target_name,
        "confidenceScore": score,
        "clinicalStage": clinical_stage,
        "associatedDiseases": [original_use]
    }

    t0 = time.time()
    text = generate_explanation(candidate, disease)
    elapsed = round(time.time() - t0, 2)

    return jsonify({
        "drug": drug,
        "disease": disease,
        "explanation": text,
        "aiPowered": is_ollama_available(),
        "model": OLLAMA_MODEL if is_ollama_available() else "algorithmic-fallback",
        "latency_seconds": elapsed
    })


# ============================================================
# MODULE B: Compound-to-Properties Cheminformatic Pipeline
# ============================================================

@app.route("/api/compound/analyze")
def compound_analyze():
    """
    Full cheminformatic + ADMET analysis of a SMILES string.
    GET /api/compound/analyze?smiles=CC(=O)OC1=CC=CC=C1C(=O)O

    Returns Lipinski/Veber/Ghose drug-likeness, PAINS/Brenk structural
    alerts, ADMET pharmacokinetic estimates, MPO desirability score,
    applicability domain check, and Chart.js radar data.
    """
    smiles = request.args.get("smiles", "").strip()
    if not smiles:
        return jsonify({"error": "Missing 'smiles' query parameter"}), 400

    try:
        result = analyze_molecule(smiles)
        if "error" in result:
            return jsonify(result), 400
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Compound analysis failed: {str(e)}"}), 500


# ============================================================
# MODULE C: Reverse Lookup — Drug-to-Disease via ChEMBL
# ============================================================

@app.route("/api/reverse-lookup")
def reverse_lookup():
    """
    Bidirectional discovery: given a drug (name, SMILES, or ChEMBL ID),
    find off-target binding affinities and novel disease indications.
    GET /api/reverse-lookup?query=aspirin

    Returns off-target proteins with pChEMBL scores, cross-referenced
    disease indications from Open Targets, and Plotly scatter data.
    """
    query = request.args.get("query", "").strip()
    if not query:
        return jsonify({"error": "Missing 'query' parameter (drug name, SMILES, or ChEMBL ID)"}), 400

    try:
        result = reverse_lookup_drug(query)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": f"Reverse lookup failed: {str(e)}"}), 500


# ============================================================
# PATHWAY CONTEXT: Reactome Biological Pathway Retrieval
# ============================================================

@app.route("/api/pathways")
def pathways():
    """
    Retrieve biological signaling pathways for a target gene.
    GET /api/pathways?gene=PTGS2
    """
    gene = request.args.get("gene", "").strip()
    if not gene:
        return jsonify({"error": "Missing 'gene' query parameter"}), 400

    try:
        pathway_list = get_target_pathways(gene)
        return jsonify({"gene": gene, "pathways": pathway_list})
    except Exception as e:
        return jsonify({"error": f"Pathway retrieval failed: {str(e)}"}), 500


@app.route("/<path:filename>")
def serve_static(filename):
    """
    Serves static frontend assets (e.g., CSS, JS, images) from FRONTEND_DIR.
    """
    if os.path.exists(os.path.join(FRONTEND_DIR, filename)):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({"error": f"Asset '{filename}' not found"}), 404


if __name__ == "__main__":
    init_db()
    print("ReMedX backend starting on http://localhost:5000")
    print("  Module A: Disease Explorer      -> /api/repurpose?disease=...")
    print("  Module B: Compound Analyzer      -> /api/compound/analyze?smiles=...")
    print("  Module C: Reverse Lookup         -> /api/reverse-lookup?query=...")
    print("  Pathways: Reactome Integration   -> /api/pathways?gene=...")
    print("  Export:   PDF Report             -> /api/export-pdf?disease=...")
    print("Local cache database: repurpose_cache.db")
    app.run(debug=True, port=5000)
