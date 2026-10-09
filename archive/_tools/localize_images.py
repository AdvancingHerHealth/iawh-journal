"""Download every Wix-hosted image/video used by the archive pages into archive/media/
and point the pages at those local copies. Safe to run repeatedly: files already
downloaded are reused. Run from the repo root:  python3 archive/_tools/localize_images.py
(The GitHub Action in .github/workflows/archive-images.yml runs this automatically.)
"""
import os, re, sys, time, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # .../archive
MEDIA = os.path.join(ROOT, 'media')
PATTERN = re.compile(r'https://(?:static|video)\.wixstatic\.com/[^\s"\')<>]+')
os.makedirs(MEDIA, exist_ok=True)


def local_name(url):
    if 'video.wixstatic.com' in url:
        return url.split('/video/')[1].split('/')[0] + '.mp4'
    name = url.split('/media/')[-1].split('/')[0]
    return re.sub(r'[^\w.~-]', '_', name)


def fetch(url, dest):
    for attempt in range(3):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (IAWH archive)'})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest + '.part', 'wb') as f:
                f.write(r.read())
            os.replace(dest + '.part', dest)
            return True
        except Exception as e:
            print(f'  retry {attempt + 1} {url}: {e}')
            time.sleep(2 * (attempt + 1))
    return False


pages = []
for dirpath, dirs, files in os.walk(ROOT):
    dirs[:] = [d for d in dirs if not d.startswith('_') and d != 'media']
    pages += [os.path.join(dirpath, f) for f in files if f.endswith('.html')]

failed, got, reused = [], 0, 0
for path in sorted(pages):
    text = open(path, encoding='utf-8').read()
    urls = sorted(set(PATTERN.findall(text)))
    if not urls:
        continue
    rel_media = os.path.relpath(MEDIA, os.path.dirname(path)).replace(os.sep, '/')
    for url in urls:
        name = local_name(url)
        dest = os.path.join(MEDIA, name)
        if os.path.exists(dest):
            reused += 1
        elif fetch(url, dest):
            got += 1
        else:
            failed.append(url)
            continue
        text = text.replace(url, f'{rel_media}/{name}')
    open(path, 'w', encoding='utf-8').write(text)

print(f'downloaded {got}, reused {reused}, failed {len(failed)}')
for u in failed:
    print('FAILED', u)
sys.exit(1 if failed else 0)
