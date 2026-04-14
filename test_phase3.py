"""
Phase 3 test script — run AFTER the server is started with:
    uvicorn app.main:app --reload

Usage:
    python test_phase3.py
"""

import time
import httpx

BASE = "http://127.0.0.1:8000"


def call(method: str, path: str):
    url = f"{BASE}{path}"
    print(f"\n{'='*60}")
    print(f"{method.upper()} {url}")
    print("=" * 60)

    with httpx.Client(timeout=120.0) as client:
        if method == "POST":
            resp = client.post(url)
        else:
            resp = client.get(url)

    print(f"Status: {resp.status_code}")
    try:
        data = resp.json()
        import json
        print(json.dumps(data, indent=2, default=str))
    except Exception:
        print(resp.text[:500])

    return resp.status_code


def main():
    print("Phase 3 Test — Sentiment Analysis Engine")
    print("Make sure the server is running on http://127.0.0.1:8000\n")

    # Step 1: Scrape articles for RELIANCE
    print("\n>>> Step 1: Scrape articles for RELIANCE")
    call("POST", "/scrape/RELIANCE")

    print("\nWaiting 3 seconds...")
    time.sleep(3)

    # Step 2: Score the articles
    print("\n>>> Step 2: Score unscored articles for RELIANCE")
    call("POST", "/sentiment/RELIANCE/score")

    print("\nWaiting 3 seconds...")
    time.sleep(3)

    # Step 3: Get aggregate sentiment
    print("\n>>> Step 3: Get sentiment summary for RELIANCE")
    call("GET", "/sentiment/RELIANCE?hours=48")

    print("\nWaiting 3 seconds...")
    time.sleep(3)

    # Step 4: Check stored articles now have sentiment
    print("\n>>> Step 4: Verify articles have sentiment labels")
    call("GET", "/scrape/RELIANCE/articles")

    print("\n" + "=" * 60)
    print("Phase 3 test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
