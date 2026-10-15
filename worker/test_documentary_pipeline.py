"""Offline checks for timing, recoverable narration and publication packaging."""
import math
from pathlib import Path
import struct
import tempfile
import unittest
from unittest.mock import patch
import wave

from build_episode import build_episode
from build_youtube_package import make_package
from synthesize_narration import (apply_baritone_pitch_calibration, cached_scene, cache_fingerprint,
                                  digest, wav_seconds, write_json)


class DocumentaryPipelineTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[1] / "renders/pipeline-test-temp"
        test_root.mkdir(parents=True, exist_ok=True)
        self.directory = tempfile.TemporaryDirectory(dir=test_root)
        # Keep recursive test cleanup strictly inside this workspace's ignored output folder.
        if not Path(self.directory.name).resolve().is_relative_to(test_root.resolve()):
            raise ValueError("Test directory escaped the workspace output folder.")
        self.addCleanup(self.directory.cleanup)
        self.public = Path(self.directory.name) / "public"
        self.public.mkdir()
        (self.public / "photo.jpg").write_bytes(b"fixture-file-only")
        self.audio_dir = self.public / "generated-audio/test"
        self.audio_dir.mkdir(parents=True)
        self.source = {"id": "test", "title": "A real documentary", "voice": "Charon", "pitchSemitones": -1,
                       "description": "Historical business documentary.", "minimumDurationSeconds": 900,
                       "tags": ["history"], "sources": [{"id": "s", "title": "Primary source", "url": "https://example.org"}],
                       "acts": [{"id": f"act-{a}", "title": f"Act {a}", "scenes": [
                           {"id": f"a{a}-s{s}", "narration": "The script of this scene.", "visualKeys": ["photo"]}
                           for s in range(2)]} for a in range(4)]}
        self.catalog = {"assets": [{"key": "photo", "src": "photo.jpg", "kind": "image", "credit": "Public domain"}]}

    def test_measured_timeline_is_complete_and_sequential(self):
        with patch("build_episode.cached_scene", return_value={"durationSeconds": 115.137}):
            result = build_episode(self.source, self.catalog, self.audio_dir, self.public)
        cursor = 0
        for act in result["acts"]:
            self.assertEqual(act["startFrame"], cursor)
            scene_cursor = 0
            for scene in act["scenes"]:
                self.assertEqual(scene["startFrame"], scene_cursor)
                self.assertGreaterEqual(scene["durationInFrames"], 115.137 * 30)
                shot_cursor = 0
                for shot in scene["shots"]:
                    self.assertEqual(shot["from"], shot_cursor)
                    self.assertLessEqual(shot["durationInFrames"], 5 * 30)
                    shot_cursor += shot["durationInFrames"]
                self.assertEqual(shot_cursor, scene["durationInFrames"])
                scene_cursor += scene["durationInFrames"]
            self.assertEqual(scene_cursor, act["durationInFrames"])
            cursor += act["durationInFrames"]
        self.assertEqual(cursor, result["durationInFrames"])
        self.assertGreaterEqual(result["metadata"]["narrationSeconds"], 900)
        package = make_package(self.source, result)
        self.assertEqual(package["chapters"][0]["time"], "00:00")
        self.assertEqual(len(package["chapters"]), 4)
        self.assertEqual(package["tags"], ["history"])

    def test_short_narration_is_rejected_instead_of_padded(self):
        with patch("build_episode.cached_scene", return_value={"durationSeconds": 100}):
            with self.assertRaisesRegex(ValueError, "Expand the actual script"):
                build_episode(self.source, self.catalog, self.audio_dir, self.public)

    def test_semantic_asset_variants_are_used_and_preserve_direction(self):
        (self.public / "other.jpg").write_bytes(b"another-file")
        self.catalog["assets"].append({"key": "photo", "src": "other.jpg", "kind": "image",
                                       "fit": "contain", "focus": {"x": .3, "y": .4}, "zoomStart": 1.2})
        with patch("build_episode.cached_scene", return_value={"durationSeconds": 115.137}):
            result = build_episode(self.source, self.catalog, self.audio_dir, self.public)
        shots = result["acts"][0]["scenes"][0]["shots"]
        self.assertEqual({shot["src"] for shot in shots}, {"photo.jpg", "other.jpg"})
        variant = next(shot for shot in shots if shot["src"] == "other.jpg")
        self.assertEqual(variant["fit"], "contain")
        self.assertEqual(variant["zoomStart"], 1.2)
        self.assertEqual(variant["focus"], {"x": .3, "y": .4})

    def test_cache_requires_matching_text_voice_and_audio(self):
        path = self.audio_dir / "scene.wav"
        with wave.open(str(path), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(b"\0\0" * 24000)
        fingerprint = cache_fingerprint("One scene", "Charon", -1.0)
        write_json(path.with_suffix(".json"), {"fingerprint": fingerprint, "audioSha256": digest(path), "durationSeconds": 1})
        self.assertIsNotNone(cached_scene(path, fingerprint))
        self.assertIsNone(cached_scene(path, cache_fingerprint("Edited scene", "Charon", -1.0)))
        self.assertIsNone(cached_scene(path, cache_fingerprint("One scene", "Fenrir", -1.0)))
        data = bytearray(path.read_bytes())
        data[-1] = 1
        path.write_bytes(data)
        self.assertIsNone(cached_scene(path, fingerprint))

    def test_cards_never_send_video_files_to_the_image_renderer(self):
        (self.public / "movie.mp4").write_bytes(b"video-fixture")
        self.catalog["assets"].append({"key": "video", "src": "movie.mp4", "kind": "video"})
        scene = self.source["acts"][0]["scenes"][0]
        scene.update({"quote": {"text": "A verified quote", "author": "A witness"},
                      "chart": {"title": "Comparison", "values": [{"label": "A", "value": 1}]}})
        for keys, expected in ((["video", "photo"], "photo.jpg"), (["video"], None)):
            with self.subTest(keys=keys), patch("build_episode.cached_scene", return_value={"durationSeconds": 115.137}):
                scene["visualKeys"] = keys
                result = build_episode(self.source, self.catalog, self.audio_dir, self.public)
            cards = [shot for shot in result["acts"][0]["scenes"][0]["shots"] if shot["type"] in ("quote", "chart")]
            self.assertEqual(len(cards), 2)
            for card in cards:
                self.assertEqual(card.get("src"), expected)
                self.assertNotIn("trimBefore", card)
                self.assertNotIn("playbackRate", card)

    def test_pitch_keeps_exact_duration(self):
        source, target = self.audio_dir / "raw.wav", self.audio_dir / "deep.wav"
        sample_count = 27103
        pcm = b"".join(struct.pack("<h", round(5000 * math.sin(index * 2 * math.pi * 220 / 24000)))
                       for index in range(sample_count))
        with wave.open(str(source), "wb") as output:
            output.setnchannels(1)
            output.setsampwidth(2)
            output.setframerate(24000)
            output.writeframes(pcm)
        apply_baritone_pitch_calibration(source, target, -1)
        self.assertEqual(wav_seconds(source), wav_seconds(target))
        self.assertNotEqual(digest(source), digest(target))


if __name__ == "__main__":
    unittest.main()
