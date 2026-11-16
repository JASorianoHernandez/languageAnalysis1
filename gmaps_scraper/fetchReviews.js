/**
 * fetchReviews.js — throttled paginator for the Google Maps BOQ endpoint.
 *
 * The npm package's paginateReviews() fires every page back-to-back with no
 * delay (~7 req/s) and, when a page fails, silently returns whatever it had —
 * so a rate-limit looks identical to "this place has few reviews".
 *
 * This module adds:
 *   · a delay + jitter between pages
 *   · one backoff retry when a page fails
 *   · an explicit stopReason so callers can tell a natural end from a cut-off
 *
 * It reuses the package's URL builder and HTTP client so the request shape
 * stays identical to the upstream implementation.
 */

const boqEndpoint = require("google-maps-review-scraper/dist/boqEndpoint.js");
const clientMod = require("google-maps-review-scraper/dist/client.js");

const getBoqUrl = boqEndpoint.default || boqEndpoint;
const createClient = clientMod.createClient || clientMod.default?.createClient;

const SORT = { most_relevant: 1, newest: 2, highest_rating: 3, lowest_rating: 4 };

const REVIEWS_PER_PAGE = 10;

/** Stop reasons that mean the data is incomplete through no fault of the place. */
const TRUNCATING = new Set(["http_error", "token_repeat", "empty_page", "parse_error"]);

const sleep = ms => new Promise(r => setTimeout(r, ms));

function placeIdFromUrl(url) {
  const m = [...url.matchAll(/!1s([a-zA-Z0-9_:]+)!/g)];
  if (!m[0]?.[1]) throw new Error(`Could not extract place id from URL: ${url}`);
  return m[1]?.[1] ? m[1][1] : m[0][1];
}

/** Pull the review array and next-page token out of one raw BOQ response. */
function extractPage(data) {
  if (!Array.isArray(data) || data.length < 2) return null;
  const payload = data[1];
  if (!Array.isArray(payload) || payload.length <= 10 || !payload[10]) return null;
  const node = payload[10];
  if (!Array.isArray(node) || node.length < 3 || !Array.isArray(node[2])) return null;
  return {
    reviews: node[2],
    nextToken: node.length > 6 && typeof node[6] === "string" ? node[6] : "",
  };
}

async function fetchOnePage({ client, placeId, sortOrder, paginationToken }) {
  const res = await client.fetch(getBoqUrl({ placeId, sortOrder, paginationToken }));
  if (!res.ok) {
    const err = new Error(`HTTP ${res.status} ${res.statusText}`);
    err.status = res.status;
    throw err;
  }
  const text = await res.text();
  const parts = text.split(")]}'");
  const rawJson = parts.length > 1 ? parts[1] : parts[0];
  if (!rawJson) throw new Error("No JSON payload in response");
  return JSON.parse(rawJson);
}

/**
 * Fetch up to `maxPages` pages of reviews, pausing between requests.
 *
 * @returns {Promise<{reviews: any[], pages: number, stopReason: string,
 *                    truncated: boolean, error: string|null, elapsedMs: number}>}
 */
async function fetchAllReviews({
  url,
  sortType = "newest",
  maxPages = 100,
  delayMs = 1500,
  jitterMs = 1000,
  retryWaitMs = 30000,
  onProgress = null,
}) {
  const sortOrder = SORT[sortType];
  if (!sortOrder) throw new Error(`Invalid sortType: ${sortType}`);

  const placeId = placeIdFromUrl(url);
  const client = createClient({ proxy: {} });
  const t0 = Date.now();

  const reviews = [];
  let pages = 0;
  let token = "";
  let stopReason = "target_reached";
  let error = null;
  let retriedOnce = false;

  while (pages < maxPages) {
    let data;
    try {
      data = await fetchOnePage({ client, placeId, sortOrder, paginationToken: token });
    } catch (e) {
      // One backoff retry — a transient 429 usually clears after a pause.
      if (!retriedOnce) {
        retriedOnce = true;
        if (onProgress) onProgress({ type: "retry", page: pages + 1, error: e.message, waitMs: retryWaitMs });
        await sleep(retryWaitMs);
        try {
          data = await fetchOnePage({ client, placeId, sortOrder, paginationToken: token });
        } catch (e2) {
          stopReason = "http_error";
          error = e2.message;
          break;
        }
      } else {
        stopReason = "http_error";
        error = e.message;
        break;
      }
    }

    let page;
    try {
      page = extractPage(data);
    } catch (e) {
      stopReason = "parse_error";
      error = e.message;
      break;
    }

    if (!page) {
      stopReason = "parse_error";
      error = "response did not match the expected page shape";
      break;
    }
    if (page.reviews.length === 0) {
      stopReason = "empty_page";
      break;
    }

    reviews.push(...page.reviews);
    pages++;
    if (onProgress) onProgress({ type: "page", page: pages, got: page.reviews.length, total: reviews.length });

    if (!page.nextToken) {
      stopReason = "no_more_pages";
      break;
    }
    if (page.nextToken === token) {
      stopReason = "token_repeat";
      break;
    }
    token = page.nextToken;

    if (pages < maxPages) {
      await sleep(delayMs + Math.random() * jitterMs);
    }
  }

  return {
    reviews,
    pages,
    stopReason,
    truncated: TRUNCATING.has(stopReason),
    error,
    elapsedMs: Date.now() - t0,
  };
}

/**
 * Flag a result that looks cut short: an explicit truncating stopReason, or a
 * page count that fell well below the request while claiming a natural end.
 */
function assessCompleteness(result, maxPages) {
  const warnings = [];
  if (result.truncated) {
    warnings.push(`stopped early: ${result.stopReason}${result.error ? ` (${result.error})` : ""}`);
  }
  const expected = result.pages * REVIEWS_PER_PAGE;
  if (result.reviews.length < expected * 0.5 && result.pages > 1) {
    warnings.push(`only ${result.reviews.length} reviews across ${result.pages} pages (expected ~${expected})`);
  }
  if (result.stopReason === "target_reached" && result.pages === maxPages) {
    warnings.push(`hit the ${maxPages}-page limit — more reviews are likely available`);
  }
  return warnings;
}

module.exports = { fetchAllReviews, assessCompleteness, placeIdFromUrl, SORT };
