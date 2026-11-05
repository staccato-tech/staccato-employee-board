"""Export public photo settings: uv run python scripts/configure_frontend.py."""
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv
from render_photos import settings

ROOT = Path(__file__).resolve().parent.parent


def main():
    load_dotenv(ROOT / '.env')
    web_url = os.getenv('AZURE_WEB_URL', '').strip().rstrip('/')
    prefix = os.getenv('AZURE_RENDERED_PHOTO_PREFIX', 'assets/photos-rendered/').strip().strip('/')
    parsed = urlsplit(web_url)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.query or parsed.fragment or parsed.username or parsed.password:
        raise SystemExit('AZURE_WEB_URL must be an HTTP(S) base URL without credentials, query, or fragment.')
    if not prefix or any(p in ('', '.', '..') for p in prefix.split('/')) or any(c in prefix for c in '\\:?#'):
        raise SystemExit('AZURE_RENDERED_PHOTO_PREFIX must be a relative container folder.')
    # Explicit allowlist: never export connection strings or other environment values.
    output, _, _ = settings()
    config = {'photoWebUrl': web_url, 'photoPrefix': prefix + '/',
              'photoLocalPath': output.relative_to(ROOT).as_posix() + '/', 'photoExtension': '.webp'}
    (ROOT / 'data/config.json').write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    print('Updated public photo settings in data/config.json')


if __name__ == '__main__':
    main()
