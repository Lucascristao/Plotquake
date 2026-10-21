"""Actual-use credits, unchanged legacy behavior and separate publication copy."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from build_youtube_package import make_package
from publication import apply_publication, selected_credits, write_clean_delivery


class PublicationTests(unittest.TestCase):
    def fixture(self):
        source = {"id": "mission", "title": "A satellite retrieval", "description": "The authored public description.",
                  "tags": ["space history"], "publication": {"standard": "cinematic-v1", "hashtags": ["NASA", "Space", "Extra"]},
                  "sources": [{"title": "Historical research", "url": "https://example.org/research"}],
                  "endCredits": {"enabled": True, "assets": [
                      {"src": "used.mp4", "author": "NASA", "title": "Selected mission footage", "license": "Public domain"},
                      {"src": "cover.jpg", "author": "Cover author", "title": "Cover only"},
                      {"src": "unused.jpg", "author": "Unused author", "title": "Not selected"},
                      {"src": "music.wav", "author": "Plotquake", "title": "Original score", "screenCredit": False}]}}
        timeline = {"id": "mission", "fps": 30, "durationInFrames": 300, "metadata": {"narrationSeconds": 9.9},
                    "audio": {"music": {"src": "music.wav"}}, "mediaCredits": [{"src": "cover.jpg", "credit": "Cover author"}],
                    "acts": [{"startFrame": 0, "scenes": [{"id": "scene", "startFrame": 0, "durationInFrames": 300,
                               "shots": [{"id": "shot", "src": "used.mp4", "type": "video"}]}]}]}
        return source, timeline

    def test_legacy_is_unchanged_and_keeps_existing_package(self):
        source, timeline = self.fixture()
        source.pop("publication")
        source.pop("endCredits")
        timeline["chapters"] = []
        before = copy.deepcopy(timeline)
        self.assertEqual(apply_publication(source, timeline), before)
        self.assertIn("SOURCES", make_package(source, timeline)["description"])

    def test_credits_follow_actual_selection_exclude_cover_and_preserve_speech(self):
        source, timeline = self.fixture()
        apply_publication(source, timeline)
        credits = timeline["endCredits"]
        self.assertEqual(credits["startFrame"], 300)
        self.assertEqual(credits["durationInFrames"], 270)
        self.assertEqual(timeline["durationInFrames"], 570)
        self.assertEqual(timeline["metadata"]["narrationSeconds"], 9.9)
        self.assertEqual(credits["cards"][0]["entries"], [{"lines": ["NASA", "Selected mission footage"]}])
        self.assertEqual({r["src"] for r in selected_credits(source, timeline)}, {"used.mp4", "music.wav"})
        before = copy.deepcopy(timeline)
        self.assertEqual(apply_publication(source, timeline), before)

    def test_clean_package_and_internal_record_do_not_mix(self):
        source, timeline = self.fixture()
        apply_publication(source, timeline)
        package = make_package(source, timeline)
        self.assertEqual(set(package), {"title", "description", "tags"})
        self.assertNotIn("SOURCES", package["description"])
        self.assertEqual(package["description"].count("#"), 2)
        test_root = Path(__file__).resolve().parents[1] / "out/publication-tests"
        test_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=test_root) as directory:
            destination = Path(directory)
            write_clean_delivery(source, timeline, destination, package)
            public = (destination / "youtube_package.txt").read_text(encoding="utf-8")
            internal = json.loads((destination / "internal_documentation.json").read_text(encoding="utf-8"))
            self.assertNotIn("example.org/research", public)
            self.assertIn("TAGS\nspace history", public)
            self.assertEqual(internal["historicalSources"], source["sources"])
            self.assertEqual(internal["filmMedia"][0]["author"], "NASA")
            # Word count is authoring information, never an added runtime gate.
            self.assertLess(internal["descriptionWordCount"], 80)


if __name__ == "__main__":
    unittest.main()
