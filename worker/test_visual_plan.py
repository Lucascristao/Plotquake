"""Technical checks for authored edits that reuse the complete, measured narration."""
import copy
import math
from pathlib import Path
import tempfile
import unittest
import wave

from build_episode import FPS, build_episode, build_shots, shot_lengths
from synthesize_narration import cache_fingerprint, digest, wav_seconds, write_json


class VisualPlanTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / "renders/visual-plan-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.addCleanup(self.temporary.cleanup)
        self.public = Path(self.temporary.name) / "public"
        self.public.mkdir()
        self.assets = {
            "still": [
                {"key": "still", "src": "a.jpg", "kind": "image", "credit": "Photographer A",
                 "origin": "https://example.org/a", "license": "CC BY 4.0"},
                {"key": "still", "src": "b.jpg", "kind": "image", "credit": "Photographer B",
                 "origin": "https://example.org/b", "license": "Public domain"}],
            "reconstruction": [{"key": "reconstruction", "src": "illustration.png", "kind": "image",
                "credit": "Plotquake · Illustrative reconstruction", "origin": "generated",
                "reconstruction": True, "license": "Original illustration", "changes": "Not an archival photograph."}],
            "archive": [{"key": "archive", "src": "archive.mp4", "kind": "video",
                "credit": "Film archive", "origin": "https://example.org/film", "durationSeconds": 4}],
        }
        for asset in self.catalog()["assets"]:
            (self.public / asset["src"]).write_bytes(b"Media-presence fixture; no decoder used by the timeline builder.")

    def catalog(self):
        return {"assets": [asset for variants in self.assets.values() for asset in variants]}

    def test_media_kind_and_motion_are_respected(self):
        for kind, key in (("image", "archive"), ("video", "still")):
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "does not match"):
                build_shots({"id": "wrong", "visualPlan": [{"mediaKey": key, "type": kind}]},
                            self.assets, 60, self.public, {}, 0)
        scene = {"id": "motion", "visualPlan": [
            {"mediaKey": "still", "motion": "pull"}, {"mediaKey": "still", "motion": "still"}]}
        pull, still = build_shots(scene, self.assets, 120, self.public, {}, 0)
        self.assertGreater(pull["zoomStart"], pull["zoomEnd"])
        self.assertEqual(still["zoomStart"], still["zoomEnd"])

    def assert_coverage(self, shots, frames):
        cursor = 0
        for shot in shots:
            self.assertEqual(shot["from"], cursor)
            self.assertGreaterEqual(shot["durationInFrames"], 1)
            cursor += shot["durationInFrames"]
        self.assertEqual(cursor, frames)

    def test_authored_order_variants_and_unequal_reading_times_survive(self):
        scene = {"id": "authored", "visualKeys": ["archive"], "visualPlan": [
            {"mediaKey": "still", "variantIndex": 1, "weight": 1, "motion": "still"},
            {"mediaKey": "reconstruction", "weight": 3, "focus": {"x": .3, "y": .4}},
            {"mediaKey": "still", "variantIndex": 0, "weight": 2, "fit": "contain"}]}
        original = copy.deepcopy(scene)
        credits = {}
        shots = build_shots(scene, self.assets, 600, self.public, credits, global_scene_index=37)
        self.assertEqual([shot["src"] for shot in shots], ["b.jpg", "illustration.png", "a.jpg"])
        self.assertEqual([shot["durationInFrames"] for shot in shots], [100, 300, 200])
        self.assertEqual(shots[0]["motion"], "still")
        self.assertEqual(shots[1]["focus"], {"x": .3, "y": .4})
        self.assertEqual(shots[2]["fit"], "contain")
        self.assertEqual(scene, original)
        self.assert_coverage(shots, 600)
        self.assertTrue(shots[1]["reconstruction"])
        self.assertEqual(shots[1]["origin"], "generated")
        self.assertEqual(shots[1]["sourceLabel"], "Plotquake · Illustrative reconstruction")
        self.assertEqual(credits["illustration.png"]["changes"], "Not an archival photograph.")
        self.assertEqual(credits["a.jpg"]["license"], "CC BY 4.0")

    def test_video_end_and_dissolve_tail_are_reserved_and_still_absorbs_remaining_time(self):
        scene = {"id": "clip-limit", "visualPlan": [
            {"mediaKey": "archive", "weight": 4, "trimStartSeconds": .5, "playbackRate": 1.25},
            {"mediaKey": "still", "weight": 1, "transition": "dissolve"}]}
        shots = build_shots(scene, self.assets, 240, self.public, {}, 0)
        self.assert_coverage(shots, 240)
        video, still = shots
        self.assertEqual([shot["type"] for shot in shots], ["video", "image"])
        self.assertEqual(video["trimBefore"], 15)
        self.assertEqual(video["playbackRate"], 1.25)
        self.assertGreater(still["durationInFrames"], video["durationInFrames"])
        # Documentary extends a shot by 12 frames when the following picture dissolves in.
        consumed_seconds = video["trimBefore"] / FPS + (video["durationInFrames"] + 12) / FPS * video["playbackRate"]
        self.assertLessEqual(consumed_seconds, 4)
        self.assertEqual(sum(shot["type"] == "video" for shot in shots), 1)
        self.assertNotIn("loop", video)
        with self.assertRaisesRegex(ValueError, "cannot cover"):
            build_shots({"id": "too-short", "visualPlan": [scene["visualPlan"][0]]},
                        self.assets, 240, self.public, {}, 0)

    def test_explicit_cards_keep_their_positions_and_never_use_an_mp4_background(self):
        scene = {"id": "evidence", "chart": {"title": "Measured values", "data": [
                     {"label": "Documented value", "percentage": 42}]},
                 "quote": {"text": "Documented words", "author": "A named witness"},
                 "visualPlan": [{"type": "quote", "mediaKey": "still", "variantIndex": 1, "weight": 2},
                                {"mediaKey": "archive", "weight": 1},
                                {"type": "chart", "mediaKey": "still", "variantIndex": 0, "weight": 3}]}
        shots = build_shots(scene, self.assets, 180, self.public, {}, 11)
        self.assert_coverage(shots, 180)
        self.assertEqual([shot["type"] for shot in shots], ["quote", "video", "chart"])
        self.assertEqual(shots[0]["src"], "b.jpg")
        self.assertEqual(shots[2]["src"], "a.jpg")
        self.assertEqual(shots[0]["quote"]["author"], "A named witness")
        self.assertEqual(shots[2]["chart"]["values"][0]["value"], 42)
        for shot in (shots[0], shots[2]):
            self.assertNotIn("trimBefore", shot)
            self.assertNotIn("playbackRate", shot)
        for card in ("chart", "quote"):
            with self.subTest(card=card):
                invalid = {**scene, "visualPlan": [{"type": card, "mediaKey": "archive"}]}
                with self.assertRaisesRegex(ValueError, "background must be a still"):
                    build_shots(invalid, self.assets, 30, self.public, {}, 0)
        # Authored plans decide whether cards appear; a source annotation does not insert extra shots.
        plain = {**scene, "visualPlan": [{"mediaKey": "still"}]}
        self.assertEqual(build_shots(plain, self.assets, 60, self.public, {}, 0)[0]["type"], "image")

    def test_video_keeps_catalog_vintage_treatment_and_authored_override(self):
        self.assets["archive"][0]["vintageFilter"] = True
        scene = {"id": "vintage", "visualPlan": [{"mediaKey": "archive"}]}
        self.assertTrue(build_shots(scene, self.assets, 30, self.public, {}, 0)[0]["vintageFilter"])
        scene["visualPlan"][0]["vintageFilter"] = False
        self.assertFalse(build_shots(scene, self.assets, 30, self.public, {}, 0)[0]["vintageFilter"])

    def test_fractional_scene_durations_keep_complete_wavs_and_global_music_cues(self):
        audio_dir = self.public / "generated-audio/visual-plan-test"
        audio_dir.mkdir(parents=True)
        scenes, originals = [], {}
        for index, seconds in enumerate((300.01, 299.99, 300)):
            scene = {"id": f"scene-{index}", "narration": f"Unchanged narration for scene {index}.",
                     "visualPlan": [{"mediaKey": "still", "variantIndex": 1, "weight": 1},
                                    {"mediaKey": "reconstruction", "weight": 3}]}
            if index:
                scene["musicVolume"] = (.06, .15)[index - 1]
            path = audio_dir / f"{scene['id']}.wav"
            with wave.open(str(path), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(24000)
                output.writeframes(b"\0\0" * round(seconds * 24000))
            originals[path] = digest(path)
            write_json(path.with_suffix(".json"), {"fingerprint": cache_fingerprint(scene["narration"], "Charon", -1.0),
                       "audioSha256": originals[path], "durationSeconds": wav_seconds(path)})
            scenes.append(scene)
        source = {"id": "visual-plan-test", "voice": "Charon", "pitchSemitones": -1,
                  "acts": [{"id": "first", "title": "First section", "scenes": scenes[:1]},
                           {"id": "second", "title": "Second section", "scenes": scenes[1:]}]}
        result = build_episode(source, self.catalog(), audio_dir, self.public)
        frames = [math.ceil(wav_seconds(path) * FPS) for path in originals]
        self.assertEqual(result["durationInFrames"], sum(frames))
        self.assertAlmostEqual(result["metadata"]["narrationSeconds"], 900)
        self.assertEqual(result["acts"][1]["startFrame"], frames[0])
        self.assertEqual(result["acts"][1]["scenes"][1]["startFrame"], frames[1])
        cues = result["audio"]["music"]["cues"]
        self.assertEqual(cues, [{"from": frames[0], "durationInFrames": frames[1], "volume": .06},
                                {"from": frames[0] + frames[1], "durationInFrames": frames[2], "volume": .15}])
        for act in result["acts"]:
            for scene in act["scenes"]:
                self.assert_coverage(scene["shots"], scene["durationInFrames"])
                original = audio_dir / f"{scene['id']}.wav"
                self.assertEqual(scene["audioSrc"], original.relative_to(self.public).as_posix())
                self.assertGreaterEqual(scene["durationInFrames"] / FPS, wav_seconds(original))
                self.assertEqual(digest(original), originals[original])
        self.assertEqual(shot_lengths([1, 3, 2], 600, [None, None, None]), [100, 300, 200])


if __name__ == "__main__":
    unittest.main()
