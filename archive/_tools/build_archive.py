"""Build the IAWH Health Journal archive (posts originally published on the Wix blog, 2020-2026).

Inputs : archive/_source/posts/*.md   (Markdown with front matter, one per post)
Outputs: archive/posts/<file>.html     (one article page per post)
         archive/<year>.html           (one table-of-contents page per year)
Run from the repo root:  python3 archive/_tools/build_archive.py
After it runs, archive/_tools/localize_images.py swaps Wix image links for local copies.
"""
import html, json, os, re
from collections import OrderedDict

import markdown

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../archive
SRC = os.path.join(ROOT, '_source', 'posts')
OUT_POSTS = os.path.join(ROOT, 'posts')
MAIN_ARCHIVE = 'https://advancingherhealth.github.io/iawh-journal/IAWH_HealthJournal_Archive.html'
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']

NAV = """  <nav class="site-nav">
    <a class="nav-brand" href="https://www.iawh.org">IAWH Health</a>
    <div class="nav-links">
      <a href="https://www.iawh.org">Home</a>
      <a class="current" href="%s">Health Journal</a>
    </div>
  </nav>""" % MAIN_ARCHIVE

FOOTER = """  <div class="page-footer">
    <div class="footer-name">IAWH Health</div>
    <div class="footer-tagline">Institute for the Advancement of Women's Health</div>
    <div class="footer-links">
      <a href="https://iawh.org">iawh.org</a>
      <a href="mailto:advancingherhealth@iawh.org">advancingherhealth@iawh.org</a>
      <a href="https://iawhhealth.substack.com">Substack</a>
    </div>
    <p class="footer-legal">
      IAWH Health &nbsp;|&nbsp; 1 Northampton Road, Petersburg, Virginia 23805<br />
      &copy; 2026 Institute for the Advancement of Women's Health. All rights reserved.<br />
      HeartStrong is a service mark of IAWH Health.
    </p>
  </div>"""

SCRIPT = """  <script>
    window.addEventListener('load', function () {
      window.scrollTo(0, 0);
      if (window.parent) { window.parent.postMessage({ scrollTo: 0 }, '*'); }
    });
    function notifyHeight() {
      var h = Math.max(document.body.scrollHeight, document.documentElement.scrollHeight,
                       document.body.offsetHeight, document.documentElement.offsetHeight);
      window.parent.postMessage({ height: h }, '*');
    }
    window.addEventListener('load', function () { notifyHeight(); setTimeout(notifyHeight, 500); setTimeout(notifyHeight, 1500); });
    window.addEventListener('resize', notifyHeight);
    if (typeof ResizeObserver !== 'undefined') { new ResizeObserver(notifyHeight).observe(document.body); }
  </script>"""

BASE_CSS = """
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --plum: #4A1942; --plum-deep: #35102f; --plum-light: #f5eef4;
    --gold: #C9A84C; --gold-light: #e2c97e; --gold-pale: #faf3e0;
    --navy: #1B2A4A; --cream: #F8F5F0; --white: #ffffff;
    --text: #2a2a2a; --muted: #6b6b6b; --rule: rgba(74,25,66,0.12);
  }
  html, body { width: 100%; max-width: 100%; overflow-x: hidden; }
  body { font-family: 'DM Sans', Arial, sans-serif; background: var(--cream); color: var(--text); -webkit-font-smoothing: antialiased; }
  img { max-width: 100%; height: auto; }
  .site-nav { background: var(--plum-deep); border-bottom: 2px solid var(--gold); padding: 0 2rem; display: flex; align-items: center; justify-content: space-between; height: 52px; }
  .nav-brand { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.1rem; color: var(--white); text-decoration: none; letter-spacing: 0.04em; }
  .nav-links { display: flex; gap: 1.6rem; }
  .nav-links a { font-size: 0.68rem; letter-spacing: 0.14em; text-transform: uppercase; color: rgba(255,255,255,0.82); text-decoration: none; }
  .nav-links a.current { color: var(--gold); }
  .page-footer { background: var(--plum-deep); padding: 2rem 3rem; text-align: center; border-top: 3px solid var(--gold); }
  .footer-name { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.2rem; color: var(--white); margin-bottom: 0.3rem; }
  .footer-tagline { font-size: 0.62rem; letter-spacing: 0.18em; text-transform: uppercase; color: var(--gold); margin-bottom: 0.8rem; }
  .footer-links a { font-size: 0.74rem; color: rgba(255,255,255,0.82); text-decoration: none; margin: 0 0.6rem; }
  .footer-legal { font-size: 0.62rem; color: rgba(255,255,255,0.5); margin-top: 0.8rem; line-height: 1.6; }
  .year-nav { display: flex; flex-wrap: wrap; gap: 0.5rem; justify-content: center; }
  .year-nav a, .year-nav span { font-size: 0.72rem; letter-spacing: 0.12em; padding: 0.45rem 0.9rem; border: 1px solid var(--rule); color: var(--plum); text-decoration: none; background: var(--white); }
  .year-nav a:hover { border-color: var(--gold); }
  .year-nav span.current { background: var(--plum); color: var(--gold-light); border-color: var(--plum); }
  @media (max-width: 600px) { .site-nav { padding: 0 1rem; } .page-footer { padding: 1.6rem 1.4rem; } }
"""

ARTICLE_CSS = """
  .article-wrapper { max-width: 780px; margin: 0 auto; }
  .article-header { background: var(--plum-deep); padding: 3rem 3rem 2.4rem; border-bottom: 3px solid var(--gold); }
  .article-kicker { font-size: 0.65rem; letter-spacing: 0.22em; text-transform: uppercase; color: var(--gold-light); margin-bottom: 0.8rem; }
  .article-title { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 2.6rem; font-weight: 500; color: var(--white); line-height: 1.15; margin-bottom: 1rem; }
  .article-byline { font-size: 0.72rem; font-weight: 300; color: rgba(255,255,255,0.6); letter-spacing: 0.08em; }
  .article-byline span { color: var(--gold-light); }
  .hero img { width: 100%; max-height: 460px; object-fit: cover; display: block; }
  .hero-video { padding: 1.2rem 3rem 0; font-size: 0.8rem; }
  .article-body { padding: 2.5rem 3rem; }
  .article-body p, .article-body li { font-family: Georgia, serif; font-size: 1rem; line-height: 1.78; color: var(--text); }
  .article-body p { margin-bottom: 1.2rem; }
  .article-body h1, .article-body h2 { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.65rem; font-weight: 500; color: var(--plum); margin: 2.2rem 0 0.8rem; line-height: 1.2; }
  .article-body h3, .article-body h4, .article-body h5, .article-body h6 { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.3rem; font-weight: 600; color: var(--plum); margin: 1.8rem 0 0.6rem; line-height: 1.25; }
  .article-body a { color: var(--plum); }
  .article-body img { display: block; margin: 1.2rem auto 0.4rem; }
  .article-body p img { display: inline-block; margin: 0.4rem; vertical-align: top; max-width: calc(50% - 0.8rem); }
  .article-body p img:only-child { display: block; margin: 1.2rem auto 0.4rem; max-width: 100%; }
  .article-body p em:only-child { display: block; text-align: center; font-family: 'DM Sans', Arial, sans-serif; font-size: 0.78rem; color: var(--muted); }
  .article-body ul, .article-body ol { margin: 0.8rem 0 1.2rem 1.4rem; }
  .article-body li { margin-bottom: 0.4rem; }
  .article-body blockquote { border-left: 3px solid var(--gold); padding: 0.4rem 1.2rem; margin: 1.6rem 0; }
  .article-body blockquote p { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.2rem; font-style: italic; color: var(--plum); }
  .article-body hr { border: none; height: 1px; background: var(--rule); margin: 2rem 0; }
  .article-body table { border-collapse: collapse; width: 100%; margin: 1.2rem 0; font-size: 0.88rem; }
  .article-body th, .article-body td { border: 1px solid var(--rule); padding: 0.5rem; text-align: left; vertical-align: top; }
  .read-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; margin: 1.4rem 0 2rem; }
  .read-card { display: flex; flex-direction: column; background: var(--white); border: 1px solid var(--rule); border-top: 3px solid var(--gold); text-decoration: none; transition: transform 0.2s ease, box-shadow 0.2s ease; }
  .read-card:hover { transform: translateY(-2px); box-shadow: 0 6px 18px rgba(53,16,47,0.12); }
  .article-body .read-card img { width: 100%; height: 150px; object-fit: cover; margin: 0; display: block; max-width: 100%; }
  .read-card span { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.05rem; font-weight: 500; line-height: 1.3; color: var(--plum); padding: 0.7rem 0.8rem 0.9rem; }
  @media (max-width: 600px) { .read-grid { grid-template-columns: 1fr 1fr; } .article-body .read-card img { height: 110px; } .read-card span { font-size: 0.95rem; } }
  .archive-note { border-top: 1px solid var(--rule); margin-top: 2.5rem; padding-top: 1.2rem; font-size: 0.78rem; color: var(--muted); line-height: 1.65; }
  .post-nav { display: flex; justify-content: space-between; gap: 1rem; margin-top: 2rem; font-size: 0.8rem; }
  .post-nav a { color: var(--plum); text-decoration: none; max-width: 48%; }
  .post-nav .next { text-align: right; margin-left: auto; }
  .back { font-size: 0.8rem; margin-top: 1.6rem; }
  .back a { color: var(--plum); }
  @media (max-width: 600px) {
    .article-header { padding: 2rem 1.4rem 1.8rem; }
    .article-title { font-size: 1.9rem; }
    .article-body { padding: 1.8rem 1.4rem; }
    .hero-video { padding: 1rem 1.4rem 0; }
    .article-body p img { max-width: 100%; }
  }
"""

INDEX_CSS = """
  .page-wrapper { max-width: 1000px; margin: 0 auto; }
  .journal-masthead { background: var(--plum-deep); padding: 3.4rem 3rem 2.8rem; text-align: center; border-bottom: 4px solid var(--gold); }
  .masthead-eyebrow { font-size: 0.62rem; letter-spacing: 0.28em; text-transform: uppercase; color: var(--gold); margin-bottom: 0.9rem; }
  .masthead-title { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 3.2rem; font-weight: 400; color: var(--white); line-height: 1.05; }
  .masthead-rule { width: 48px; height: 1px; background: var(--gold); margin: 1rem auto; opacity: 0.7; }
  .masthead-tagline { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.1rem; font-style: italic; font-weight: 300; color: rgba(255,255,255,0.82); }
  .year-bar { padding: 1.6rem 1.6rem 0.4rem; }
  .list-section { padding: 2rem 2rem 3rem; }
  .list-inner { max-width: 720px; margin: 0 auto; }
  .entry { display: flex; gap: 1.2rem; align-items: center; padding: 1rem 0; border-bottom: 1px solid var(--rule); text-decoration: none; color: inherit; transition: padding-left 0.2s ease; }
  .entry:hover { padding-left: 0.4rem; }
  .entry:hover .entry-title { color: var(--plum); }
  .thumb { flex: 0 0 104px; height: 78px; background: linear-gradient(135deg, var(--plum) 0%, var(--navy) 100%); overflow: hidden; }
  .thumb img { width: 100%; height: 100%; object-fit: cover; display: block; }
  .entry-date { font-size: 0.65rem; letter-spacing: 0.14em; text-transform: uppercase; color: var(--muted); margin-bottom: 0.25rem; }
  .entry-title { font-family: 'Cormorant Garamond', Georgia, serif; font-size: 1.3rem; font-weight: 500; color: var(--text); line-height: 1.25; }
  .entry-meta { font-size: 0.68rem; color: var(--gold); letter-spacing: 0.06em; margin-top: 0.3rem; }
  .list-foot { padding: 0 1.6rem 2.6rem; }
  .back { text-align: center; font-size: 0.8rem; margin-top: 1.4rem; }
  .back a { color: var(--plum); }
  @media (max-width: 600px) {
    .journal-masthead { padding: 2.6rem 1.4rem 2.2rem; }
    .masthead-title { font-size: 2.3rem; }
    .list-section { padding: 1.4rem 1.2rem 2.4rem; }
    .thumb { flex-basis: 76px; height: 64px; }
    .entry-title { font-size: 1.12rem; }
  }
"""


def page(title, css, body):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>{html.escape(title)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com" />
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300;0,400;0,500;0,600;1,300;1,400;1,500&family=DM+Sans:wght@300;400;500&display=swap" rel="stylesheet" />
<style>{BASE_CSS}{css}</style>
</head>
<body>
{NAV}
{body}
{SCRIPT}
</body>
</html>
"""


def parse(path):
    text = open(path, encoding='utf-8').read()
    _, fm, body = text.split('---', 2)
    meta = {}
    for line in fm.strip().splitlines():
        k, v = line.split(':', 1)
        v = v.strip()
        if v.startswith('[') or v.startswith('"'):
            v = json.loads(v)
        meta[k.strip()] = v
    return meta, body.strip()


def nice_date(d):
    y, m, day = d.split('-')
    return f'{MONTHS[int(m) - 1]} {int(day)}, {y}'


def year_nav(years, current):
    parts = []
    for y in years:
        if y == current:
            parts.append(f'<span class="current">{y}</span>')
        else:
            parts.append(f'<a href="{y}.html">{y}</a>')
    return '<div class="year-nav">' + ''.join(parts) + '</div>'


posts = []
for fn in sorted(os.listdir(SRC), reverse=True):
    if fn.endswith('.md'):
        meta, body = parse(os.path.join(SRC, fn))
        meta['file'] = fn[:-3] + '.html'
        meta['body'] = body
        meta['year'] = meta['date'][:4]
        posts.append(meta)
posts.sort(key=lambda p: (p['date'], p['file']), reverse=True)
slug_to_file = {p['original_url'].rsplit('/', 1)[-1]: p['file'] for p in posts}
by_year = OrderedDict()
for p in posts:
    by_year.setdefault(p['year'], []).append(p)
years = list(by_year)

os.makedirs(OUT_POSTS, exist_ok=True)
md = markdown.Markdown(extensions=['tables', 'sane_lists'])


SLUGS = sorted(slug_to_file, key=len, reverse=True)


def relink(body):
    # Old iawh.org/post/<slug> links now point to the archived copies.
    # Match the longest known slug, since some link text runs straight into the next word.
    def sub(m):
        got = m.group(1)
        for slug in SLUGS:
            if got.startswith(slug):
                return slug_to_file[slug] + got[len(slug):]
        return m.group(0)
    return re.sub(r'https?://(?:www\.)?iawh\.org/post/([\w%\-]+)', sub, body)


def cardify(body):
    # A row of images followed by a matching list of article links becomes clickable cards
    # (image above its title), instead of a bare image strip with a separate list below.
    pat = re.compile(r'((?:!\[[^\]]*\]\([^)]+\)\n){2,})\n((?:(?:\d+\.|-) \[[^\]]+\]\([^)]+\)\n*){2,})')

    def sub(m):
        imgs = re.findall(r'!\[[^\]]*\]\(([^)]+)\)', m.group(1))
        links = re.findall(r'(?:\d+\.|-) \[([^\]]+)\]\(([^)]+)\)', m.group(2))
        if len(imgs) != len(links):
            return m.group(0)
        cards = ''.join(
            f'<a class="read-card" href="{href}"><img src="{img}" alt="" loading="lazy" />'
            f'<span>{html.escape(title)}</span></a>'
            for img, (title, href) in zip(imgs, links))
        return f'\n<div class="read-grid">{cards}</div>\n\n'
    return pat.sub(sub, body)


def tidy_emphasis(body):
    # Wix often put spaces inside bold/italic runs ("**Sources: **"), which Markdown won't render.
    body = body.replace(' ', ' ')
    body = re.sub(r'(?<![*\w])\*([^*\n]+)\*\*\*', r'***\1***', body)   # "*Word.***" -> bold italic
    body = re.sub(r'\*\*([ \t]*)([^*\n]*?[^*\s])([ \t]+)\*\*', r'\1**\2**\3', body)
    body = re.sub(r'\*\*([ \t]+)([^*\s][^*\n]*?)\*\*', r'\1**\2**', body)
    body = re.sub(r'(?<![*\w])\*([ \t]+)([^*\s][^*\n]*?)\*(?![*\w])', r'\1*\2*', body)
    body = re.sub(r'(?<![*\w])\*([^*\s][^*\n]*?)([ \t]+)\*(?![*\w])', r'*\1*\2', body)
    return body


for i, p in enumerate(posts):
    body = p['body']
    cover = p.get('cover_image')
    # Avoid showing the cover twice when the post body opens with the same image.
    first_img = re.match(r'\s*!\[[^\]]*\]\(([^)]+)\)', body)
    hero = ''
    if cover and not (first_img and first_img.group(1) == cover):
        alt = html.escape(p.get('cover_alt') or p['title'])
        hero = f'  <div class="hero"><img src="{cover}" alt="{alt}" /></div>\n'
    if p.get('cover_video'):
        hero += f'  <p class="hero-video"><a href="{p["cover_video"]}" target="_blank">&#9654; Watch the featured video</a></p>\n'
    md.reset()
    body_html = md.convert(tidy_emphasis(cardify(relink(body))))
    body_html = body_html.replace('<a href="http', '<a target="_blank" rel="noopener" href="http')
    # Remove any leftover emphasis markers Wix's formatting left unpaired (never real text).
    body_html = re.sub(r'(>[^<]*)', lambda m: m.group(1).replace('**', ''), body_html)
    body_html = re.sub(r'(?<=[\s>])\*(?=\s*</)|(?<=>)\*(?=\s)', '', body_html)
    newer = posts[i - 1] if i > 0 else None
    older = posts[i + 1] if i + 1 < len(posts) else None
    nav = '<div class="post-nav">'
    if older:
        nav += f'<a class="prev" href="{older["file"]}">&larr; {html.escape(older["title"])}</a>'
    if newer:
        nav += f'<a class="next" href="{newer["file"]}">{html.escape(newer["title"])} &rarr;</a>'
    nav += '</div>'
    note = p.get('archive_note')
    extra = f' {html.escape(note)}' if note else ''
    tags = p.get('tags') or []
    cats = p.get('categories') or []
    kicker_topic = (cats or [''])[0]
    kicker = 'IAWH Health Journal &nbsp;|&nbsp; From the Archive' + (f' &nbsp;|&nbsp; {html.escape(kicker_topic)}' if kicker_topic else '')
    tag_line = f'<br />Topics: {html.escape(", ".join(tags))}' if tags else ''
    content = f"""<div class="article-wrapper">
  <div class="article-header">
    <p class="article-kicker">{kicker}</p>
    <h1 class="article-title">{html.escape(p['title'])}</h1>
    <p class="article-byline">Originally published <span>{nice_date(p['date'])}</span></p>
  </div>
{hero}  <div class="article-body">
{body_html}
    <p class="archive-note">This article first appeared on the IAWH Health blog on {nice_date(p['date'])} and is preserved here as part of the IAWH Health Journal archive. Information reflects what was known at the time of publication. This article is for general education and is not medical advice.{extra}{tag_line}</p>
    {nav}
    <p class="back"><a href="../{p['year']}.html">&larr; All {p['year']} articles</a> &nbsp;|&nbsp; <a href="{MAIN_ARCHIVE}">IAWH Health Journal Archive</a></p>
  </div>
{FOOTER}
</div>"""
    open(os.path.join(OUT_POSTS, p['file']), 'w', encoding='utf-8').write(
        page(f"{p['title']} | IAWH Health Journal", ARTICLE_CSS, content))

for y, items in by_year.items():
    entries = []
    for p in items:
        thumb = f'<img src="{p["cover_image"]}" alt="" loading="lazy" />' if p.get('cover_image') else ''
        meta_bits = ', '.join((p.get('categories') or []) + (p.get('tags') or [])[:3])
        meta_line = f'<div class="entry-meta">{html.escape(meta_bits)}</div>' if meta_bits else ''
        entries.append(f"""      <a class="entry" href="posts/{p['file']}">
        <div class="thumb">{thumb}</div>
        <div>
          <div class="entry-date">{nice_date(p['date'])}</div>
          <div class="entry-title">{html.escape(p['title'])}</div>
          {meta_line}
        </div>
      </a>""")
    count = len(items)
    content = f"""<div class="page-wrapper">
  <div class="journal-masthead">
    <p class="masthead-eyebrow">IAWH Health Journal &nbsp;|&nbsp; From the Archive</p>
    <h1 class="masthead-title">{y}</h1>
    <div class="masthead-rule"></div>
    <p class="masthead-tagline">{count} article{'s' if count != 1 else ''} published in {y}</p>
  </div>
  <div class="year-bar">{year_nav(years, y)}</div>
  <div class="list-section">
    <div class="list-inner">
{chr(10).join(entries)}
    </div>
  </div>
  <div class="list-foot">
    {year_nav(years, y)}
    <p class="back"><a href="{MAIN_ARCHIVE}">&larr; Back to the IAWH Health Journal Archive</a></p>
  </div>
{FOOTER}
</div>"""
    open(os.path.join(ROOT, f'{y}.html'), 'w', encoding='utf-8').write(
        page(f'{y} Archive | IAWH Health Journal', INDEX_CSS, content))

json.dump([{'year': y, 'count': len(v)} for y, v in by_year.items()],
          open(os.path.join(ROOT, '_tools', 'years.json'), 'w'), indent=1)
print(f'{len(posts)} article pages, {len(years)} year pages:', {y: len(v) for y, v in by_year.items()})
