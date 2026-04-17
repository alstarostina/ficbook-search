# ficbook search

Search across ficbook.net blog posts tagged with `#почитатели`.

Since ficbook does not provide native search across tagged blog posts, this script
automates a real Chrome browser to visit each post and search for your term.

> **Note:** The search is performed on the entire page content, not just the blog
> post body. This means it may occasionally match text in navigation menus, sidebars,
> comments, or other page elements — not only the post text itself.

---

## Requirements

- Python 3
- Playwright: `pip install playwright && python3 -m playwright install chromium`
- Google Chrome installed

---

## Setup (once)

Launch Chrome with remote debugging enabled:

```bash
google-chrome --remote-debugging-port=9222 --user-data-dir=/tmp/chrome-debug
```

In the Chrome window that opens, log into ficbook.net and navigate to the tag page.
Solve any Cloudflare security check if prompted. Once you can see the posts listed
normally, the script is ready to run.

---

## Usage

```bash
python3 ficbook_search.py <search term>                  # exact phrase (default)
python3 ficbook_search.py --all "word1 word2"            # all words must appear in the post
python3 ficbook_search.py --any "word1 word2"            # any word matches
python3 ficbook_search.py --fuzzy волк                   # also matches волку, волком, …
python3 ficbook_search.py --any --fuzzy "волк лис"       # combine with --all / --any
```

Search is case-insensitive. By default it matches whole words only — searching for
`лин` will not match `роулинг`. Add `--fuzzy` to disable this and allow partial/suffix
matches (useful for declined or conjugated Russian words).

---

## Notes

- Keep the Chrome window open while the script runs
- With ~335 posts the search takes roughly 15 minutes
- Matched posts are printed to the terminal as they are found
