"""Measure decoded test signals to verify complete speech, offsets and musical direction."""
from array import array
import hashlib
import io
import json
import math
from pathlib import Path
import subprocess
import tempfile
import time
import unittest
import wave

from render_documentary import check_audio, make_plan, render_master


RATE = 48000


def write_tone(path: Path, seconds: float, frequency: float = 440, *, channels: int = 1,
               tail_frequency: float | None = None) -> None:
    with wave.open(str(path), "wb") as output:
        output.setnchannels(channels)
        output.setsampwidth(2)
        output.setframerate(RATE)
        pcm = array("h")
        for index in range(round(seconds * RATE)):
            hz = tail_frequency if tail_frequency and index >= (seconds - .15) * RATE else frequency
            value = round(9000 * math.sin(index * 2 * math.pi * hz / RATE)) if hz else 0
            pcm.extend([value] * channels)
        output.writeframes(pcm.tobytes())


def decode(path: Path) -> array:
    result = subprocess.check_output(["ffmpeg", "-v", "error", "-i", str(path), "-vn", "-ac", "1",
                                      "-ar", str(RATE), "-c:a", "pcm_s16le", "-f", "wav", "-"])
    with wave.open(io.BytesIO(result), "rb") as audio:
        pcm = array("h")
        pcm.frombytes(audio.readframes(audio.getnframes()))
    return array("f", (value / 32768 for value in pcm))


def rms(samples: array, start: float, end: float) -> float:
    selected = samples[round(start * RATE):round(end * RATE)]
    return math.sqrt(sum(value * value for value in selected) / len(selected))


class AudioMasterTests(unittest.TestCase):
    def setUp(self):
        parent = Path(__file__).resolve().parents[1] / "renders/audio-tests"
        parent.mkdir(parents=True, exist_ok=True)
        self.temporary = tempfile.TemporaryDirectory(dir=parent)
        self.directory = Path(self.temporary.name)
        self.public = self.directory / "public"
        self.public.mkdir()

    def tearDown(self):
        self.temporary.cleanup()

    def test_complete_voices_keep_offsets_tails_and_sound_across_video_boundaries(self):
        first, second, effect = [self.public / name for name in ("first.wav", "second.wav", "effect.wav")]
        write_tone(first, 1.5, 440, tail_frequency=990)
        write_tone(second, 2, 660)
        write_tone(effect, 2, 880)
        original_hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)]
        episode = {"id": "speech-test", "fps": 30, "durationInFrames": 180,
                   "audio": {"effects": [{"src": "effect.wav", "from": 75,
                                           "durationInFrames": 15, "volume": .16}]},
                   "acts": [
                       {"startFrame": 0, "scenes": [{"id": "first", "startFrame": 15,
                           "durationInFrames": 45, "audioSrc": "first.wav", "shots": []}]},
                       {"startFrame": 90, "scenes": [{"id": "second", "startFrame": 15,
                           "durationInFrames": 60, "audioSrc": "second.wav", "shots": []}]}]}
        props = self.directory / "props.json"
        props.write_text(json.dumps({"episode": episode}), encoding="utf-8")
        plan, output = make_plan(episode, target_seconds=1, workers=2), self.directory / "master.m4a"
        started = time.monotonic()
        # Existing props-file callers remain valid; no browser path or prepared default timeline is needed.
        render_master(plan, output, browser="not-a-browser", props=str(props), public_root=self.public)
        elapsed = time.monotonic() - started
        check_audio(output, plan)
        samples = decode(output)
        self.assertLess(rms(samples, .1, .4), .001)
        self.assertGreater(rms(samples, .6, .9), .1)
        self.assertGreater(rms(samples, 1.9, 1.98), .1)  # The end of the first spoken file survives.
        self.assertLess(rms(samples, 2.05, 2.4), .001)
        self.assertGreater(rms(samples, 2.6, 2.9), .015)
        self.assertLess(rms(samples, 3.1, 3.4), .001)  # Effect ends at its authored limit.
        self.assertGreater(rms(samples, 3.6, 3.9), .1)
        self.assertAlmostEqual(rms(samples, 3.92, 3.98) / rms(samples, 4.02, 4.08), 1, delta=.08)
        self.assertGreater(rms(samples, 5.35, 5.48), .1)  # The complete second file, not just a scene prefix.
        self.assertLess(rms(samples, 5.6, 5.9), .001)
        self.assertEqual(original_hashes, [hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)])
        print(f"[Audio benchmark] Six-second continuous mix completed in {elapsed:.3f}s.")

    def test_music_loops_fades_ducks_and_applies_last_matching_absolute_volume_cue(self):
        write_tone(self.public / "music.wav", 1, 220, channels=2)
        write_tone(self.public / "quiet-voice.wav", 3, 0)
        episode = {"id": "music-test", "fps": 30, "durationInFrames": 180,
                   "audio": {"music": {"src": "music.wav", "volume": .13, "cues": [
                       {"from": 90, "durationInFrames": 30, "volume": .04},
                       {"from": 105, "durationInFrames": 9, "volume": .02}]}},
                   "acts": [{"startFrame": 0, "scenes": [{"id": "voice", "startFrame": 0,
                       "durationInFrames": 90, "audioSrc": "quiet-voice.wav", "shots": []}]}]}
        output = self.directory / "music-master.m4a"
        render_master(make_plan(episode), output, timeline=episode, public_root=self.public)
        samples = decode(output)
        reference = rms(samples, 2.27, 2.33)
        self.assertGreater(reference, .02)
        self.assertAlmostEqual(rms(samples, .97, 1.03) / reference, 1 / 1.7, delta=.04)
        self.assertAlmostEqual(rms(samples, 3.27, 3.33) / reference, .04 / .13 * 1.22 * .9, delta=.04)
        self.assertAlmostEqual(rms(samples, 3.57, 3.63) / reference, .02 / .13 * 1.22 * .8, delta=.03)
        self.assertAlmostEqual(rms(samples, 4.47, 4.53) / reference, 1.22 * .5, delta=.04)
        self.assertLess(rms(samples, 5.94, 5.99), .002)

    def test_scene_audio_gain_changes_only_playback_and_preserves_full_voice(self):
        first, second = self.public / "first.wav", self.public / "second.wav"
        write_tone(first, 1.5, 440, tail_frequency=990)
        write_tone(second, 2, 660)
        hashes = [hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)]
        episode = {"id": "gain-test", "fps": 30, "durationInFrames": 180,
                   "acts": [
                       {"startFrame": 0, "scenes": [{"id": "first", "startFrame": 15,
                           "durationInFrames": 45, "audioSrc": "first.wav", "audioGain": .5, "shots": []}]},
                       {"startFrame": 90, "scenes": [{"id": "second", "startFrame": 15,
                           "durationInFrames": 60, "audioSrc": "second.wav", "audioGain": 1.25, "shots": []}]}]}
        output = self.directory / "gain-master.m4a"
        render_master(make_plan(episode), output, timeline=episode, public_root=self.public)
        samples = decode(output)
        # Voice normalization is measured on the original mono WAV. Copy it
        # to L/R at unity so the master preserves that target and preview level.
        reference = 9000 / 32768 / math.sqrt(2)
        self.assertLess(rms(samples, .1, .4), .001)
        self.assertAlmostEqual(rms(samples, .7, 1.1), reference * .5, delta=.004)
        self.assertAlmostEqual(rms(samples, 1.9, 1.98), reference * .5, delta=.006)
        self.assertLess(rms(samples, 2.1, 3.3), .001)
        self.assertAlmostEqual(rms(samples, 3.7, 4.1), reference * 1.25, delta=.006)
        self.assertGreater(rms(samples, 5.35, 5.48), reference)
        self.assertEqual(hashes, [hashlib.sha256(path.read_bytes()).hexdigest() for path in (first, second)])

    def test_directed_music_keeps_prepared_level_and_ignores_legacy_fades_and_cues(self):
        write_tone(self.public / "directed.wav", 6, 220, channels=2)
        episode = {"id": "directed-test", "fps": 30, "durationInFrames": 180, "acts": [],
                   "audio": {"music": {"src": "directed.wav", "directed": True, "loop": False,
                       "cues": [{"from": 30, "durationInFrames": 90, "volume": .01}]}}}
        output = self.directory / "directed-master.m4a"
        render_master(make_plan(episode), output, timeline=episode, public_root=self.public)
        samples = decode(output)
        reference = 9000 / 32768 / math.sqrt(2)
        # No second 0.72, silent-scene 1.22 boost, cue attenuation or global fades.
        for start, end in [(0.1, .4), (1.1, 1.4), (3.1, 3.4), (5.7, 5.9)]:
            self.assertAlmostEqual(rms(samples, start, end), reference, delta=.005)

    def test_directed_music_defaults_to_playing_once(self):
        write_tone(self.public / "short-directed.wav", 2, 220, channels=2)
        episode = {"id": "nonloop-test", "fps": 30, "durationInFrames": 180, "acts": [],
                   "audio": {"music": {"src": "short-directed.wav", "directed": True, "volume": .5}}}
        output = self.directory / "nonloop-master.m4a"
        render_master(make_plan(episode), output, timeline=episode, public_root=self.public)
        samples = decode(output)
        self.assertGreater(rms(samples, .2, 1.8), .09)
        self.assertLess(rms(samples, 2.2, 5.9), .001)

    def test_invalid_voice_gain_is_rejected_without_rewriting_source(self):
        voice = self.public / "voice.wav"
        write_tone(voice, 1, 440)
        source_hash = hashlib.sha256(voice.read_bytes()).hexdigest()
        for gain in [-.1, float("nan"), float("inf")]:
            episode = {"id": "invalid-gain", "fps": 30, "durationInFrames": 30,
                       "acts": [{"startFrame": 0, "scenes": [{"id": "voice", "startFrame": 0,
                           "durationInFrames": 30, "audioSrc": "voice.wav", "audioGain": gain, "shots": []}]}]}
            with self.assertRaisesRegex(ValueError, "finite, nonnegative gain"):
                render_master(make_plan(episode), self.directory / "bad-gain.m4a",
                              timeline=episode, public_root=self.public)
        self.assertEqual(source_hash, hashlib.sha256(voice.read_bytes()).hexdigest())

    def test_overlong_spoken_file_is_rejected_instead_of_silently_truncated(self):
        write_tone(self.public / "too-long.wav", 2)
        episode = {"id": "length-test", "fps": 30, "durationInFrames": 180,
                   "acts": [{"startFrame": 0, "scenes": [{"id": "long", "startFrame": 0,
                       "durationInFrames": 30, "audioSrc": "too-long.wav", "shots": []}]}]}
        with self.assertRaisesRegex(ValueError, "Complete narration exceeds"):
            render_master(make_plan(episode), self.directory / "bad.m4a", timeline=episode, public_root=self.public)


if __name__ == "__main__":
    unittest.main()
