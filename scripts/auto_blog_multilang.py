import os
import json
import re
import html
import base64
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path


# ============================================================
# ASTRO AVYUG - MULTILINGUAL AUTOMATIC AI BLOG PUBLISHER
#
# One scheduled run:
#   1. Researches one verified topic.
#   2. Creates a Hindi article.
#   3. Creates a faithful English version of the same article.
#   4. Creates one topic-matched AI image shared by both languages.
#   5. Publishes Hindi under /hi/blog/posts/
#   6. Publishes English under /en/blog/posts/
#   7. Adds the Hindi card to /blog/ and /hi/blog/
#   8. Adds the English card to /en/blog/
#   9. Updates sitemap.xml with both article URLs.
# ============================================================

ROOT = Path(__file__).resolve().parents[1]

MAIN_BLOG = ROOT / "blog"
MAIN_IMAGES = MAIN_BLOG / "images"

HI_BLOG = ROOT / "hi" / "blog"
HI_POSTS = HI_BLOG / "posts"

EN_BLOG = ROOT / "en" / "blog"
EN_POSTS = EN_BLOG / "posts"

KEY = os.environ.get("OPENAI_API_KEY")

if not KEY:
    raise SystemExit("Missing OPENAI_API_KEY")

MAIN_IMAGES.mkdir(parents=True, exist_ok=True)
HI_POSTS.mkdir(parents=True, exist_ok=True)
EN_POSTS.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# INDIA DATE
# ------------------------------------------------------------

today = datetime.now(
    timezone(timedelta(hours=5, minutes=30))
)

date = today.strftime("%Y-%m-%d")


# ------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------

def call_responses(payload, timeout=180):
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            return json.load(response)

    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print("OpenAI API error:")
        print(error_body)
        raise SystemExit("OpenAI request failed")


def response_text(data):
    text = data.get("output_text", "")

    if text:
        return text

    return "".join(
        c.get("text", "")
        for item in data.get("output", [])
        for c in item.get("content", [])
        if c.get("type") in ("output_text", "text")
    )


def parse_json_object(text):
    match = re.search(r"\{.*\}", text, re.S)

    if not match:
        raise SystemExit("Invalid AI JSON")

    try:
        return json.loads(match.group(0))
    except json.JSONDecodeError:
        raise SystemExit("Could not decode AI JSON")


def require_article_fields(article, label):
    for key in (
        "title",
        "slug",
        "category",
        "excerpt",
        "meta_description",
        "content_html",
    ):
        if not article.get(key):
            raise SystemExit(f"Missing {label}.{key}")


def safe_slug(value, fallback):
    slug = re.sub(
        r"[^a-z0-9-]+",
        "-",
        value.lower(),
    ).strip("-")

    return slug or fallback


def unique_slug(folder, slug):
    candidate = slug
    n = 2

    while (folder / (candidate + ".html")).exists():
        candidate = slug + "-" + date

        if (folder / (candidate + ".html")).exists():
            candidate = slug + "-" + date + "-" + str(n)
            n += 1
        else:
            break

    return candidate


def esc(value):
    return html.escape(str(value), quote=True)


# ============================================================
# 1. GENERATE VERIFIED HINDI ARTICLE
# ============================================================

hi_prompt = f"""
You are the editorial AI for Astro Avyug, an Indian astrology website.

India date: {date}.

Research and create ONE original Hindi astrology article relevant to today's
genuinely verified significance.

Prefer a verified festival/vrat/observance, astronomical or planetary event,
zodiac, numerology, tarot, Kundli, marriage, relationship or career topic.

Never invent a festival, transit, muhurat, astronomical event or date.

If no major date-specific observance exists, choose a useful evergreen topic.

Return ONLY valid JSON with exactly these keys:

title
slug
category
excerpt
meta_description
content_html

Important:
- slug MUST be lowercase ASCII English letters/numbers/hyphens only.
- Write natural, professional Hindi.
- Article length: 900-1400 words.
- content_html may use ONLY: h2, h3, p, ul, li, strong, blockquote.
- Include exactly 3 FAQs.
- Include a responsible astrology disclaimer.
- Do not make high-stakes guarantees.
- Do not fabricate citations.
- Do not use clickbait.
- Do not use keyword stuffing.
- The article should be genuinely useful for Astro Avyug readers.
"""

hi_payload = {
    "model": "gpt-5.6-luna",
    "input": hi_prompt,
    "tools": [
        {
            "type": "web_search_preview"
        }
    ],
    "max_output_tokens": 7000,
}

hi_data = call_responses(
    hi_payload,
    timeout=180,
)

hi_article = parse_json_object(
    response_text(hi_data)
)

require_article_fields(
    hi_article,
    "Hindi article",
)


# ============================================================
# 2. CREATE FAITHFUL ENGLISH VERSION
# ============================================================

en_prompt = f"""
You are the English editor for Astro Avyug.

Below is a verified Hindi astrology article already researched for India date
{date}.

Create a faithful English-language version of THE SAME ARTICLE.

Do not add new dates, events, transits, claims, facts or predictions.
Preserve the meaning, structure and factual content.
Make the English natural and professional rather than word-for-word awkward.

Return ONLY valid JSON with exactly these keys:

title
slug
category
excerpt
meta_description
content_html

Important:
- slug MUST be lowercase ASCII English letters/numbers/hyphens only.
- Article length should remain approximately 900-1400 words.
- content_html may use ONLY: h2, h3, p, ul, li, strong, blockquote.
- Keep exactly 3 FAQs.
- Keep the responsible astrology disclaimer.
- Do not add citations that are not in the source.
- Do not make high-stakes guarantees.

HINDI SOURCE JSON:
{json.dumps(hi_article, ensure_ascii=False)}
"""

en_payload = {
    "model": "gpt-5.6-luna",
    "input": en_prompt,
    "max_output_tokens": 7000,
}

en_data = call_responses(
    en_payload,
    timeout=180,
)

en_article = parse_json_object(
    response_text(en_data)
)

require_article_fields(
    en_article,
    "English article",
)


# ------------------------------------------------------------
# SAFE / UNIQUE SLUGS
# ------------------------------------------------------------

hi_slug = safe_slug(
    hi_article["slug"],
    "astro-avyug-hi-" + date,
)

en_slug = safe_slug(
    en_article["slug"],
    "astro-avyug-en-" + date,
)

hi_slug = unique_slug(
    HI_POSTS,
    hi_slug,
)

en_slug = unique_slug(
    EN_POSTS,
    en_slug,
)


# ------------------------------------------------------------
# ARTICLE URLS
# ------------------------------------------------------------

hi_url = (
    "https://astroavyug.com/hi/blog/posts/"
    + hi_slug
    + ".html"
)

en_url = (
    "https://astroavyug.com/en/blog/posts/"
    + en_slug
    + ".html"
)


# ============================================================
# 3. ONE SHARED TOPIC-MATCHED IMAGE
# ============================================================

print("Generating topic-matched AI image...")

image_prompt = f"""
Create a premium editorial hero image for the Astro Avyug astrology website.

The image must visually match this specific article topic.

Hindi title:
{hi_article["title"]}

English title:
{en_article["title"]}

Hindi category:
{hi_article["category"]}

Article summary:
{hi_article["excerpt"]}

Requirements:
- Indian spiritual/astrology editorial aesthetic where appropriate.
- Premium, realistic and professional.
- Rich cinematic lighting.
- Elegant composition.
- Clearly connected to the article subject.
- No random unrelated objects.
- No visible website UI.
- No watermark.
- No logo.
- No text.
- No captions.
- No fake newspaper layout.
- No promotional banner.
- No borders.
- Landscape hero image suitable for a blog article.
"""

image_payload = {
    "model": "gpt-5.6-luna",
    "input": image_prompt,
    "tools": [
        {
            "type": "image_generation",
            "model": "gpt-image-2",
        }
    ],
    "tool_choice": {
        "type": "image_generation"
    },
}

image_data = call_responses(
    image_payload,
    timeout=300,
)

image_base64 = None

for output in image_data.get("output", []):
    if output.get("type") == "image_generation_call":
        image_base64 = output.get("result")
        if image_base64:
            break

if not image_base64:
    raise SystemExit(
        "AI image was not returned. Blog was not published."
    )


# ------------------------------------------------------------
# SAVE SHARED IMAGE
# ------------------------------------------------------------

image_slug = en_slug
image_path = MAIN_IMAGES / (image_slug + ".png")

try:
    image_bytes = base64.b64decode(image_base64)
except Exception:
    raise SystemExit("Invalid base64 image returned by AI")

image_path.write_bytes(image_bytes)

image_src = (
    "/blog/images/"
    + image_slug
    + ".png"
)

og_image_url = (
    "https://astroavyug.com"
    + image_src
)

print("Image saved:", image_path.relative_to(ROOT))


# ============================================================
# 4. ARTICLE TEMPLATE
# ============================================================

article_template = """<!doctype html>
<html lang="HTML_LANG">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">

<!-- Google tag (gtag.js) -->
<script async src="https://www.googletagmanager.com/gtag/js?id=G-7EGB6BFB0Y"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){dataLayer.push(arguments);}
  gtag('js', new Date());
  gtag('config', 'G-7EGB6BFB0Y');
</script>

<title>TITLE | Astro Avyug</title>
<meta name="description" content="DESC">
<link rel="canonical" href="CANONICAL">

<link rel="alternate" hreflang="hi" href="HI_URL">
<link rel="alternate" hreflang="en" href="EN_URL">
<link rel="alternate" hreflang="x-default" href="HI_URL">

<link rel="icon" href="/favicon.ico" sizes="any">
<link rel="shortcut icon" href="/favicon.ico">
<link rel="icon" type="image/png" sizes="48x48" href="/favicon-48x48.png">
<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96x96.png">
<link rel="apple-touch-icon" sizes="180x180" href="/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<meta name="theme-color" content="#100b25">

<meta property="og:type" content="article">
<meta property="og:title" content="TITLE">
<meta property="og:description" content="DESC">
<meta property="og:url" content="CANONICAL">
<meta property="og:image" content="OG_IMAGE">
<meta property="og:image:alt" content="IMAGE_ALT">

<style>
body{
    margin:0;
    background:
        radial-gradient(circle at 8% 18%,rgba(39,146,255,.18),transparent 20%),
        radial-gradient(circle at 88% 12%,rgba(184,63,255,.20),transparent 22%),
        linear-gradient(135deg,#070817,#100b25,#071b32);
    color:#eee;
    font-family:system-ui,-apple-system,Segoe UI,sans-serif;
    line-height:1.8;
}
.wrap{
    max-width:900px;
    margin:auto;
    padding:28px 20px 70px;
}
a{color:#ffe5a1}
.lang-nav{
    display:flex;
    gap:10px;
    flex-wrap:wrap;
    margin:0 0 18px;
}
.lang-nav a{
    border:1px solid #ffffff20;
    border-radius:999px;
    padding:7px 12px;
    text-decoration:none;
}
article{
    background:#0a091ed1;
    border:1px solid #d6a75a33;
    border-radius:24px;
    padding:clamp(22px,5vw,50px);
}
.tag{
    color:#e9bf68;
    font-size:12px;
    font-weight:800;
}
h1{
    font-family:Georgia,serif;
    color:#ffe5a1;
    line-height:1.2;
    font-size:clamp(32px,6vw,56px);
}
h2,h3{
    color:#f2cf83;
    font-family:Georgia,serif;
    margin-top:34px;
}
p,li{color:#d8d0e4}
.hero{
    margin:28px 0 34px;
    overflow:hidden;
    border-radius:20px;
    border:1px solid #d6a75a33;
    background:#070817;
}
.hero img{
    display:block;
    width:100%;
    height:auto;
    max-height:560px;
    object-fit:cover;
}
.hero figcaption{
    padding:10px 14px;
    font-size:12px;
    color:#aaa0b8;
    text-align:center;
}
.notice{
    margin-top:30px;
    padding:16px;
    border:1px solid #ffffff18;
    border-radius:14px;
}
</style>
</head>

<body>
<main class="wrap">

<div class="lang-nav">
<a href="HOME_URL">HOME_LABEL</a>
<a href="BLOG_URL">BLOG_LABEL</a>
<a href="OTHER_URL">OTHER_LABEL</a>
</div>

<article>

<div class="tag">CATEGORY</div>

<h1>TITLE</h1>

<p><strong>EXCERPT</strong></p>

<figure class="hero">
<img
    src="IMAGE"
    alt="IMAGE_ALT"
    loading="eager"
    decoding="async"
>
<figcaption>CAPTION</figcaption>
</figure>

CONTENT

<div class="notice">
DISCLAIMER
</div>

</article>
</main>
</body>
</html>
"""


def build_article_page(
    article,
    lang,
    canonical,
    home_url,
    home_label,
    blog_url,
    blog_label,
    other_url,
    other_label,
    caption,
    disclaimer,
):
    title = esc(article["title"])
    desc = esc(article["meta_description"])
    category = esc(article["category"])
    excerpt = esc(article["excerpt"])
    image_alt = esc(article["title"])
    content = article["content_html"]

    return (
        article_template
        .replace("HTML_LANG", lang)
        .replace("TITLE", title)
        .replace("DESC", desc)
        .replace("CANONICAL", canonical)
        .replace("HI_URL", hi_url)
        .replace("EN_URL", en_url)
        .replace("OG_IMAGE", og_image_url)
        .replace("IMAGE_ALT", image_alt)
        .replace("HOME_URL", home_url)
        .replace("HOME_LABEL", home_label)
        .replace("BLOG_URL", blog_url)
        .replace("BLOG_LABEL", blog_label)
        .replace("OTHER_URL", other_url)
        .replace("OTHER_LABEL", other_label)
        .replace("CATEGORY", category)
        .replace("EXCERPT", excerpt)
        .replace("IMAGE", image_src)
        .replace("CAPTION", caption)
        .replace("CONTENT", content)
        .replace("DISCLAIMER", disclaimer)
    )


# ------------------------------------------------------------
# WRITE HINDI ARTICLE
# ------------------------------------------------------------

hi_page = build_article_page(
    hi_article,
    "hi-IN",
    hi_url,
    "/hi/",
    "मुखपृष्ठ",
    "/hi/blog/",
    "ब्लॉग",
    en_url,
    "English",
    "Astro Avyug · विषयानुकूल AI-generated illustration",
    (
        "यह लेख ज्योतिषीय/आध्यात्मिक सामान्य मार्गदर्शन के लिए है। "
        "इसे निश्चित भविष्यवाणी या महत्वपूर्ण निर्णय का एकमात्र आधार न मानें।"
    ),
)

hi_path = HI_POSTS / (hi_slug + ".html")

hi_path.write_text(
    hi_page,
    encoding="utf-8",
)

print(
    "Hindi article created:",
    hi_path.relative_to(ROOT),
)


# ------------------------------------------------------------
# WRITE ENGLISH ARTICLE
# ------------------------------------------------------------

en_page = build_article_page(
    en_article,
    "en-IN",
    en_url,
    "/en/",
    "Home",
    "/en/blog/",
    "Blog",
    hi_url,
    "हिन्दी",
    "Astro Avyug · Topic-matched AI-generated illustration",
    (
        "This article provides general astrological/spiritual guidance. "
        "Do not treat it as a guaranteed prediction or as the sole basis "
        "for an important decision."
    ),
)

en_path = EN_POSTS / (en_slug + ".html")

en_path.write_text(
    en_page,
    encoding="utf-8",
)

print(
    "English article created:",
    en_path.relative_to(ROOT),
)


# ============================================================
# 5. UPDATE BLOG INDEXES
# ============================================================

marker = (
    '<div class="blog-grid" '
    'id="grid" '
    'style="margin-top:28px">'
)


def make_card(
    article,
    article_url,
    read_more_text,
):
    title = esc(article["title"])
    category = esc(article["category"])
    excerpt = esc(article["excerpt"])
    image_alt = esc(article["title"])

    data_text = esc(
        article["title"]
        + " "
        + article["excerpt"]
    )

    return (
        '<article class="blog-card" '
        'data-cat="' + esc(article["category"].lower()) + '" '
        'data-text="' + data_text + '">'

        '<a href="' + article_url + '" '
        'style="text-decoration:none">'

        '<img src="' + image_src + '" '
        'alt="' + image_alt + '" '
        'loading="lazy" '
        'style="width:100%;height:220px;'
        'object-fit:cover;border-radius:16px;'
        'display:block;margin-bottom:16px">'

        '</a>'

        '<span class="tag">' + category + '</span>'

        '<h3>' + title + '</h3>'

        '<p>' + excerpt + '</p>'

        '<div class="read">'

        '<a href="' + article_url + '">'
        + read_more_text +
        '</a>'

        '</div>'

        '</article>'
    )


hi_card = make_card(
    hi_article,
    hi_url,
    "पूरा लेख पढ़ें →",
)

en_card = make_card(
    en_article,
    en_url,
    "Read More →",
)

# Root /blog/ is the default blog landing page.
# It receives the Hindi article card and links to the Hindi article URL.
index_jobs = [
    (
        MAIN_BLOG / "index.html",
        hi_card,
        hi_url,
    ),
    (
        HI_BLOG / "index.html",
        hi_card,
        hi_url,
    ),
    (
        EN_BLOG / "index.html",
        en_card,
        en_url,
    ),
]

# Validate first, then write all.
validated = []

for index_file, card, article_url in index_jobs:
    if not index_file.exists():
        raise SystemExit(
            "Blog index missing: "
            + str(index_file.relative_to(ROOT))
        )

    page_html = index_file.read_text(
        encoding="utf-8"
    )

    if marker not in page_html:
        raise SystemExit(
            "Blog grid marker missing in "
            + str(index_file.relative_to(ROOT))
        )

    validated.append(
        (
            index_file,
            page_html,
            card,
            article_url,
        )
    )


for index_file, page_html, card, article_url in validated:
    if article_url in page_html:
        print(
            "Card already exists:",
            index_file.relative_to(ROOT),
        )
        continue

    page_html = page_html.replace(
        marker,
        marker + "\n" + card,
        1,
    )

    index_file.write_text(
        page_html,
        encoding="utf-8",
    )

    print(
        "Blog index updated:",
        index_file.relative_to(ROOT),
    )


# ============================================================
# 6. UPDATE ROOT SITEMAP
# ============================================================

sitemap = ROOT / "sitemap.xml"

if not sitemap.exists():
    raise SystemExit("Root sitemap.xml not found")

sitemap_text = sitemap.read_text(
    encoding="utf-8"
)


def sitemap_entry(url):
    return (
        "  <url>"
        "<loc>" + url + "</loc>"
        "<lastmod>" + date + "</lastmod>"
        "</url>\n"
    )


entries = ""

for article_url in (hi_url, en_url):
    if article_url not in sitemap_text:
        entries += sitemap_entry(
            article_url
        )


if entries:
    if "</urlset>" not in sitemap_text:
        raise SystemExit(
            "Closing </urlset> not found in sitemap.xml"
        )

    sitemap_text = sitemap_text.replace(
        "</urlset>",
        entries + "</urlset>",
    )

    sitemap.write_text(
        sitemap_text,
        encoding="utf-8",
    )

    print("Sitemap updated")



# ============================================================
# 7. UPDATE RSS FEED AND BLOG SITEMAP
# ============================================================

from xml.sax.saxutils import escape as xml_escape

feed_file = ROOT / "feed.xml"
if feed_file.exists():
    feed_text = feed_file.read_text(encoding="utf-8")
    feed_items = ""
    for article, article_url, lang_code in (
        (hi_article, hi_url, "hi-IN"),
        (en_article, en_url, "en-IN"),
    ):
        if article_url not in feed_text:
            feed_items += (
                "<item>"
                "<title>" + xml_escape(str(article["title"])) + "</title>"
                "<link>" + xml_escape(article_url) + "</link>"
                "<guid isPermaLink=\"true\">" + xml_escape(article_url) + "</guid>"
                "<description>" + xml_escape(str(article["excerpt"])) + "</description>"
                "<category>" + xml_escape(str(article["category"])) + "</category>"
                "<pubDate>" + today.strftime("%a, %d %b %Y 00:00:00 +0530") + "</pubDate>"
                "</item>\n"
            )
    if feed_items:
        if "</channel>" not in feed_text:
            raise SystemExit("Closing </channel> not found in feed.xml")
        feed_text = feed_text.replace("</channel>", feed_items + "</channel>", 1)
        feed_file.write_text(feed_text, encoding="utf-8")
        print("RSS feed updated")

blog_sitemap = MAIN_BLOG / "sitemap.xml"
if blog_sitemap.exists():
    blog_sitemap_text = blog_sitemap.read_text(encoding="utf-8")
    blog_entries = ""
    for article_url in (hi_url, en_url):
        if article_url not in blog_sitemap_text:
            blog_entries += sitemap_entry(article_url)
    if blog_entries:
        if "</urlset>" not in blog_sitemap_text:
            raise SystemExit("Closing </urlset> not found in blog/sitemap.xml")
        blog_sitemap_text = blog_sitemap_text.replace("</urlset>", blog_entries + "</urlset>", 1)
        blog_sitemap.write_text(blog_sitemap_text, encoding="utf-8")
        print("Blog sitemap updated")

# ============================================================
# DONE
# ============================================================

print("")
print("================================================")
print("ASTRO AVYUG MULTILINGUAL BLOG PUBLISHED")
print("================================================")
print("Hindi:", hi_url)
print("English:", en_url)
print("Image:", og_image_url)
print("Date:", date)
print("================================================")
