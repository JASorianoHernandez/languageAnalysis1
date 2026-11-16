/**
 * topup_gwangjang.js — Extra reviews for 광장시장 to reach ≥30 English reviews.
 * Merges into existing gmaps_reviews_raw.json (dedup by review_id).
 *
 * Run: node topup_gwangjang.js
 */
const { scraper } = require("google-maps-review-scraper");
const fs   = require("fs");
const path = require("path");

const OUT   = path.join(__dirname, "..", "data", "gmaps_reviews_raw.json");
const PAGES = 20;  // ~200 reviews

const PLACE = {
  name: "광장시장",
  url:  "https://www.google.com/maps/place/Gwangjang+Market/data=!3m1!4b1!4m4!3m3!1s0x357ca2ed7e74759b:0xd656a34831089f44!16s%2Fm%2F012r1x6q!20s8Q98HXCX%2B2R9FMCG?entry=ttu&g_ep=EgoyMDI2MDkyMy4wIKXMDSoASAFQAw%3D%3D",
};

async function main() {
  const allResults = JSON.parse(fs.readFileSync(OUT, "utf8"));

  console.log(`Scraping extra reviews: ${PLACE.name} (${PAGES} pages)`);

  let fresh;
  try {
    fresh = await scraper({ url: PLACE.url, sort_type: "newest", pages: PAGES, clean: true });
    console.log(`  Fetched: ${fresh.length} reviews`);
  } catch (err) {
    console.error(`  ERROR: ${err.message}`);
    process.exit(1);
  }

  const entry = allResults.find(p => p.name === PLACE.name);
  if (!entry) {
    console.error("Place not found in existing JSON");
    process.exit(1);
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

  fs.writeFileSync(OUT, JSON.stringify(allResults, null, 2), "utf8");
  const total = allResults.reduce((s, p) => s + p.reviews.length, 0);
  console.log(`\nSaved: ${OUT}`);
  console.log(`Total reviews across all places: ${total}`);
}

main().catch(err => { console.error("Fatal:", err); process.exit(1); });
