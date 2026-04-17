#!/usr/bin/env python3
"""Search across ficbook.net tagged blog posts.

Requires Chrome running with remote debugging:
  google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug

Usage:
  python3 ficbook_search.py <search term>
"""

import re
import sys
import time
from playwright.sync_api import sync_playwright


def match(text, term):
    pattern = re.escape(term) if FUZZY else r'\b' + re.escape(term) + r'\b'
    return bool(re.search(pattern, text, re.IGNORECASE))

TAG_URL = "https://ficbook.net/user_blog/tag/%23%D0%BF%D0%BE%D1%87%D0%B8%D1%82%D0%B0%D1%82%D0%B5%D0%BB%D0%B8"
DELAY = 1.5  # seconds between requests

args = sys.argv[1:]
if "--all" in args:
    MODE = "all"
    args.remove("--all")
elif "--any" in args:
    MODE = "any"
    args.remove("--any")
else:
    MODE = "exact"

FUZZY = "--fuzzy" in args
if FUZZY:
    args.remove("--fuzzy")

SEARCH_TERM = " ".join(args)
if not SEARCH_TERM:
    print("Usage: python3 ficbook_search.py [--all|--any] [--fuzzy] <search term>")
    print("  (default) exact phrase match")
    print("  --all     all words must appear somewhere in the post")
    print("  --any     any word matches")
    print("  --fuzzy   partial/suffix forms also match (e.g. волк matches волку)")
    sys.exit(1)

WORDS = SEARCH_TERM.lower().split()


def wait_for_page(page):
    """Wait for any anti-bot interstitial to resolve."""
    try:
        page.wait_for_function(
            "() => document.title !== 'Один момент…' && document.title !== ''",
            timeout=15000
        )
    except Exception:
        pass


def collect_post_urls(page):
    urls = []
    listing_page = 1
    while True:
        url = TAG_URL if listing_page == 1 else f"{TAG_URL}?p={listing_page}"
        print(f"  Page {listing_page}...", end=" ", flush=True)
        page.goto(url, wait_until="load")
        wait_for_page(page)
        page.wait_for_timeout(1000)

        links = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
        post_links = list(dict.fromkeys(
            l.split("#")[0] for l in links
            if re.search(r"ficbook\.net/authors/[^/]+/blog/\d+$", l.split("#")[0])
        ))

        if not post_links:
            print("no posts found, stopping.")
            break

        new = [l for l in post_links if l not in urls]
        urls.extend(new)
        print(f"{len(new)} posts ({len(urls)} total)")

        if not page.query_selector(f"a[href*='?p={listing_page + 1}']"):
            break
        listing_page += 1
        time.sleep(DELAY)

    return urls


def search_post(page, url):
    page.goto(url, wait_until="load")
    wait_for_page(page)
    page.wait_for_timeout(800)

    body = page.query_selector(".blog-post-content, .post-content, article, .entry-content, main")
    text = body.inner_text() if body else page.inner_text("body")

    # For --all: check the whole post first, then collect matching lines as context
    if MODE == "all":
        if not all(match(text, w) for w in WORDS):
            return []
        return [
            (i, line.strip())
            for i, line in enumerate(text.splitlines(), 1)
            if any(match(line, w) for w in WORDS) and line.strip()
        ]

    # For exact / --any: check line by line
    return [
        (i, line.strip())
        for i, line in enumerate(text.splitlines(), 1)
        if line.strip() and (
            match(line, SEARCH_TERM) if MODE == "exact"
            else any(match(line, w) for w in WORDS)
        )
    ]


MODE_LABEL = {"exact": "exact phrase", "all": "all words", "any": "any word"}
fuzzy_suffix = ", fuzzy" if FUZZY else ""
print(f"\nSearching for: «{SEARCH_TERM}» ({MODE_LABEL[MODE]}{fuzzy_suffix})\n")

with sync_playwright() as p:
    browser = p.chromium.connect_over_cdp("http://localhost:9222")
    page = browser.contexts[0].new_page()

    print("Step 1: Collecting post URLs...")
    post_urls = collect_post_urls(page)
    print(f"\n  Total: {len(post_urls)} posts\n")

    if not post_urls:
        print("No posts found. Make sure you're logged in and the tag page is visible in Chrome.")
        page.close()
        sys.exit(1)

    print("Step 2: Searching...\n")
    found_any = False
    for i, url in enumerate(post_urls, 1):
        time.sleep(DELAY)
        print(f"  [{i}/{len(post_urls)}]", end=" ", flush=True)
        try:
            hits = search_post(page, url)
            if hits:
                found_any = True
                print(f"MATCH: {url}")
                for _, snippet in hits[:5]:
                    print(f"    {snippet[:120]}")
                if len(hits) > 5:
                    print(f"    ... and {len(hits) - 5} more")
                print()
            else:
                print("no match")
        except Exception as e:
            print(f"ERROR: {e}")

    page.close()

if not found_any:
    print("\nNo matches found.")
