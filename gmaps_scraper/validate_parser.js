/**
 * validate_parser.js — check that our slot map holds across places, and show
 * what our parser recovers that the package's own parser drops.
 *
 * Run: node validate_parser.js
 */
const { scraper } = require("google-maps-review-scraper");
const { parseRawReviews, validateSlots } = require("./parseRaw.js");

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

const PAGES = 3; // ~30 reviews per place — enough to hit textful + photo reviews

(async () => {
  for (const place of PLACES) {
    console.log("\n" + "█".repeat(78));
    console.log(`█  ${place.name}`);
    console.log("█".repeat(78));

    let raw;
    try {
      raw = await scraper({ url: place.url, sort_type: "newest", pages: PAGES, clean: false });
    } catch (e) {
      console.error(`  FETCH FAILED: ${e.message}`);
      continue;
    }

    // ── slot validation ─────────────────────────────────────────────────────
    const v = validateSlots(raw);
    console.log(`\n── SLOT VALIDATION (${v.sampled} reviews) ──`);
    for (const c of v.checks) {
      console.log(`  ${c.pass ? "PASS" : "FAIL"}  ${c.name}`);
      console.log(`        ${c.detail}`);
    }
    console.log(`\n  OVERALL: ${v.ok ? "ALL CHECKS PASS" : "SOME CHECKS FAILED"}`);

    // ── our parser vs package parser ────────────────────────────────────────
    const ours = parseRawReviews(raw);
    let theirs = [];
    try {
      theirs = await scraper({ url: place.url, sort_type: "newest", pages: PAGES, clean: true });
    } catch (e) {
      console.error(`  (package parser failed: ${e.message})`);
    }

    console.log(`\n── COUNTS ──`);
    console.log(`  our parser:     ${ours.length} reviews`);
    console.log(`  package parser: ${theirs.length} reviews`);

    const withText = a => a.filter(r => r.review?.text).length;
    const withLang = a => a.filter(r => r.review?.language).length;
    const withPhotos = a => a.filter(r => (r.images || []).length > 0).length;

    console.log(`\n── FIELD RECOVERY ──`);
    console.log(`  ${"field".padEnd(26)}${"ours".padEnd(10)}package`);
    console.log(`  ${"-".repeat(46)}`);
    console.log(`  ${"reviews with text".padEnd(26)}${String(withText(ours)).padEnd(10)}${withText(theirs)}`);
    console.log(`  ${"reviews with language".padEnd(26)}${String(withLang(ours)).padEnd(10)}${withLang(theirs)}`);
    console.log(`  ${"reviews with photos".padEnd(26)}${String(withPhotos(ours)).padEnd(10)}${withPhotos(theirs)}`);
    const authStats = ours.filter(r => r.author.review_count !== null).length;
    console.log(`  ${"author review_count".padEnd(26)}${String(authStats).padEnd(10)}0  (not parsed)`);
    const authPhotos = ours.filter(r => r.author.photo_count !== null).length;
    console.log(`  ${"author photo_count".padEnd(26)}${String(authPhotos).padEnd(10)}0  (not parsed)`);
    const trans = ours.filter(r => r.review.text_translated).length;
    console.log(`  ${"translation available".padEnd(26)}${String(trans).padEnd(10)}0  (not parsed)`);

    // ── language comparison ─────────────────────────────────────────────────
    const tally = arr => {
      const t = {};
      for (const r of arr) {
        const k = r.review?.language || "(null)";
        t[k] = (t[k] || 0) + 1;
      }
      return t;
    };
    console.log(`\n── LANGUAGE DISTRIBUTION ──`);
    console.log(`  ours:    ${JSON.stringify(tally(ours))}`);
    console.log(`  package: ${JSON.stringify(tally(theirs))}`);

    const srcTally = {};
    for (const r of ours) {
      const k = r.review.language_source || "(no text)";
      srcTally[k] = (srcTally[k] || 0) + 1;
    }
    console.log(`  our language source: ${JSON.stringify(srcTally)}`);

    // ── sample record ───────────────────────────────────────────────────────
    const sample = ours.find(r => r.review.text && r.author.review_count) || ours[0];
    if (sample) {
      console.log(`\n── SAMPLE RECORD (ours) ──`);
      console.log(`  review_id:      ${sample.review_id.slice(0, 40)}…`);
      console.log(`  rating:         ${sample.review.rating}`);
      console.log(`  language:       ${sample.review.language}  (${sample.review.language_source})`);
      console.log(`  author:         ${sample.author.name}  id=${sample.author.id}`);
      console.log(`  author reviews: ${sample.author.review_count}`);
      console.log(`  author photos:  ${sample.author.photo_count}`);
      console.log(`  n_photos:       ${sample.n_photos}`);
      console.log(`  published:      ${sample.time.published}  (${sample.time.published_relative})`);
      console.log(`  text:           ${(sample.review.text || "").slice(0, 90)}…`);
      if (sample.review.text_translated)
        console.log(`  translated:     ${sample.review.text_translated.slice(0, 90)}…`);
    }

    // ── image structure, if any review has photos ───────────────────────────
    const withImg = ours.find(r => r.images.length > 0);
    if (withImg) {
      console.log(`\n── IMAGE STRUCTURE (review with ${withImg.images.length} photo(s)) ──`);
      console.log(`  ${JSON.stringify(withImg.images[0]).slice(0, 200)}`);
    } else {
      console.log(`\n── IMAGE STRUCTURE: no review in this sample has photos ──`);
    }

    await new Promise(r => setTimeout(r, 4000));
  }
})().catch(e => {
  console.error("FATAL:", e);
  process.exit(1);
});
