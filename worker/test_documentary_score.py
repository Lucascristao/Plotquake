"""Focused checks for measured timing, chunk seams and the audible harmonic score."""
import copy
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from generate_documentary_score import SAMPLE_RATE, Segment, resolve_score, write_score


class DocumentaryScoreTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary_root = Path(__file__).resolve().parents[1] / "out/score-tests"
        cls.temporary_root.mkdir(parents=True, exist_ok=True)

    def fixture(self):
        source = {"id": "score-test", "score": {"engine": "ode-procedural-v1", "volume": .72,
                  "segments": [{"fromScene": "a", "throughScene": "a", "profile": "finance"},
                               {"fromScene": "b", "throughScene": "c", "profile": "alert", "pluck": .6}]}}
        timeline = {"id": "score-test", "fps": 30, "durationInFrames": 271,
                    "acts": [{"startFrame": 0, "scenes": [
                        {"id": "a", "startFrame": 0, "durationInFrames": 111}]},
                        {"startFrame": 111, "scenes": [
                        {"id": "b", "startFrame": 0, "durationInFrames": 79},
                        {"id": "c", "startFrame": 79, "durationInFrames": 81}]}]}
        return source, timeline

    def test_measured_frames_resolve_across_acts_and_keep_mix_gain_separate(self):
        source, timeline = self.fixture()
        segments, total, volume = resolve_score(source, {"episode": timeline})
        self.assertEqual(total, 271 * 1600)
        self.assertEqual(segments[0].end_sample, 111 * 1600)
        self.assertEqual(segments[1].start_sample, 111 * 1600)
        self.assertEqual(segments[1].end_sample, total)
        self.assertEqual(segments[0].gain, 1)
        self.assertEqual(volume, .72)
        changed = copy.deepcopy(source)
        changed["score"]["volume"] = .2
        self.assertEqual(resolve_score(changed, timeline)[:2], (segments, total))

    def test_rejects_wrong_timeline_and_incomplete_or_reversed_ranges(self):
        source, timeline = self.fixture()
        for mutator in (
            lambda value: value.update(id="another-episode"),
            lambda value: value["score"]["segments"].pop(),
            lambda value: value["score"]["segments"][1].update(fromScene="c", throughScene="b"),
            lambda value: value["score"]["segments"][1].update(profile="missing"),
        ):
            changed = copy.deepcopy(source)
            mutator(changed)
            with self.assertRaises(ValueError):
                resolve_score(changed, timeline)

    def test_pcm_is_identical_across_write_chunk_sizes_and_has_exact_duration(self):
        source, timeline = self.fixture()
        segments, total, _ = resolve_score(source, timeline)
        with tempfile.TemporaryDirectory(dir=self.temporary_root) as directory:
            paths = [Path(directory) / "a.wav", Path(directory) / "b.wav"]
            reports = [write_score(path, segments, total, source["id"], chunk_seconds=chunk)
                       for path, chunk in zip(paths, (1.3, 8))]
            self.assertEqual(paths[0].read_bytes(), paths[1].read_bytes())
            self.assertEqual(reports[0]["pcmSha256"], reports[1]["pcmSha256"])
            self.assertEqual(reports[0]["clippedSamples"], 0)
            with wave.open(str(paths[0]), "rb") as audio:
                self.assertEqual((audio.getnframes(), audio.getframerate(), audio.getnchannels(), audio.getsampwidth()),
                                 (total, SAMPLE_RATE, 2, 2))
                samples = np.frombuffer(audio.readframes(total), dtype="<i2").reshape(-1, 2) / 32768
            # No reset/click at the crossfade or arbitrary file-writing boundary.
            for boundary in (round(1.3 * SAMPLE_RATE), segments[1].start_sample):
                self.assertLess(float(np.max(np.abs(samples[boundary] - samples[boundary - 1]))), .03)
            mono = samples[SAMPLE_RATE:3*SAMPLE_RATE].mean(axis=1)
            energy = np.abs(np.fft.rfft(mono * np.hanning(len(mono)))) ** 2
            frequencies = np.fft.rfftfreq(len(mono), 1 / SAMPLE_RATE)
            self.assertGreater(float(energy[(frequencies >= 200) & (frequencies < 2000)].sum() / energy.sum()), .1)

    def test_deliberate_silence_and_segment_gain_are_applied_once(self):
        total = 2 * SAMPLE_RATE
        with tempfile.TemporaryDirectory(dir=self.temporary_root) as directory:
            output = Path(directory) / "zero.wav"
            report = write_score(output, [Segment(0, total, "finance", gain=0)], total, "silence")
            with wave.open(str(output), "rb") as audio:
                self.assertEqual(set(audio.readframes(total)), {0})
            self.assertEqual(report["peakDbfs"], -240)

    def test_chunks_have_a_resource_ceiling(self):
        with tempfile.TemporaryDirectory(dir=self.temporary_root) as directory:
            with self.assertRaisesRegex(ValueError, "16 seconds"):
                write_score(Path(directory) / "invalid.wav", [Segment(0, SAMPLE_RATE, "finance")],
                            SAMPLE_RATE, "limit", chunk_seconds=17)

    def test_credit_tail_extends_music_without_extending_scene_ranges(self):
        source, timeline = self.fixture()
        timeline["endCredits"] = {"startFrame": 271, "durationInFrames": 90}
        timeline["durationInFrames"] = 361
        source["score"]["endCredits"] = {"profile": "personal_finance", "gain": .45, "pluck": .15}
        segments, total, _ = resolve_score(source, timeline)
        self.assertEqual(segments[-2].end_sample, 271 * 1600)
        self.assertEqual(segments[-1], Segment(271 * 1600, 361 * 1600, "personal_finance", .45, .15))
        self.assertEqual(total, 361 * 1600)


if __name__ == "__main__":
    unittest.main()
