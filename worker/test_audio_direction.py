"""Verify voice gain, real speech pauses and untouched source WAVs."""
import copy
from pathlib import Path
import tempfile
import unittest
import wave

import numpy as np

from prepare_audio_direction import (SAMPLE_RATE, file_hash, pause_envelope, prepare_direction,
                                     read_pcm16, measure_voice)


def write_wav(path, samples, rate):
    samples = np.asarray(samples)
    if samples.ndim == 1:
        samples = samples[:, None]
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(samples.shape[1])
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(np.rint(samples * 32767).astype("<i2").tobytes())


class AudioDirectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).resolve().parents[1] / "out/audio-direction-tests"
        cls.root.mkdir(parents=True, exist_ok=True)

    def fixture(self, directory):
        rate = 24000
        times = np.arange(4 * rate) / rate
        first = .1 * np.sin(2 * np.pi * 220 * times)
        first[(times >= .9) & (times < 2)] = 0
        first[(times >= .3) & (times < .4)] = 0  # short interruption is not a musical pause
        second = .25 * np.sin(2 * np.pi * 330 * np.arange(2 * rate) / rate)
        write_wav(directory / "a.wav", first, rate)
        write_wav(directory / "b.wav", second, rate)
        write_wav(directory / "raw-score.wav", np.full((6 * SAMPLE_RATE, 2), .1), SAMPLE_RATE)
        timeline = {"episode": {"id": "directions", "fps": 30, "durationInFrames": 180,
            "audio": {"music": {"src": "old.wav", "volume": .03, "cues": [{"volume": .01}]}},
            "acts": [{"startFrame": 0, "scenes": [
                {"id": "a", "startFrame": 0, "durationInFrames": 120, "audioSrc": "a.wav"},
                {"id": "b", "startFrame": 120, "durationInFrames": 60, "audioSrc": "b.wav"}]}]}}
        return {"id": "directions", "score": {"volume": .72, "pauseLift": 1.6}}, timeline

    def test_shared_voice_level_real_pause_lift_and_original_bytes_preserved(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            directory = Path(temporary)
            source, timeline = self.fixture(directory)
            hashes = {name: file_hash(directory / name) for name in ("a.wav", "b.wav", "raw-score.wav")}
            report = prepare_direction(source, timeline, directory / "raw-score.wav", directory / "directed.wav", directory)
            self.assertAlmostEqual(report["commonActiveRmsDbfs"], -18, places=8)
            levels = [item["activeRmsDbfs"] + 20 * np.log10(item["audioGain"]) for item in report["voiceScenes"]]
            self.assertAlmostEqual(levels[0], levels[1], places=8)
            self.assertGreater(report["voiceScenes"][0]["audioGain"], 1)
            self.assertLess(report["voiceScenes"][1]["audioGain"], 1)
            self.assertEqual(len(report["pauses"]), 1)
            self.assertAlmostEqual(report["pauses"][0]["fromSeconds"], .9, places=6)
            self.assertAlmostEqual(report["pauses"][0]["toSeconds"], 2, places=6)
            directed, rate = read_pcm16(directory / "directed.wav")
            raw, _ = read_pcm16(directory / "raw-score.wav")
            for t, multiplier in ((.2, 1), (.35, 1), (1.4, 1.6), (1.95, 1), (2.01, 1), (4.2, 1)):
                i = round(t * rate)
                self.assertAlmostEqual(float(directed[i, 0] / raw[i, 0]), .72 * multiplier, delta=.001)
            for name, before in hashes.items():
                self.assertEqual(file_hash(directory / name), before)
            self.assertTrue(all(item["sourceSha256Before"] == item["sourceSha256After"] for item in report["voiceScenes"]))
            music = timeline["episode"]["audio"]["music"]
            self.assertEqual(music, {"src": "directed.wav", "volume": 1, "loop": False, "directed": True})
            self.assertTrue(report["scoreVolumeAppliedToWav"])
            self.assertFalse(report["globalFadeAppliedHere"])
            # Reapplying metadata measures original voice, never the prior gain.
            second = prepare_direction(source, timeline, directory / "raw-score.wav", directory / "directed-again.wav", directory)
            self.assertEqual(report["directedPcmSha256"], second["directedPcmSha256"])
            self.assertEqual([s["audioGain"] for s in report["voiceScenes"]], [s["audioGain"] for s in second["voiceScenes"]])

    def test_peak_limit_lowers_one_shared_target_instead_of_clipping_a_scene(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            directory = Path(temporary)
            source, timeline = self.fixture(directory)
            voice, rate = read_pcm16(directory / "a.wav")
            voice *= .1
            voice[0, 0] = .95
            write_wav(directory / "a.wav", voice, rate)
            report = prepare_direction(source, timeline, directory / "raw-score.wav", directory / "directed.wav", directory)
            self.assertLess(report["commonActiveRmsDbfs"], -18)
            self.assertLessEqual(max(item["expectedSamplePeak"] for item in report["voiceScenes"]), .86000001)
            self.assertAlmostEqual(report["voiceScenes"][0]["expectedActiveRmsDbfs"], report["voiceScenes"][1]["expectedActiveRmsDbfs"])

    def test_shortest_pause_uses_smooth_ramps_and_returns_before_next_speech(self):
        samples = 2 * SAMPLE_RATE
        envelope = pause_envelope(0, samples, [{"fromSeconds": .5, "toSeconds": 1.2}], 1.6)
        self.assertAlmostEqual(envelope[round(.61 * SAMPLE_RATE)], 1)
        self.assertGreater(float(envelope.max()), 1.59)
        self.assertAlmostEqual(envelope[round(1.04 * SAMPLE_RATE)], 1)
        self.assertLess(float(np.max(np.abs(np.diff(envelope)))), .001)

    def test_full_score_duration_required_and_voice_output_protected(self):
        with tempfile.TemporaryDirectory(dir=self.root) as temporary:
            directory = Path(temporary)
            source, timeline = self.fixture(directory)
            with self.assertRaisesRegex(ValueError, "overwrite a narration"):
                prepare_direction(source, copy.deepcopy(timeline), directory / "raw-score.wav", directory / "a.wav", directory)
            write_wav(directory / "short.wav", np.zeros((SAMPLE_RATE, 2)), SAMPLE_RATE)
            with self.assertRaisesRegex(ValueError, "full measured timeline"):
                prepare_direction(source, copy.deepcopy(timeline), directory / "short.wav", directory / "bad.wav", directory)


if __name__ == "__main__":
    unittest.main()
