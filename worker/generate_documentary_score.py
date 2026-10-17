"""Stream an original ODE-style harmonic score against the measured documentary clock.

No external music, API or samples. Segment gain is baked into this WAV;
score.volume is NOT: the final mixer applies that playback gain once.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np

SAMPLE_RATE = 48_000
ENGINE = "ode-procedural-v1"
TRANSITION_SECONDS = 2.0
PROFILES = {
    "finance": {"bpm": 108, "chords": [
        [146.83, 220, 261.63, 329.63, 349.23],
        [116.54, 174.61, 220, 293.66, 349.23],
        [98, 146.83, 174.61, 233.08, 293.66],
        [130.81, 196, 261.63, 293.66, 329.63]],
        "bass": [73.42, 58.27, 49, 65.41]},
    "market": {"bpm": 114, "chords": [
        [110, 164.81, 196, 246.94, 261.63],
        [87.31, 130.81, 174.61, 220, 261.63],
        [146.83, 220, 261.63, 349.23, 440],
        [98, 146.83, 196, 261.63, 293.66]],
        "bass": [55, 43.65, 73.42, 49]},
    "alert": {"bpm": 104, "chords": [
        [82.41, 123.47, 164.81, 196, 246.94],
        [130.81, 164.81, 196, 246.94, 329.63],
        [110, 164.81, 220, 261.63, 329.63],
        [123.47, 185, 220, 293.66, 370]],
        "bass": [41.20, 65.41, 55, 61.74]},
    "personal_finance": {"bpm": 106, "chords": [
        [98, 146.83, 196, 246.94, 293.66],
        [82.41, 123.47, 164.81, 246.94, 293.66],
        [130.81, 164.81, 196, 246.94, 329.63],
        [146.83, 220, 261.63, 293.66, 370]],
        "bass": [49, 41.20, 65.41, 73.42]},
}


@dataclass(frozen=True)
class Segment:
    start_sample: int
    end_sample: int
    profile: str
    gain: float = 1.0
    pluck: float = 1.0


def _finite(value, name: str, *, minimum: float = 0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a finite number >= {minimum}.")
    number = float(value)
    if not math.isfinite(number) or number < minimum:
        raise ValueError(f"{name} must be a finite number >= {minimum}.")
    return number


def _frame(value, name: str) -> int:
    number = _finite(value, name)
    if number != int(number):
        raise ValueError(f"{name} must be a whole frame.")
    return int(number)


def resolve_score(source: dict, timeline: dict) -> tuple[list[Segment], int, float]:
    """Resolve source scene anchors to real measured sample positions."""
    timeline = timeline.get("episode", timeline)
    if source.get("id") != timeline.get("id"):
        raise ValueError("Episode and timeline IDs differ.")
    fps = _finite(timeline["fps"], "fps", minimum=.001)
    frames = _frame(timeline["durationInFrames"], "durationInFrames")
    total = round(frames * SAMPLE_RATE / fps)
    if total <= 0:
        raise ValueError("The measured timeline must contain audio time.")
    score = source.get("score") or {}
    if score.get("engine", ENGINE) != ENGINE:
        raise ValueError(f"Unsupported score engine; expected {ENGINE}.")
    if score.get("sampleRate", SAMPLE_RATE) != SAMPLE_RATE:
        raise ValueError("The score uses 48000 Hz PCM.")
    mix_volume = _finite(score.get("volume", .72), "score.volume")
    raw_segments = score.get("segments")
    if not raw_segments:
        return [Segment(0, total, "finance")], total, mix_volume

    scenes = {}
    order = []
    for act in timeline.get("acts", []):
        act_start = _frame(act.get("startFrame", 0), "Act start")
        for scene in act.get("scenes", []):
            scene_id = scene["id"]
            start = act_start + _frame(scene.get("startFrame", 0), "Scene start")
            end = start + _frame(scene["durationInFrames"], "Scene duration")
            if scene_id in scenes or not start < end <= frames:
                raise ValueError(f"Invalid or duplicate scene timing: {scene_id}.")
            scenes[scene_id] = (start, end)
            order.append(scene_id)

    segments = []
    for raw in raw_segments:
        first, last = raw["fromScene"], raw["throughScene"]
        if first not in scenes or last not in scenes or order.index(first) > order.index(last):
            raise ValueError(f"Unknown or reversed score scene range: {first}–{last}.")
        profile = raw["profile"]
        if profile not in PROFILES:
            raise ValueError(f"Unknown score profile: {profile}.")
        start = round(scenes[first][0] * SAMPLE_RATE / fps)
        end = round(scenes[last][1] * SAMPLE_RATE / fps)
        segments.append(Segment(start, end, profile,
                                _finite(raw.get("gain", 1), "Segment gain"),
                                _finite(raw.get("pluck", 1), "Segment pluck")))
    segments.sort(key=lambda segment: segment.start_sample)
    cursor = 0
    for segment in segments:
        if segment.start_sample != cursor:
            raise ValueError("Score segments must cover the timeline without gaps or overlaps; use gain 0 for deliberate silence.")
        cursor = segment.end_sample
    if cursor != total:
        raise ValueError("Score segments do not reach the measured timeline end.")
    return segments, total, mix_volume


def _pad(times: np.ndarray, chord: list[float]) -> np.ndarray:
    pad = np.zeros((len(times), 2), dtype=np.float64)
    for frequency in chord:
        for channel, detune in enumerate((-.35, .35)):
            phase = 2 * np.pi * (frequency + detune) * times
            pad[:, channel] += .7 * np.sin(phase) + .15 * np.sin(2 * phase)
    return pad / len(chord)


def _segment_audio(times: np.ndarray, segment: Segment) -> np.ndarray:
    """ODE pad/bass/pluck synthesis. Time never restarts at a write chunk."""
    profile = PROFILES[segment.profile]
    beat_seconds = 60 / profile["bpm"]
    bar_seconds = beat_seconds * 4
    bar_number = np.floor(times / bar_seconds).astype(np.int64)
    chord_index = bar_number % len(profile["chords"])
    bar_time = np.remainder(times, bar_seconds)
    bar_progress = bar_time / bar_seconds
    beat_progress = np.remainder(times / beat_seconds, 1)
    sixteenths = times / beat_seconds * 4
    note_number = np.floor(sixteenths).astype(np.int64) % 16
    note_progress = np.remainder(sixteenths, 1)
    result = np.zeros((len(times), 2), dtype=np.float64)

    # A phrase grows and relaxes over the musical segment, not every photo/scene.
    segment_seconds = (segment.end_sample - segment.start_sample) / SAMPLE_RATE
    progress = np.clip(times / max(segment_seconds, 1 / SAMPLE_RATE), 0, 1)
    activity = .68 + .32 * np.sin(np.pi * progress)
    pluck_envelope = np.exp(-22 * note_progress) * np.minimum(1, note_progress * beat_seconds / (.004 * 4))
    bass_envelope = np.exp(-3.5 * beat_progress) * np.minimum(1, beat_progress * beat_seconds / .006)

    for index, chord in enumerate(profile["chords"]):
        mask = chord_index == index
        if not np.any(mask):
            continue
        t = times[mask]
        pad = _pad(t, chord)
        # The source Python generator changes phase/frequency at chords. An 80ms
        # chord blend removes that discontinuity while preserving its harmony.
        blend = np.minimum(1, bar_time[mask] / .08)
        blend = .5 - .5 * np.cos(np.pi * blend)
        changing = blend < 1
        if np.any(changing):
            previous = _pad(t[changing], profile["chords"][(index - 1) % len(profile["chords"])])
            pad[changing] = pad[changing] * blend[changing, None] + previous * (1 - blend[changing, None])
        pad *= (.65 + .35 * np.sin(np.pi * bar_progress[mask]))[:, None]
        bass_phase = 2 * np.pi * profile["bass"][index] * t
        bass = (np.sin(bass_phase) + .25 * np.sin(2 * bass_phase)) * bass_envelope[mask] * .55
        notes = np.asarray(chord)[note_number[mask] % len(chord)] * 2
        pluck = np.sin(2 * np.pi * notes * t) * pluck_envelope[mask] * .18 * segment.pluck * activity[mask]
        even = note_number[mask] % 2 == 0
        result[mask, 0] = pad[:, 0] * .38 + bass * .32 + pluck * np.where(even, 1, .25)
        result[mask, 1] = pad[:, 1] * .38 + bass * .32 + pluck * np.where(even, .25, 1)
    return result * (.32 * segment.gain)


def _air(start: int, stop: int, seed: int) -> np.ndarray:
    """Quiet deterministic air, independent of chunk size, with 31-sample history."""
    indices = np.arange(start - 31, stop, dtype=np.int64).astype(np.uint32)
    values = indices ^ np.uint32(seed)
    values = (values ^ (values >> 16)) * np.uint32(0x7FEB352D)
    values = (values ^ (values >> 15)) * np.uint32(0x846CA68B)
    values ^= values >> 16
    noise = values.astype(np.float64) / 2147483648 - 1
    return np.convolve(noise, np.ones(32) / 32, mode="valid") * (.003 * .32)


def render_block(start: int, stop: int, segments: list[Segment], total_samples: int,
                 seed: int) -> np.ndarray:
    """Return stereo float PCM for one bounded absolute sample interval."""
    indices = np.arange(start, stop, dtype=np.int64)
    output = np.zeros((stop - start, 2), dtype=np.float64)
    for position, segment in enumerate(segments):
        # Each boundary is a 2s equal-power crossfade, shortened for tiny probes.
        half_in = min(SAMPLE_RATE, (segment.end_sample - segment.start_sample) // 2,
                      (segments[position - 1].end_sample - segments[position - 1].start_sample) // 2) if position else 0
        half_out = min(SAMPLE_RATE, (segment.end_sample - segment.start_sample) // 2,
                       (segments[position + 1].end_sample - segments[position + 1].start_sample) // 2) if position + 1 < len(segments) else 0
        audible_start = segment.start_sample - half_in
        audible_end = segment.end_sample + half_out
        mask = (indices >= audible_start) & (indices < audible_end)
        if not np.any(mask):
            continue
        active_indices = indices[mask]
        local_times = (active_indices - segment.start_sample) / SAMPLE_RATE
        gain = np.ones(len(active_indices), dtype=np.float64)
        if half_in:
            ramp = np.clip((active_indices - audible_start) / (2 * half_in), 0, 1)
            gain *= np.sin(np.pi * .5 * ramp)
        if half_out:
            ramp = np.clip((active_indices - (segment.end_sample - half_out)) / (2 * half_out), 0, 1)
            gain *= np.cos(np.pi * .5 * ramp)
        output[mask] += _segment_audio(local_times, segment) * gain[:, None]

    # Air is decorative, far below musical layers. Respect deliberate silence.
    air_gain = np.zeros(len(indices), dtype=np.float64)
    for segment in segments:
        air_gain[(indices >= segment.start_sample) & (indices < segment.end_sample)] = segment.gain
    output += (_air(start, stop, seed) * air_gain)[:, None]
    times = indices / SAMPLE_RATE
    duration = total_samples / SAMPLE_RATE
    fade = np.minimum(1, times / min(2, duration / 2)) * np.clip((duration - times) / min(3.5, duration / 2), 0, 1)
    return output * fade[:, None]


def write_score(output: Path, segments: list[Segment], total_samples: int, episode_id: str,
                *, chunk_seconds: float = 8) -> dict:
    """Write a full-length WAV with bounded working memory and one sample clock."""
    if not segments or total_samples <= 0:
        raise ValueError("A score needs segments and a positive sample count.")
    chunk_seconds = _finite(chunk_seconds, "chunk_seconds", minimum=.001)
    if chunk_seconds > 16:
        raise ValueError("Score chunks may not exceed 16 seconds.")
    chunk_samples = max(1, round(chunk_seconds * SAMPLE_RATE))
    seed = int.from_bytes(hashlib.sha256(episode_id.encode()).digest()[:4], "little")
    output.parent.mkdir(parents=True, exist_ok=True)
    peak, square_sum, clipped_samples = 0., 0., 0
    digest = hashlib.sha256()
    with wave.open(str(output), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(SAMPLE_RATE)
        for start in range(0, total_samples, chunk_samples):
            stop = min(total_samples, start + chunk_samples)
            samples = render_block(start, stop, segments, total_samples, seed)
            block_peak = float(np.max(np.abs(samples)))
            peak = max(peak, block_peak)
            clipped_samples += int(np.count_nonzero(np.abs(samples) >= 1))
            square_sum += float(np.sum(samples * samples))
            if block_peak >= 1:
                raise ValueError("Score clips; reduce authored segment gains.")
            pcm = np.rint(samples * 32767).astype("<i2").tobytes()
            digest.update(pcm)
            handle.writeframesraw(pcm)
    return {"engine": ENGINE, "episodeId": episode_id, "sampleRate": SAMPLE_RATE,
            "channels": 2, "sampleCount": total_samples, "durationSeconds": total_samples / SAMPLE_RATE,
            "pcmSha256": digest.hexdigest(), "chunkSeconds": chunk_seconds,
            "peakDbfs": 20 * math.log10(max(peak, 1e-12)),
            "rmsDbfs": 10 * math.log10(max(square_sum / (2 * total_samples), 1e-24)),
            "clippedSamples": clipped_samples, "segments": [asdict(segment) for segment in segments],
            "provenance": "Original procedural pad/bass/arpeggio synthesis adapted from the user's O Dinheiro Explica engine; no external samples or music API.",
            "pauseDucking": "Applied separately by Plotquake's final mixer, not present in the original ODE music engine."}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--test-duration", type=float, help="Limit a technical probe; never used for production.")
    args = parser.parse_args()
    source = json.loads(args.episode.read_text(encoding="utf-8"))
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    segments, total, mix_volume = resolve_score(source, timeline)
    if args.test_duration is not None:
        seconds = _finite(args.test_duration, "test duration", minimum=1 / SAMPLE_RATE)
        total = min(total, round(seconds * SAMPLE_RATE))
        segments = [Segment(segment.start_sample, min(total, segment.end_sample), segment.profile,
                            segment.gain, segment.pluck) for segment in segments if segment.start_sample < total]
    report = write_score(args.output, segments, total, source["id"])
    report.update({"output": str(args.output), "mixPlaybackVolume": mix_volume,
                   "mixPlaybackVolumeAppliedToWav": False, "technicalProbe": args.test_duration is not None})
    manifest = args.output.with_suffix(".json")
    manifest.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[ODE score] {args.output}: {total / SAMPLE_RATE:.3f}s, stereo 48kHz; "
          f"peak {report['peakDbfs']:.1f} dBFS; mixer volume {mix_volume:g} applies once in final mix.")


if __name__ == "__main__":
    main()
