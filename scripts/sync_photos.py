"""Push or pull photos: uv run python scripts/sync_photos.py push|pull [--dry-run]."""
import argparse
import hashlib
import mimetypes
import os
from pathlib import Path
import tempfile

from azure.core import MatchConditions
from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import BlobServiceClient, ContentSettings
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
PHOTOS = ROOT / 'assets/photos'
EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.avif'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def sync(container, args):
    prefix = os.getenv('AZURE_PHOTO_PREFIX', 'assets/photos/').strip().strip('/')
    if not prefix or any(part in ('', '.', '..') for part in prefix.split('/')) or '\\' in prefix or ':' in prefix:
        raise ValueError('Invalid AZURE_PHOTO_PREFIX')
    prefix += '/'
    remote = {}
    for item in container.list_blobs(name_starts_with=prefix, include=['metadata']):
        name = item.name.removeprefix(prefix)
        if (item.name.startswith(prefix) and name
                and Path(name).suffix.lower() in EXTENSIONS
                and not any(c in name for c in '/\\:')):
            remote[name] = item
    if args.command == 'push' and not PHOTOS.is_dir():
        raise ValueError('Local photo directory is missing')
    names = (sorted(p.name for p in PHOTOS.iterdir()
                    if p.is_file() and p.suffix.lower() in EXTENSIONS)
             if args.command == 'push' else sorted(remote))
    changed = skipped = conflicts = 0
    for name in names:
        path = PHOTOS / name
        blob = container.get_blob_client(prefix + name)
        old = remote.get(name)
        guard = ({'etag': old.etag, 'match_condition': MatchConditions.IfNotModified}
                 if old else {})
        sha = None
        if old:
            sha = (old.metadata or {}).get('sha256')
            if not sha:
                sha = hashlib.sha256(blob.download_blob(**guard).readall()).hexdigest()
        local_sha = digest(path) if path.exists() else None
        if local_sha == sha:
            skipped += 1
            continue
        if args.command == 'pull' and path.exists() and not args.overwrite:
            print(f'Conflict: {name}; use pull --overwrite to replace local content')
            conflicts += 1
            continue
        print(f'{"Would " if args.dry_run else ""}{args.command}: {prefix}{name}')
        if not args.dry_run:
            if args.command == 'push':
                with path.open('rb') as stream:
                    blob.upload_blob(stream, overwrite=bool(old),
                                     metadata={'sha256': local_sha},
                                     content_settings=ContentSettings(
                                         content_type=mimetypes.guess_type(name)[0]
                                         or 'application/octet-stream'), **guard)
            else:
                PHOTOS.mkdir(parents=True, exist_ok=True)
                temporary = None
                try:
                    with tempfile.NamedTemporaryFile(dir=PHOTOS, delete=False) as stream:
                        temporary = Path(stream.name)
                        blob.download_blob(**guard).readinto(stream)
                    if digest(temporary) != sha:
                        raise ValueError('Downloaded checksum mismatch')
                    temporary.replace(path)
                finally:
                    if temporary is not None:
                        temporary.unlink(missing_ok=True)
        changed += 1
    print(f'{"Planned" if args.dry_run else "Synced"}: {changed}; unchanged: {skipped}; conflicts: {conflicts}')
    return 1 if conflicts else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    for command in ('push', 'pull'):
        sub = commands.add_parser(command)
        sub.add_argument('--dry-run', action='store_true')
        if command == 'pull':
            sub.add_argument('--overwrite', action='store_true')
    args = parser.parse_args()
    load_dotenv(ROOT / '.env')
    keys = ('AZURE_STORAGE_CONTAINER_CONNECTION_STRING', 'AZURE_STORAGE_CONTAINER')
    missing = [key for key in keys if not os.getenv(key)]
    if missing:
        parser.error('Missing .env settings: ' + ', '.join(missing))
    try:
        with BlobServiceClient.from_connection_string(os.environ[keys[0]]) as service:
            return sync(service.get_container_client(os.environ[keys[1]]), args)
    except ResourceNotFoundError:
        print('Azure resource not found. Verify AZURE_STORAGE_CONTAINER exists in the account identified by AZURE_STORAGE_CONTAINER_CONNECTION_STRING.')
        return 1
    except Exception as error:
        # Avoid printing SDK messages that may contain credentials in URLs.
        print(f'Sync failed ({type(error).__name__}); check configuration, container access, and connectivity.')
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
