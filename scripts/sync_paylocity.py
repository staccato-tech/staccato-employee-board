#!/usr/bin/env python3
"""Sync the board with a Paylocity export.

    pip3 install openpyxl            # once
    python3 scripts/sync_paylocity.py path/to/Paylocity_Data_Dump.xlsx            # preview only
    python3 scripts/sync_paylocity.py path/to/Paylocity_Data_Dump.xlsx --write    # save changes

Expected columns: FirstName, LastName, JobTitle, HireDate, BirthDate, Veteran Status

Rules
  * Matching: last name + hire date, then the hand-made pairs in
    data/paylocity_overrides.json ("match").
  * Matched people: title, birthday (month/day only) and veteran status come from
    Paylocity. The board's name, hire date, photo and department are kept.
    Veteran badges are only added or changed, never removed: Paylocity is often blank
    for veterans HR hasn't recorded.
  * People in Paylocity but not on the board are added, unless they're listed in
    "exclude". Use --no-add to skip adding.
  * People on the board but not in Paylocity are listed, never removed.
  * Spelling fixes in "titleFixes" / "nameFixes" are applied every run, so typos
    in Paylocity don't come back.
"""
import argparse, json, re, sys, unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EMP = ROOT / 'data/employees.json'
OVR = ROOT / 'data/paylocity_overrides.json'
VET = {'marine corps': 'Marines', 'marines': 'Marines', 'army': 'Army', 'navy': 'Navy',
       'air force': 'Air Force', 'coast guard': 'Coast Guard', 'space force': 'Space Force'}

def norm(s):
    return re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', str(s or '')).encode('ascii', 'ignore').decode().lower())

def clean(s):
    return re.sub(r'\s+', ' ', str(s or '')).strip()

def read_paylocity(path):
    try:
        import openpyxl
    except ImportError:
        sys.exit('openpyxl is required: pip3 install openpyxl')
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    it = ws.iter_rows(values_only=True)
    head = [norm(h) for h in next(it)]
    col = {k: head.index(norm(k)) for k in ('FirstName', 'LastName', 'JobTitle', 'HireDate', 'BirthDate', 'Veteran Status')}
    rows = []
    for r in it:
        if not r or not any(r):
            continue
        g = lambda k: r[col[k]]
        hire, bday, vet = g('HireDate'), g('BirthDate'), g('Veteran Status')
        rows.append({
            'first': clean(g('FirstName')), 'last': clean(g('LastName')), 'title': clean(g('JobTitle')),
            'hire': hire.date().isoformat() if hasattr(hire, 'date') else (str(hire)[:10] if hire else None),
            'bday': bday.strftime('%m-%d') if hasattr(bday, 'strftime') else None,
            'vet': VET.get(clean(vet).lower(), clean(vet)) if vet else None,
        })
    return rows

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('xlsx')
    ap.add_argument('--write', action='store_true', help='save changes (default is a preview)')
    ap.add_argument('--no-add', action='store_true', help="don't add people who aren't on the board")
    o = ap.parse_args()

    ovr = json.loads(OVR.read_text()) if OVR.exists() else {}
    tfix, nfix = ovr.get('titleFixes', {}), ovr.get('nameFixes', {})
    match = {norm(k): v for k, v in ovr.get('match', {}).items()}
    exclude = {norm(n) for n in ovr.get('exclude', [])}

    emps = json.loads(EMP.read_text())
    by_name = {norm(e['name']): e for e in emps}
    rows = read_paylocity(o.xlsx)

    changes, added, used = [], [], set()
    for r in rows:
        full = f"{r['first']} {r['last']}"
        e = None
        if norm(full) in match:
            e = by_name.get(norm(match[norm(full)]))
        if e is None and r['last'] and r['hire']:
            cands = [x for x in emps if x['hireDate'] == r['hire'] and norm(r['last']) in norm(x['name'])]
            if len(cands) > 1:
                cands = [x for x in cands if norm(x['name']).startswith(norm(r['first'])[:3])]
            e = cands[0] if len(cands) == 1 else None

        title = tfix.get(r['title'], r['title'])
        if e is not None:
            used.add(id(e))
            for field, new in (('title', title), ('birthday', r['bday']), ('service', r['vet'])):
                if field == 'service' and not new:
                    continue                      # never remove a veteran badge
                if new and e.get(field) != new:
                    changes.append(f"  {e['name']}: {field} {e.get(field)!r} -> {new!r}")
                    e[field] = new
        elif not o.no_add and norm(full) not in exclude:
            name = nfix.get(clean(full), clean(full))
            if norm(name) in exclude or norm(name) in by_name:
                continue
            rec = {'id': max(x['id'] for x in emps) + 1, 'name': name, 'title': title, 'department': '',
                   'hireDate': r['hire'], 'photo': None, 'service': r['vet'], 'featured': False, 'birthday': r['bday']}
            emps.append(rec); by_name[norm(name)] = rec; used.add(id(rec))
            added.append(f"  {name} | {title} | hired {r['hire']}")

    # spelling fixes on everyone, every run
    for e in emps:
        if e['title'] in tfix:
            changes.append(f"  {e['name']}: title {e['title']!r} -> {tfix[e['title']]!r}"); e['title'] = tfix[e['title']]
        if e['name'] in nfix:
            changes.append(f"  name {e['name']!r} -> {nfix[e['name']]!r}"); e['name'] = nfix[e['name']]

    missing = [e['name'] for e in emps if id(e) not in used]
    print(f'{len(rows)} Paylocity rows, {len(emps)} on board')
    print(f'\n{len(changes)} updates:'); print('\n'.join(changes) or '  none')
    print(f'\n{len(added)} to add:'); print('\n'.join(added) or '  none')
    print(f'\n{len(missing)} on the board but not matched in Paylocity (left alone):')
    print('  ' + ', '.join(missing) if missing else '  none')

    if o.write:
        emps.sort(key=lambda e: e['hireDate'] or '', reverse=True)
        EMP.write_text(json.dumps(emps, indent=1, ensure_ascii=False))
        print('\nSaved data/employees.json. Review with `git diff`, then commit and push.')
    else:
        print('\nPreview only. Run again with --write to save.')

if __name__ == '__main__':
    main()
