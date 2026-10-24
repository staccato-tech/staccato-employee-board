#!/usr/bin/env python3
"""Download employee photos from the old WordPress site into assets/photos/
and point data/employees.json at the local copies, so the new site no longer
depends on WP Engine. Run this once from the repo root on a machine that can
reach the old site:

    uv run scripts/localize_photos.py
"""
import json, urllib.request, pathlib, sys
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
urllib.request.install_opener(opener)
ROOT = pathlib.Path(__file__).resolve().parent.parent
data = ROOT / 'data/employees.json'
out = ROOT / 'assets/photos'; out.mkdir(parents=True, exist_ok=True)
emps = json.loads(data.read_text())
ok = fail = 0
for e in emps:
    url = e.get('photo')
    if not url or not url.startswith('http'):
        continue
    dest = out / f"{e['id']}{pathlib.Path(url).suffix.lower() or '.jpg'}"
    try:
        if not dest.exists():
            urllib.request.urlretrieve(url, dest)
        e['photo'] = dest.relative_to(ROOT).as_posix(); ok += 1
    except Exception as ex:
        print('skip', e['name'], ex, file=sys.stderr); fail += 1
data.write_text(json.dumps(emps, indent=1, ensure_ascii=False))
print(f'{ok} photos saved, {fail} failed')
