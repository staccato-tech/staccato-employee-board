"""Run with uv run python -m unittest discover -s scripts -p 'test_*.py'."""
import hashlib
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from PIL import Image
import render_photos
import sync_photos


class PhotoTests(unittest.TestCase):
    def test_render_and_invalidation(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            output = Path(directory) / 'output'
            source.mkdir()
            image = Image.new('RGB', (1200, 600), 'red')
            exif = Image.Exif()
            exif[274] = 6
            image.save(source / '123.jpg', exif=exif)
            original_hash = render_photos.checksum(source / '123.jpg')
            with patch.object(render_photos, 'SOURCE', source), patch.object(render_photos, 'settings', return_value=(output, 960, 82)):
                render_photos.render()
                dest = output / '123.webp'
                with Image.open(dest) as result:
                    self.assertEqual(result.size, (480, 960))
                    self.assertFalse(result.getexif())
                stamp = dest.stat().st_mtime_ns
                render_photos.render()
                self.assertEqual(dest.stat().st_mtime_ns, stamp)
                Image.new('RGB', (100, 50), 'blue').save(source / '123.jpg')
                render_photos.render()
                with Image.open(dest) as result:
                    self.assertEqual(result.size, (100, 50))
            self.assertNotEqual(render_photos.checksum(source / '123.jpg'), original_hash)

    def test_source_preservation_transparency_and_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / 'source'
            output = Path(directory) / 'output'
            source.mkdir()
            path = source / '1.png'
            Image.new('RGBA', (20, 30), (255, 0, 0, 0)).save(path)
            before = path.read_bytes()
            with patch.object(render_photos, 'SOURCE', source), patch.object(render_photos, 'settings', return_value=(output, 960, 82)):
                render_photos.render()
                self.assertEqual(path.read_bytes(), before)
                with Image.open(output / '1.webp') as result:
                    self.assertEqual(result.getpixel((0, 0))[3], 0)
                Image.new('RGB', (20, 30)).save(source / '1.jpg')
                with self.assertRaisesRegex(ValueError, 'collide'):
                    render_photos.render()

    def test_sync_prefix_and_pull(self):
        with tempfile.TemporaryDirectory() as directory:
            photos = Path(directory)
            path = photos / '123.webp'
            path.write_bytes(b'rendered')
            container = Mock()
            container.list_blobs.return_value = []
            args = SimpleNamespace(command='push', dry_run=True)
            sync_photos.sync(container, args, photos, 'assets/photos-rendered/')
            container.get_blob_client.assert_called_with('assets/photos-rendered/123.webp')
            container.get_blob_client.return_value.upload_blob.assert_not_called()
            args.dry_run = False
            sync_photos.sync(container, args, photos, 'assets/photos-rendered/')
            self.assertEqual(container.get_blob_client.return_value.upload_blob.call_args.kwargs['content_settings'].content_type, 'image/webp')
            path.unlink()
            remote = SimpleNamespace(name='assets/photos-rendered/123.webp', metadata={'sha256': hashlib.sha256(b'rendered').hexdigest()}, etag='etag')
            container.list_blobs.return_value = [remote]
            container.get_blob_client.return_value.download_blob.return_value.readinto.side_effect = lambda stream: stream.write(b'rendered')
            args.command = 'pull'
            args.overwrite = False
            sync_photos.sync(container, args, photos, 'assets/photos-rendered/')
            self.assertEqual(path.read_bytes(), b'rendered')
            self.assertFalse((photos / 'assets').exists())


if __name__ == '__main__':
    unittest.main()
