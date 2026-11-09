#!/usr/bin/env python3
"""Import a folder of headshots named after employees ("First Last.jpg") into the board.

    uv run scripts/import_headshots.py "path/to/Edited"            # preview
    uv run scripts/import_headshots.py "path/to/Edited" --write    # import

For each photo it finds the employee by name (exact match, or through
data/headshot_aliases.json), saves a 2400px JPEG original as
assets/photos/<id>-<date>.jpg and points that person's `photo` at it.
Subfolders are included. Files that don't match anyone are listed and skipped.

Then publish the photos to Azure and the board:

    uv run python scripts/sync_photos.py push
    git commit -am "Add new headshots" && git push
"""
import argparse, datetime, json, re, sys
from pathlib import Path
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / 'data/employees.json'
ALIASES = ROOT / 'data/headshot_aliases.json'
OUT = ROOT / 'assets/photos'
EXTS = {'.jpg', '.jpeg', '.png', '.tif', '.tiff', '.heic', '.webp'}

def key(s):
    return re.sub(r'\s+', ' ', s).strip().lower()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('folder')
    ap.add_argument('--write', action='store_true')
    ap.add_argument('--max', type=int, default=2400, help='longest side of the saved original (px)')
    o = ap.parse_args()

    emps = json.loads(DATA.read_text())
    by_name = {key(e['name']): e for e in emps}
    aliases = {key(k): v for k, v in json.loads(ALIASES.read_text()).items() if not k.startswith('_')} if ALIASES.exists() else {}
    stamp = datetime.date.today().strftime('%Y%m')

    files = sorted(p for p in Path(o.folder).expanduser().rglob('*') if p.is_file() and p.suffix.lower() in EXTS)
    matched, unmatched, dupes = [], [], {}
    for f in files:
        name = re.sub(r'\s*\(\d+\)$', '', f.stem)          # "Sam Sanderford (1)" -> "Sam Sanderford"
        e = by_name.get(key(aliases.get(key(name), name)))
        if not e:
            unmatched.append(f.name); continue
        if e['id'] in dupes:                                 # two files for one person: prefer the one without a
            prev = dupes[e['id']][0]                         # "(1)" copy suffix, which can be a misnamed photo
            print(f"  Note: two photos for {e['name']}: {prev.name} and {f.name}")
            if re.search(r'\(\d+\)$', f.stem) or not re.search(r'\(\d+\)$', prev.stem):
                continue
            matched.remove(dupes[e['id']])
        dupes[e['id']] = (f, e)
        matched.append((f, e))

    print(f'{len(files)} photos, {len(matched)} matched, {len(unmatched)} not matched\n')
    for f, e in sorted(matched, key=lambda m: m[1]['name']):
        print(f"  {f.name:32} -> {e['name']}{'  (replaces existing photo)' if e.get('photo') else ''}")
    if unmatched:
        print('\nNot matched (add to data/headshot_aliases.json if they belong to someone):')
        print('\n'.join('  ' + n for n in unmatched))
    if not o.write:
        print('\nPreview only. Run again with --write to import.'); return

    OUT.mkdir(parents=True, exist_ok=True)
    for f, e in matched:
        dest = OUT / f"{e['id']}-{stamp}.jpg"
        with Image.open(f) as im:
            im = ImageOps.exif_transpose(im).convert('RGB')
            im.thumbnail((o.max, o.max), Image.Resampling.LANCZOS)
            im.save(dest, 'JPEG', quality=90, optimize=True)
        e['photo'] = dest.relative_to(ROOT).as_posix()
    DATA.write_text(json.dumps(emps, indent=1, ensure_ascii=False))
    print(f'\nSaved {len(matched)} photos to assets/photos and updated data/employees.json.')
    print('Next: uv run python scripts/sync_photos.py push   (uploads to Azure), then commit and push.')

if __name__ == '__main__':
    main()
