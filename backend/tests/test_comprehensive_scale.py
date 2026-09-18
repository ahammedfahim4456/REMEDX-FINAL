"""
Comprehensive stress test suite for ReMedX.
Tests a large suite of uncached diseases, reverse lookup drugs, and chemical molecules.
"""
import requests
import time
import json
import sqlite3

BASE = "http://localhost:5000"

# 1. UNCACHED DISEASES TEST SET (diverse therapeutic areas)
UNCACHED_DISEASES = [
    "glioblastoma",
    "Huntington disease",
    "Crohn's disease",
    "ulcerative colitis",
    "systemic lupus erythematosus",
    "amyotrophic lateral sclerosis",
    "pulmonary arterial hypertension",
    "idiopathic pulmonary fibrosis",
    "multiple myeloma",
    "colorectal cancer",
    "pancreatic adenocarcinoma",
    "melanoma",
    "chronic kidney disease",
    "heart failure",
    "glaucoma",
    "major depressive disorder",
    "gout",
    "ankylosing spondylitis",
    "atopic dermatitis",
    "endometriosis"
]

# 2. REVERSE LOOKUP DRUGS TEST SET
TEST_DRUGS = [
    "Atorvastatin",
    "Metformin",
    "Sildenafil",
    "Imatinib",
    "Rapamycin",
    "Dexamethasone",
    "Celecoxib",
    "Tamoxifen",
    "Methotrexate",
    "Simvastatin",
    "Losartan",
    "Propranolol",
    "Fluoxetine",
    "Omeprazole",
    "Warfarin"
]

# 3. CHEMICAL COMPOUNDS SMILES TEST SET
TEST_MOLECULES = [
    ("Aspirin", "CC(=O)OC1=CC=CC=C1C(=O)O"),
    ("Metformin", "CN(C)C(=N)N=C(N)N"),
    ("Sildenafil", "CCCC1=NN(C)C2=C1N=C(NC2=O)C3=C(OCC)C=CC(=C3)S(=O)(=O)N4CCN(C)CC4"),
    ("Imatinib", "CC1=C(C=C(C=C1)NC(=O)C2=CC=C(C=C2)CN3CCN(CC3)C)NC4=NC=CC(=N4)C5=CN=CC=C5"),
    ("Dexamethasone", "CC1CC2C3CCC4=CC(=O)C=CC4(C3(C(CC2(C1(C(=O)CO)O)C)O)F)C"),
    ("Thalidomide", "O=C1CCC(N2C(=O)C3=CC=CC=C3C2=O)C(=O)N1"),
    ("Celecoxib", "CC1=CC=C(C=C1)C2=CC(=NN2C3=CC=C(C=C3)S(=O)(=O)N)C(F)(F)F"),
    ("Tamoxifen", "CCC(=C(C1=CC=CC=C1)C2=CC=C(C=C2)OCCN(C)C)C3=CC=CC=C3"),
    ("Caffeine", "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"),
    ("Paracetamol", "CC(=O)NC1=CC=C(C=C1)O"),
    ("Ibuprofen", "CC(C)CC1=CC=C(C=C1)C(C)C(=O)O"),
    ("Resveratrol", "C1=CC(=CC=C1/C=C/C2=CC(=CC(=C2)O)O)O"),
    ("Curcumin", "COC1=C(C=CC(=C1)/C=C/C(=O)CC(=O)/C=C/C2=CC(=C(C=C2)O)OC)O"),
    ("Artemisinin", "CC1CCC2C(C(=O)OC3C24C1CCC(O3)(OO4)C)C"),
    ("Chloroquine", "CCN(CC)CCCC(C)NC1=C2C=CC(=CC2=NC=C1)Cl")
]


def test_diseases(sample_size=10):
    print("\n" + "=" * 75)
    print(f"TEST 1: UNCACHED FORWARD DISEASE DISCOVERY ({sample_size} novel conditions)")
    print("=" * 75)
    results = []
    
    for i, disease in enumerate(UNCACHED_DISEASES[:sample_size], 1):
        t0 = time.time()
        try:
            r = requests.get(f"{BASE}/api/repurpose", params={"disease": disease}, timeout=35)
            elapsed = round(time.time() - t0, 2)
            if r.status_code == 200:
                d = r.json()
                cands = len(d.get("candidates", []))
                resolved = d.get("resolvedName", "N/A")
                top_cand = d.get("candidates", [{}])[0].get("drugName", "N/A") if cands > 0 else "None"
                top_score = d.get("candidates", [{}])[0].get("confidenceScore", 0) if cands > 0 else 0
                cached = d.get("_cached", False)
                print(f"[{i}/{sample_size}] SUCCESS: '{disease}' -> '{resolved}' | {cands} candidates | Top: {top_cand} ({top_score:.2f}) | {elapsed}s (cached={cached})")
                results.append(True)
            else:
                print(f"[{i}/{sample_size}] HTTP {r.status_code}: '{disease}' ({elapsed}s)")
                results.append(False)
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"[{i}/{sample_size}] ERROR: '{disease}' ({e}) [{elapsed}s]")
            results.append(False)
            
    success_rate = (sum(results) / len(results)) * 100 if results else 0
    print(f"\n--> Disease Discovery Success Rate: {sum(results)}/{len(results)} ({success_rate:.1f}%)")
    return results


def test_reverse_lookup(sample_size=10):
    print("\n" + "=" * 75)
    print(f"TEST 2: REVERSE POLYPHARMACOLOGY & OFF-TARGET LOOKUP ({sample_size} diverse drugs)")
    print("=" * 75)
    results = []
    
    for i, drug in enumerate(TEST_DRUGS[:sample_size], 1):
        t0 = time.time()
        try:
            r = requests.get(f"{BASE}/api/reverse-lookup", params={"query": drug}, timeout=25)
            elapsed = round(time.time() - t0, 2)
            if r.status_code == 200:
                d = r.json()
                cid = d.get("chembl_id", "N/A")
                acts = d.get("total_bioactivities_found", 0)
                off_targets = len(d.get("top_off_targets", []))
                novel = len(d.get("novel_repurposing_indications", []))
                print(f"[{i}/{sample_size}] SUCCESS: '{drug}' -> {cid} | {acts} assays | {off_targets} off-targets | {novel} novel hypotheses | {elapsed}s")
                results.append(True)
            else:
                print(f"[{i}/{sample_size}] HTTP {r.status_code}: '{drug}' ({elapsed}s)")
                results.append(False)
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"[{i}/{sample_size}] ERROR: '{drug}' ({e}) [{elapsed}s]")
            results.append(False)
            
    success_rate = (sum(results) / len(results)) * 100 if results else 0
    print(f"\n--> Reverse Lookup Success Rate: {sum(results)}/{len(results)} ({success_rate:.1f}%)")
    return results


def test_cheminformatics():
    print("\n" + "=" * 75)
    print(f"TEST 3: CHEMINFORMATICS, QSAR & ADMET RADAR ({len(TEST_MOLECULES)} molecules)")
    print("=" * 75)
    results = []
    
    for i, (name, smiles) in enumerate(TEST_MOLECULES, 1):
        t0 = time.time()
        try:
            r = requests.get(f"{BASE}/api/compound/analyze", params={"smiles": smiles}, timeout=10)
            elapsed = round(time.time() - t0, 2)
            if r.status_code == 200:
                d = r.json()
                desc = d.get("descriptors", {})
                ev = d.get("evaluation", {})
                lip = ev.get("lipinski", {}).get("pass", False)
                mpo = ev.get("mpo", {}).get("desirability_index", 0)
                pains = d.get("alerts", {}).get("pains_flag", False)
                print(f"[{i}/{len(TEST_MOLECULES)}] SUCCESS: '{name}' | MW: {desc.get('mw')} | Lipinski: {lip} | MPO: {mpo} | PAINS Alert: {pains} | {elapsed}s")
                results.append(True)
            else:
                print(f"[{i}/{len(TEST_MOLECULES)}] HTTP {r.status_code}: '{name}' ({elapsed}s)")
                results.append(False)
        except Exception as e:
            elapsed = round(time.time() - t0, 2)
            print(f"[{i}/{len(TEST_MOLECULES)}] ERROR: '{name}' ({e}) [{elapsed}s]")
            results.append(False)
            
    success_rate = (sum(results) / len(results)) * 100 if results else 0
    print(f"\n--> Cheminformatics Success Rate: {sum(results)}/{len(results)} ({success_rate:.1f}%)")
    return results


if __name__ == "__main__":
    print("=" * 75)
    print("STARTING REMEDX AUTOMATED MULTI-PILLAR STRESS & DISCOVERY SUITE")
    print("=" * 75)
    
    # Run tests
    r_chemi = test_cheminformatics()
    r_rev = test_reverse_lookup(sample_size=8)
    r_dis = test_diseases(sample_size=8)
    
    print("\n" + "=" * 75)
    print("ALL TEST MODULES COMPLETED")
    print("=" * 75)
