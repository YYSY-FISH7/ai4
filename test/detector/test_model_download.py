"""Model download contract: no pip, no overwrite, exact size/SHA before publish."""
import hashlib
import io
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
import urllib.error

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / 'scripts/冲突库下载/install_m4_onnx_deps.sh'


class Response(io.BytesIO):
    def __init__(self, data, length=None, url='https://example.org/model.onnx'):
        super().__init__(data)
        self.headers = {} if length is None else {'Content-Length': str(length)}
        self.url = url

    def geturl(self):
        return self.url


@unittest.skipUnless(sys.platform.startswith('linux'), 'Ubuntu downloader uses fcntl')
class ModelDownloadTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='m4-download-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.deps = self.root / 'lib/m4_onnx'
        self.deps.mkdir(parents=True)
        self.marker = self.deps / 'existing-dependency'
        self.marker.write_bytes(b'unchanged')
        self.path = self.deps / 'model/yolo11s-drone.onnx'
        code = SCRIPT.read_text(encoding='utf-8').split('# BEGIN MODEL DOWNLOAD\n', 1)[1].split('# END MODEL DOWNLOAD', 1)[0]
        self.ns = {'__name__': 'download_test'}
        exec(compile(code, str(SCRIPT), 'exec'), self.ns)
        self.data = b'verified test fixture' * 100
        self.ns['MODEL_SIZE'] = len(self.data)
        self.ns['MODEL_SHA256'] = hashlib.sha256(self.data).hexdigest()
        self.addCleanup(self.assert_preserved)

    def assert_preserved(self):
        self.assertEqual(self.marker.read_bytes(), b'unchanged')
        self.assertFalse(list(self.deps.glob('model/*.part')))

    def download(self, data=None, length=None, path=None, response_url=None):
        response = Response(self.data if data is None else data, length,
                            response_url or 'https://example.org/model.onnx')
        with patch.object(self.ns['urllib'].request.OpenerDirector, 'open', return_value=response):
            return self.ns['download_model'](path or self.path, 'https://example.org/model.onnx')

    def test_verified_download(self):
        self.assertEqual(self.download(), 'downloaded')
        self.assertEqual(self.path.read_bytes(), self.data)

    def test_existing_valid_skips_without_network(self):
        self.path.parent.mkdir()
        self.path.write_bytes(self.data)
        with patch.object(self.ns['urllib'].request.OpenerDirector, 'open', side_effect=AssertionError('network called')):
            self.assertEqual(self.ns['download_model'](self.path, 'unused URL'), 'skipped')

    def test_existing_wrong_file_not_overwritten(self):
        self.path.parent.mkdir()
        self.path.write_bytes(b'original other file')
        with self.assertRaises(ValueError):
            self.download()
        self.assertEqual(self.path.read_bytes(), b'original other file')

    def test_existing_dangling_model_link_preserved(self):
        self.path.parent.mkdir()
        self.path.symlink_to(self.root / 'missing')
        with self.assertRaises(ValueError):
            self.download()
        self.assertTrue(self.path.is_symlink())

    def test_wrong_sha_not_published(self):
        with self.assertRaises(ValueError):
            self.download(data=b'x' * len(self.data))
        self.assertFalse(self.path.exists())

    def test_truncated_download_not_published(self):
        with self.assertRaises(ValueError):
            self.download(data=self.data[:-1])
        self.assertFalse(self.path.exists())

    def test_oversized_download_not_published(self):
        with self.assertRaises(ValueError):
            self.download(data=self.data + b'x')
        self.assertFalse(self.path.exists())

    def test_wrong_content_length_rejected(self):
        with self.assertRaises(ValueError):
            self.download(length=1)
        self.assertFalse(self.path.exists())

    def test_http_error_no_published_or_partial_file(self):
        with patch.object(self.ns['urllib'].request.OpenerDirector, 'open', side_effect=urllib.error.HTTPError('https://example.org', 404, 'missing', {}, None)):
            with self.assertRaises(urllib.error.HTTPError):
                self.ns['download_model'](self.path, 'https://example.org/model.onnx')
        self.assertFalse(self.path.exists())

    def test_remote_plain_http_rejected(self):
        with self.assertRaises(ValueError):
            self.ns['download_model'](self.path, 'http://example.org/model.onnx')

    def test_file_url_rejected(self):
        with self.assertRaises(ValueError):
            self.ns['download_model'](self.path, 'file:///etc/passwd')

    def test_credential_url_rejected(self):
        with self.assertRaises(ValueError):
            self.ns['download_model'](self.path, 'https://user:password@example.org/model')

    def test_unsafe_redirect_rejected(self):
        with self.assertRaises(ValueError):
            self.download(response_url='http://example.org/model')

    def test_missing_dependency_directory_not_created(self):
        p = self.root / 'missing_deps/model/yolo11s-drone.onnx'
        with self.assertRaises(ValueError):
            self.download(path=p)
        self.assertFalse(p.parent.parent.exists())

    def test_dependency_directory_symlink_supported(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.deps, target_is_directory=True)
        self.assertEqual(self.download(path=alias / 'model/yolo11s-drone.onnx'), 'downloaded')
        self.assertTrue(self.path.is_file())

    def test_publish_race_never_overwrites_other_file(self):
        original_link = self.ns['os'].link

        def concurrent_writer(source, destination):
            Path(destination).write_bytes(b'concurrent writer')
            original_link(source, destination)

        with patch.object(self.ns['os'], 'link', side_effect=concurrent_writer):
            with self.assertRaises(FileExistsError):
                self.download()
        self.assertEqual(self.path.read_bytes(), b'concurrent writer')


if __name__ == '__main__':
    unittest.main()
