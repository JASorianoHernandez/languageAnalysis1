/**
 * probe_ceiling.js — how many unique reviews will Google actually return?
 *
 * Fetches a large page count and reports where the unique-review count
 * saturates, plus the language breakdown of what we get. Used to decide
 * whether a multi-language group design (KO/EN/JA/ZH) is feasible.
 *
 * Run: node probe_ceiling.js
 */
const { scraper } = require("google-maps-review-scraper");
const { parseRawReviews } = require("./parseRaw.js");

const PLACES = [
  {
    name: "광안리해수욕장",
    url: "https://www.google.com/maps/place/Gwangalli+Beach/data=!3m1!4b1!4m4!3m3!1s0x3568ed2f27c70ec7:0xff6df0e14d9216fb!16s%2Fm%2F03hp9yc!20s8Q7F5439%2B7F7MRQ5?entry=ttu&g_ep=EgoyMDI2MDkyNy4xIKXMDSoASAFQAw%3D%3D",
  },
  {
    name: "해운대해수욕장",
    url: "https://www.google.com/maps/place/Playa+Haeundae/data=!4m2!3m1!1s0x35688d5c0efe075f:0x9963b1d5c163ac98!18m1!1e1?utm_source=mstt_1&entry=gps",
  },
];

const STEPS = [10, 25, 50, 100];
const CORE = ["ko", "en", "ja", "zh-Hant", "zh-Hans", "zh"];

async function probe(place) {
  console.log("\n" + "█".repeat(72));
  console.log(`█  ${place.name}`);
  console.log("█".repeat(72));
  console.log(`\n${"pages".padEnd(8)}${"returned".padEnd(11)}${"unique".padEnd(9)}${"w/ text".padEnd(9)}elapsed`);
  console.log("-".repeat(50));

  let lastUnique = 0;
  let final = null;

  for (const pages of STEPS) {
    const t0 = Date.now();
    let raw;
    try {
      raw = await scraper({ url: place.url, sort_type: "newest", pages, clean: false });
    } catch (e) {
      console.log(`${String(pages).padEnd(8)}FETCH FAILED: ${e.message}`);
      break;
    }
    const parsed = parseRawReviews(raw);
    const uniq = new Map();
    for (const r of parsed) if (r.review_id) uniq.set(r.review_id, r);

    const withText = [...uniq.values()].filter(r => r.review.text).length;
    const secs = ((Date.now() - t0) / 1000).toFixed(0);

    console.log(
      `${String(pages).padEnd(8)}${String(parsed.length).padEnd(11)}${String(uniq.size).padEnd(9)}${String(withText).padEnd(9)}${secs}s`
    );

    const tally = {};
    for (const r of uniq.values()) {
      if (!r.review.text) continue;
      const k = r.review.language || "(null)";
      tally[k] = (tally[k] || 0) + 1;
    }
    const sorted = Object.entries(tally).sort((a, b) => b[1] - a[1]);
    console.log(`        langs: ${sorted.map(([k, v]) => `${k}=${v}`).join("  ")}`);

    const photos = [...uniq.values()].filter(r => r.n_photos > 0).length;
    console.log(`        with photos: ${photos}/${uniq.size}`);

    final = { pages, total: uniq.size, withText, tally, photos };

    if (uniq.size === lastUnique) {
      console.log(`\n  >>> saturated at ${pages} pages — no new unique reviews.`);
      break;
    }
    lastUnique = uniq.size;
    console.log();
    await new Promise(r => setTimeout(r, 5000));
  }

  return { place: place.name, ...final };
}

(async () => {
  const results = [];
  for (const p of PLACES) results.push(await probe(p));

  console.log("\n\n" + "=".repeat(72));
  console.log("SIDE-BY-SIDE at deepest page count");
  console.log("=".repeat(72));

  const hdr = "metric".padEnd(22) + results.map(r => r.place.padEnd(18)).join("");
  console.log("\n" + hdr);
  console.log("-".repeat(hdr.length));

  const row = (label, fn) =>
    console.log(label.padEnd(22) + results.map(r => String(fn(r)).padEnd(18)).join(""));

  row("pages fetched", r => r.pages);
  row("unique reviews", r => r.total);
  row("with text", r => r.withText);
  row("text rate", r => `${((r.withText / r.total) * 100).toFixed(0)}%`);
  row("with photos", r => r.photos);
  console.log();
  for (const lang of CORE) {
    row(`  ${lang}`, r => r.tally[lang] || 0);
  }
  console.log();
  row("  Chinese (all)", r => (r.tally["zh-Hant"] || 0) + (r.tally["zh-Hans"] || 0) + (r.tally["zh"] || 0));
  row("distinct languages", r => Object.keys(r.tally).length);
  row("non-Korean w/ text", r => r.withText - (r.tally["ko"] || 0));

  console.log("\n\nFEASIBILITY — cells reaching n>=30 for a KO/EN/JA/ZH design:");
  for (const r of results) {
    const zh = (r.tally["zh-Hant"] || 0) + (r.tally["zh-Hans"] || 0) + (r.tally["zh"] || 0);
    const cells = { ko: r.tally["ko"] || 0, en: r.tally["en"] || 0, ja: r.tally["ja"] || 0, zh };
    const ok = Object.entries(cells).filter(([, v]) => v >= 30).map(([k]) => k);
    const bad = Object.entries(cells).filter(([, v]) => v < 30).map(([k, v]) => `${k}(${v})`);
    console.log(`  ${r.place}: OK=[${ok.join(", ")}]${bad.length ? `  SHORT=[${bad.join(", ")}]` : ""}`);
  }

  console.log("\nDone.");
})().catch(e => {
  console.error("FATAL:", e.message);
  process.exit(1);
});
