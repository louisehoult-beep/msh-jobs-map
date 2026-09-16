"""
Postcode -> lat/long via postcodes.io — free, no API key, UK government
postcode data (ONS). Used to place job pins precisely on the map when a
listing carries a postcode; region-bucket placement (regions.py) is the
fallback when it doesn't.

Batched via postcodes.io's own /postcodes bulk endpoint (up to 100 per call)
to keep this cheap and fast inside a daily GitHub Actions run.
"""
import json
import urllib.request

BULK_URL = "https://api.postcodes.io/postcodes"
BATCH_SIZE = 100


def geocode_postcodes(postcodes: list[str]) -> dict[str, tuple[float, float] | None]:
    """
    postcodes: list of raw postcode strings (may include duplicates/None).
    Returns: dict of postcode -> (lat, lon) or None if not found.
    """
    unique = sorted({p.strip().upper() for p in postcodes if p})
    results: dict[str, tuple[float, float] | None] = {}

    for i in range(0, len(unique), BATCH_SIZE):
        batch = unique[i : i + BATCH_SIZE]
        payload = json.dumps({"postcodes": batch}).encode("utf-8")
        req = urllib.request.Request(
            BULK_URL,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # network/API failure shouldn't kill the whole build
            print(f"[geocode] batch failed, skipping {len(batch)} postcodes: {exc}")
            for p in batch:
                results[p] = None
            continue

        for row in body.get("result", []):
            pc = row.get("query", "").strip().upper()
            r = row.get("result")
            results[pc] = (r["latitude"], r["longitude"]) if r else None

    return results
