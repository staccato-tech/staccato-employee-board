#!/usr/bin/env python3
"""Download any employee photos still on the old WordPress site into assets/photos/
as originals (assets/photos/<id>.<ext>) and point data/employees.json at them.
Then archive and publish them with:

    uv run python scripts/sync_photos.py push

Usage:  uv run scripts/localize_photos.py
"""
import json, pathlib, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / 'data/employees.json'
OUT = ROOT / 'assets/photos'
OUT.mkdir(parents=True, exist_ok=True)
opener = urllib.request.build_opener()
opener.addheaders = [('User-Agent', 'Mozilla/5.0')]

emps = json.loads(DATA.read_text())
ok = fail = 0
for e in emps:
    url = e.get('photo') or ''
    if not url.startswith('http'):
        continue
    dest = OUT / f"{e['id']}{(pathlib.Path(url.split('?')[0]).suffix.lower() or '.jpg')}"
    try:
        if not dest.exists():
            with opener.open(url.replace('http://', 'https://'), timeout=60) as r:
                dest.write_bytes(r.read())
        e['photo'] = dest.relative_to(ROOT).as_posix(); ok += 1
    except Exception as ex:
        print('skip', e['name'], ex, file=sys.stderr); fail += 1
DATA.write_text(json.dumps(emps, indent=1, ensure_ascii=False))
print(f'{ok} photos saved to assets/photos, {fail} failed')
