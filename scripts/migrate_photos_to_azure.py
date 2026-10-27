#!/usr/bin/env python3
"""Move every image the board uses off the old WordPress site and into
Azure Blob Storage, then point the site's data files at the Azure copies.

Run on your Mac from the repo root, signed in with `az login`:

    python3 scripts/migrate_photos_to_azure.py --account <storage-account> [--container employee-board]

Steps
  1. Download every employee photo and bulletin image still served from
     WP Engine into ./_migrate/ (skips files already downloaded).
  2. Create the container (anonymous read on blobs only) if it doesn't exist.
  3. Upload with `az storage blob upload-batch` (correct Content-Type, long cache).
  4. Rewrite data/employees.json and data/bulletins.json to the blob URLs.

Re-running is safe. Use --dry-run to see what would happen without uploading
or rewriting anything. Use --sas "<token>" instead of `az login` if you prefer.
"""
import argparse, json, mimetypes, pathlib, re, subprocess, sys, urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
WP_HOST = 'stacemployees.wpenginepowered.com'
WORK = ROOT / '_migrate'

def az(args, sas):
    cmd = ['az', *args] + (['--sas-token', sas] if sas else ['--auth-mode', 'login'])
    print('  $ az', ' '.join(a for a in args if not a.startswith('?')))
    subprocess.run(cmd, check=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--account', required=True, help='Azure storage account name')
    ap.add_argument('--container', default='employee-board')
    ap.add_argument('--sas', help='SAS token instead of az login')
    ap.add_argument('--dry-run', action='store_true')
    o = ap.parse_args()
    base = f'https://{o.account}.blob.core.windows.net/{o.container}'

    emp_path, bul_path = ROOT / 'data/employees.json', ROOT / 'data/bulletins.json'
    emps = json.loads(emp_path.read_text())
    buls = json.loads(bul_path.read_text())

    # url -> blob name
    jobs = {}
    for e in emps:
        u = e.get('photo') or ''
        if WP_HOST in u:
            ext = pathlib.Path(u.split('?')[0]).suffix.lower() or '.jpg'
            jobs[u] = f'employees/{e["id"]}{ext}'
    for b in buls:
        for u in re.findall(r'''(?:src|url)=?["']?\s*:?\s*["']?(https?://%s/[^"'\s)]+)''' % re.escape(WP_HOST), b['html']):
            jobs[u] = 'bulletins/' + pathlib.Path(u.split('?')[0]).name
    if not jobs:
        print('Nothing left on WP Engine. Already migrated.'); return
    print(f'{len(jobs)} images to migrate -> {base}')

    # 1. download
    ok = {}
    for u, name in jobs.items():
        dest = WORK / name
        dest.parent.mkdir(parents=True, exist_ok=True)
        try:
            if not dest.exists() or dest.stat().st_size == 0:
                req = urllib.request.Request(u.replace('http://', 'https://'), headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=60) as r, open(dest, 'wb') as f:
                    f.write(r.read())
            ok[u] = name
        except Exception as ex:
            print(f'  ! download failed, keeping old URL: {u} ({ex})', file=sys.stderr)
    print(f'downloaded {len(ok)}/{len(jobs)}')
    if o.dry_run:
        print('dry run: stopping before upload'); return

    # 2-3. container + upload
    try:
        az(['storage', 'container', 'create', '--account-name', o.account, '--name', o.container, '--public-access', 'blob'], o.sas)
    except subprocess.CalledProcessError:
        print('  (container create failed; it may already exist, continuing)')
    az(['storage', 'blob', 'upload-batch', '--account-name', o.account, '--destination', o.container,
        '--source', str(WORK), '--overwrite', 'true', '--content-cache-control', 'public, max-age=604800'], o.sas)

    # 4. rewrite data
    for e in emps:
        if e.get('photo') in ok:
            e['photo'] = f'{base}/{ok[e["photo"]]}'
    for b in buls:
        for u, name in ok.items():
            b['html'] = b['html'].replace(u, f'{base}/{name}')
    emp_path.write_text(json.dumps(emps, indent=1, ensure_ascii=False))
    bul_path.write_text(json.dumps(buls, indent=1, ensure_ascii=False))

    # quick check
    sample = next((f'{base}/{n}' for n in ok.values()), None)
    if sample:
        try:
            urllib.request.urlopen(urllib.request.Request(sample, method='HEAD'), timeout=20)
            print(f'verified public read: {sample}')
        except Exception as ex:
            print(f'WARNING: {sample} is not publicly readable ({ex}). '
                  'Enable "Allow Blob anonymous access" on the storage account and re-run.', file=sys.stderr)
    print('Done. Review with `git diff --stat`, then commit and push.')

if __name__ == '__main__':
    main()
