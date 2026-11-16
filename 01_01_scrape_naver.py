"""
01_01_scrape_naver.py — Scrape reviews from Naver Place (네이버 플레이스).

For each place:
  1. Opens the mobile Naver Place review page
  2. Clicks 더보기 (load more) up to MAX_PAGES times
  3. Extracts all visible reviews
  4. Saves raw data to data/naver_reviews_raw.json

Fields extracted per review:
  - nickname, profile_url        : reviewer (personal data: never leaves data/)
  - text, rating, tags           : review body, stars (only on some reviews), keyword tags
  - visit_keywords               : purpose, companions, waiting time, reservation
  - visit_date                   : visible visit date ("9.24.목"); parsed downstream
  - visit_date_full              : Naver's hidden full date, unreliable (often +1 month)
  - visit_count, verification    : n-th visit, how it was verified (영수증, 예약, ...)
  - reactions, reaction_types    : people who reacted (도움돼요, 멋져요, ...)
  - user_reviews/photos/followers: reviewer lifetime stats
  - n_photos                     : photos attached to the review

Setup (one time):
  pip install selenium webdriver-manager

Run:
  C:\\Users\\crono\\anaconda3\\python.exe 01_01_scrape_naver.py              places not yet scraped
  C:\\Users\\crono\\anaconda3\\python.exe 01_01_scrape_naver.py 홍대거리 광장시장
        re-scrape the named places from scratch (replaces their stored reviews)

NOTE: If selectors break (Naver updates UI), run the script with
      DEBUG=True to print the raw HTML and find the new class names.
"""

import sys
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
import json, time, re, random, sys
from pathlib import Path
from datetime import datetime

import undetected_chromedriver as uc
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    NoSuchElementException, TimeoutException, ElementClickInterceptedException
)

ROOT    = Path(__file__).parent
OUT     = ROOT / "data" / "naver_reviews_raw.json"
DEBUG   = False
MAX_CLICKS = 60      # "load more" iterations per place (~10 reviews each, ~10 s each)
WAIT_SEC   = 8       # seconds to wait after each scroll for XHR to complete
# Review order. None keeps Naver's default order, which is how the existing data was
# collected; "recent" or "best" clicks that sort tab first. Use the same setting for
# every place so samples stay comparable.
SORT = None

# ── Places ────────────────────────────────────────────────────────────────────
# Single source of truth: places.json (edit there -- paste a naver_id and this
# list picks it up). A place with no naver_id yet (e.g. 종묘) is left out rather
# than sent to a URL that 404s; see places_data.py's docstring for the schema.
from places_data import NAVER_PLACES as PLACES

def review_url(naver_id):
    # type=photoView is required to load the review list layout on Naver mobile
    return f"https://m.place.naver.com/place/{naver_id}/review/visitor?type=photoView"

# ── Selectors (update here if Naver changes its HTML) ─────────────────────────
SEL_REVIEW_BLOCK  = "li.pui__X35jYm"          # each review container
SEL_NICKNAME      = "span.pui__uslU0d"         # reviewer nickname
SEL_TEXT          = "span.pui__xtsTC7"         # review text body
SEL_VISIT_DATE    = "span.pui__gfuIDb"         # visit date / visit count
SEL_TAGS          = "span.pui__jhpEyP"         # experience tags
SEL_USER_REVIEWS  = "span.pui__wQyn6b"         # total reviews by this user
SEL_PROFILE_LINK  = "a.pui__Jk7COe"            # profile link
SEL_MORE_BUTTON   = "a.pui__vUWfSl"            # 더보기 button

# ── Helpers ───────────────────────────────────────────────────────────────────
def safe_text(el, selector):
    try:
        return el.find_element(By.CSS_SELECTOR, selector).text.strip()
    except NoSuchElementException:
        return None

def safe_texts(el, selector):
    try:
        return [e.text.strip() for e in el.find_elements(By.CSS_SELECTOR, selector) if e.text.strip()]
    except NoSuchElementException:
        return []

def safe_attr(el, selector, attr):
    try:
        return el.find_element(By.CSS_SELECTOR, selector).get_attribute(attr)
    except NoSuchElementException:
        return None

def parse_review(el):
    visit_raw  = safe_text(el, SEL_VISIT_DATE) or ""
    visit_date = None
    visit_count = None
    # format: "2025.03  ·  2번째 방문" or just "2025.03"
    parts = [p.strip() for p in visit_raw.split("·")]
    if parts:
        visit_date = parts[0].strip()
    if len(parts) > 1:
        m = re.search(r"(\d+)번째", parts[1])
        if m:
            visit_count = int(m.group(1))

    user_reviews_raw = safe_text(el, SEL_USER_REVIEWS) or ""
    m2 = re.search(r"(\d+)", user_reviews_raw)
    user_reviews = int(m2.group(1)) if m2 else None

    return {
        "nickname":     safe_text(el, SEL_NICKNAME),
        "text":         safe_text(el, SEL_TEXT),
        "visit_date":   visit_date,
        "visit_count":  visit_count,
        "tags":         safe_texts(el, SEL_TAGS),
        "user_reviews": user_reviews,
        "profile_url":  safe_attr(el, SEL_PROFILE_LINK, "href"),
    }

# ── Driver setup ──────────────────────────────────────────────────────────────
def make_driver():
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=390,844")
    options.add_argument("--lang=ko-KR")
    options.add_argument(
        "user-agent=Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
    )
    return uc.Chrome(options=options, version_main=153)

# ── Main ──────────────────────────────────────────────────────────────────────
print("Starting Naver Place review scraper...\n")

MIN_REVIEWS = 25    # skip a place only if it already has this many reviews
                    # (25 keeps 홍대거리's 31 reviews from being discarded on re-run)

# Load existing results; skip places that already have enough reviews
existing = {}
if OUT.exists():
    with open(OUT, encoding="utf-8") as f:
        for p in json.load(f):
            existing[p["name"]] = p

# Place names given on the command line are re-scraped from scratch, replacing
# whatever is stored for them. With no arguments, places that already have
# enough reviews are left alone.
forced = set(sys.argv[1:])
if forced:
    unknown = forced - {p["name"] for p in PLACES}
    if unknown:
        print(f"Unknown place name(s): {', '.join(unknown)}")
        print(f"Known places: {', '.join(p['name'] for p in PLACES)}")
        exit(1)
    places_todo  = [p for p in PLACES if p["name"] in forced]
    all_results  = [p for name, p in existing.items() if name not in forced]
    print(f"Re-scraping (replacing existing data): {', '.join(forced)}")
else:
    skip = {name for name, p in existing.items() if len(p["reviews"]) >= MIN_REVIEWS}
    if skip:
        print(f"Skipping (already have ≥{MIN_REVIEWS} reviews): {', '.join(skip)}")
    places_todo = [p for p in PLACES if p["name"] not in skip]
    all_results = [p for name, p in existing.items() if name in skip]

if not places_todo:
    print("All places already have enough reviews. Nothing to do.")
    exit(0)
print(f"Places to scrape: {[p['name'] for p in places_todo]}\n")
driver = make_driver()

# Enable proper mobile touch emulation — without this Naver ignores wheel/keyboard scroll
driver.execute_cdp_cmd("Emulation.setDeviceMetricsOverride", {
    "width": 390, "height": 844, "deviceScaleFactor": 3,
    "mobile": True, "hasTouch": True,
    "screenOrientation": {"type": "portraitPrimary", "angle": 0}
})
driver.execute_cdp_cmd("Emulation.setTouchEmulationEnabled", {"enabled": True, "maxTouchPoints": 5})


def touch_swipe_down(drv, x=195, y_from=700, y_to=150, steps=15):
    """Simulate a finger swipe up (= scroll down) using CDP touch events."""
    drv.execute_cdp_cmd("Input.dispatchTouchEvent", {
        "type": "touchStart",
        "touchPoints": [{"x": x, "y": y_from, "id": 0, "radiusX": 1, "radiusY": 1, "force": 1.0}]
    })
    for s in range(1, steps + 1):
        y = y_from + (y_to - y_from) * s / steps
        drv.execute_cdp_cmd("Input.dispatchTouchEvent", {
            "type": "touchMove",
            "touchPoints": [{"x": x, "y": y, "id": 0, "radiusX": 1, "radiusY": 1, "force": 1.0}]
        })
        time.sleep(0.03)
    drv.execute_cdp_cmd("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})


# Inject fetch interceptor before any page loads.
# window.__APOLLO_STATE__ is a frozen SSR snapshot — only the first 10 reviews.
# New batches loaded by infinite scroll go to the in-memory Apollo cache (not that snapshot).
# We capture them by wrapping window.fetch instead.
FETCH_INTERCEPTOR = """
window._nr = [];
(function() {
    var _of = window.fetch;
    window.fetch = function(url, opts) {
        return _of.apply(this, arguments).then(function(resp) {
            resp.clone().json().then(function(data) {
                window._nr.push({url: String(url), data: data});
            }).catch(function(){});
            return resp;
        });
    };
})();
"""
driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": FETCH_INTERCEPTOR})


def extract_from_network(captured):
    """Walk captured fetch responses and pull out review objects."""
    reviews = []
    seen = set()

    def walk(obj):
        if isinstance(obj, dict):
            body = obj.get("body") or obj.get("text") or obj.get("contents") or ""
            if (isinstance(body, str) and len(body.strip()) >= 3 and
                    any(k in obj for k in ("visitDate", "rating", "visitCount", "votedKeywords"))):
                rid = str(obj.get("id") or obj.get("reviewId") or body[:30])
                if rid not in seen:
                    seen.add(rid)
                    author = obj.get("author") or {}
                    keywords = obj.get("votedKeywords") or []
                    reviews.append({
                        "nickname":    author.get("nickname") or author.get("name") or "" if isinstance(author, dict) else "",
                        "text":        body.strip(),
                        "visit_date":  obj.get("visitDate") or obj.get("created") or "",
                        "visit_count": obj.get("visitCount"),
                        "tags":        [k.get("name","") for k in keywords if isinstance(k, dict)],
                        "rating":      obj.get("rating"),
                        "language":    obj.get("language") or "",
                        "profile_url": (author.get("profileImageUrl") or "") if isinstance(author, dict) else "",
                    })
                return
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for item in obj:
                walk(item)

    for entry in captured:
        walk(entry.get("data", entry))
    return reviews


try:
    for place in places_todo:
        url = review_url(place["naver_id"])
        print(f"Scraping: {place['name']}  ({url})")
        driver.get(url)
        time.sleep(random.uniform(2.0, 4.0))

        # Click the visitor review sub-tab explicitly (the page defaults to blog reviews)
        # data-nlog-area="plc_rrv.rrvtab" is the <a> tag for 방문자 리뷰
        try:
            review_tab = WebDriverWait(driver, 8).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "a[data-nlog-area='plc_rrv.rrvtab']"))
            )
            review_tab.click()
            time.sleep(3.0)  # wait for visitor reviews to render
        except TimeoutException:
            pass  # tab not found — already on visitor reviews or different layout

        # Wait for visitor review footers (pui__QztK4Q) to actually appear in the DOM
        try:
            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.CSS_SELECTOR, ".pui__QztK4Q")) > 0
            )
        except TimeoutException:
            print("  WARNING: visitor review footers did not appear in 10s")

        if SORT in ("recent", "best"):
            try:
                sort_tab = WebDriverWait(driver, 8).until(EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, f"a[data-nlog-area='plc_rrv.sort{SORT}']")))
                sort_tab.click()
                time.sleep(3.0)
                print(f"  sorted by: {SORT}")
            except TimeoutException:
                print(f"  WARNING: sort tab '{SORT}' not found; using Naver's default order")

        if DEBUG:
            debug_path = ROOT / "data" / f"debug_{place['name']}.html"
            with open(debug_path, "w", encoding="utf-8") as dbf:
                dbf.write(driver.page_source)
            print(f"  DEBUG: HTML saved to {debug_path}")

        # Scroll using ActionChains wheel events — triggers Naver's IntersectionObserver
        # (pure JS scrollTop changes don't fire scroll events the observer listens to)
        def count_apollo_reviews():
            s = driver.execute_script("return window.__APOLLO_STATE__ || {}")
            return sum(
                1 for v in s.values()
                if isinstance(v, dict)
                and "VisitorReview" in v.get("__typename", "")
                and (v.get("body") or v.get("text") or "")
            )

        # Give keyboard focus without triggering a click event (avoid accidental navigation)
        driver.execute_script("document.body.focus()")
        time.sleep(0.5)

        # Naver uses a virtual DOM — only ~10 reviews rendered at a time.
        # We must extract each batch from the DOM before scrolling destroys it.
        DOM_JS = r"""
var items = [];
var seen = new Set();
// pui__QztK4Q is the footer div of each review (reactions + date).
// closest('li') is required: the footer sits 2-3 divs below the review <li>.
var footers = document.querySelectorAll('.pui__QztK4Q');
for (var footer of footers) {
    var li = footer.closest('li');
    if (!li || seen.has(li)) continue;
    seen.add(li);

    // Expand truncated review text first
    var expandBtn = li.querySelector('[data-pui-click-code="rvshowmore"]');
    if (expandBtn) { try { expandBtn.click(); } catch(e) {} }

    function txt(sel, root) {
        var el = (root || li).querySelector(sel);
        return el ? (el.textContent || '').trim() : '';
    }

    // ── Review text ───────────────────────────────────────────────────────
    // Two elements carry data-nlog-area="plc_rrv.rvshowmore": the body text and
    // the "더보기" button (class pui__wFzIYl). Take the one that is not the button.
    var text = '';
    var candidates = li.querySelectorAll('a[data-nlog-area="plc_rrv.rvshowmore"]');
    for (var c of candidates) {
        if (!c.classList.contains('pui__wFzIYl')) {
            text = (c.innerText || '').trim();
            break;
        }
    }
    // Naver only wraps the body in that anchor when the text is long enough to
    // need a "더보기" toggle, so short reviews have none. Fall back to stripping
    // the known structural blocks and keeping whatever remains.
    if (!text) {
        var clone = li.cloneNode(true);
        [
            '.pui__QztK4Q',                               // footer: date, reactions
            'a[data-nlog-area="plc_rrv.profile"]',        // profile block
            'span.pui__NMi-Dp',                           // nickname
            'span.pui__WN-kAf',                           // reviewer lifetime stats
            'a[data-nlog-area="plc_rrv.follow"]',         // follow button
            'div.pui__6abRMf',                            // rating number
            'span.pui__blind',                            // screen-reader labels
            'a[data-nlog-area="plc_rrv.visitkeywords"]',  // visit keywords
            'li.pui__jhpEyP',                             // experience tags
            'a[data-nlog-area="plc_rrv.keywordmore"]',    // tag overflow link
            'a.pui__wFzIYl'                               // 더보기 button
        ].forEach(function(sel) {
            clone.querySelectorAll(sel).forEach(function(el) { el.remove(); });
        });
        text = (clone.innerText || '').trim();
    }

    // ── Rating (div.pui__6abRMf holds the bare number; 별점/점 are sr-only) ──
    var ratingTxt = txt('div.pui__6abRMf');
    var rating = ratingTxt ? parseFloat(ratingTxt.replace(/[^\d.]/g, '')) : null;
    if (isNaN(rating)) rating = null;

    // ── Experience tags (li.pui__jhpEyP) ─────────────────────────────────
    var tags = [];
    li.querySelectorAll('li.pui__jhpEyP').forEach(function(t) {
        var v = (t.textContent || '').trim();
        if (v) tags.push(v);
    });

    // ── Structured visit keywords (purpose, companions, wait time) ────────
    var visitKeywords = [];
    var vkBlock = li.querySelector('a[data-nlog-area="plc_rrv.visitkeywords"]');
    if (vkBlock) {
        vkBlock.querySelectorAll('em').forEach(function(e) {
            var v = (e.textContent || '').trim();
            if (v) visitKeywords.push(v);
        });
    }

    // ── Reviewer identity + lifetime stats (span.pui__WN-kAf) ────────────
    var nickname = txt('span.pui__NMi-Dp');
    var userReviews = null, userPhotos = null, userFollowers = null;
    li.querySelectorAll('span.pui__WN-kAf').forEach(function(s) {
        var v = (s.textContent || '').trim();
        var m = v.match(/([\d,]+)/);
        if (!m) return;
        var num = parseInt(m[1].replace(/,/g, ''));
        if (v.indexOf('리뷰')   === 0) userReviews   = num;
        else if (v.indexOf('사진')   === 0) userPhotos    = num;
        else if (v.indexOf('팔로워') === 0) userFollowers = num;
    });

    var profileEl = li.querySelector('a[data-nlog-area="plc_rrv.profile"]');
    var profileUrl = profileEl ? (profileEl.getAttribute('href') || '') : '';

    // ── Reactions ─────────────────────────────────────────────────────────
    // The react button always carries a hidden "반응 남기기" label, so it cannot
    // tell zero from non-zero. The count of people who reacted is in the
    // reaction-list link ("<em>7</em>명"); it is absent when nobody reacted.
    var reactions = 0;
    var listEl = li.querySelector('a[data-nlog-area="plc_rrv.reactionlist"] em');
    if (listEl) {
        var rm = (listEl.textContent || '').replace(/,/g, '').match(/(\d+)/);
        reactions = rm ? parseInt(rm[1]) : 0;
    }
    // Reaction types shown on the button (e.g. 도움돼요, 멋져요, 가고 싶어요)
    var reactionTypes = [];
    li.querySelectorAll('a[data-nlog-area="plc_rrv.react"] img').forEach(function(im) {
        if (im.alt) reactionTypes.push(im.alt);
    });

    // ── Dates ─────────────────────────────────────────────────────────────
    // The visible date ("9.24.목", or "25.9.24.수" for earlier years) is correct.
    // The hidden full date next to it is Naver's own and is one month ahead in
    // about 40% of reviews, so it is kept only for reference; dates are parsed
    // from the visible one in 02_naver_build_dataset.py.
    var visitRoot = li.querySelector('.pui__QKE5Pr') || footer;
    var timeEl = visitRoot.querySelector('time');
    var visitDate = timeEl ? timeEl.textContent.trim() : '';
    var visitDateFull = '';
    visitRoot.querySelectorAll('span.pui__blind').forEach(function(s) {
        var v = (s.textContent || '').trim();
        if (/\d{4}년/.test(v)) visitDateFull = v;
    });

    var visitText = (visitRoot.innerText || visitRoot.textContent || '');
    var countMatch = visitText.match(/(\d+)번째\s*방문/);
    var visitCount = countMatch ? parseInt(countMatch[1]) : null;

    // How the visit was verified (영수증 = receipt, 예약 = reservation, ...)
    var verification = '';
    visitRoot.querySelectorAll('span.pui__gfuUIT').forEach(function(s) {
        var blind = s.querySelector('span.pui__blind');
        if (blind && (blind.textContent || '').indexOf('인증 수단') !== -1) {
            verification = (s.textContent || '').replace('인증 수단', '').trim();
        }
    });

    // ── Photos attached to THIS review (exclude profile pic + tag emoji) ──
    // Review photos are hosted on pup-review-phinf and may be <img> tags or CSS
    // backgrounds; reaction icons (/reactiontype/), emoji and the profile picture are
    // not photos. Count distinct photo URLs found either way.
    var photoUrls = new Set();
    li.querySelectorAll('img').forEach(function(im) {
        var src = im.currentSrc || im.src || im.getAttribute('data-src') || '';
        if (src.indexOf('pup-review-phinf') !== -1) photoUrls.add(src.split('?')[0]);
    });
    li.querySelectorAll('[style*="pup-review-phinf"]').forEach(function(el) {
        var m = (el.getAttribute('style') || '').match(/url\(["']?([^"')]+)/);
        if (m) photoUrls.add(m[1].split('?')[0]);
    });
    var nPhotos = photoUrls.size;

    // Keep every rendered review, including rating-or-tags-only ones with no
    // body. Dropping them here would also make the scroll loop's "no new
    // reviews" counter fire early and cut the run short.
    {
        items.push({
            text:            text,
            rating:          rating,
            tags:            tags,
            visit_keywords:  visitKeywords,
            nickname:        nickname,
            profile_url:     profileUrl,
            user_reviews:    userReviews,
            user_photos:     userPhotos,
            user_followers:  userFollowers,
            reactions:       reactions,
            reaction_types:  reactionTypes,
            n_photos:        nPhotos,
            visit_date:      visitDate,
            visit_date_full: visitDateFull,
            visit_count:     visitCount,
            verification:    verification,
            language:        'ko'
        });
    }
}
return items;
"""
        seen_keys = set()
        accumulated = []
        body = driver.find_element(By.TAG_NAME, "body")
        no_new_streak = 0

        def review_key(r):
            """Identify a review without relying on its text.

            Text alone fails twice: rating-or-tags-only reviews have none, and
            short ones like "좋아요" collide across different reviewers. The
            profile URL carries a per-user hash, so pairing it with the visit
            date and count separates reviewers and repeat visits.
            """
            # The same review is rendered with and without line breaks (and with a
            # "동영상" badge when it has a video), so the text part is normalized.
            text = re.sub(r"^(동영상\s*)+", "", (r.get("text") or "").strip())
            return (
                r.get("profile_url", ""),
                r.get("visit_date", ""),
                r.get("visit_count"),
                re.sub(r"[\W_]+", "", text)[:40],
            )

        # Debug: inspect DOM state
        if DEBUG:
            diag = driver.execute_script("""
var footers = document.querySelectorAll('.pui__QztK4Q');
// Find the scroll container by walking up from the first footer
var scrollContainer = null;
if (footers.length > 0) {
    var el = footers[0];
    while (el && el !== document.body) {
        var st = window.getComputedStyle(el);
        if (st.overflowY === 'auto' || st.overflowY === 'scroll') {
            scrollContainer = {tag: el.tagName, cls: el.className.substring(0,60),
                               scrollTop: el.scrollTop, scrollHeight: el.scrollHeight,
                               clientHeight: el.clientHeight};
            break;
        }
        el = el.parentElement;
    }
}
return {
    url: window.location.href,
    footers: footers.length,
    scrollContainer: scrollContainer
};
""")
            print(f"  DEBUG: url=...{diag['url'][-50:]}")
            print(f"  DEBUG: footers={diag['footers']}  scrollContainer={diag['scrollContainer']}")

        # Extract initial batch before any scrolling
        batch = driver.execute_script(DOM_JS)
        for r in batch:
            key = review_key(r)
            if key not in seen_keys:
                seen_keys.add(key)
                accumulated.append(r)
        print(f"    initial: {len(accumulated)} reviews")

        for i in range(MAX_CLICKS):
            # Find and click the "펼쳐서 더보기" (load more reviews) button
            # data-nlog-area="plc_rrv.more" appears after the last visible review
            more_btns = driver.find_elements(By.CSS_SELECTOR, "a[data-nlog-area='plc_rrv.more']")
            if more_btns:
                try:
                    driver.execute_script("arguments[0].scrollIntoView({block:'center'})", more_btns[0])
                    time.sleep(0.5)
                    more_btns[0].click()
                    if DEBUG:
                        print(f"    scroll {i+1}: clicked plc_rrv.more button")
                except Exception as e:
                    if DEBUG:
                        print(f"    scroll {i+1}: click failed ({e}), falling back to touch swipe")
                    touch_swipe_down(driver)
            else:
                # No more-button found — scroll to bottom to try to reveal it
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
                if DEBUG:
                    print(f"    scroll {i+1}: no plc_rrv.more button, scrolled to bottom")

            time.sleep(random.uniform(WAIT_SEC, WAIT_SEC + 3))  # wait for XHR + render

            batch = driver.execute_script(DOM_JS)
            new_n = 0
            for r in batch:
                key = review_key(r)
                if key not in seen_keys:
                    seen_keys.add(key)
                    accumulated.append(r)
                    new_n += 1
            print(f"    scroll {i+1}/{MAX_CLICKS}: +{new_n} new  (total {len(accumulated)})")

            if new_n == 0:
                no_new_streak += 1
                if no_new_streak >= 5:
                    print("    5 scrolls with no new reviews — stopping early")
                    break
            else:
                no_new_streak = 0

        reviews = accumulated
        print(f"  DOM accumulation done: {len(reviews)} unique reviews")

        # Fallback to Apollo State if DOM gave nothing
        if not reviews:
            print("  DOM empty — falling back to Apollo State (first 10 only)")
            apollo = driver.execute_script("return window.__APOLLO_STATE__ || {}")
            for val in apollo.values():
                if not isinstance(val, dict): continue
                if "VisitorReview" not in val.get("__typename", ""): continue
                text = val.get("body") or val.get("text") or ""
                if not text or len(text.strip()) < 3: continue
                author = val.get("author") or {}
                keywords = val.get("votedKeywords") or []
                reviews.append({
                    "nickname":    (author.get("nickname") or author.get("name") or "") if isinstance(author, dict) else "",
                    "text":        text.strip(),
                    "visit_date":  val.get("visitDate") or val.get("created") or "",
                    "visit_count": val.get("visitCount"),
                    "tags":        [k.get("name","") for k in keywords if isinstance(k, dict)],
                    "rating":      val.get("rating"),
                    "language":    val.get("language") or "",
                    "profile_url": (author.get("profileImageUrl") or "") if isinstance(author, dict) else "",
                })

        print(f"  Reviews collected: {len(reviews)}")

        all_results.append({
            "name":      place["name"],
            "naver_id":  place["naver_id"],
            "url":       url,
            "sort":      SORT or "default",
            "scraped_at": datetime.now().isoformat(),
            "reviews":   reviews,
        })

        # Random pause between places (5–12 seconds)
        if place != places_todo[-1]:
            wait = random.uniform(5, 12)
            print(f"  Waiting {wait:.1f}s before next place...")
            time.sleep(wait)
        print()

finally:
    driver.quit()

# ── Save ──────────────────────────────────────────────────────────────────────
with open(OUT, "w", encoding="utf-8") as f:
    json.dump(all_results, f, ensure_ascii=False, indent=2)

total = sum(len(p["reviews"]) for p in all_results)
print(f"Saved: {OUT}")
print(f"Total reviews collected: {total}")
