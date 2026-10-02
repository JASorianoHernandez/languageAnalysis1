"""
07_llm_analysis.py
LLM-based analysis using two Qwen models (both cached locally).

Part 1 — Qwen2-0.5B-Instruct  →  Aspect-Based Sentiment Analysis (ABSA)
  Extracts sentiment (-1/0/1) per aspect for every review:
    · historical_cultural  (역사·문화적 가치)
    · accessibility        (접근성·편의시설)
    · crowding             (혼잡도·쾌적함)
    · food                 (음식·미식 경험)
    · visual_photo         (시각적 경험·사진)

Part 2 — Qwen2.5-7B-Instruct  →  Narrative summaries
  One analytical paragraph per place × language (8 total).
  Suitable for the paper's Discussion / Qualitative Findings section.

Outputs → data/analysis/
  absa_results.csv           per-review aspect scores
  absa_summary.csv           mean aspect score by place × language
  llm_summaries.json         8 narrative paragraphs
  analysis_data.json         updated
"""

import os, warnings, json, re, time
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_OFFLINE"]  = "1"
warnings.filterwarnings("ignore")

import torch
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM

# ── paths & data ──────────────────────────────────────────────────────────────
ANALYSIS = Path("data/analysis")
FIGS     = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

PLACE_EN = {
    "경복궁":      "Gyeongbokgung",
    "창덕궁":      "Changdeokgung",
    "북촌한옥마을":  "Bukchon Village",
    "인사동길":     "Insadong-gil",
    "광장시장":     "Gwangjang Mkt",
    "홍대거리":     "Hongdae St.",
    "N서울타워":    "N Seoul Tower",
    "롯데월드":     "Lotte World",
    "광안리해수욕장": "Gwangalli Beach",
    "해운대해수욕장": "Haeundae Beach",
}
ASPECTS = ["historical_cultural", "accessibility", "crowding", "food", "visual_photo"]
ASPECT_LABELS = {
    "historical_cultural": "Historical &\nCultural Value",
    "accessibility":       "Accessibility &\nConvenience",
    "crowding":            "Crowding &\nComfort",
    "food":                "Food &\nGastronomy",
    "visual_photo":        "Visual &\nPhotography",
}

df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
PLACES = [p for p in PLACE_EN if p in df["place"].unique()]
print(f"Corpus: {len(df)} reviews, {len(PLACES)} places\n")

# ── LLM helper ────────────────────────────────────────────────────────────────
def load_model(model_id, dtype=torch.float16):
    print(f"  Loading {model_id}...")
    tok = AutoTokenizer.from_pretrained(model_id)
    mdl = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=dtype,
        device_map="auto",   # GPU first, spills to CPU RAM if needed
    )
    mdl.eval()
    params = sum(p.numel() for p in mdl.parameters()) / 1e6
    device = next(mdl.parameters()).device
    print(f"  {params:.0f}M params loaded on {device}")
    return tok, mdl

def generate(tok, mdl, messages, max_new_tokens=128, temperature=0.1):
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    device = next(mdl.parameters()).device
    enc  = tok(text, return_tensors="pt").to(device)
    with torch.no_grad():
        out = mdl.generate(
            **enc,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            do_sample=False,
            pad_token_id=tok.eos_token_id,
        )
    decoded = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
    return decoded.strip()

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — ABSA with Qwen2-0.5B-Instruct
# ══════════════════════════════════════════════════════════════════════════════
print("═" * 60)
print("PART 1 — ABSA  (Qwen2-0.5B-Instruct)")
print("═" * 60)

tok_s, mdl_s = load_model("Qwen/Qwen2-0.5B-Instruct")

ABSA_SYSTEM = (
    "You are a tourism review analyst. "
    "Given a tourist review, output ONLY a valid JSON object — no explanation. "
    "For each aspect assign: 1 (positive mention), -1 (negative mention), 0 (not mentioned or neutral). "
    'Keys: "historical_cultural", "accessibility", "crowding", "food", "visual_photo".'
)

def parse_absa(raw: str) -> dict:
    """Extract the JSON object from model output; fall back to zeros on failure."""
    default = {a: 0 for a in ASPECTS}
    try:
        m = re.search(r'\{[^{}]+\}', raw, re.DOTALL)
        if not m:
            return default
        obj = json.loads(m.group())
        result = {}
        for a in ASPECTS:
            v = obj.get(a, 0)
            result[a] = int(v) if v in (1, -1, 0, "1", "-1", "0") else 0
        return result
    except Exception:
        return default

absa_rows = []
n = len(df)
t0 = time.time()

for idx, row in df.iterrows():
    text = str(row["text"])[:500]
    messages = [
        {"role": "system", "content": ABSA_SYSTEM},
        {"role": "user",   "content": f'Review: "{text}"\n\nJSON:'},
    ]
    raw    = generate(tok_s, mdl_s, messages, max_new_tokens=80)
    scores = parse_absa(raw)

    absa_rows.append({
        "place":    row["place"],
        "language": row["language"],
        "text":     text[:100],
        **scores,
        "raw_output": raw[:120],
    })

    done = idx - df.index[0] + 1
    if done % 20 == 0 or done == 1:
        elapsed = time.time() - t0
        eta = (elapsed / done) * (n - done)
        print(f"  {done}/{n}  ({elapsed:.0f}s elapsed, ~{eta:.0f}s remaining)")

# free memory before loading 7B
del mdl_s, tok_s
import gc; gc.collect()

absa_df = pd.DataFrame(absa_rows)
absa_df.to_csv(ANALYSIS / "absa_results.csv", index=False, encoding="utf-8-sig")
print(f"\nSaved: absa_results.csv  ({len(absa_df)} rows)")

# ── ABSA summary ──────────────────────────────────────────────────────────────
summary_rows = []
for place in PLACES:
    for lang in ["ko", "en"]:
        sub = absa_df[(absa_df.place == place) & (absa_df.language == lang)]
        row = {"place": place, "language": lang}
        for a in ASPECTS:
            row[f"{a}_mean"] = round(sub[a].mean(), 3)
            row[f"{a}_pos"]  = int((sub[a] == 1).sum())
            row[f"{a}_neg"]  = int((sub[a] == -1).sum())
        summary_rows.append(row)

absa_summ = pd.DataFrame(summary_rows)
absa_summ.to_csv(ANALYSIS / "absa_summary.csv", index=False, encoding="utf-8-sig")
print("Saved: absa_summary.csv")

# ── ABSA heatmap: mean score per place × language ─────────────────────────────
for lang, group_label in [("ko", "Korean (Naver)"), ("en", "English (GMaps)")]:
    sub  = absa_summ[absa_summ.language == lang].set_index("place").reindex(PLACES)
    sub.index = [PLACE_EN[p] for p in PLACES]
    mat  = sub[[f"{a}_mean" for a in ASPECTS]].values

    fig, ax = plt.subplots(figsize=(10, 4))
    im = ax.imshow(mat, cmap="RdYlGn", vmin=-0.6, vmax=0.6, aspect="auto")
    plt.colorbar(im, ax=ax, label="Mean sentiment score")
    ax.set_xticks(range(len(ASPECTS)))
    ax.set_xticklabels([ASPECT_LABELS[a] for a in ASPECTS], fontsize=9)
    ax.set_yticks(range(len(PLACES)))
    ax.set_yticklabels(sub.index, fontsize=10)
    for i in range(len(PLACES)):
        for j in range(len(ASPECTS)):
            v = mat[i, j]
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=9,
                    fontweight="bold",
                    color="white" if abs(v) > 0.35 else "black")
    ax.set_title(f"Aspect-Based Sentiment — {group_label}", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / f"09_absa_heatmap_{lang}.png", dpi=300)
    plt.close()
    print(f"Saved: 09_absa_heatmap_{lang}.png")

# ── ABSA radar chart: KO vs EN per aspect (all places combined) ───────────────
ko_means = absa_summ[absa_summ.language=="ko"][[f"{a}_mean" for a in ASPECTS]].mean().values
en_means = absa_summ[absa_summ.language=="en"][[f"{a}_mean" for a in ASPECTS]].mean().values

angles = np.linspace(0, 2*np.pi, len(ASPECTS), endpoint=False).tolist()
angles += angles[:1]
ko_vals = ko_means.tolist() + [ko_means[0]]
en_vals = en_means.tolist() + [en_means[0]]

fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
ax.plot(angles, ko_vals, "o-", linewidth=2, color="#2563EB", label="Korean")
ax.fill(angles, ko_vals, alpha=0.15, color="#2563EB")
ax.plot(angles, en_vals, "s-", linewidth=2, color="#DC2626", label="English")
ax.fill(angles, en_vals, alpha=0.15, color="#DC2626")
ax.set_xticks(angles[:-1])
ax.set_xticklabels([ASPECT_LABELS[a].replace("\n", " ") for a in ASPECTS], fontsize=9)
ax.set_ylim(-0.5, 0.5)
ax.set_title("ABSA Radar: Korean vs English\n(all places combined)", fontsize=11, fontweight="bold", pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
fig.tight_layout()
fig.savefig(FIGS / "10_absa_radar.png", dpi=300, bbox_inches="tight")
plt.close()
print("Saved: 10_absa_radar.png")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — Narrative summaries with Qwen2.5-7B-Instruct
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═"*60)
print("PART 2 — Narrative summaries  (Qwen2.5-7B-Instruct)")
print("═"*60)

try:
    tok_l, mdl_l = load_model("Qwen/Qwen2.5-7B-Instruct", dtype=torch.float16)
    USE_7B = True
except Exception as e:
    print(f"  7B load failed ({e}) — skipping narrative summaries")
    USE_7B = False

summaries = {}
if USE_7B:
    SUMM_SYSTEM = (
        "You are a tourism and consumer behavior researcher. "
        "Write precise, academic-style analytical summaries. "
        "Be concise: 3-4 sentences only."
    )
    for place in PLACES:
        summaries[place] = {}
        for lang, group in [("ko", "Korean domestic"), ("en", "English-speaking foreign")]:
            reviews = df[(df.place==place) & (df.language==lang)]["text"].tolist()
            sample  = reviews[:20]   # first 20 reviews to stay within context
            reviews_text = "\n".join(f"[{i+1}] {r[:200]}" for i, r in enumerate(sample))

            messages = [
                {"role": "system", "content": SUMM_SYSTEM},
                {"role": "user", "content":
                    f"Below are {len(sample)} reviews of {place} (Seoul) written by {group} tourists.\n\n"
                    f"{reviews_text}\n\n"
                    f"Summarize in 3-4 sentences: (1) main themes emphasized, "
                    f"(2) overall sentiment and tone, (3) what distinguishes this group's experience."},
            ]
            t0 = time.time()
            summary = generate(tok_l, mdl_l, messages, max_new_tokens=200, temperature=0.2)
            elapsed = time.time() - t0
            summaries[place][lang] = summary
            print(f"\n  [{place} / {lang}]  ({elapsed:.0f}s)")
            print(f"  {summary[:200]}...")

    del mdl_l, tok_l
    gc.collect()

with open(ANALYSIS / "llm_summaries.json", "w", encoding="utf-8") as f:
    json.dump(summaries, f, ensure_ascii=False, indent=2)
print("\nSaved: llm_summaries.json")

# ══════════════════════════════════════════════════════════════════════════════
# UPDATE analysis_data.json
# ══════════════════════════════════════════════════════════════════════════════
json_path = ANALYSIS / "analysis_data.json"
data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}

data["absa"] = {
    "model": "Qwen2-0.5B-Instruct",
    "aspects": ASPECTS,
    "summary": absa_summ.to_dict(orient="records"),
}
data["llm_summaries"] = {
    "model": "Qwen2.5-7B-Instruct" if USE_7B else "skipped",
    "summaries": summaries,
}

json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated: analysis_data.json")

print("\n── Done ──")
for f in sorted(FIGS.iterdir()):
    print(f"  {f.name}")
