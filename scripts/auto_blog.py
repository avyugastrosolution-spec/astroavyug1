import os,json,re,html,urllib.request
from datetime import datetime,timezone,timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
BLOG=ROOT/"blog"
POSTS=BLOG/"posts"
KEY=os.environ.get("OPENAI_API_KEY")
if not KEY: raise SystemExit("Missing OPENAI_API_KEY")
POSTS.mkdir(parents=True,exist_ok=True)

today=datetime.now(timezone(timedelta(hours=5,minutes=30)))
date=today.strftime("%Y-%m-%d")
prompt=f"""
You are the editorial AI for Astro Avyug, an Indian astrology website.
India date: {date}.
Create ONE original Hindi astrology article relevant to today's genuinely verified significance.
Prefer a verified festival/vrat/observance, astronomical or planetary event, zodiac,
numerology, tarot, Kundli, marriage, relationship or career topic.
Never invent a festival, transit, muhurat, astronomical event or date.
If no major date-specific observance exists, choose a useful evergreen topic.
Return ONLY JSON with title, slug, category, excerpt, meta_description, content_html.
Write natural professional Hindi, 900-1400 words. content_html may use only h2,h3,p,ul,li,strong,blockquote.
Include exactly 3 FAQs and a responsible astrology disclaimer. No high-stakes guarantees,
fabricated citations, clickbait or keyword stuffing.
"""
payload={
 "model":"gpt-5.6-luna",
 "input":prompt,
 "tools":[{"type":"web_search_preview"}],
 "max_output_tokens":6000
}
req=urllib.request.Request(
 "https://api.openai.com/v1/responses",
 data=json.dumps(payload).encode(),
 headers={"Authorization":"Bearer "+KEY,"Content-Type":"application/json"},
 method="POST")
with urllib.request.urlopen(req,timeout=180) as response:
    data=json.load(response)

text=data.get("output_text","")
if not text:
    text="".join(c.get("text","") for item in data.get("output",[])
                 for c in item.get("content",[])
                 if c.get("type") in ("output_text","text"))
m=re.search(r"\{.*\}",text,re.S)
if not m: raise SystemExit("Invalid AI JSON")
a=json.loads(m.group(0))
for k in ("title","slug","category","excerpt","meta_description","content_html"):
    if not a.get(k): raise SystemExit("Missing "+k)

slug=re.sub(r"[^a-z0-9-]+","-",a["slug"].lower()).strip("-") or "astro-avyug-"+date
path=POSTS/(slug+".html")
if path.exists():
    slug += "-"+date
    path=POSTS/(slug+".html")

title=html.escape(a["title"])
cat=html.escape(a["category"])
excerpt=html.escape(a["excerpt"])
desc=html.escape(a["meta_description"])
content=a["content_html"]
url="https://astroavyug.com/blog/posts/"+slug+".html"

template="""<!doctype html>
<html lang="hi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>TITLE | Astro Avyug</title>
<meta name="description" content="DESC">
<link rel="canonical" href="URL">
<link rel="icon" href="/favicon.ico" sizes="any">
<meta property="og:type" content="article">
<meta property="og:title" content="TITLE">
<meta property="og:description" content="DESC">
<meta property="og:url" content="URL">
<style>
body{margin:0;background:linear-gradient(135deg,#070817,#100b25,#071b32);color:#eee;font-family:system-ui;line-height:1.8}
.wrap{max-width:900px;margin:auto;padding:28px 20px 70px}
a{color:#ffe5a1}
article{background:#0a091ed1;border:1px solid #d6a75a33;border-radius:24px;padding:clamp(22px,5vw,50px)}
.tag{color:#e9bf68;font-size:12px;font-weight:800}
h1{font-family:Georgia,serif;color:#ffe5a1;line-height:1.2;font-size:clamp(32px,6vw,56px)}
h2,h3{color:#f2cf83;font-family:Georgia,serif;margin-top:34px}
p,li{color:#d8d0e4}
.notice{margin-top:30px;padding:16px;border:1px solid #ffffff18;border-radius:14px}
</style>
</head>
<body>
<main class="wrap">
<p><a href="/">Astro Avyug</a> · <a href="/blog/">Blog</a></p>
<article>
<div class="tag">CATEGORY</div>
<h1>TITLE</h1>
<p><strong>EXCERPT</strong></p>
CONTENT
<div class="notice">यह लेख ज्योतिषीय/आध्यात्मिक सामान्य मार्गदर्शन के लिए है। इसे निश्चित भविष्यवाणी या महत्वपूर्ण निर्णय का एकमात्र आधार न मानें।</div>
</article>
</main>
</body>
</html>"""
page=(template.replace("TITLE",title).replace("DESC",desc)
      .replace("URL",url).replace("CATEGORY",cat)
      .replace("EXCERPT",excerpt).replace("CONTENT",content))
path.write_text(page,encoding="utf-8")

index= BLOG/"index.html"
s=index.read_text(encoding="utf-8")
marker='<div class="blog-grid" id="grid" style="margin-top:28px">'
if marker not in s: raise SystemExit("Blog grid marker not found")
card='<article class="blog-card" data-cat="'+cat.lower()+'" data-text="'+html.escape(a["title"]+" "+a["excerpt"],quote=True)+'"><span class="tag">'+cat+'</span><h3>'+title+'</h3><p>'+excerpt+'</p><div class="read"><a href="/blog/posts/'+slug+'.html">Read More →</a></div></article>'
index.write_text(s.replace(marker,marker+"\n"+card,1),encoding="utf-8")

sitemap=ROOT/"sitemap.xml"
s=sitemap.read_text(encoding="utf-8")
if url not in s:
    sitemap.write_text(s.replace("</urlset>",'  <url><loc>'+url+'</loc><lastmod>'+date+'</lastmod></url>\n</urlset>'),encoding="utf-8")
print("Published:",url)
