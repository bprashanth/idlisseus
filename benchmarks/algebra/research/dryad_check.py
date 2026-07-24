"""Validate Dryad auth end-to-end: creds -> token -> download a real file -> ingest.

Run this AFTER putting your credentials in ~/.config/idlisseus/dryad.json
(copy dryad.json.example, fill client_id + client_secret from datadryad.org/account).

  python3 research/dryad_check.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "semantic_broker", "connectors"))
import paper_data as pd  # noqa: E402


def main():
    if not pd.dryad_configured():
        print("✗ No Dryad creds found. Put client_id/client_secret in one of:")
        for p in pd._CRED_PATHS:
            print("    ", p)
        print("   (copy ~/.config/idlisseus/dryad.json.example and fill it in)")
        return 1
    print("✓ creds found")
    try:
        tok = pd._dryad_token()
    except Exception as ex:
        print(f"✗ token exchange failed: {ex}")
        print("   check client_id/client_secret are correct (from datadryad.org/account)")
        return 1
    print(f"✓ got bearer token ({tok[:12]}…)")

    recs = pd.dryad_find("Western Ghats restoration canopy", size=4)
    print(f"✓ search returned {len(recs)} datasets with tabular files")
    if not recs:
        return 1
    r = recs[0]
    f = r["files"][0]
    print(f"  downloading: {f['name']} from {r['title'][:45]}…")
    try:
        raw = pd._get(f["url"])
    except Exception as ex:
        print(f"✗ authenticated download FAILED: {ex}")
        return 1
    print(f"✓ downloaded {len(raw)} bytes WITH token (was 401 without)")

    ing = pd.ingest_dataset(r)
    print(f"✓ ingest strategy={ing.get('strategy')} points={len(ing.get('points', []))}")
    print("\nDryad is live. Re-run the crawl to fold Dryad into the corpus:")
    print("  python3 dss/loop/crawl.py --max-datasets 250 --theme-per-query 15")
    return 0


if __name__ == "__main__":
    sys.exit(main())
