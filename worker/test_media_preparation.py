"""Versioned authentic photos must be verified without another network fetch."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from PIL import Image
from prepare_blackberry_media import prepare_asset

class VersionedPhotoTests(unittest.TestCase):
    def test_verified_original_is_reused_without_network_and_corruption_is_rejected(self):
        parent=Path(__file__).resolve().parents[1]/"renders/media-tests"
        parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=parent) as temp:
            root=Path(temp)/"public"
            picture=root/"assets/images/blackberry-redo/test.jpg"
            picture.parent.mkdir(parents=True)
            Image.new("RGB",(32,24),(45,56,67)).save(picture,"JPEG")
            source={"id":"test","original":"https://example.org/photo","reuseFamily":"photo-one",
                    "author":"Test author","license":"CC BY 4.0"}
            asset={"id":"test","kind":"image","src":"assets/images/blackberry-redo/test.jpg",
                   "label":"Test photo","preparedSha256":hashlib.sha256(picture.read_bytes()).hexdigest()}
            with patch("prepare_blackberry_media.download_source",side_effect=AssertionError("Network must not be used")):
                actual=prepare_asset(source,asset,root,Path(temp)/"cache","missing-ffmpeg","missing-ffprobe")
                self.assertEqual((actual["width"],actual["height"]),(32,24))
                self.assertEqual(actual["reuseFamily"],"photo-one")
                picture.write_bytes(b"damaged")
                with self.assertRaisesRegex(ValueError,"checksum mismatch"):
                    prepare_asset(source,asset,root,Path(temp)/"cache","missing-ffmpeg","missing-ffprobe")

if __name__=="__main__":unittest.main()
