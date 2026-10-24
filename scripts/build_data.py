#!/usr/bin/env python3
"""Convert a WordPress export (Tools > Export) from the old Employee Board
into the JSON files this site reads.

    uv run scripts/build_data.py path/to/export.xml

Writes data/employees.json and data/bulletins.json.
"""
import json, re, sys, html
import xml.etree.ElementTree as ET
from pathlib import Path

NS = {'wp': 'http://wordpress.org/export/1.2/',
      'content': 'http://purl.org/rss/1.0/modules/content/'}
ROOT = Path(__file__).resolve().parent.parent
PLACEHOLDER_PHOTOS = {'Star_blu_SF.png'}

DEPT_MAP = {
    'ops- machine shop': 'Machine Shop', 'machine shop': 'Machine Shop',
    'gun shop': 'Gun Shop', 'coating department': 'Coating',
    'customer service - ts': 'Customer Service', 'customer service': 'Customer Service',
    'customer - kb': 'Customer Service',
    'ops - new product development': 'New Product Development',
    'sales leo - old': 'Sales – LEO', 'sales leo': 'Sales – LEO',
    'selling - business development': 'Business Development', 'sales - bda': 'Business Development',
    'accounting': 'Accounting', 'marketing': 'Marketing', 'ecommerce': 'Ecommerce',
    'warranty': 'Warranty', 'engineering': 'Engineering', 'operations': 'Operations',
    'purchasing department': 'Purchasing', 'administrative': 'Administrative',
    'ops- facilities': 'Facilities', 'facilities': 'Facilities',
    'human resources': 'Human Resources', 'quality': 'Quality',
    'it': 'IT', 'information technology': 'IT',
    'ops- shipping and receiving': 'Shipping & Receiving', 'ops- inventory': 'Inventory',
    'stg': 'STG',
}

def clean_dept(raw):
    s = (raw or '').strip()
    s = re.sub(r'^department\s+', '', s, flags=re.I)
    s = re.sub(r'^\d{3}\s*-\s*', '', s)           # "910 - OPS- Machine Shop"
    if re.fullmatch(r'[A-Z]?\d{5,}', s):          # stray employee IDs
        return ''
    return DEPT_MAP.get(s.lower(), s.title())

def meta(it):
    return {pm.findtext('wp:meta_key', namespaces=NS): pm.findtext('wp:meta_value', namespaces=NS) or ''
            for pm in it.findall('wp:postmeta', namespaces=NS)}

def main(path):
    ch = ET.parse(path).getroot().find('channel')
    items = ch.findall('item')
    att = {it.findtext('wp:post_id', namespaces=NS): it.findtext('wp:attachment_url', namespaces=NS)
           for it in items if it.findtext('wp:post_type', namespaces=NS) == 'attachment'}
    emps, bulletins = [], []
    for it in items:
        ptype = it.findtext('wp:post_type', namespaces=NS)
        if it.findtext('wp:status', namespaces=NS) != 'publish':
            continue
        m = meta(it)
        if ptype == 'employee':
            photo = att.get(m.get('_thumbnail_id', ''))
            if photo and photo.rsplit('/', 1)[-1] in PLACEHOLDER_PHOTOS:
                photo = None
            if photo:
                photo = photo.replace('http://', 'https://')
            emps.append({
                'id': int(it.findtext('wp:post_id', namespaces=NS)),
                'name': html.unescape(it.findtext('title') or '').strip(),
                'title': m.get('_employee_job_title', '').strip(),
                'department': clean_dept(m.get('_employee_department')),
                'hireDate': m.get('_employee_hire_date') or None,
                'photo': photo,
                'service': m.get('_employee_category') or None,
                'featured': m.get('_employee_featured') in ('yes', '1'),
                'birthday': m.get('_employee_birthday') in ('yes', '1'),
            })
        elif ptype == 'bulletin':
            body = it.findtext('content:encoded', namespaces=NS) or ''
            bulletins.append({
                'id': int(it.findtext('wp:post_id', namespaces=NS)),
                'title': html.unescape(it.findtext('title') or '').strip(),
                'type': m.get('_bulletin_type') or 'info',
                'expires': m.get('_bulletin_expiration') or None,
                'html': body,
            })
    emps.sort(key=lambda e: e['hireDate'] or '', reverse=True)
    (ROOT / 'data').mkdir(exist_ok=True)
    (ROOT / 'data/employees.json').write_text(json.dumps(emps, indent=1, ensure_ascii=False))
    (ROOT / 'data/bulletins.json').write_text(json.dumps(bulletins, indent=1, ensure_ascii=False))
    print(f'{len(emps)} employees, {len(bulletins)} bulletins')

if __name__ == '__main__':
    main(sys.argv[1])
