"""
04_02_geo_bubble.py
Geographic bubble visualization of review analysis results.

Outputs (data/analysis/figures/):
  bubble_map.html          — interactive map (folium, opens in browser)
  11_geo_bubble_seoul.png  — static Seoul panel for paper
  11_geo_bubble_busan.png  — static Busan panel for paper

Encoding:
  Position = geographic coordinates of each place
  Radius   = mean sentiment score (scaled)
  Color    = KO (blue) / EN (red), two bubbles per place
  Label    = dominant LDA topic

Requires: folium (pip install folium), matplotlib, pandas
Run:  python 04_02_geo_bubble.py
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path

ANALYSIS = Path("data/analysis")
FIGS     = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

# ── coordinates / English names: single source of truth, places.json ─────────
# COORDS only has entries for places with lat/lon set there; a place with none
# simply doesn't appear on the map (same as before, now explicit -- see
# places_data.py's docstring to add coordinates for a new place).
from places_data import COORDS, PLACE_EN

PALETTE = {"ko": "#2563EB", "en": "#DC2626"}

# ── load data ────────────────────────────────────────────────────────────────
df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
sent_df = pd.read_csv(ANALYSIS / "sentiment_results.csv")

df = df.merge(
    sent_df[["place", "language", "text", "sentiment"]],
    on=["place", "language", "text"], how="left",
)

PLACES = [p for p in COORDS if p in df["place"].unique()]
seoul_places = [p for p in PLACES if COORDS[p][0] > 36]
busan_places = [p for p in PLACES if COORDS[p][0] < 36]

agg = df.groupby(["place", "language"])["sentiment"].agg(
    ["mean", "std", "count"]
).reset_index()

# load topic info if available
topic_df = None
topic_labels = {"en": {}, "ko": {}}
try:
    topic_df = pd.read_csv(ANALYSIS / "topic_assignments.csv")
    for lang in ["en", "ko"]:
        tl = pd.read_csv(ANALYSIS / f"lda_{lang}_topics.csv")
        if "label" in tl.columns:
            topic_labels[lang] = {row["topic"]: row["label"] for _, row in tl.iterrows()}
        else:
            topic_labels[lang] = {
                row["topic"]: row["top_words"].split(",")[0].strip()
                for _, row in tl.iterrows()
            }
except FileNotFoundError:
    pass

def dominant_topic(place, lang):
    if topic_df is None:
        return ""
    sub = topic_df[(topic_df.place == place) & (topic_df.language == lang)]
    if sub.empty:
        return ""
    dt = sub["dominant_topic"].mode()
    if dt.empty:
        return ""
    t = int(dt.iloc[0])
    lbl = topic_labels.get(lang, {}).get(t, f"Topic {t}")
    return lbl

print(f"Loaded {len(df)} reviews, {len(PLACES)} places")
print(f"  Seoul: {[PLACE_EN[p] for p in seoul_places]}")
print(f"  Busan: {[PLACE_EN[p] for p in busan_places]}")

# ═════════════════════════════════════════════════════════════════════════════
# 1. INTERACTIVE MAP (folium)
# ═════════════════════════════════════════════════════════════════════════════
try:
    import folium

    m = folium.Map(location=[36.5, 128.0], zoom_start=7, tiles="OpenStreetMap")

    for place in PLACES:
        lat, lng = COORDS[place]

        ko_row = agg[(agg.place == place) & (agg.language == "ko")]
        en_row = agg[(agg.place == place) & (agg.language == "en")]
        ko_mean = float(ko_row["mean"].iloc[0]) if not ko_row.empty else 0
        en_mean = float(en_row["mean"].iloc[0]) if not en_row.empty else 0
        ko_std  = float(ko_row["std"].iloc[0])  if not ko_row.empty else 0
        en_std  = float(en_row["std"].iloc[0])  if not en_row.empty else 0
        ko_n    = int(ko_row["count"].iloc[0])   if not ko_row.empty else 0
        en_n    = int(en_row["count"].iloc[0])   if not en_row.empty else 0
        ko_topic = dominant_topic(place, "ko")
        en_topic = dominant_topic(place, "en")

        popup_html = (
            f"<div style='font:13px/1.6 sans-serif; min-width:220px'>"
            f"<b style='font-size:15px'>{PLACE_EN[place]}</b> ({place})<br>"
            f"<hr style='margin:4px 0'>"
            f"<span style='color:#2563EB'><b>Korean</b></span>: "
            f"n={ko_n} reviews<br>"
            f"<span style='color:#2563EB'>Topic</span>: {ko_topic}<br>"
            f"</div>"
        )

        pairs = [
            ("ko", ko_mean, PALETTE["ko"]),
            # ("en", en_mean, PALETTE["en"]),  # GMaps — paused (Naver-only scope)
        ]
        pairs.sort(key=lambda x: x[1], reverse=True)

        for lang, mean_s, color in pairs:
            radius_m = max(mean_s * 200, 120)

            folium.Circle(
                location=[lat, lng],
                radius=radius_m,
                color=color,
                fill=True,
                fill_color=color,
                fill_opacity=0.45,
                weight=2.5,
                popup=folium.Popup(popup_html, max_width=300),
                tooltip=f"{PLACE_EN[place]}",
            ).add_to(m)

    legend_html = """
    <div style="position:fixed; bottom:30px; left:30px; z-index:1000;
         background:white; padding:12px 16px; border-radius:8px;
         box-shadow:0 2px 8px rgba(0,0,0,0.2); font:13px/1.5 sans-serif;">
      <b>Bubble Map</b><br>
      <span style="color:#2563EB">●</span> Korean (Naver)<br>
      <span style="font-size:11px; color:#666">Radius = sentiment score</span>
    </div>
    """
    m.get_root().html.add_child(folium.Element(legend_html))

    out_html = FIGS / "bubble_map.html"
    m.save(str(out_html))
    print(f"\n  Saved interactive map: {out_html}")

except ImportError:
    print("\n  folium not installed — skipping interactive map")
    print("  Install with: pip install folium")

# ═════════════════════════════════════════════════════════════════════════════
# 2. STATIC FIGURES (matplotlib) — one panel per city
# ═════════════════════════════════════════════════════════════════════════════
print("\nGenerating static figures...")

def plot_bubble_panel(places, city_name, filename):
    if not places:
        print(f"  No {city_name} places — skipping")
        return

    fig, ax = plt.subplots(figsize=(10, 8))

    lats = [COORDS[p][0] for p in places]
    lngs = [COORDS[p][1] for p in places]
    lat_margin = max((max(lats) - min(lats)) * 0.35, 0.008)
    lng_margin = max((max(lngs) - min(lngs)) * 0.35, 0.015)

    for place in places:
        lat, lng = COORDS[place]
        for lang, dx in [("ko", -0.0015), ("en", 0.0015)]:
            row = agg[(agg.place == place) & (agg.language == lang)]
            if row.empty:
                continue
            mean_s = float(row["mean"].iloc[0])
            n      = int(row["count"].iloc[0])
            dtopic = dominant_topic(place, lang)

            size = max(mean_s * 800, 80)

            ax.scatter(
                lng + dx, lat,
                s=size, alpha=0.55, linewidths=1.5,
                edgecolors=PALETTE[lang], facecolors=PALETTE[lang],
                zorder=3,
            )
            ax.annotate(
                f"{mean_s:.2f}",
                (lng + dx, lat),
                ha="center", va="center",
                fontsize=7, fontweight="bold", color="white", zorder=4,
            )

        ax.annotate(
            f"{PLACE_EN[place]}",
            (lng, lat + lat_margin * 0.12),
            ha="center", va="bottom",
            fontsize=9, fontweight="bold", zorder=5,
            bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="gray",
                      alpha=0.85, lw=0.5),
        )

        dtopic_ko = dominant_topic(place, "ko")
        dtopic_en = dominant_topic(place, "en")
        topic_text = ""
        if dtopic_ko and dtopic_en:
            topic_text = f"KO: {dtopic_ko}\nEN: {dtopic_en}"
        elif dtopic_ko:
            topic_text = f"KO: {dtopic_ko}"
        if topic_text:
            ax.annotate(
                topic_text,
                (lng, lat - lat_margin * 0.10),
                ha="center", va="top",
                fontsize=6.5, color="#555", zorder=5,
                style="italic",
            )

    ax.set_xlim(min(lngs) - lng_margin, max(lngs) + lng_margin)
    ax.set_ylim(min(lats) - lat_margin, max(lats) + lat_margin)
    ax.set_xlabel("Longitude", fontsize=10)
    ax.set_ylabel("Latitude", fontsize=10)
    ax.set_title(
        f"Sentiment Bubble Map — {city_name}\n"
        f"(radius = mean sentiment, blue = Korean, red = English)",
        fontsize=12, fontweight="bold",
    )
    ax.set_aspect("equal")
    ax.grid(True, alpha=0.2, linestyle="--")
    ax.spines[["top", "right"]].set_visible(False)

    from matplotlib.lines import Line2D
    legend_elements = [
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#2563EB",
               markersize=12, alpha=0.7, label="Korean (Naver)"),
        Line2D([0], [0], marker="o", color="w", markerfacecolor="#DC2626",
               markersize=12, alpha=0.7, label="English (GMaps)"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", fontsize=10,
              framealpha=0.9)

    fig.tight_layout()
    fig.savefig(FIGS / filename, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"  Saved: {filename}")

plot_bubble_panel(seoul_places, "Seoul", "11_geo_bubble_seoul.png")
plot_bubble_panel(busan_places, "Busan", "11_geo_bubble_busan.png")

# ═════════════════════════════════════════════════════════════════════════════
# 3. SENTIMENT COMPARISON SCATTER (KO vs EN per place)
# ═════════════════════════════════════════════════════════════════════════════
print("\nGenerating sentiment comparison bubble chart...")

fig, ax = plt.subplots(figsize=(8, 7))

for place in PLACES:
    ko_row = agg[(agg.place == place) & (agg.language == "ko")]
    en_row = agg[(agg.place == place) & (agg.language == "en")]
    if ko_row.empty or en_row.empty:
        continue

    ko_mean = float(ko_row["mean"].iloc[0])
    en_mean = float(en_row["mean"].iloc[0])
    n_total = int(ko_row["count"].iloc[0]) + int(en_row["count"].iloc[0])

    city = "Busan" if COORDS[place][0] < 36 else "Seoul"
    marker = "D" if city == "Busan" else "o"

    ax.scatter(
        en_mean, ko_mean,
        s=n_total * 6, alpha=0.5,
        edgecolors="#333", linewidths=1.2,
        facecolors="#2563EB" if city == "Seoul" else "#0891b2",
        marker=marker, zorder=3,
    )
    ax.annotate(
        PLACE_EN[place],
        (en_mean, ko_mean),
        textcoords="offset points", xytext=(8, 6),
        fontsize=8.5, fontweight="bold", zorder=5,
    )

lim = (0, 1.05)
ax.plot(lim, lim, "--", color="#aaa", linewidth=1, zorder=1, label="KO = EN line")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_xlabel("English (GMaps) — Mean Sentiment", fontsize=11)
ax.set_ylabel("Korean (Naver) — Mean Sentiment", fontsize=11)
ax.set_title(
    "Sentiment Comparison: Korean vs English Reviewers\n"
    "(bubble size = total reviews, above line = KO more positive)",
    fontsize=12, fontweight="bold",
)
ax.legend(fontsize=9, loc="lower right")
ax.set_aspect("equal")
ax.grid(True, alpha=0.15)
ax.spines[["top", "right"]].set_visible(False)

fig.tight_layout()
fig.savefig(FIGS / "12_sentiment_scatter.png", dpi=300, bbox_inches="tight")
plt.close()
print("  Saved: 12_sentiment_scatter.png")

print("\n── Done ──")
