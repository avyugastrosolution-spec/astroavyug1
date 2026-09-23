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
# ASTRO AVYUG - AUTOMATIC AI BLOG + AI IMAGE PUBLISHER
# ============================================================

ROOT = Path(__file__).resolve().parents[1]
BLOG = ROOT / "blog"
POSTS = BLOG / "posts"
IMAGES = BLOG / "images"

KEY = os.environ.get("OPENAI_API_KEY")

if not KEY:
    raise SystemExit("Missing OPENAI_API_KEY")

POSTS.mkdir(parents=True, exist_ok=True)
IMAGES.mkdir(parents=True, exist_ok=True)


# ------------------------------------------------------------
# India date/time
# ------------------------------------------------------------

today = datetime.now(
    timezone(timedelta(hours=5, minutes=30))
)

date = today.strftime("%Y-%m-%d")


# ------------------------------------------------------------
# BLOG CONTENT PROMPT
# ------------------------------------------------------------

prompt = f"""
You are the editorial AI for Astro Avyug, an Indian astrology website.

India date: {date}.

Create ONE original Hindi astrology article relevant to today's genuinely
verified significance.

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

Write natural, professional Hindi.

Article length:
900-1400 words.

content_html may use ONLY:

h2
h3
p
ul
li
strong
blockquote

Include exactly 3 FAQs.

Include a responsible astrology disclaimer.

Do not make high-stakes guarantees.

Do not fabricate citations.

Do not use clickbait.

Do not use keyword stuffing.

The article should be genuinely useful for Astro Avyug readers.
"""


# ------------------------------------------------------------
# OPENAI TEXT RESPONSE
# ------------------------------------------------------------

payload = {
    "model": "gpt-5.6-luna",
    "input": prompt,
    "tools": [
        {
            "type": "web_search_preview"
        }
    ],
    "max_output_tokens": 6000
}


req = urllib.request.Request(
    "https://api.openai.com/v1/responses",
    data=json.dumps(payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json"
    },
    method="POST"
)


try:
    with urllib.request.urlopen(req, timeout=180) as response:
        data = json.load(response)

except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8", errors="replace")
    print("OpenAI text API error:")
    print(error_body)
    raise SystemExit("Text generation failed")


# ------------------------------------------------------------
# EXTRACT TEXT
# ------------------------------------------------------------

text = data.get("output_text", "")

if not text:
    text = "".join(
        c.get("text", "")
        for item in data.get("output", [])
        for c in item.get("content", [])
        if c.get("type") in ("output_text", "text")
    )


# ------------------------------------------------------------
# PARSE JSON
# ------------------------------------------------------------

m = re.search(r"\{.*\}", text, re.S)

if not m:
    raise SystemExit("Invalid AI JSON")

try:
    a = json.loads(m.group(0))
except json.JSONDecodeError:
    raise SystemExit("Could not decode AI JSON")


# ------------------------------------------------------------
# REQUIRED FIELDS
# ------------------------------------------------------------

for k in (
    "title",
    "slug",
    "category",
    "excerpt",
    "meta_description",
    "content_html"
):
    if not a.get(k):
        raise SystemExit("Missing " + k)


# ------------------------------------------------------------
# SAFE SLUG
# ------------------------------------------------------------

slug = re.sub(
    r"[^a-z0-9-]+",
    "-",
    a["slug"].lower()
).strip("-")

if not slug:
    slug = "astro-avyug-" + date


path = POSTS / (slug + ".html")

if path.exists():
    slug += "-" + date
    path = POSTS / (slug + ".html")


# ------------------------------------------------------------
# SAFE HTML VALUES
# ------------------------------------------------------------

title = html.escape(a["title"], quote=True)
cat = html.escape(a["category"], quote=True)
excerpt = html.escape(a["excerpt"], quote=True)
desc = html.escape(a["meta_description"], quote=True)

content = a["content_html"]


# ------------------------------------------------------------
# ARTICLE URL
# ------------------------------------------------------------

url = (
    "https://astroavyug.com/blog/posts/"
    + slug
    + ".html"
)


# ============================================================
# AI IMAGE GENERATION
# ============================================================

print("Generating topic-matched AI image...")


image_prompt = f"""
Create a premium editorial hero image for the Astro Avyug astrology website.

The image MUST visually match the subject of this specific article.

Article title:
{a["title"]}

Category:
{a["category"]}

Article summary:
{a["excerpt"]}

Article content:
{re.sub(r"<[^>]+>", " ", a["content_html"])[:3500]}

Requirements:

- Create a visually relevant image based on the article topic.
- Indian spiritual/astrology editorial aesthetic where appropriate.
- Premium, realistic and professional.
- Suitable for a professional astrology website.
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
            "model": "gpt-image-2"
        }
    ],
    "tool_choice": {
        "type": "image_generation"
    }
}


image_req = urllib.request.Request(
    "https://api.openai.com/v1/responses",
    data=json.dumps(image_payload).encode("utf-8"),
    headers={
        "Authorization": "Bearer " + KEY,
        "Content-Type": "application/json"
    },
    method="POST"
)


try:
    with urllib.request.urlopen(image_req, timeout=300) as response:
        image_response = json.load(response)

except urllib.error.HTTPError as e:
    error_body = e.read().decode("utf-8", errors="replace")
    print("OpenAI image API error:")
    print(error_body)
    raise SystemExit("Image generation failed")


# ------------------------------------------------------------
# EXTRACT GENERATED IMAGE
# ------------------------------------------------------------

image_base64 = None

for output in image_response.get("output", []):

    if output.get("type") == "image_generation_call":

        image_base64 = output.get("result")

        if image_base64:
            break


if not image_base64:
    raise SystemExit(
        "AI image was not returned. Blog was not published."
    )


# ------------------------------------------------------------
# SAVE IMAGE
# ------------------------------------------------------------

image_path = IMAGES / (slug + ".png")

try:
    image_bytes = base64.b64decode(image_base64)
except Exception:
    raise SystemExit("Invalid base64 image returned by AI")


image_path.write_bytes(image_bytes)


print("Image saved:", image_path)


# ------------------------------------------------------------
# IMAGE URLS
# ------------------------------------------------------------

image_url = "/blog/images/" + slug + ".png"

og_image_url = (
    "https://astroavyug.com"
    + image_url
)


image_alt = html.escape(
    a["title"],
    quote=True
)


# ============================================================
# BLOG ARTICLE HTML
# ============================================================

template = """<!doctype html>
<html lang="hi">

<head>

<meta charset="utf-8">

<meta
    name="viewport"
    content="width=device-width,initial-scale=1"
>

<title>TITLE | Astro Avyug</title>

<meta
    name="description"
    content="DESC"
>

<link
    rel="canonical"
    href="URL"
>

<link
    rel="icon"
    href="/favicon.ico"
    sizes="any"
>

<meta
    property="og:type"
    content="article"
>

<meta
    property="og:title"
    content="TITLE"
>

<meta
    property="og:description"
    content="DESC"
>

<meta
    property="og:url"
    content="URL"
>

<meta
    property="og:image"
    content="OG_IMAGE"
>

<meta
    property="og:image:alt"
    content="IMAGE_ALT"
>

<style>

body{
    margin:0;
    background:
        linear-gradient(
            135deg,
            #070817,
            #100b25,
            #071b32
        );
    color:#eee;
    font-family:system-ui;
    line-height:1.8;
}

.wrap{
    max-width:900px;
    margin:auto;
    padding:28px 20px 70px;
}

a{
    color:#ffe5a1;
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

h2,
h3{
    color:#f2cf83;
    font-family:Georgia,serif;
    margin-top:34px;
}

p,
li{
    color:#d8d0e4;
}

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

<p>
<a href="/">Astro Avyug</a>
·
<a href="/blog/">Blog</a>
</p>

<article>

<div class="tag">
CATEGORY
</div>

<h1>
TITLE
</h1>

<p>
<strong>
EXCERPT
</strong>
</p>

<figure class="hero">

<img
    src="IMAGE"
    alt="IMAGE_ALT"
    loading="eager"
    decoding="async"
>

<figcaption>
Astro Avyug · विषयानुकूल AI-generated illustration
</figcaption>

</figure>

CONTENT

<div class="notice">
यह लेख ज्योतिषीय/आध्यात्मिक सामान्य मार्गदर्शन के लिए है।
इसे निश्चित भविष्यवाणी या महत्वपूर्ण निर्णय का एकमात्र आधार न मानें।
</div>

</article>

</main>

</body>

</html>
"""


page = (
    template
    .replace("TITLE", title)
    .replace("DESC", desc)
    .replace("URL", url)
    .replace("OG_IMAGE", og_image_url)
    .replace("IMAGE_ALT", image_alt)
    .replace("CATEGORY", cat)
    .replace("EXCERPT", excerpt)
    .replace("IMAGE", image_url)
    .replace("CONTENT", content)
)


# ------------------------------------------------------------
# WRITE ARTICLE
# ------------------------------------------------------------

path.write_text(
    page,
    encoding="utf-8"
)


print("Blog article created:", path)


# ============================================================
# UPDATE BLOG INDEX
# ============================================================

index = BLOG / "index.html"

s = index.read_text(
    encoding="utf-8"
)


marker = (
    '<div class="blog-grid" '
    'id="grid" '
    'style="margin-top:28px">'
)


if marker not in s:
    raise SystemExit(
        "Blog grid marker not found"
    )


card = (
    '<article class="blog-card" '
    'data-cat="' + cat.lower() + '" '
    'data-text="' +
    html.escape(
        a["title"] + " " + a["excerpt"],
        quote=True
    ) +
    '">'
    
    '<a href="/blog/posts/' + slug + '.html" '
    'style="text-decoration:none">'
    
    '<img src="/blog/images/' + slug + '.png" '
    'alt="' + image_alt + '" '
    'loading="lazy" '
    'style="width:100%;height:220px;'
    'object-fit:cover;border-radius:16px;'
    'display:block;margin-bottom:16px">'
    
    '</a>'
    
    '<span class="tag">' + cat + '</span>'
    
    '<h3>' + title + '</h3>'
    
    '<p>' + excerpt + '</p>'
    
    '<div class="read">'
    
    '<a href="/blog/posts/' + slug + '.html">'
    'Read More →'
    '</a>'
    
    '</div>'
    
    '</article>'
)


s = s.replace(
    marker,
    marker + "\n" + card,
    1
)


index.write_text(
    s,
    encoding="utf-8"
)


print("Blog index updated")


# ============================================================
# UPDATE SITEMAP
# ============================================================

sitemap = ROOT / "sitemap.xml"

s = sitemap.read_text(
    encoding="utf-8"
)


if url not in s:

    sitemap.write_text(
        s.replace(
            "</urlset>",
            "  <url>"
            "<loc>" + url + "</loc>"
            "<lastmod>" + date + "</lastmod>"
            "</url>\n"
            "</urlset>"
        ),
        encoding="utf-8"
    )


print("Sitemap updated")

print("")
print("==============================================")
print("ASTRO AVYUG BLOG PUBLISHED SUCCESSFULLY")
print("==============================================")
print("Article:", url)
print("Image:", og_image_url)
print("Date:", date)
print("==============================================")
