/**
 * parseRaw.js — our own parser for Google Maps BOQ review payloads.
 *
 * The `google-maps-review-scraper` package's built-in parser (clean:true) drops
 * fields Google actually sends: the author's lifetime review/photo counts, the
 * reliable original-language code, and the auto-translation. We fetch with
 * clean:false and parse the nested arrays ourselves.
 *
 * Slot map (verified against 광안리해수욕장 and 해운대해수욕장):
 *   [1]      rating (1-5)
 *   [2]      [relative_time, ?, epoch_ms]
 *   [3]      [name, avatar_url, contrib_url, review_count, photo_count, [?, ?]]
 *   [5]      review_id
 *   [12]     review permalink
 *   [26]     original language code ('' when the review is in the display language)
 *   [27]     original text
 *   [35]     images
 *   [36]     original language display name
 *   [37]     text translated into the display language
 *   [41]     translation target language name
 *
 * Slot positions are Google's internal format and can shift without notice, so
 * validateSlots() must pass before a scrape is trusted.
 */

const DISPLAY_LANG = "ko"; // requests are made with hl=ko-KR

function at(arr, ...idx) {
  let cur = arr;
  for (const i of idx) {
    if (!Array.isArray(cur) || i >= cur.length) return undefined;
    cur = cur[i];
  }
  return cur;
}

const str = v => (typeof v === "string" ? v : "");
const num = v => (typeof v === "number" ? v : null);

/** Unwrap the nested page payload down to the array of review entries. */
function toReviewList(raw) {
  let cur = raw;
  while (Array.isArray(cur) && cur.length === 1 && Array.isArray(cur[0])) cur = cur[0];
  return Array.isArray(cur) ? cur : [];
}

/** A raw entry looks like an image when its first element is a Google-hosted URL. */
function isImageEntry(item) {
  if (!Array.isArray(item) || typeof item[0] !== "string") return false;
  const u = item[0];
  if (u.includes("googleusercontent")) return true;
  return (u.startsWith("//") || u.startsWith("http")) && !u.includes("gstatic.com");
}

/** Index of the trailing ["Google", …] marker that closes the review body. */
function googleMarkerIndex(rev) {
  for (let i = rev.length - 1; i >= 0; i--) {
    if (Array.isArray(rev[i]) && rev[i][0] === "Google") return i;
  }
  return rev.length;
}

/**
 * Images sit in a sub-array at a position that shifts per review, so scan the
 * body range rather than reading a fixed slot.
 */
function parseImages(rev) {
  const until = googleMarkerIndex(rev);
  for (let i = 6; i < until; i++) {
    const el = rev[i];
    if (!Array.isArray(el) || el.length === 0) continue;
    const entries = el.filter(isImageEntry);
    if (entries.length === 0) continue;
    return entries.map(im => {
      const out = { id: str(at(im, 3)), url: str(at(im, 0)) };
      // Google sometimes carries [width, height] alongside the URL.
      const dims = at(im, 1);
      if (Array.isArray(dims) && typeof dims[0] === "number" && typeof dims[1] === "number") {
        out.width = dims[0];
        out.height = dims[1];
      }
      return out;
    });
  }
  return [];
}

function parseOne(rev) {
  if (!Array.isArray(rev)) return null;

  const rating = num(at(rev, 1));
  if (rating === null) return null;

  const text = str(at(rev, 27)).trim();

  // Google only reports an original-language code when it had to translate.
  // A review with text but no code was already written in the display language.
  const langCode = str(at(rev, 26)).trim();
  let language = null;
  if (text) language = langCode || DISPLAY_LANG;

  const contribUrl = str(at(rev, 3, 2));
  const idMatch = contribUrl.match(/\/contrib\/(\d+)/);

  const images = parseImages(rev);

  return {
    review_id: str(at(rev, 5)),
    time: {
      published: str(at(rev, 2, 2)) || null,
      published_relative: str(at(rev, 2, 0)) || null,
      last_edited: null,
    },
    author: {
      name: str(at(rev, 3, 0)) || "A Google User",
      profile_url: str(at(rev, 3, 1)),
      url: contribUrl,
      id: idMatch ? idMatch[1] : "Unknown",
      review_count: num(at(rev, 3, 3)),
      photo_count: num(at(rev, 3, 4)),
    },
    review: {
      rating,
      text: text || null,
      language,
      language_source: text ? (langCode ? "google" : "inferred_display_lang") : null,
      text_translated: str(at(rev, 37)).trim() || null,
      translated_to: str(at(rev, 41)).trim() || null,
    },
    images,
    n_photos: images.length,
    permalink: str(at(rev, 12)) || null,
    source: "Google Local Search Panel (own parser)",
    response: null,
  };
}

/**
 * Check the structural assumptions above against a fetched payload.
 * Returns { ok, checks, sampled } — never throws, so the caller decides.
 */
function validateSlots(raw) {
  const revs = toReviewList(raw);
  const checks = [];
  const add = (name, pass, detail) => checks.push({ name, pass, detail });

  if (revs.length === 0) {
    add("payload has reviews", false, "unwrapped list is empty");
    return { ok: false, checks, sampled: 0 };
  }

  const ratings = revs.map(r => at(r, 1));
  add(
    "[1] is a 1-5 rating",
    ratings.every(v => typeof v === "number" && v >= 1 && v <= 5),
    `values: ${JSON.stringify(ratings)}`
  );

  const names = revs.map(r => at(r, 3, 0));
  add(
    "[3][0] is author name (string)",
    names.every(v => typeof v === "string" && v.length > 0),
    `e.g. ${JSON.stringify(names[0])}`
  );

  const contribs = revs.map(r => str(at(r, 3, 2)));
  add(
    "[3][2] is a /contrib/ URL",
    contribs.every(v => v.includes("/contrib/")),
    `e.g. ${contribs[0].slice(0, 60)}`
  );

  const rc = revs.map(r => at(r, 3, 3));
  const pc = revs.map(r => at(r, 3, 4));
  add(
    "[3][3] author review_count is int",
    rc.every(v => Number.isInteger(v) && v >= 0),
    `values: ${JSON.stringify(rc)}`
  );
  add(
    "[3][4] author photo_count is int",
    pc.every(v => Number.isInteger(v) && v >= 0),
    `values: ${JSON.stringify(pc)}`
  );
  add(
    "author counts vary across reviews (not a constant)",
    new Set(rc).size > 1,
    `${new Set(rc).size} distinct values in ${rc.length} reviews`
  );

  const ids = revs.map(r => str(at(r, 5)));
  add(
    "[5] review_id non-empty and unique",
    ids.every(v => v.length > 10) && new Set(ids).size === ids.length,
    `${new Set(ids).size} unique of ${ids.length}`
  );

  const epochs = revs.map(r => str(at(r, 2, 2)));
  add(
    "[2][2] is an epoch-ms string",
    epochs.every(v => /^\d{13}$/.test(v)),
    `e.g. ${epochs[0]}`
  );

  // BCP 47 tags: 2-3 letter language, optional script or region suffix, where
  // the region may be numeric ("zh-Hant", "en-GB", "es-419").
  const langs = revs.map(r => str(at(r, 26)));
  const badLangs = [...new Set(langs)].filter(
    v => v !== "" && !/^[a-z]{2,3}(-[A-Za-z0-9]{2,4})?$/.test(v)
  );
  add(
    "[26] is a language code or empty",
    badLangs.length === 0,
    badLangs.length
      ? `unexpected: ${JSON.stringify(badLangs)}`
      : `${new Set(langs).size} distinct values, all well-formed`
  );

  // The key inference: text present + empty [26] should mean Korean text.
  const inferred = revs.filter(r => str(at(r, 27)).trim() && !str(at(r, 26)).trim());
  const hangul = /[가-힣]/;
  const inferredOk = inferred.filter(r => hangul.test(str(at(r, 27))));
  add(
    "text with empty [26] really is Korean",
    inferred.length === 0 || inferredOk.length === inferred.length,
    `${inferredOk.length}/${inferred.length} contain Hangul` +
      (inferred.length === 0 ? " (no such reviews in this sample)" : "")
  );

  const imgCounts = revs.map(r => parseImages(r).length);
  add(
    "images are found in at least one review",
    imgCounts.some(n => n > 0),
    `reviews with photos: ${imgCounts.filter(n => n > 0).length}/${revs.length}, ` +
      `max ${Math.max(...imgCounts)}`
  );

  return { ok: checks.every(c => c.pass), checks, sampled: revs.length };
}

function parseRawReviews(raw) {
  return toReviewList(raw).map(parseOne).filter(Boolean);
}

module.exports = { parseRawReviews, validateSlots, toReviewList };
