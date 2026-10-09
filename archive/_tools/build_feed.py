"""Build RSS feeds of the archive for importing into Substack.

  archive/feed.xml       all archived posts, full text, original publish dates
  archive/feed-test.xml  ONE older post only, for a safe trial import first

Run after build_archive.py and localize_images.py (it reads the finished article pages):
  python3 archive/_tools/build_feed.py
Image links are made absolute so Substack can fetch them from GitHub Pages.
"""
import html, os, re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../archive
SITE = 'https://advancingherhealth.github.io/iawh-journal/archive'
TEST_POST = '2020-07-28-let-s-keep-writing.html'
EASTERN = timezone(timedelta(hours=-5))
MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August',
          'September', 'October', 'November', 'December']


def item_for(fn):
    page = open(os.path.join(ROOT, 'posts', fn), encoding='utf-8').read()
    title = html.unescape(re.search(r'<h1 class="article-title">(.*?)</h1>', page, re.S).group(1))
    date = fn[:10]
    y, m, d = (int(x) for x in date.split('-'))
    hero = re.search(r'<div class="hero"><img src="([^"]+)"', page)
    body = page.split('<div class="article-body">', 1)[1].split('<p class="archive-note">', 1)[0]
    body = body.replace('../media/', f'{SITE}/media/')
    body = re.sub(r'href="(\d{4}-\d{2}-\d{2}-[^"]+\.html)"', rf'href="{SITE}/posts/\1"', body)
    nice = f'{MONTHS[m - 1]} {d}, {y}'
    lead = (f'<p><em>Originally published on the IAWH Health blog on {nice}. '
            f'Part of the IAWH Health Journal archive.</em></p>')
    cover = f'<p><img src="{hero.group(1).replace("../media/", SITE + "/media/")}" alt="" /></p>' if hero else ''
    content = lead + cover + body.strip()
    pub = format_datetime(datetime(y, m, d, 12, 0, tzinfo=EASTERN))
    link = f'{SITE}/posts/{fn}'
    return f"""    <item>
      <title>{html.escape(title)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{pub}</pubDate>
      <dc:creator>IAWH Health</dc:creator>
      <content:encoded><![CDATA[{content.replace(']]>', ']]]]><![CDATA[>')}]]></content:encoded>
    </item>"""


def write(name, files, title):
    items = '\n'.join(item_for(f) for f in files)
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>{title}</title>
    <link>{SITE}/</link>
    <description>Articles from the IAWH Health blog, 2020-2026, preserved in the IAWH Health Journal archive.</description>
    <language>en-us</language>
{items}
  </channel>
</rss>
"""
    open(os.path.join(ROOT, name), 'w', encoding='utf-8').write(xml)
    print(name, len(files), 'posts')


posts = sorted((f for f in os.listdir(os.path.join(ROOT, 'posts')) if f.endswith('.html')), reverse=True)
# The test post was already imported to Substack on 2026-10-09, so the full feed leaves it out.
write('feed.xml', [p for p in posts if p != TEST_POST], 'IAWH Health Journal Archive')
write('feed-test.xml', [TEST_POST], 'IAWH Health Journal Archive (test)')
