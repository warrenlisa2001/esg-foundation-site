#!/usr/bin/env python3
"""
Drafts a new Keeping Current article from the ESG Today RSS feed.

- Never publishes on its own. It only writes files into the repo checkout;
  the GitHub Action wrapping this script opens a Pull Request with those
  changes, and a human has to review and merge before anything goes live.
- Drafts at most ONE article per run, so each PR is small and easy to review.
- Keeps a simple JSON file (automation/seen-items.json) of feed items it has
  already turned into a draft, so it never repeats a story.
- Asks Claude to paraphrase, not copy, the source article -- and always
  includes a visible link back to the original, per the site's own rule
  that every figure needs a source.

Run manually to test:
    export ANTHROPIC_API_KEY=sk-ant-...
    python automation/draft_article.py
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

import feedparser
import requests
import anthropic

FEED_URL = "https://www.esgtoday.com/feed/"
SEEN_FILE = "automation/seen-items.json"
ARTICLES_DIR = "keeping-current"
INDEX_FILE = "keeping-current.html"

# The four categories already used across the site's Keeping Current section.
ALLOWED_CATEGORIES = ["Governance", "Climate", "Social", "Foundation"]

# Two existing articles to link under "More from Keeping Current".
# Update these occasionally to point at more recent stories.
MORE_LINKS = [
    ("uae-esg-governance-sustainability.html",
     "UAE Formalises ESG Disclosure Metrics as Sustainable Bond Issuance Hits a Record AED 28.6 Billion"),
    ("scope-3-lags-scope-1-2.html",
     "Scope 3 Reporting Still Lags Behind Scope 1 and 2, Library Analysis Shows"),
]


def load_seen():
    if not os.path.exists(SEEN_FILE):
        return []
    with open(SEEN_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_seen(seen):
    os.makedirs(os.path.dirname(SEEN_FILE), exist_ok=True)
    with open(SEEN_FILE, "w", encoding="utf-8") as f:
        json.dump(seen, f, indent=2)


def slugify(title):
    slug = title.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    slug = slug.strip("-")
    return slug[:80]


def strip_html(html):
    text = re.sub(r"<[^>]+>", " ", html or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def fetch_new_item(seen_guids):
    resp = requests.get(FEED_URL, timeout=20, headers={"User-Agent": "ESGFoundationBot/1.0"})
    resp.raise_for_status()
    feed = feedparser.parse(resp.content)

    for entry in feed.entries:
        guid = entry.get("id") or entry.get("link")
        if guid in seen_guids:
            continue
        summary_html = entry.get("summary", "") or entry.get("description", "")
        summary_text = strip_html(summary_html)
        return {
            "guid": guid,
            "title": entry.get("title", "").strip(),
            "link": entry.get("link", "").strip(),
            "published": entry.get("published", ""),
            "summary": summary_text[:1200],  # cap length fed to the model
        }
    return None


def draft_with_claude(item):
    client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env

    prompt = f"""You are drafting a short news item for "Keeping Current", the newsroom
section of ESG Foundation's website. House style rules, all mandatory:

- Two short paragraphs only. Combined, under 130 words.
- PARAPHRASE the source in your own words. Do not copy sentences from it.
  Do not quote more than a few words verbatim at a time.
- Do not invent any statistic, name, or date that is not in the source text below.
- Voice: mostly plain and direct (state what happened, in short sentences),
  a little of the writing can be precise and cite what's known, and keep it warm/plain
  rather than corporate. Avoid words like: leverage, empower, journey, impactful,
  thought leader, best-in-class, holistic, unlock, world-class, revolutionary,
  leading, trusted, the standard, global (unless literally true here).
- Sentence case headings. British English spelling.
- Pick exactly one category from this list: {", ".join(ALLOWED_CATEGORIES)}.

Source article title: {item['title']}
Source article summary: {item['summary']}
Source publisher: ESG Today ({item['link']})

Respond with ONLY a JSON object, no other text, in this exact shape:
{{
  "title": "a short, plain title for this item (can closely follow the source title)",
  "category": "one of {ALLOWED_CATEGORIES}",
  "paragraph1": "first paragraph",
  "paragraph2": "second paragraph"
}}"""

    response = client.messages.create(
        model="claude-sonnet-5",
        max_tokens=600,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    raw = re.sub(r"^```json\s*|\s*```$", "", raw.strip())
    return json.loads(raw)


ARTICLE_TEMPLATE = """<!DOCTYPE html>
<html lang="en-GB">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">

  <title>{title} | ESG Foundation</title>
  <meta name="description" content="{paragraph1_short}">
  <link rel="canonical" href="https://esgfoundation.org/keeping-current/{slug}.html">

  <meta property="og:title" content="{title} | ESG Foundation">
  <meta property="og:description" content="{paragraph1_short}">
  <meta property="og:type" content="article">
  <meta property="og:url" content="https://esgfoundation.org/keeping-current/{slug}.html">
  <meta property="og:image" content="https://esgfoundation.org/assets/img/og-default.png">

  <link rel="stylesheet" href="../assets/img/css/esgf-brand.css">

  <style>

    .esgf-article-head {{
      padding: 56px 0 40px;
      background: var(--esgf-surface);
      border-bottom: 1px solid var(--esgf-rule);
    }}

    .esgf-breadcrumb {{
      display: inline-block;
      margin-bottom: 16px;
      color: var(--esgf-depth);
      font-size: 13px;
      font-weight: 600;
      text-decoration: none;
    }}

    .esgf-article-tag {{
      display: inline-flex;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--esgf-rule-soft);
      color: var(--esgf-slate);
      font-size: 11px;
      font-weight: 700;
      letter-spacing: .08em;
      text-transform: uppercase;
    }}

    .esgf-article-title {{
      margin: 14px 0 0;
      font-family: var(--esgf-font-display);
      font-size: clamp(28px, 4vw, 38px);
      font-weight: 800;
      letter-spacing: -.02em;
      line-height: 1.15;
      color: var(--esgf-ink);
    }}

    .esgf-byline {{
      margin-top: 12px;
      color: var(--esgf-mist);
      font-family: var(--esgf-font-mono);
      font-size: 13px;
    }}

    .esgf-article-body {{
      max-width: 680px;
      margin: 0 auto;
      font-size: 17px;
      line-height: 1.7;
      color: var(--esgf-ink);
    }}

    .esgf-article-body p {{
      margin: 0 0 20px;
    }}

    .esgf-sources {{
      margin-top: 24px;
      color: var(--esgf-mist);
      font-size: 13px;
    }}

    .esgf-more {{
      margin-top: 40px;
      padding-top: 22px;
      border-top: 1px solid var(--esgf-rule);
    }}

    .esgf-more a {{
      display: inline-block;
      margin: 12px 20px 0 0;
      font-weight: 600;
    }}

  </style>
</head>

<body>

  <header class="esgf-header">
    <div class="esgf-container esgf-header__inner">

      <a class="esgf-brand" href="../index.html" aria-label="ESG Foundation home">
        <img src="../assets/img/og-default.png" alt="ESG Foundation">
      </a>

      <nav class="esgf-nav" aria-label="Main navigation">
        <a href="../gcc-benchmark.html">Record</a>
        <a href="../method.html">Method</a>
        <a href="../reports-showcase.html">Research</a>
        <a href="../about.html">About</a>
        <a class="esgf-nav__search" href="../gcc-benchmark.html">Search data</a>
      </nav>

    </div>
  </header>


  <main>

    <div class="esgf-article-head">
      <div class="esgf-container">
        <a class="esgf-breadcrumb" href="../keeping-current.html">← Keeping Current</a><br>
        <span class="esgf-article-tag">{category}</span>
        <h1 class="esgf-article-title">{title}</h1>
        <p class="esgf-byline">{date} · ESG Foundation</p>
      </div>
    </div>

    <section class="esgf-section esgf-section--tight">
      <div class="esgf-container">
        <div class="esgf-article-body">

          <p>{paragraph1}</p>
          <p>{paragraph2}</p>
          <p class="esgf-sources">Source: <a href="{source_link}" target="_blank" rel="noopener">ESG Today</a>, {source_date}.</p>

          <div class="esgf-more">
            <span class="esgf-eyebrow">More from Keeping Current</span>
            <div>
              <a href="{more1_url}">{more1_title}</a>
              <a href="{more2_url}">{more2_title}</a>
            </div>
          </div>
        </div>
      </div>
    </section>

  </main>


  <footer class="esgf-footer">
    <div class="esgf-container esgf-grid">

      <div style="grid-column:1 / span 4;">
        <div class="esgf-footer__brand">ESG Foundation</div>
        <p style="margin-top:16px; max-width:36ch; color:rgba(255,255,255,.8);">
          ESG Foundation is a non-profit knowledge base for environmental,
          social and governance data. We aggregate disclosures, filings and
          public reporting from across the ESG field, publish the method we
          use to do it, and make the record free to read. Where data does
          not exist, we publish the gap.
        </p>
      </div>

      <div style="grid-column:5 / span 3;">
        <p class="esgf-eyebrow" style="color:rgba(255,255,255,.6);">Explore</p>
        <p style="margin:0 0 8px;"><a href="../gcc-benchmark.html">Record</a></p>
        <p style="margin:0 0 8px;"><a href="../method.html">Method</a></p>
        <p style="margin:0 0 8px;"><a href="../reports-showcase.html">Research</a></p>
        <p style="margin:0;"><a href="../about.html">About</a></p>
      </div>

      <div style="grid-column:8 / span 3;">
        <p class="esgf-eyebrow" style="color:rgba(255,255,255,.6);">Foundation</p>
        <p style="margin:0 0 8px;"><a href="../awards.html">Awards</a></p>
        <p style="margin:0 0 8px;"><a href="../jobs.html">Jobs</a></p>
        <p style="margin:0;"><a href="../join-us.html">Join us</a></p>
      </div>

      <div style="grid-column:11 / span 2;">
        <p class="esgf-eyebrow" style="color:rgba(255,255,255,.6);">Contact</p>
        <p style="margin:0 0 8px;"><a href="mailto:info@esgfoundation.org">info@esgfoundation.org</a></p>
        <p style="margin:0;"><a href="tel:+971504400162">+971 50 440 0162</a></p>
      </div>

      <div style="grid-column:1 / -1; margin-top:48px; padding-top:24px; border-top:1px solid rgba(255,255,255,.18);">
        <p class="esgf-mono" style="color:rgba(255,255,255,.6);">
          © 2026 ESG Foundation. A company limited by guarantee registered in England &amp; Wales, no. 17355087.
          Registered office: 71-75 Shelton Street, Covent Garden, London, WC2H 9JQ.
          Operational address: PO Box 50017, Dubai, United Arab Emirates.
        </p>
        <p style="margin-top:8px;">
          <a href="../privacy.html">Privacy notice</a> · <a href="../terms.html">Terms of use</a>
        </p>
      </div>

    </div>
  </footer>

</body>
</html>
"""


def build_article_html(draft, item, slug, date_str):
    return ARTICLE_TEMPLATE.format(
        title=draft["title"],
        category=draft["category"],
        date=date_str,
        paragraph1=draft["paragraph1"],
        paragraph2=draft["paragraph2"],
        paragraph1_short=draft["paragraph1"][:150],
        slug=slug,
        source_link=item["link"],
        source_date=item.get("published", date_str),
        more1_url=MORE_LINKS[0][0],
        more1_title=MORE_LINKS[0][1],
        more2_url=MORE_LINKS[1][0],
        more2_title=MORE_LINKS[1][1],
    )


def insert_into_index(draft, slug):
    with open(INDEX_FILE, "r", encoding="utf-8") as f:
        content = f.read()

    new_item = f'''
          <article class="esgf-news-item" data-category="{draft['category']}">
            <span class="esgf-news-tag">{draft['category']}</span>
            <h3><a href="keeping-current/{slug}.html">{draft['title']}</a></h3>
            <p>{draft['paragraph1']}</p>
          </article>
'''

    marker = '<div id="news-list">'
    idx = content.find(marker)
    if idx == -1:
        print("WARNING: could not find news-list marker in keeping-current.html; skipping index update")
        return

    insert_at = idx + len(marker)
    content = content[:insert_at] + new_item + content[insert_at:]

    with open(INDEX_FILE, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    seen = load_seen()
    seen_guids = {s["guid"] for s in seen}

    item = fetch_new_item(seen_guids)
    if item is None:
        print("No new, un-drafted items found. Nothing to do.")
        return

    print(f"Drafting from: {item['title']}")
    draft = draft_with_claude(item)

    if draft["category"] not in ALLOWED_CATEGORIES:
        draft["category"] = "Foundation"  # safe fallback

    slug = slugify(draft["title"])
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    os.makedirs(ARTICLES_DIR, exist_ok=True)
    article_path = os.path.join(ARTICLES_DIR, f"{slug}.html")
    with open(article_path, "w", encoding="utf-8") as f:
        f.write(build_article_html(draft, item, slug, date_str))
    print(f"Wrote {article_path}")

    insert_into_index(draft, slug)
    print(f"Updated {INDEX_FILE}")

    seen.append({"guid": item["guid"], "slug": slug, "drafted_at": date_str})
    save_seen(seen)
    print(f"Recorded in {SEEN_FILE}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)
