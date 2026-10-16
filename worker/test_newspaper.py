"""Offline checks for optional document overlays, provenance and unchanged narration."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from build_episode import build_episode, build_newspaper


class NewspaperTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / "renders/newspaper-test-temp"
        test_root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=test_root)
        if not Path(self.directory.name).resolve().is_relative_to(test_root.resolve()):
            raise ValueError("Test directory escaped the workspace output folder.")
        self.addCleanup(self.directory.cleanup)
        self.public = Path(self.directory.name)
        (self.public / "clipping.png").write_bytes(b"image fixture")
        self.asset = {"key": "clipping", "src": "clipping.png", "kind": "image",
                      "credit": "Archive scan / CC0", "publication": "Verified original publication",
                      "origin": "https://example.org/archive/document", "date": "January 10, 2007"}
        self.assets = {"clipping": [self.asset]}

    def test_clipping_preserves_catalog_provenance_and_normalized_highlights(self):
        credits = {}
        result = build_newspaper({"mode": "clipping", "mediaKey": "clipping", "atSeconds": 12.5,
                                 "durationSeconds": 11, "highlightBoxes": [
                                     {"x": .1, "y": .2, "width": .6, "height": .08}]},
                                self.assets, 1200, self.public, credits, "scene")
        self.assertEqual(result["from"], 375)
        self.assertEqual(result["durationInFrames"], 330)
        self.assertEqual(result["imageSrc"], "clipping.png")
        self.assertEqual(result["sourceUrl"], self.asset["origin"])
        self.assertEqual(result["source"], self.asset["publication"])
        self.assertEqual(result["highlightBoxes"][0]["x"], .1)
        self.assertIn(self.asset["publication"], credits["newspaper:scene"]["credit"])
        self.assertEqual(credits["newspaper:scene"]["origin"], self.asset["origin"])

    def test_defaults_fit_remaining_scene_without_extending_it(self):
        result = build_newspaper({"mode": "reconstruction", "headline": "An editorial explanation",
                                 "highlightWords": ["explanation"]}, {}, 90, self.public, {}, "scene")
        self.assertEqual(result["from"], 0)
        self.assertEqual(result["durationInFrames"], 90)
        self.assertEqual(result["highlightWords"], ["explanation"])
        self.assertEqual(result["mode"], "reconstruction")
        self.assertNotIn("imageSrc", result)

    def test_generated_asset_cannot_lose_its_reconstruction_label(self):
        self.asset["origin"] = "generated"
        self.asset["reconstruction"] = True
        credits = {}
        result = build_newspaper({"mode": "clipping", "mediaKey": "clipping"},
                                self.assets, 600, self.public, credits, "scene")
        self.assertEqual(result["mode"], "reconstruction")
        self.assertIn("Editorial reconstruction", credits["newspaper:scene"]["credit"])

    def test_invalid_timing_missing_files_and_outside_highlights_are_concrete_errors(self):
        base = {"mode": "clipping", "mediaKey": "clipping"}
        for timing in ({"atSeconds": float("nan")}, {"durationSeconds": -1}, {"atSeconds": 20}):
            with self.subTest(timing=timing), self.assertRaises(ValueError):
                build_newspaper({**base, **timing}, self.assets, 300, self.public, {}, "scene")
        with self.assertRaisesRegex(ValueError, "inside the original image"):
            build_newspaper({**base, "highlightBoxes": [{"x": .8, "y": 0, "width": .4, "height": .1}]},
                            self.assets, 300, self.public, {}, "scene")
        (self.public / "clipping.png").unlink()
        with self.assertRaisesRegex(ValueError, "does not exist"):
            build_newspaper(base, self.assets, 300, self.public, {}, "scene")

    def test_overlay_does_not_replace_chart_quote_shots_or_audio(self):
        source = {"id": "newspaper-test", "title": "A documentary", "acts": [{"id": "act", "title": "Act",
                  "scenes": [{"id": "scene", "narration": "The full narration stays unchanged.",
                              "visualKeys": ["clipping"], "chart": {"title": "Data", "values": []},
                              "quote": {"text": "Verified words", "author": "Witness"}}]}]}
        catalog = {"assets": [self.asset]}
        with patch("build_episode.cached_scene", return_value={"durationSeconds": 910}):
            original = build_episode(source, catalog, self.public, self.public)
            altered = copy.deepcopy(source)
            altered["acts"][0]["scenes"][0]["newspaper"] = {
                "mode": "clipping", "mediaKey": "clipping", "atSeconds": 23, "durationSeconds": 15}
            result = build_episode(altered, catalog, self.public, self.public)
        original_scene = original["acts"][0]["scenes"][0]
        output = result["acts"][0]["scenes"][0]
        self.assertEqual(output["shots"], original_scene["shots"])
        self.assertEqual({shot["type"] for shot in output["shots"]}, {"image", "chart", "quote"})
        self.assertEqual(output["audioSrc"], original_scene["audioSrc"])
        self.assertEqual(output["narration"], original_scene["narration"])
        self.assertEqual(result["durationInFrames"], original["durationInFrames"])
        self.assertEqual(result["audio"], original["audio"])
        self.assertEqual(len(result["mediaCredits"]), len(original["mediaCredits"]) + 1)
        self.assertEqual(output["newspaper"]["from"], 690)


if __name__ == "__main__":
    unittest.main()
