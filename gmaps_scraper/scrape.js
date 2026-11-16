/**
 * scrape.js — Collect Google Maps reviews.
 *
 * Uses our own throttled paginator (fetchReviews.js) and parser (parseRaw.js)
 * instead of the npm package's defaults, which fire requests with no delay and
 * drop the author stats, original-language code and translation that Google
 * actually sends.
 *
 * Saves to ../data/gmaps_reviews_raw.json, merging by review_id so a re-run
 * tops a place up instead of replacing it.
 *
 * Run: node scrape.js [--replace] [placeName ...]
 *   With no arguments, scrapes every place that is not yet in the JSON.
 *   With names, scrapes (or tops up) only those places.
 *   With --replace, stored reviews for the named places are discarded first —
 *   needed when re-scraping data that was collected with the old parser, since
 *   merging would leave one array holding two different record shapes.
 */
const fs = require("fs");
const path = require("path");
const { fetchAllReviews, assessCompleteness } = require("./fetchReviews.js");
const { parseRawReviews, validateSlots } = require("./parseRaw.js");

const OUT = path.join(__dirname, "..", "data", "gmaps_reviews_raw.json");

// Pacing. 100 pages at ~2s each is roughly 3.5 min per place — slow enough to
// stay well clear of rate limiting, still trivial next to the Naver scraper.
const MAX_PAGES = 100;
const DELAY_MS = 1500;
const JITTER_MS = 1000;
const PLACE_PAUSE_MS = [20000, 40000]; // random pause between places

// Single source of truth: ../places.json (edit there -- paste a Google Maps
// URL and this list picks it up). Node loads JSON natively via require(),
// so this stays in sync with the Python side (places_data.py) by construction.
// A place with no gmaps_url yet is left out.
const PLACES_JSON = require("../places.json");
const PLACES = Object.entries(PLACES_JSON)
  .filter(([, p]) => p.gmaps_url)
  .map(([name, p]) => ({ name, url: p.gmaps_url }));

const sleep = ms => new Promise(r => setTimeout(r, ms));
const fmt = ms => `${(ms / 1000).toFixed(0)}s`;

function langTally(reviews) {
  const t = {};
  for (const r of reviews) {
    if (!r.review?.text) continue;
    const k = r.review.language || "(unknown)";
    t[k] = (t[k] || 0) + 1;
  }
  return Object.entries(t).sort((a, b) => b[1] - a[1]);
}

async function main() {
  const args = process.argv.slice(2);
  const replace = args.includes("--replace");
  const requested = args.filter(a => a !== "--replace");

  let results = [];
  if (fs.existsSync(OUT)) results = JSON.parse(fs.readFileSync(OUT, "utf8"));
  const byName = new Map(results.map(p => [p.name, p]));

  const todo = requested.length
    ? PLACES.filter(p => requested.includes(p.name))
    : PLACES.filter(p => !byName.has(p.name));

  if (requested.length) {
    const unknown = requested.filter(n => !PLACES.some(p => p.name === n));
    if (unknown.length) console.log(`Unknown place name(s) ignored: ${unknown.join(", ")}`);
  }

  if (todo.length === 0) {
    console.log("Nothing to scrape. Pass place names to top up existing ones.");
    console.log(`Known places: ${PLACES.map(p => p.name).join(", ")}`);
    return;
  }

  console.log(`Scraping ${todo.length} place(s): ${todo.map(p => p.name).join(", ")}`);
  console.log(`Config: ${MAX_PAGES} pages max, ${DELAY_MS}-${DELAY_MS + JITTER_MS}ms between pages`);
  if (replace) console.log(`Mode: REPLACE — existing reviews for these places will be discarded\n`);
  else console.log("");

  const warningsByPlace = [];

  for (const place of todo) {
    console.log("=".repeat(70));
    console.log(`${place.name}`);
    console.log("=".repeat(70));

    let last = 0;
    const result = await fetchAllReviews({
      url: place.url,
      sortType: "newest",
      maxPages: MAX_PAGES,
      delayMs: DELAY_MS,
      jitterMs: JITTER_MS,
      onProgress: ev => {
        if (ev.type === "retry") {
          console.log(`  ! page ${ev.page} failed (${ev.error}); waiting ${fmt(ev.waitMs)} before retry`);
        } else if (ev.page - last >= 10 || ev.page === 1) {
          last = ev.page;
          console.log(`  page ${ev.page}: ${ev.total} reviews so far`);
        }
      },
    });

    console.log(`  fetched ${result.reviews.length} raw entries over ${result.pages} pages in ${fmt(result.elapsedMs)}`);
    console.log(`  stop reason: ${result.stopReason}`);

    // Structural check before we trust the slot map.
    const v = validateSlots(result.reviews);
    if (!v.ok) {
      const failed = v.checks.filter(c => !c.pass);
      console.log(`  !! SLOT VALIDATION FAILED (${failed.length} check(s)) — Google may have changed its format:`);
      for (const c of failed) console.log(`     - ${c.name}: ${c.detail}`);
      warningsByPlace.push(`${place.name}: slot validation failed`);
    }

    const parsed = parseRawReviews(result.reviews);

    const warnings = assessCompleteness(result, MAX_PAGES);
    for (const w of warnings) {
      console.log(`  !! ${w}`);
      warningsByPlace.push(`${place.name}: ${w}`);
    }

    // Merge by review_id, or start clean when replacing old-format data.
    const entry = byName.get(place.name) || {
      name: place.name,
      url: place.url,
      reviews: [],
    };
    if (replace && entry.reviews.length) {
      console.log(`  discarding ${entry.reviews.length} stored review(s)`);
      entry.reviews = [];
    }
    const seen = new Set(entry.reviews.map(r => r.review_id).filter(Boolean));
    let added = 0;
    for (const r of parsed) {
      if (r.review_id && !seen.has(r.review_id)) {
        entry.reviews.push(r);
        seen.add(r.review_id);
        added++;
      }
    }
    entry.scraped_at = new Date().toISOString();
    entry.last_stop_reason = result.stopReason;
    entry.last_pages = result.pages;

    if (!byName.has(place.name)) {
      results.push(entry);
      byName.set(place.name, entry);
    }

    const withText = entry.reviews.filter(r => r.review?.text).length;
    console.log(`  parsed ${parsed.length}, added ${added} new -> ${entry.reviews.length} total (${withText} with text)`);
    console.log(`  languages: ${langTally(entry.reviews).map(([k, v]) => `${k}=${v}`).join("  ")}`);

    fs.mkdirSync(path.dirname(OUT), { recursive: true });
    fs.writeFileSync(OUT, JSON.stringify(results, null, 2), "utf8");
    console.log(`  saved`);

    if (todo.indexOf(place) < todo.length - 1) {
      const wait = PLACE_PAUSE_MS[0] + Math.random() * (PLACE_PAUSE_MS[1] - PLACE_PAUSE_MS[0]);
      console.log(`\n  pausing ${fmt(wait)} before the next place...\n`);
      await sleep(wait);
    }
  }

  const total = results.reduce((s, p) => s + p.reviews.length, 0);
  console.log("\n" + "=".repeat(70));
  console.log(`Done. ${results.length} places, ${total} reviews total.`);
  if (warningsByPlace.length) {
    console.log(`\nWARNINGS (${warningsByPlace.length}) — review these before trusting the data:`);
    for (const w of warningsByPlace) console.log(`  - ${w}`);
  } else {
    console.log("No completeness warnings.");
  }
}

main().catch(err => {
  console.error("Fatal:", err);
  process.exit(1);
});
