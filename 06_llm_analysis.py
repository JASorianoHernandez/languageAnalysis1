"""
06_llm_analysis.py
LLM-based analysis with Qwen2.5-7B-Instruct loaded in 4-bit (fits an 8 GB GPU).
The same model and prompt are used for both languages.

Part 1  Aspect-Based Sentiment Analysis (ABSA): -1 / 0 / 1 per aspect for every review
          historical_cultural  (역사·문화적 가치)
          accessibility        (접근성·편의시설)
          crowding             (혼잡도·쾌적함)
          food                 (음식·미식 경험)
          visual_photo         (시각적 경험·사진)
        Answers that are not a valid -1/0/1 are stored as missing (parse_ok = False)
        instead of being silently turned into 0.
Part 2  Narrative summaries: one paragraph per place x language.

Usage (faiss-gpu env):
  python 06_llm_analysis.py              full run (ABSA + summaries)
  python 06_llm_analysis.py --pilot 20   ABSA on 20 stratified reviews only -> absa_pilot.csv
  python 06_llm_analysis.py --naver      ABSA on the Korean-only dataset (02_naver_build_dataset.py)
                                         -> naver/naver_absa.csv

Outputs (data/analysis/):
  absa_results.csv, absa_summary.csv, llm_summaries.json, analysis_data.json (updated),
  figures/09_absa_heatmap_{ko,en}.png, figures/10_absa_radar.png
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

import os, warnings, json, re, time, gc
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"
os.environ["TRANSFORMERS_OFFLINE"] = "1"
warnings.filterwarnings("ignore")

import torch
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

MODEL_ID = "Qwen/Qwen2.5-7B-Instruct"
MAX_CHARS = 1200

ANALYSIS = Path("data/analysis")
FIGS = ANALYSIS / "figures"
FIGS.mkdir(parents=True, exist_ok=True)

for fp in ("C:/Windows/Fonts/malgunbd.ttf", "C:/Windows/Fonts/malgun.ttf"):
    if Path(fp).exists():
        fm.fontManager.addfont(fp)
        plt.rcParams["font.family"] = fm.FontProperties(fname=fp).get_name()
        break

# Single source of truth: places.json (see places_data.py's docstring).
from places_data import PLACE_EN, CITY
ASPECTS = ["historical_cultural", "accessibility", "crowding", "food", "visual_photo", "service_experience"]
ASPECT_LABELS = {
    "historical_cultural": "Historical &\nCultural Value",
    "accessibility":       "Accessibility &\nConvenience",
    "crowding":            "Crowding &\nComfort",
    "food":                "Food &\nGastronomy",
    "visual_photo":        "Visual &\nPhotography",
    "service_experience":  "Service &\nExperience",
}

pilot_n = int(sys.argv[sys.argv.index("--pilot") + 1]) if "--pilot" in sys.argv else None
naver_mode = "--naver" in sys.argv

if naver_mode:
    df = pd.read_csv(ANALYSIS / "naver" / "naver_dataset.csv", encoding="utf-8-sig")[["place", "text"]]
    df["language"] = "ko"
    before = len(df)
    df = df[df["text"].notna() & (df["text"].astype(str).str.len() >= 10)].reset_index(drop=True)
    print(f"Filtered to reviews with text (>=10 chars): {len(df)} of {before} "
          f"(dropped {before - len(df)} keyword-only / empty reviews).")
else:
    df = pd.read_csv("data/corpus.csv", encoding="utf-8-sig")
PLACES = [p for p in PLACE_EN if p in df["place"].unique()]
if pilot_n:
    per_lang = pilot_n // 2
    df = pd.concat([
        df[df.language == lang].sample(frac=1, random_state=0)
          .groupby("place").head(-(-per_lang // len(PLACES))).head(per_lang)
        for lang in ("ko", "en")
    ]).reset_index(drop=True)
mode = "pilot" if pilot_n else "Korean-only dataset, ABSA only" if naver_mode else "full run"
print(f"Reviews to process (before resume filter): {len(df)}  ({mode})\n")

# ── resume logic (--naver mode only): skip reviews already in naver_absa.csv ─
naver_out_path = ANALYSIS / "naver" / "naver_absa.csv"
done_keys = set()
if naver_mode and naver_out_path.exists():
    prev = pd.read_csv(naver_out_path, encoding="utf-8-sig")
    done_keys = set(zip(prev["place"].astype(str), prev["text"].astype(str)))
    print(f"Resume: {len(done_keys)} reviews already in {naver_out_path.name}; skipping them.")
    mask = ~df.apply(lambda r: (str(r["place"]), str(r["text"])) in done_keys, axis=1)
    df = df[mask].reset_index(drop=True)
    print(f"Remaining to process: {len(df)}\n")

if len(df) == 0:
    print("Nothing to process (resume complete). Exiting.")
    sys.exit(0)

# ── hardware check with user confirmation ────────────────────────────────────
print("=" * 60)
print("HARDWARE CHECK")
print("=" * 60)
if torch.cuda.is_available():
    name = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    print(f"GPU detected: {name}  ({vram:.1f} GB VRAM)")
    print(f"The model (Qwen2.5-7B in 4-bit) needs ~6 GB and will run on this GPU.")
    device_ok = True
else:
    print("WARNING: No CUDA GPU detected.")
    print("The model will fall back to CPU, which is MUCH slower (~30-60 s/review).")
    print(f"At that rate, {len(df)} reviews would take {len(df) * 45 / 3600:.1f} hours or more.")
    device_ok = False

print(f"\nMode: {mode}")
print(f"Reviews to process: {len(df)}")
if torch.cuda.is_available():
    print(f"Estimated time at GPU speed (~2-3 s/review): {len(df) * 2.5 / 3600:.1f} hours")
print()

# --yes flag skips the confirmation prompt (useful for overnight / background runs)
if "--yes" in sys.argv:
    print("--yes flag detected: skipping confirmation and continuing.\n")
else:
    ans = input("Continue? [Enter / y / 1 = yes, anything else = abort]: ").strip().lower()
    if ans not in ("", "y", "yes", "1"):
        print("Aborted by user.")
        sys.exit(0)
    print()


# ── model ────────────────────────────────────────────────────────────────────
def load_model():
    print(f"Loading {MODEL_ID} in 4-bit...")
    quant = BitsAndBytesConfig(
        load_in_4bit=True, bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16, bnb_4bit_use_double_quant=True,
    )
    tok = AutoTokenizer.from_pretrained(MODEL_ID)
    # device_map {"": 0}: fail loudly instead of silently offloading to CPU/disk
    mdl = AutoModelForCausalLM.from_pretrained(
        MODEL_ID, quantization_config=quant, device_map={"": 0}, torch_dtype=torch.float16)
    mdl.eval()
    print(f"  GPU memory allocated: {torch.cuda.memory_allocated() / 1e9:.1f} GB\n")
    return tok, mdl


def generate(tok, mdl, messages, max_new_tokens):
    text = tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    enc = tok(text, return_tensors="pt").to(mdl.device)
    with torch.no_grad():
        out = mdl.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False,
                           pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


tok, mdl = load_model()

# ══════════════════════════════════════════════════════════════════════════════
# PART 1 — ABSA
# ══════════════════════════════════════════════════════════════════════════════
print("═" * 60)
print("PART 1 — ABSA")
print("═" * 60)

ABSA_SYSTEM = """You annotate tourist reviews written in Korean or English.
For each aspect, give the reviewer's sentiment toward that aspect:
1 = positive, -1 = negative, 0 = not mentioned or neutral.

Aspects:
- historical_cultural: the heritage itself -- history, traditional culture, architecture,
  monuments, the cultural or symbolic meaning of the place. Not the quality of the guide
  or the tour (that is service_experience).
- accessibility: getting there, public transport, parking, opening hours, tickets,
  reservations, admission price, discounts, value for money, facilities, convenience.
- crowding: crowd level and comfort. -1 = crowded, queues, long waits, noisy or
  uncomfortable; 1 = quiet, not crowded, easy to move around; 0 = not mentioned. A
  lively or bustling atmosphere described only as fun is 0 here (it is not a judgement
  about crowding).
- food: food, drinks, restaurants, street food, cafes, food quality.
- visual_photo: scenery, views, night views, beauty, decorations, photo spots, the
  aesthetics of the place itself.
- service_experience: the quality of human interaction and participatory programs at
  the site -- guided tours, staff friendliness, hands-on experiences (e.g. hanji
  crafts, hanbok rentals, cultural programs), explanations by guides or teachers,
  educational workshops. This is about the mediated experience, not the heritage itself.

Answer with ONLY a JSON object with exactly these six keys and integer values -1, 0 or 1."""

FEW_SHOT = [
    ("경치는 정말 예쁜데 사람이 너무 많아서 30분 줄 섰어요. 지하철역에서 가까워서 편해요.",
     {"historical_cultural": 0, "accessibility": 1, "crowding": -1,
      "food": 0, "visual_photo": 1, "service_experience": 0}),
    ("Fascinating history and the guided tour was free, but the food stalls were overpriced.",
     {"historical_cultural": 1, "accessibility": 1, "crowding": 0,
      "food": -1, "visual_photo": 0, "service_experience": 1}),
    ("선생님께서 한지공예를 자세히 설명해주셨고 체험이 정말 즐거웠어요. 한옥 분위기도 멋졌어요.",
     {"historical_cultural": 1, "accessibility": 0, "crowding": 0,
      "food": 0, "visual_photo": 1, "service_experience": 1}),
]


def absa_messages(text):
    msgs = [{"role": "system", "content": ABSA_SYSTEM}]
    for example, labels in FEW_SHOT:
        msgs.append({"role": "user", "content": f"Review: {example}"})
        msgs.append({"role": "assistant", "content": json.dumps(labels)})
    msgs.append({"role": "user", "content": f"Review: {text}"})
    return msgs


def to_label(v):
    try:
        x = int(float(str(v).strip().replace("+", "")))
    except ValueError:
        return np.nan
    return x if x in (-1, 0, 1) else np.nan


def parse_absa(raw):
    m = re.search(r"\{.*?\}", raw, re.DOTALL)
    try:
        obj = json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        obj = {}
    return {a: to_label(obj.get(a, "missing")) for a in ASPECTS}


absa_rows = []
t0 = time.time()
CHECKPOINT_EVERY = 50  # incremental save: never lose more than CHECKPOINT_EVERY reviews on crash

def _flush_checkpoint(rows):
    """Append new rows to naver_absa.csv (writes header only if file is empty/absent)."""
    if not rows or not naver_mode:
        return
    out = pd.DataFrame(rows)
    header = not naver_out_path.exists() or naver_out_path.stat().st_size == 0
    out.to_csv(naver_out_path, mode="a", header=header, index=False, encoding="utf-8-sig")

for i, row in enumerate(df.itertuples(index=False), start=1):
    try:
        raw = generate(tok, mdl, absa_messages(str(row.text)[:MAX_CHARS]), max_new_tokens=60)
    except KeyboardInterrupt:
        print(f"\nInterrupted at review {i}/{len(df)}. Flushing pending rows...")
        _flush_checkpoint(absa_rows)
        print(f"Saved {len(absa_rows)} rows before exit. Rerun to resume.")
        sys.exit(130)
    scores = parse_absa(raw)
    absa_rows.append({
        "place": row.place, "language": row.language, "text": row.text,
        **scores, "parse_ok": not any(np.isnan(v) for v in scores.values()),
        "raw_output": raw,
    })
    if i % CHECKPOINT_EVERY == 0:
        _flush_checkpoint(absa_rows)
        absa_rows = []  # already on disk
    if i % 20 == 0 or i == 1 or i == len(df):
        elapsed = time.time() - t0
        print(f"  {i}/{len(df)}  ({elapsed:.0f}s elapsed, ~{elapsed / i * (len(df) - i):.0f}s left)")

# flush any trailing rows not yet checkpointed
_flush_checkpoint(absa_rows)

# For end-of-run summary stats, load the full on-disk file (--naver mode) or just the in-memory rows
if naver_mode:
    absa_df = pd.read_csv(naver_out_path, encoding="utf-8-sig")
else:
    absa_df = pd.DataFrame(absa_rows)
valid = absa_df.groupby("language")["parse_ok"].mean().mul(100).round(1)
print(f"\nValid JSON answers: KO {valid.get('ko', 0)}%, EN {valid.get('en', 0)}%")

if pilot_n:
    absa_df.to_csv(ANALYSIS / "absa_pilot.csv", index=False, encoding="utf-8-sig")
    print("\nDetection rate (share of reviews with a non-zero label):")
    print(absa_df.groupby("language")[ASPECTS].apply(lambda g: (g.fillna(0) != 0).mean()).round(2))
    print("\nSample answers:")
    for r in absa_df.itertuples():
        labels = " ".join(f"{a[:4]}={getattr(r, a):+.0f}" if not np.isnan(getattr(r, a)) else f"{a[:4]}=NA"
                          for a in ASPECTS)
        print(f"  [{r.language}] {labels} | {str(r.text)[:70]}")
    print(f"\nSaved: {ANALYSIS / 'absa_pilot.csv'}  (pilot mode: summaries skipped)")
    sys.exit(0)

if naver_mode:
    # File already on disk from incremental checkpointing; just report final size.
    print(f"Final file: {naver_out_path}  ({len(absa_df)} total rows)")
    print(f"(Korean-only mode: summaries and figures skipped.)")
    sys.exit(0)

absa_df.to_csv(ANALYSIS / "absa_results.csv", index=False, encoding="utf-8-sig")
print(f"Saved: absa_results.csv  ({len(absa_df)} rows)")

summary_rows = []
for place in PLACES:
    for lang in ["ko", "en"]:
        sub = absa_df[(absa_df.place == place) & (absa_df.language == lang)]
        row = {"place": place, "language": lang, "n_valid": int(sub["parse_ok"].sum())}
        for a in ASPECTS:
            row[f"{a}_mean"] = round(sub[a].mean(), 3)
            row[f"{a}_pos"] = int((sub[a] == 1).sum())
            row[f"{a}_neg"] = int((sub[a] == -1).sum())
        summary_rows.append(row)
absa_summ = pd.DataFrame(summary_rows)
absa_summ.to_csv(ANALYSIS / "absa_summary.csv", index=False, encoding="utf-8-sig")
print("Saved: absa_summary.csv")

for lang, group_label in [("ko", "Korean-language reviews"), ("en", "English-language reviews")]:
    sub = absa_summ[absa_summ.language == lang].set_index("place").reindex(PLACES)
    sub.index = [PLACE_EN[p] for p in PLACES]
    mat = sub[[f"{a}_mean" for a in ASPECTS]].values

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
            ax.text(j, i, f"{v:+.2f}", ha="center", va="center", fontsize=9, fontweight="bold",
                    color="white" if abs(v) > 0.35 else "black")
    ax.set_title(f"Aspect-Based Sentiment: {group_label}", fontsize=12, fontweight="bold")
    fig.tight_layout()
    fig.savefig(FIGS / f"09_absa_heatmap_{lang}.png", dpi=300)
    plt.close()
    print(f"Saved: 09_absa_heatmap_{lang}.png")

ko_means = absa_df[absa_df.language == "ko"][ASPECTS].mean().values
en_means = absa_df[absa_df.language == "en"][ASPECTS].mean().values
angles = np.linspace(0, 2 * np.pi, len(ASPECTS), endpoint=False).tolist()
angles += angles[:1]
fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})
for means, label, color, marker in [(ko_means, "Korean", "#2563EB", "o-"),
                                    (en_means, "English", "#DC2626", "s-")]:
    vals = means.tolist() + [means[0]]
    ax.plot(angles, vals, marker, linewidth=2, color=color, label=label)
    ax.fill(angles, vals, alpha=0.15, color=color)
ax.set_xticks(angles[:-1])
ax.set_xticklabels([ASPECT_LABELS[a].replace("\n", " ") for a in ASPECTS], fontsize=9)
ax.set_ylim(-0.5, 0.5)
ax.set_title("ABSA Radar: Korean vs English\n(all places combined)", fontsize=11,
             fontweight="bold", pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=10)
fig.tight_layout()
fig.savefig(FIGS / "10_absa_radar.png", dpi=300, bbox_inches="tight")
plt.close()
print("Saved: 10_absa_radar.png")

# ══════════════════════════════════════════════════════════════════════════════
# PART 2 — Narrative summaries
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "═" * 60)
print("PART 2 — Narrative summaries")
print("═" * 60)

SUMM_SYSTEM = ("You are a tourism and consumer behavior researcher. "
               "Write precise, academic-style analytical summaries. Be concise: 3-4 sentences only.")
summaries = {}
for place in PLACES:
    summaries[place] = {}
    for lang, group in [("ko", "Korean domestic"), ("en", "English-speaking foreign")]:
        sample = df[(df.place == place) & (df.language == lang)]["text"].tolist()[:20]
        reviews_text = "\n".join(f"[{i + 1}] {r[:200]}" for i, r in enumerate(sample))
        messages = [
            {"role": "system", "content": SUMM_SYSTEM},
            {"role": "user", "content":
                f"Below are {len(sample)} reviews of {place} ({CITY[place]}) written by {group} tourists.\n\n"
                f"{reviews_text}\n\n"
                f"Summarize in 3-4 sentences: (1) main themes emphasized, "
                f"(2) overall sentiment and tone, (3) what distinguishes this group's experience."},
        ]
        t0 = time.time()
        summaries[place][lang] = generate(tok, mdl, messages, max_new_tokens=200)
        print(f"  [{place} / {lang}]  ({time.time() - t0:.0f}s)")

with open(ANALYSIS / "llm_summaries.json", "w", encoding="utf-8") as f:
    json.dump(summaries, f, ensure_ascii=False, indent=2)
print("Saved: llm_summaries.json")

del mdl, tok
gc.collect()

json_path = ANALYSIS / "analysis_data.json"
data = json.loads(json_path.read_text(encoding="utf-8")) if json_path.exists() else {}
data["absa"] = {"model": f"{MODEL_ID} (4-bit)", "aspects": ASPECTS,
                "summary": absa_summ.to_dict(orient="records")}
data["llm_summaries"] = {"model": f"{MODEL_ID} (4-bit)", "summaries": summaries}
json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
print("Updated: analysis_data.json")
print("\n── Done ──")
