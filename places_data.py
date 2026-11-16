"""
places_data.py
Single source of truth for every tourist place used in this project. Backed by
places.json in the same directory -- edit the JSON (paste a naver_id or a
Google Maps URL), never a dict inside a script.

places.json schema, per Korean place name:
  name_en                English label used on charts and figures
  naver_id                Naver Place numeric id, or null if not yet scraped
  gmaps_url               Google Maps place URL used by gmaps_scraper/scrape.js
  place_type              palace | traditional | market | entertainment |
                           museum | modern | nature  (descriptive only --
                           no model uses this as a regressor)
  city                    Seoul | Busan | Gyeonggi | ...
  lat, lon                coordinates for 04_02_geo_bubble.py, or null
  yanolja_rank             rank in Yanolja Research "Korea's Top 500"
                           (see memory: project-place-selection-criteria), or null
  cross_cultural_corpus    true if this place is in the paused Naver+GMaps
                           paired-sample branch (02_cc_build_corpus.py)

A place missing place_type or name_en prints a warning at import time instead
of silently falling back to "other" -- see MEMORY.md / project_naver_only_scope
for why that used to happen.

Usage:
    from places_data import PLACE_EN, PLACE_TYPE, CITY, COORDS, NAVER_PLACES
"""

import json
import sys
from pathlib import Path

_PLACES_JSON = Path(__file__).resolve().parent / "places.json"


def _load():
    with open(_PLACES_JSON, encoding="utf-8") as f:
        data = json.load(f)
    missing_type = [name for name, p in data.items() if not p.get("place_type")]
    missing_en = [name for name, p in data.items() if not p.get("name_en")]
    if missing_type:
        print(f"WARNING [places_data]: no place_type for {missing_type} "
              f"in places.json", file=sys.stderr)
    if missing_en:
        print(f"WARNING [places_data]: no name_en for {missing_en} "
              f"in places.json", file=sys.stderr)
    return data


PLACES = _load()

# ── Convenience views, built from PLACES so a script never keeps its own copy ──

PLACE_EN = {k: v["name_en"] for k, v in PLACES.items() if v.get("name_en")}
PLACE_TYPE = {k: v["place_type"] for k, v in PLACES.items() if v.get("place_type")}
CITY = {k: v["city"] for k, v in PLACES.items() if v.get("city")}
COORDS = {k: (v["lat"], v["lon"]) for k, v in PLACES.items()
          if v.get("lat") is not None and v.get("lon") is not None}

# Places with a naver_id, in the {"name": ..., "naver_id": ...} shape
# 01_01_scrape_naver.py expects. A place with naver_id = null (e.g. 종묘) is
# skipped here rather than sent to a URL that 404s.
NAVER_PLACES = [{"name": k, "naver_id": v["naver_id"]}
                for k, v in PLACES.items() if v.get("naver_id")]

# Places in the paused cross-cultural corpus (Naver + Google Maps paired sample)
CROSS_CULTURAL_PLACES = [k for k, v in PLACES.items() if v.get("cross_cultural_corpus")]


if __name__ == "__main__":
    # python places_data.py -- quick sanity check / inventory
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    print(f"{len(PLACES)} places in {_PLACES_JSON.name}")
    print(f"  with naver_id:              {len(NAVER_PLACES)}")
    print(f"  with coordinates:           {len(COORDS)}")
    print(f"  in cross-cultural corpus:   {len(CROSS_CULTURAL_PLACES)}")
    missing_naver = [k for k, v in PLACES.items() if not v.get("naver_id")]
    if missing_naver:
        print(f"  missing naver_id:           {missing_naver}")
