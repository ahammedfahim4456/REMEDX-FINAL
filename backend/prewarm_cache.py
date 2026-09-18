"""
Pre-warms the ReMedX cache before a demo.

Run this BEFORE your presentation, with app.py already running in
another terminal. It searches each disease below through your own
backend (same as a normal user search would), so by the time you're
presenting, every one of these is already cached and returns
instantly -- no waiting on Open Targets or local AI generation live
in front of judges.

Usage:
    1. In one terminal: python app.py
    2. In another terminal: python prewarm_cache.py
"""

import requests
import time

BACKEND_URL = "http://localhost:5000"

# Edit this list to match whatever diseases you actually plan to
# demo or expect judges might ask about.
DEMO_DISEASES = [
    "Alzheimer's disease",
    "Parkinson disease",
    "Type 2 diabetes",
    "Breast cancer",
    "Rheumatoid arthritis",
    "Asthma",
    "Schizophrenia",
    "Psoriasis",
]


def prewarm():
    print(f"Pre-warming cache for {len(DEMO_DISEASES)} diseases...\n")

    for disease in DEMO_DISEASES:
        print(f"  Searching: {disease} ... ", end="", flush=True)
        start = time.time()

        try:
            resp = requests.get(
                f"{BACKEND_URL}/api/repurpose",
                params={"disease": disease},
                timeout=90,  # generous, since this is a one-time warm-up, not a live demo wait
            )
            resp.raise_for_status()
            data = resp.json()

            if "error" in data:
                print(f"FAILED ({data['error']})")
                continue

            elapsed = time.time() - start
            candidate_count = len(data.get("candidates", []))
            print(f"done in {elapsed:.1f}s -- {candidate_count} candidates cached")

        except requests.exceptions.ConnectionError:
            print("FAILED -- is app.py running on localhost:5000?")
            return
        except Exception as e:
            print(f"FAILED ({e})")

    print("\nDone. All successful searches above are now cached and will")
    print("return instantly during your live demo.")


if __name__ == "__main__":
    prewarm()
