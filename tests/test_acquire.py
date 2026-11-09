import tempfile
import unittest
import hashlib
from pathlib import Path
from src.acquire import save_verified

class SourceAcquisitionTests(unittest.TestCase):
    def test_changed_source_is_rejected_without_writing(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            with self.assertRaises(ValueError):
                save_verified(path, b'changed', hashlib.sha256(b'original').hexdigest())
            self.assertFalse(path.exists())

    def test_exact_snapshot_is_saved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            save_verified(path, b'original', hashlib.sha256(b'original').hexdigest())
            self.assertEqual(path.read_bytes(), b'original')

    def test_existing_snapshot_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.json'
            path.write_bytes(b'existing')
            with self.assertRaises(FileExistsError):
                save_verified(path, b'new', hashlib.sha256(b'new').hexdigest())
            self.assertEqual(path.read_bytes(), b'existing')
