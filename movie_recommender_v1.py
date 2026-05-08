import os
import tkinter as tk
from collections import Counter
from io import BytesIO
from tkinter import ttk

import matplotlib.pyplot as plt
import pandas as pd
import requests
import seaborn as sns
from PIL import Image, ImageDraw, ImageTk

TSV_PATH = "title.basics.tsv"
CHUNK_SIZE = 80_000
CURRENT_YEAR = 2026
USECOLS = ["titleType", "startYear", "genres", "primaryTitle"]

# Posters: TMDB is used when TMDB_API_KEY is set; otherwise English Wikipedia thumbnails are used (no key).
TMDB_API_KEY = os.environ.get("TMDB_API_KEY", "").strip()
POSTER_W, POSTER_H = 92, 138
TMDB_IMG = "https://image.tmdb.org/t/p/w185"
HTTP_HEADERS = {
    "User-Agent": "MovieRecommenderEducational/1.0 (Python; local student project)",
}


def _iter_movie_chunks(path):
    """Yield only movie rows with valid year, genres, and title — one chunk at a time."""
    reader = pd.read_csv(
        path,
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
        if len(chunk):
            yield chunk


def collect_top5(genre_name, tsv_path=TSV_PATH):
    """Return up to five (year, title) tuples, newest first."""
    best = []
    for part in _iter_movie_chunks(tsv_path):
        m = part[
            part["genres"].str.contains(
                genre_name, case=False, na=False, regex=False
            )
        ]
        for y, t in zip(m["startYear"], m["primaryTitle"]):
            best.append((int(y), str(t)))
        best = sorted(best, key=lambda x: -x[0])[:5]
    return best


def _tmdb_poster_url(title: str, year: int, api_key: str | None) -> str | None:
    if not api_key:
        return None
    try:
        r = requests.get(
            "https://api.themoviedb.org/3/search/movie",
            params={"api_key": api_key, "query": title, "year": year},
            headers=HTTP_HEADERS,
            timeout=12,
        )
        r.raise_for_status()
        data = r.json()
        results = data.get("results") or []
        chosen = None
        ystr = str(year)
        for res in results:
            if not res.get("poster_path"):
                continue
            rd = (res.get("release_date") or "")[:4]
            if rd == ystr:
                chosen = res
                break
            if chosen is None:
                chosen = res
        if chosen and chosen.get("poster_path"):
            return f"{TMDB_IMG}{chosen['poster_path']}"
    except (OSError, requests.RequestException):
        pass
    return None


def _wikipedia_thumb_url(title: str, year: int) -> str | None:
    """Public Wikipedia API — no key. Thumbnail may be a logo or infobox image, not always a poster."""
    try:
        r = requests.get(
            "https://en.wikipedia.org/w/api.php",
            params={
                "action": "query",
                "format": "json",
                "generator": "search",
                "gsrsearch": f"{title} {year} film",
                "gsrlimit": "1",
                "gsrnamespace": "0",
                "prop": "pageimages",
                "piprop": "thumbnail",
                "pithumbsize": "320",
            },
            headers=HTTP_HEADERS,
            timeout=14,
        )
        r.raise_for_status()
        pages = r.json().get("query", {}).get("pages") or {}
        for _pid, page in pages.items():
            if isinstance(page, dict):
                thumb = page.get("thumbnail") or {}
                src = thumb.get("source")
                if src:
                    return str(src)
    except (OSError, requests.RequestException, ValueError, KeyError):
        pass
    return None


def _poster_image_url(title: str, year: int, tmdb_key: str | None) -> str | None:
    url = _tmdb_poster_url(title, year, tmdb_key)
    if url:
        return url
    return _wikipedia_thumb_url(title, year)


def _placeholder_photo(text: str) -> ImageTk.PhotoImage:
    im = Image.new("RGB", (POSTER_W, POSTER_H), (36, 40, 48))
    draw = ImageDraw.Draw(im)
    draw.rectangle([0, 0, POSTER_W - 1, POSTER_H - 1], outline=(70, 78, 96))
    msg = (text or "?")[:40]
    draw.text((8, POSTER_H // 2 - 14), msg, fill=(140, 148, 170))
    draw.text((8, POSTER_H // 2 + 2), f"{POSTER_W}x{POSTER_H}", fill=(90, 98, 116))
    return ImageTk.PhotoImage(im)


def _photo_from_url(url: str) -> ImageTk.PhotoImage | None:
    try:
        r = requests.get(url, timeout=15, headers=HTTP_HEADERS)
        r.raise_for_status()
        im = Image.open(BytesIO(r.content)).convert("RGB")
        im.thumbnail((POSTER_W, POSTER_H), Image.Resampling.LANCZOS)
        bg = Image.new("RGB", (POSTER_W, POSTER_H), (20, 22, 28))
        ox = (POSTER_W - im.width) // 2
        oy = (POSTER_H - im.height) // 2
        bg.paste(im, (max(0, ox), max(0, oy)))
        return ImageTk.PhotoImage(bg)
    except (OSError, requests.RequestException):
        return None


def run_genre_picker(sorted_genres, tsv_path: str, tmdb_key: str | None):
    """Genre dropdown plus poster + title rows. Keeps PhotoImage refs on the root window."""
    root = tk.Tk()
    root.title("Movie recommender — select a genre")
    root.minsize(520, 640)

    main = ttk.Frame(root, padding=12)
    main.pack(fill=tk.BOTH, expand=True)

    ttk.Label(
        main,
        text=(
            "Select a genre, then click Get recommendations. "
            "Images: TMDB if you set TMDB_API_KEY, otherwise Wikipedia thumbnails (no signup)."
        ),
        wraplength=480,
    ).pack(anchor=tk.W)

    row = ttk.Frame(main)
    row.pack(fill=tk.X, pady=(10, 6))

    var = tk.StringVar()
    default = "Sci-Fi" if "Sci-Fi" in sorted_genres else (sorted_genres[0] if sorted_genres else "")
    var.set(default)

    cb = ttk.Combobox(
        row,
        textvariable=var,
        values=sorted_genres,
        width=40,
        state="readonly",
    )
    cb.pack(side=tk.LEFT, fill=tk.X, expand=True)

    btn = ttk.Button(row, text="Get recommendations", width=18)
    btn.pack(side=tk.LEFT, padx=(8, 0))

    mid = ttk.Frame(main)
    mid.pack(fill=tk.BOTH, expand=True, pady=(8, 0))

    canvas = tk.Canvas(mid, highlightthickness=0)
    scroll = ttk.Scrollbar(mid, orient=tk.VERTICAL, command=canvas.yview)
    results = ttk.Frame(canvas)
    results.bind(
        "<Configure>",
        lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
    )
    inner_id = canvas.create_window((0, 0), window=results, anchor=tk.NW)

    def _stretch_inner(event):
        canvas.itemconfigure(inner_id, width=event.width)

    canvas.bind("<Configure>", _stretch_inner)
    canvas.configure(yscrollcommand=scroll.set)

    canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scroll.pack(side=tk.RIGHT, fill=tk.Y)

    def _on_mousewheel(event):
        canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    canvas.bind_all("<MouseWheel>", _on_mousewheel)

    foot = ttk.Frame(main)
    foot.pack(fill=tk.X, pady=(8, 0))
    ttk.Label(
        foot,
        text=(
            "Posters: TMDB (optional key; not endorsed by TMDB) or Wikipedia / Wikimedia Commons thumbnails."
        ),
        font=("", 8),
        foreground="#666",
        wraplength=480,
    ).pack(anchor=tk.W)
    ttk.Label(foot, text="Results also print in the terminal.", font=("", 9)).pack(anchor=tk.W)

    root.poster_refs = []

    def show_report():
        choice = var.get().strip()
        if not choice:
            return
        for w in results.winfo_children():
            w.destroy()
        root.poster_refs.clear()

        best = collect_top5(choice, tsv_path=tsv_path)
        lines = [
            f"Top 5 newest '{choice.title()}' movies:",
            "-" * 40,
        ]
        if not best:
            lines.append(f"No movies found for genre: {choice}")
            ttk.Label(results, text="\n".join(lines), font=("Consolas", 10)).pack(anchor=tk.W)
            print("\n" + "\n".join(lines))
            return

        for i, (yr, title) in enumerate(best, 1):
            lines.append(f"{i}. {title} ({yr})")
        text_block = "\n".join(lines)
        print("\n" + text_block)

        for i, (yr, title) in enumerate(best, 1):
            row_f = ttk.Frame(results, padding=(0, 6))
            row_f.pack(fill=tk.X)

            url = _poster_image_url(title, yr, tmdb_key)
            photo = _photo_from_url(url) if url else None
            if photo is None:
                photo = _placeholder_photo("No image")

            root.poster_refs.append(photo)
            pic = tk.Label(row_f, image=photo, bd=1, relief=tk.GROOVE)
            pic.pack(side=tk.LEFT)

            txt = ttk.Label(
                row_f,
                text=f"{i}. {title}\n({yr})",
                font=("Segoe UI", 11),
                wraplength=360,
                justify=tk.LEFT,
            )
            txt.pack(side=tk.LEFT, padx=(12, 0), anchor=tk.N)

        canvas.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    btn.configure(command=show_report)
    root.after(150, show_report)
    root.mainloop()


try:
    print("Starting to scan the IMDb dataset in chunks... please wait.")

    genre_counter = Counter()
    movie_total = 0

    for part in _iter_movie_chunks(TSV_PATH):
        movie_total += len(part)
        exploded = part["genres"].str.split(",").explode().str.strip().dropna()
        exploded = exploded[exploded != ""]
        genre_counter.update(exploded)

    if movie_total == 0:
        raise ValueError("No movie rows found — check title.basics.tsv")

    top_pairs = genre_counter.most_common(10)
    genre_counts = pd.Series({name: count for name, count in top_pairs})

    print(f"Setup complete! Summarized {movie_total:,} movie titles.")

    plt.figure(figsize=(12, 7))
    genre_counts_k = genre_counts / 1000
    sns.barplot(
        x=genre_counts_k.values,
        y=genre_counts_k.index,
        palette="viridis",
        edgecolor="black",
    )
    plt.title("Top 10 Movie Genres in the IMDb Dataset", fontsize=16, fontweight="bold")
    plt.xlabel("Number of Movies (in Thousands)", fontsize=12)
    plt.ylabel("Genres", fontsize=12)
    plt.grid(axis="x", linestyle="--", alpha=0.6)
    plt.tight_layout()
    print("Generating visualization... Close the chart window to open the genre picker.")
    plt.show()

    genre_choices = sorted(genre_counter.keys(), key=str.lower)
    run_genre_picker(genre_choices, TSV_PATH, TMDB_API_KEY or None)

except FileNotFoundError:
    print(f"ERROR: '{TSV_PATH}' not found in the current folder.")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
