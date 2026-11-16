/**
 * topup.js — Scrape extra reviews for places that need more non-Korean text reviews.
 * Merges new reviews into the existing gmaps_reviews_raw.json (dedup by review_id).
 *
 * Run: node topup.js
 */
const { scraper } = require("google-maps-review-scraper");
const fs   = require("fs");
const path = require("path");

const OUT   = path.join(__dirname, "..", "data", "gmaps_reviews_raw.json");
const PAGES = 20;  // ~200 reviews — plenty to find 3 more non-Korean ones

const TOPUP_PLACES = [
  { name: "홍대거리",     url: "https://www.google.com/maps/place/Hongdae+Street/data=!3m1!4b1!4m4!3m3!1s0x357c98c52a22c0eb:0xd5c6adb2b4dc943a!16s%2Fg%2F11bwm5q2sv!20s8Q98HW4G%2BF2FRF7H?entry=ttu&g_ep=EgoyMDI2MDkyMy4wIKXMDSoASAFQAw%3D%3D" },
  { name: "북촌한옥마을", url: "https://www.google.com/maps/place/Bukchon+Hanok+Village/data=!3m1!4b1!4m4!3m3!1s0x357ca2daaff8c14f:0xcdbcbaa9ffc9e59a!16s%2Fm%2F043pdws!20s8Q98HXJM%2BHXPMXM3?entry=ttu&g_ep=EgoyMDI2MDkyMy4wIKXMDSoASAFQAw%3D%3D" },
];

async function main() {
  const allResults = JSON.parse(fs.readFileSync(OUT, "utf8"));

  for (const place of TOPUP_PLACES) {
    console.log(`\nScraping extra reviews: ${place.name} (${PAGES} pages)`);

    let fresh;
    try {
      fresh = await scraper({ url: place.url, sort_type: "newest", pages: PAGES, clean: true });
      console.log(`  Fetched: ${fresh.length} reviews`);
    } catch (err) {
      console.error(`  ERROR: ${err.message}`);
      continue;
    }

    // Merge into existing entry for this place
    const entry = allResults.find(p => p.name === place.name);
    if (!entry) {
      console.log(`  Place not found in existing data — skipping`);
      continue;
    }

    const existingIds = new Set(entry.reviews.map(r => r.review_id).filter(Boolean));
    let added = 0;
    for (const r of fresh) {
      if (!existingIds.has(r.review_id)) {
        entry.reviews.push(r);
        existingIds.add(r.review_id);
        added++;
      }
    }
    console.log(`  Added ${added} new unique reviews (total now: ${entry.reviews.length})`);

    // Pause between places
    if (TOPUP_PLACES.indexOf(place) < TOPUP_PLACES.length - 1) {
      const wait = Math.floor(Math.random() * 5000) + 5000;
      console.log(`  Waiting ${(wait/1000).toFixed(1)}s...`);
      await new Promise(r => setTimeout(r, wait));
    }
  }

  fs.writeFileSync(OUT, JSON.stringify(allResults, null, 2), "utf8");
  const total = allResults.reduce((s, p) => s + p.reviews.length, 0);
  console.log(`\nSaved: ${OUT}`);
  console.log(`Total reviews across all places: ${total}`);
}

main().catch(err => { console.error("Fatal:", err); process.exit(1); });
