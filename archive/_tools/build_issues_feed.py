"""Build an RSS feed of the August and September 2026 journal articles for importing into Substack.

The article pages embed their images directly in the HTML (data: URIs), which Substack's importer
can't fetch. This script saves each embedded image as a file under archive/media/issues/ and writes
archive/feed-issues-2026.xml with absolute image links. The article pages themselves are not changed.

Run from the repo root:  python3 archive/_tools/build_issues_feed.py
"""
import base64, hashlib, html, os, re
from datetime import datetime, timezone, timedelta
from email.utils import format_datetime

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MEDIA = os.path.join(REPO, 'archive', 'media', 'issues')
SITE = 'https://advancingherhealth.github.io/iawh-journal'
EASTERN = timezone(timedelta(hours=-4))   # EDT in late summer
EXT = {'jpeg': 'jpg', 'jpg': 'jpg', 'png': 'png', 'webp': 'webp', 'gif': 'gif', 'svg+xml': 'svg'}

# File, publish date (date first added to the journal), newest issue first within each date.
ARTICLES = [
    ('IAWH_Article_AFib_Sep2026.html', '2026-09-29'),
    ('IAWH_Article_GLP1_Sep2026.html', '2026-09-29'),
    ('IAWH_Article_Soup_Sep2026.html', '2026-09-29'),
    ('IAWH_Article_Medication_Aug2026.html', '2026-08-27'),
    ('IAWH_Article_WatchingRoundup_Aug2026.html', '2026-08-27'),
    ('IAWH_Article_AnnualExam_Aug2026.html', '2026-08-27'),
]
os.makedirs(MEDIA, exist_ok=True)


def save_data_uri(m):
    kind, data = m.group(1), m.group(2)
    raw = base64.b64decode(data)
    name = hashlib.sha1(raw).hexdigest()[:16] + '.' + EXT.get(kind, 'bin')
    path = os.path.join(MEDIA, name)
    if not os.path.exists(path):
        open(path, 'wb').write(raw)
    return f'{SITE}/archive/media/issues/{name}'


def item(fn, date):
    page = open(os.path.join(REPO, fn), encoding='utf-8').read()
    page = re.sub(r'data:image/([a-z+]+);base64,([A-Za-z0-9+/=\s]+)', save_data_uri, page)
    title = html.unescape(re.sub(r'<[^>]+>', '', re.search(r'<h1 class="article-title">(.*?)</h1>', page, re.S).group(1))).strip()
    kicker = re.sub(r'<[^>]+>', '', re.search(r'<p class="article-kicker">(.*?)</p>', page, re.S).group(1))
    byline = re.sub(r'<[^>]+>', '', re.search(r'<p class="article-byline">(.*?)</p>', page, re.S).group(1))
    kicker = html.unescape(kicker).replace('\xa0', ' ').strip()
    byline = html.unescape(byline).replace('\xa0', ' ').split('|')[0].strip()
    wrapper = page.split('<div class="article-wrapper">', 1)[1]
    header_end = wrapper.index('</div>', wrapper.index('<div class="article-header">')) + len('</div>')
    after_header = wrapper[header_end:]
    pre_body, body = after_header.split('<div class="article-body">', 1)
    body = body.split('<div class="article-footer">', 1)[0]
    body = re.sub(r'<p class="back">.*?</p>', '', body, flags=re.S)
    body = re.sub(r'</div>\s*$', '', body.strip())
    # Images shown above the article body (hero) and their captions.
    lead_imgs = ''.join(f'<p>{tag}</p>' for tag in re.findall(r'<img[^>]+>', pre_body))
    lead_caps = ''.join(f'<p><em>{c.strip()}</em></p>' for c in re.findall(r'<p class="hero-caption">(.*?)</p>', pre_body, re.S))
    intro = f'<p><em>{html.escape(byline)}. From the IAWH Health Journal, {html.escape(re.sub(r"\s*\|\s*", ", ", kicker.split("|", 1)[1].strip() if "|" in kicker else kicker))}.</em></p>'
    content = intro + lead_imgs + lead_caps + body
    content = re.sub(r'\sstyle="[^"]*"', '', content)
    y, m, d = (int(x) for x in date.split('-'))
    link = f'{SITE}/{fn}'
    pub = format_datetime(datetime(y, m, d, 12, 0, tzinfo=EASTERN))
    return title, f"""    <item>
      <title>{html.escape(title)}</title>
      <link>{link}</link>
      <guid isPermaLink="true">{link}</guid>
      <pubDate>{pub}</pubDate>
      <dc:creator>{html.escape(byline.replace('By ', '').replace('From the ', ''))}</dc:creator>
      <content:encoded><![CDATA[{content.replace(']]>', ']]]]><![CDATA[>')}]]></content:encoded>
    </item>"""


items = [item(f, d) for f, d in ARTICLES]
xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/" xmlns:dc="http://purl.org/dc/elements/1.1/">
  <channel>
    <title>IAWH Health Journal, August and September 2026</title>
    <link>{SITE}/IAWH_HealthJournal_Archive.html</link>
    <description>Articles from the August and September 2026 issues of the IAWH Health Journal.</description>
    <language>en-us</language>
{chr(10).join(x for _, x in items)}
  </channel>
</rss>
"""
open(os.path.join(REPO, 'archive', 'feed-issues-2026.xml'), 'w', encoding='utf-8').write(xml)
for t, _ in items:
    print(' -', t)
print(len(items), 'articles;', len(os.listdir(MEDIA)), 'images saved in archive/media/issues')
