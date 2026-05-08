"""
Generate data/app_data.json for the web UI from title.basics.tsv (local only).

Run after placing IMDb title.basics.tsv in this folder:
    python build_data.py

For a quick demo bundle without the TSV:
    python build_data.py --sample
"""

from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
OUT_PATH = ROOT / "data" / "app_data.json"
CURRENT_YEAR = 2026
CHUNK_SIZE = 80_000
USECOLS = ["titleType", "startYear", "genres", "primaryTitle"]


def _write(obj: dict) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(obj, indent=2), encoding="utf-8")
    print(f"Wrote {OUT_PATH}")


def build_sample() -> dict:
    top = [
        ("Drama", 185),
        ("Comedy", 142),
        ("Documentary", 98),
        ("Romance", 76),
        ("Thriller", 71),
        ("Action", 68),
        ("Horror", 52),
        ("Sci-Fi", 48),
        ("Animation", 39),
        ("Crime", 35),
    ]
    genres = [{"genre": name, "count": count} for name, count in top]
    recs = {
        "drama": [
            {"title": "Echoes of Tomorrow", "year": 2025},
            {"title": "The Last Ceremony", "year": 2024},
            {"title": "Paper Bridges", "year": 2023},
            {"title": "Winter Orchard", "year": 2022},
            {"title": "Quiet Rails", "year": 2021},
        ],
        "comedy": [
            {"title": "Sorted!", "year": 2025},
            {"title": "Budget Holiday", "year": 2024},
            {"title": "Roommates Anonymous", "year": 2023},
            {"title": "Spill the Soup", "year": 2022},
            {"title": "Dial M for Mime", "year": 2021},
        ],
        "action": [
            {"title": "Night Courier", "year": 2025},
            {"title": "Steel Horizon", "year": 2024},
            {"title": "Rogue Vector", "year": 2023},
            {"title": "Concrete Tide", "year": 2022},
            {"title": "Burn Curve", "year": 2021},
        ],
        "sci-fi": [
            {"title": "Orbital Drift", "year": 2025},
            {"title": "Signal from Kepler-442", "year": 2024},
            {"title": "Ash Astronaut", "year": 2023},
            {"title": "The Quiet Sun", "year": 2022},
            {"title": "Dust Architects", "year": 2021},
        ],
        "horror": [
            {"title": "The House Below Zero", "year": 2025},
            {"title": "Static on Channel 6", "year": 2024},
            {"title": "Borrowed Faces", "year": 2023},
            {"title": "Midnight Inventory", "year": 2022},
            {"title": "Glass in the Walls", "year": 2021},
        ],
    }
    return {
        "meta": {"source": "sample", "movieCount": 12500},
        "topGenres": genres,
        "recommendations": recs,
    }


def _merge_top5(
    current: list[tuple[int, str]], additions: list[tuple[int, str]], k: int = 5
) -> list[tuple[int, str]]:
    return sorted(current + additions, key=lambda x: -x[0])[:k]


def build_from_tsv(tsv_path: Path) -> dict:
    genre_counter: Counter[str] = Counter()
    best_per_genre: dict[str, list[tuple[int, str]]] = defaultdict(list)
    n_movies = 0

    reader = pd.read_csv(
        tsv_path,
        sep="\t",
        chunksize=CHUNK_SIZE,
        na_values="\\N",
        dtype=str,
        usecols=USECOLS,
        low_memory=True,
    )

    for chunk in reader:
        chunk = chunk[chunk["titleType"] == "movie"]
        chunk = chunk.dropna(subset=["startYear", "genres", "primaryTitle"])
        if chunk.empty:
            continue
        chunk = chunk.copy()
        chunk["startYear"] = pd.to_numeric(chunk["startYear"], errors="coerce")
        chunk = chunk.dropna(subset=["startYear"])
        chunk["startYear"] = chunk["startYear"].astype(int)
        chunk = chunk[chunk["startYear"] <= CURRENT_YEAR]
        if chunk.empty:
            continue

        n_movies += len(chunk)

        exploded = chunk["genres"].str.split(",").explode().str.strip().dropna()
        exploded = exploded[exploded != ""]
        genre_counter.update(exploded)

        tmp = chunk.assign(_g=chunk["genres"].str.split(",")).explode("_g")
        tmp["_g"] = tmp["_g"].str.strip()
        tmp = tmp[tmp["_g"].notna() & (tmp["_g"] != "")]
        for g, y, t in zip(tmp["_g"], tmp["startYear"], tmp["primaryTitle"]):
            key = str(g).lower()
            y_int = int(y)
            title = str(t)
            best_per_genre[key] = _merge_top5(best_per_genre[key], [(y_int, title)])

    if n_movies == 0:
        raise ValueError("No movie rows found in TSV.")

    top_counts = genre_counter.most_common(10)
    top_genres = [{"genre": str(name), "count": int(count)} for name, count in top_counts]

    recommendations: dict[str, list[dict]] = {}
    for key, pairs in best_per_genre.items():
        if not pairs:
            continue
        recommendations[key] = [
            {"title": title, "year": year} for year, title in sorted(pairs, key=lambda x: -x[0])
        ]

    return {
        "meta": {"source": "imdb_title_basics", "movieCount": n_movies},
        "topGenres": top_genres,
        "recommendations": recommendations,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--sample",
        action="store_true",
        help="Write demo JSON without title.basics.tsv",
    )
    parser.add_argument(
        "--tsv",
        type=Path,
        default=ROOT / "title.basics.tsv",
        help="Path to title.basics.tsv",
    )
    args = parser.parse_args()

    if args.sample:
        _write(build_sample())
        return

    if not args.tsv.is_file():
        print(f"TSV not found: {args.tsv}; use --sample or add title.basics.tsv")
        raise SystemExit(1)

    _write(build_from_tsv(args.tsv))


if __name__ == "__main__":
    main()
