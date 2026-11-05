"""Create optimized WebP photos: uv run python scripts/render_photos.py."""
import hashlib
import json
import os
from pathlib import Path
import tempfile

from dotenv import load_dotenv
from PIL import Image, ImageOps, ImageCms
from io import BytesIO

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / 'assets/photos'
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'}


def checksum(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def settings():
    relative = os.getenv('PHOTO_OUTPUT_PATH', 'assets/photos-rendered/').strip().strip('/')
    if not relative or any(p in ('', '.', '..') for p in relative.split('/')) or any(c in relative for c in '\\:?#'):
        raise ValueError('PHOTO_OUTPUT_PATH must be a relative folder')
    output = ROOT / relative
    if output.resolve() == SOURCE.resolve() or SOURCE.resolve() in output.resolve().parents or output.resolve() in SOURCE.resolve().parents:
        raise ValueError('Photo source and output folders must be separate')
    size = int(os.getenv('PHOTO_MAX_SIZE', '960'))
    quality = int(os.getenv('PHOTO_WEBP_QUALITY', '82'))
    if not 1 <= size <= 4096 or not 1 <= quality <= 100:
        raise ValueError('PHOTO_MAX_SIZE must be 1–4096 and PHOTO_WEBP_QUALITY 1–100')
    return output, size, quality


def render(output=None):
    configured, size, quality = settings()
    output = output or configured
    if not SOURCE.is_dir():
        raise ValueError('Missing source photo folder; pull originals first')
    sources = sorted(p for p in SOURCE.iterdir() if p.is_file() and p.suffix.lower() in EXTENSIONS)
    names = [p.stem.lower() for p in sources]
    if len(names) != len(set(names)):
        raise ValueError('Source photos have duplicate stems; WebP filenames would collide')
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = output / '.render-manifest.json'
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    updated = 0
    for source in sources:
        dest = output / (source.stem + '.webp')
        signature = {'source': checksum(source), 'size': size, 'quality': quality, 'version': 1}
        previous = manifest.get(source.name, {})
        if previous.get('settings') == signature and dest.exists() and previous.get('output') == checksum(dest):
            continue
        temporary = None
        try:
            with Image.open(source) as original:
                image = ImageOps.exif_transpose(original)
                alpha = image.convert('RGBA').getchannel('A') if 'A' in image.getbands() or 'transparency' in image.info else None
                profile = image.info.get('icc_profile')
                if profile:
                    image = ImageCms.profileToProfile(image.convert('RGB') if alpha is not None else image,
                        ImageCms.ImageCmsProfile(BytesIO(profile)), ImageCms.createProfile('sRGB'), outputMode='RGB')
                else:
                    image = image.convert('RGB')
                if alpha is not None:
                    image.putalpha(alpha)
                image.thumbnail((size, size), Image.Resampling.LANCZOS)
                image.info.clear()
                with tempfile.NamedTemporaryFile(dir=output, suffix='.webp', delete=False) as stream:
                    temporary = Path(stream.name)
                image.save(temporary, 'WEBP', quality=quality, method=6)
            temporary.replace(dest)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        manifest[source.name] = {'settings': signature, 'output': checksum(dest)}
        updated += 1
    with tempfile.NamedTemporaryFile(mode='w', dir=output, delete=False, encoding='utf-8') as stream:
        json.dump(manifest, stream, indent=2)
        temporary = Path(stream.name)
    temporary.replace(manifest_path)
    print(f'Rendered {updated}; unchanged {len(sources) - updated}')
    return output


if __name__ == '__main__':
    load_dotenv(ROOT / '.env')
    render()
