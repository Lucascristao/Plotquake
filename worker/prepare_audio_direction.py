"""Level existing voice WAVs by gain metadata and lift the score in real pauses.

Raw narration and pitch remain untouched. Only a new score WAV and the derived
timeline are written. The directed score includes score.volume exactly once.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import wave

import numpy as np

from generate_documentary_score import SAMPLE_RATE

PUBLIC_ROOT = Path(__file__).resolve().parents[1] / "public"
METHOD = "active-speech-rms-shared-target-and-real-pause-envelope-v1"
WINDOW_SECONDS = .02
VOICE_TARGET_DBFS = -18.
VOICE_PEAK_CEILING = .86


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for data in iter(lambda: handle.read(65536), b""):
            digest.update(data)
    return digest.hexdigest()


def media_path(src: str, public_root: Path) -> Path:
    path = Path(src)
    if not path.is_absolute():
        path = public_root / path
    if not path.is_file():
        raise ValueError(f"Audio file is missing: {path}")
    return path.resolve()


def _number(value, name: str, minimum=0., maximum=None) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {name}.")
    value = float(value)
    if not math.isfinite(value) or value < minimum or (maximum is not None and value > maximum):
        raise ValueError(f"Invalid {name}.")
    return value


def _frame(value, name: str) -> int:
    value = _number(value, name)
    if int(value) != value:
        raise ValueError(f"Invalid whole-frame {name}.")
    return int(value)


def read_pcm16(path: Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as handle:
        if handle.getsampwidth() != 2 or handle.getcomptype() != "NONE":
            raise ValueError(f"Expected uncompressed PCM16 voice: {path}")
        rate, channels = handle.getframerate(), handle.getnchannels()
        pcm = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2").astype(np.float64)
    if not len(pcm) or rate <= 0:
        raise ValueError(f"Empty voice audio: {path}")
    return pcm.reshape(-1, channels) / 32768, rate


def runs(mask: np.ndarray, value: bool) -> list[tuple[int, int]]:
    edges = np.diff(np.concatenate(([False], mask == value, [False])).astype(np.int8))
    return list(zip(np.flatnonzero(edges == 1).tolist(), np.flatnonzero(edges == -1).tolist()))


def close_short_holes(mask: np.ndarray, maximum_windows: int) -> np.ndarray:
    closed = mask.copy()
    for first, last in runs(closed, False):
        if first and last < len(closed) and last - first <= maximum_windows:
            closed[first:last] = True
    return closed


def measure_voice(path: Path) -> dict:
    samples, rate = read_pcm16(path)
    window = max(1, round(rate * WINDOW_SECONDS))
    energy = np.mean(samples * samples, axis=1)
    padded = np.pad(energy, (0, (-len(energy)) % window))
    energies = padded.reshape(-1, window).mean(axis=1)
    active = energies[energies > 10 ** (-45 / 10)]
    if not len(active):
        raise ValueError(f"No measurable active speech in voice file: {path}")
    rms_dbfs = 10 * math.log10(float(active.mean()))
    threshold = max(-45., rms_dbfs - 24)
    mask = close_short_holes(energies > 10 ** (threshold / 10),
                             math.floor(.15 / WINDOW_SECONDS + 1e-9))
    duration = len(samples) / rate
    activity = [(first * window / rate, min(duration, last * window / rate))
                for first, last in runs(mask, True)]
    peak = float(np.max(np.abs(samples)))
    return {"durationSeconds": duration, "sampleRate": rate,
            "activeRmsDbfs": rms_dbfs, "samplePeak": peak,
            "samplePeakDbfs": 20 * math.log10(max(peak, 1e-12)),
            "pauseThresholdDbfs": threshold, "speechWindows": activity}


def merge_windows(windows: list[tuple[float, float]], *, close_seconds=.15) -> list[tuple[float, float]]:
    merged = []
    for first, last in sorted(windows):
        if merged and first - merged[-1][1] <= close_seconds + 1e-9:
            merged[-1] = (merged[-1][0], max(last, merged[-1][1]))
        else:
            merged.append((first, last))
    return merged


def plan_direction(source: dict, timeline: dict, public_root: Path = PUBLIC_ROOT) -> dict:
    """Mutate gain metadata only; do not rewrite or transpose the scene WAVs."""
    episode = timeline.get("episode", timeline)
    if source.get("id") != episode.get("id"):
        raise ValueError("Episode and timeline IDs differ.")
    fps = _number(episode["fps"], "fps", minimum=.001)
    frames = _frame(episode["durationInFrames"], "durationInFrames")
    total = round(frames * SAMPLE_RATE / fps)
    duration = total / SAMPLE_RATE
    score = source.get("score") or {}
    volume = _number(score.get("volume", .72), "score.volume")
    lift = _number(score.get("pauseLift", 1.6), "score.pauseLift", minimum=1, maximum=2)
    pause_minimum = _number(score.get("pauseMinimumSeconds", .70), "score.pauseMinimumSeconds", minimum=.70)
    measurements, windows, seen = [], [], set()
    for act in episode.get("acts", []):
        act_start = _frame(act.get("startFrame", 0), "act start")
        for scene in act.get("scenes", []):
            if not scene.get("audioSrc"):
                continue
            scene_id = scene["id"]
            if scene_id in seen:
                raise ValueError(f"Duplicate voiced scene: {scene_id}")
            seen.add(scene_id)
            path = media_path(scene["audioSrc"], public_root)
            measured = measure_voice(path)
            start = (act_start + _frame(scene["startFrame"], "scene start")) / fps
            end = start + _frame(scene["durationInFrames"], "scene duration") / fps
            if measured["durationSeconds"] > end - start + 1 / measured["sampleRate"] or end > duration + 1 / SAMPLE_RATE:
                raise ValueError(f"Complete voice exceeds its measured scene: {scene_id}")
            windows.extend((start + first, start + last) for first, last in measured["speechWindows"])
            measurements.append({"id": scene_id, "source": str(path), "sourceSha256Before": file_hash(path),
                                 "startSeconds": start, **measured, "_scene": scene})
    if not measurements:
        raise ValueError("The timeline has no scene narration to measure.")
    ceiling_dbfs = 20 * math.log10(VOICE_PEAK_CEILING)
    common = min([VOICE_TARGET_DBFS] + [item["activeRmsDbfs"] + ceiling_dbfs - item["samplePeakDbfs"]
                                      for item in measurements])
    for measured in measurements:
        gain = 10 ** ((common - measured["activeRmsDbfs"]) / 20)
        measured.pop("_scene")["audioGain"] = gain
        measured["audioGain"] = gain
        measured["expectedActiveRmsDbfs"] = common
        measured["expectedSamplePeak"] = measured["samplePeak"] * gain
        # The full activity window list is global below; avoid duplicating it in the report.
        del measured["speechWindows"]
    merged = merge_windows(windows)
    pauses = []
    cursor = 0.
    # End credits have their own authored musical tail. Their lack of narration
    # must not trigger a prolonged pause boost on top of that arrangement.
    story_duration = (episode.get("endCredits") or {}).get("startFrame", frames) / fps
    for first, last in merged + [(story_duration, story_duration)]:
        if first - cursor >= pause_minimum - 1e-9:
            pauses.append({"fromSeconds": cursor, "toSeconds": first,
                           "durationSeconds": first - cursor})
        cursor = max(cursor, last)
    return {"method": METHOD, "episodeId": source["id"], "durationSeconds": duration,
            "sampleCount": total, "requestedActiveRmsDbfs": VOICE_TARGET_DBFS,
            "commonActiveRmsDbfs": common, "voicePeakCeiling": VOICE_PEAK_CEILING,
            "measurementWindowSeconds": WINDOW_SECONDS, "speechActivityFloorDbfs": -45,
            "closedSpeechHolesSeconds": .15, "mixPlaybackVolume": volume,
            "pauseLift": lift, "pauseMinimumSeconds": pause_minimum,
            "pauseEnvelope": {"delaySeconds": .12, "rampSeconds": .25, "beforeSpeechGuardSeconds": .16},
            "pauses": pauses, "voiceScenes": measurements,
            "scope": "PCM activity, gain and sample-peak measurements only. No subjective listening, text-fidelity assessment, pitch change or source-WAV rewrite.",
            "provenance": "Pause lift is Plotquake's improvement; the inspected O Dinheiro Explica engine has no pause ducking."}


def pause_envelope(start: int, stop: int, pauses: list[dict], lift: float) -> np.ndarray:
    times = np.arange(start, stop, dtype=np.int64) / SAMPLE_RATE
    envelope = np.ones(stop - start, dtype=np.float64)
    if lift == 1:
        return envelope
    for pause in pauses:
        first, last = pause["fromSeconds"], pause["toSeconds"]
        rise_start, return_end = first + .12, last - .16
        if rise_start >= return_end or return_end <= start / SAMPLE_RATE or rise_start >= stop / SAMPLE_RATE:
            continue
        ramp = min(.25, (return_end - rise_start) / 2)
        up = np.clip((times - rise_start) / ramp, 0, 1)
        down = np.clip((return_end - times) / ramp, 0, 1)
        # Raised cosine, continuous value and slope at both ends.
        curve = (.5 - .5 * np.cos(np.pi * up)) * (.5 - .5 * np.cos(np.pi * down))
        envelope = np.maximum(envelope, 1 + (lift - 1) * curve)
    return envelope


def write_directed_score(score_path: Path, output: Path, report: dict, *, chunk_seconds=8.) -> dict:
    if score_path.resolve() == output.resolve():
        raise ValueError("Directed output must differ from the raw score.")
    chunk_seconds = _number(chunk_seconds, "chunk_seconds", minimum=.001, maximum=16)
    chunk = max(1, round(chunk_seconds * SAMPLE_RATE))
    total = report["sampleCount"]
    output.parent.mkdir(parents=True, exist_ok=True)
    peak, raw_peak, square_sum = 0., 0., 0.
    digest = hashlib.sha256()
    with wave.open(str(score_path), "rb") as source:
        if (source.getframerate(), source.getnchannels(), source.getsampwidth(), source.getnframes()) != (SAMPLE_RATE, 2, 2, total):
            raise ValueError("Raw score must be stereo PCM16 48kHz with the full measured timeline duration.")
        with wave.open(str(output), "wb") as destination:
            destination.setnchannels(2)
            destination.setsampwidth(2)
            destination.setframerate(SAMPLE_RATE)
            for start in range(0, total, chunk):
                count = min(chunk, total - start)
                raw = np.frombuffer(source.readframes(count), dtype="<i2").astype(np.float64).reshape(-1, 2) / 32768
                raw_peak = max(raw_peak, float(np.abs(raw).max()))
                gain = pause_envelope(start, start + count, report["pauses"], report["pauseLift"])
                directed = raw * (report["mixPlaybackVolume"] * gain)[:, None]
                peak = max(peak, float(np.abs(directed).max()))
                if peak >= 1:
                    raise ValueError("Directed score clips; reduce score/segment gain.")
                square_sum += float(np.sum(directed * directed))
                pcm = np.rint(directed * 32767).astype("<i2").tobytes()
                digest.update(pcm)
                destination.writeframesraw(pcm)
    return {"rawScoreSha256": file_hash(score_path), "directedPcmSha256": digest.hexdigest(),
            "rawScoreSamplePeak": raw_peak, "directedScoreSamplePeak": peak,
            "directedScoreRmsDbfs": 10 * math.log10(max(square_sum / (2 * total), 1e-24)),
            "scoreVolumeAppliedToWav": True, "mixerPlaybackVolume": 1,
            "globalFadeAppliedHere": False, "chunkSeconds": chunk_seconds, "clippedSamples": 0}


def prepare_direction(source: dict, timeline: dict, score_path: Path, output: Path,
                      public_root: Path = PUBLIC_ROOT) -> dict:
    episode = timeline.get("episode", timeline)
    report = plan_direction(source, timeline, public_root)
    originals = {Path(item["source"]) for item in report["voiceScenes"]}
    if output.resolve() in originals:
        raise ValueError("Directed score cannot overwrite a narration source.")
    report.update(write_directed_score(score_path, output, report))
    for item in report["voiceScenes"]:
        item["sourceSha256After"] = file_hash(Path(item["source"]))
        if item["sourceSha256After"] != item["sourceSha256Before"]:
            raise ValueError(f"Narration source changed during audio direction: {item['id']}")
    try:
        src = output.resolve().relative_to(public_root.resolve()).as_posix()
    except ValueError:
        src = str(output.resolve())
    episode.setdefault("audio", {})["music"] = {"src": src, "volume": 1, "loop": False, "directed": True}
    episode.setdefault("metadata", {})["audioDirection"] = {
        "method": METHOD, "commonActiveRmsDbfs": report["commonActiveRmsDbfs"],
        "voicePeakCeiling": VOICE_PEAK_CEILING, "pauseCount": len(report["pauses"]),
        "scoreVolumeAppliedOnce": True, "sourceWavsUnchanged": True, "pitchCorrectionApplied": False,
        "reportPath": str(output.with_suffix(".json"))}
    report["output"] = str(output)
    report["sourceWavsUnchanged"] = True
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True, type=Path)
    parser.add_argument("--timeline", required=True, type=Path)
    parser.add_argument("--score", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    source = json.loads(args.episode.read_text(encoding="utf-8"))
    timeline = json.loads(args.timeline.read_text(encoding="utf-8"))
    report = prepare_direction(source, timeline, args.score, args.output)
    args.output.with_suffix(".json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    args.timeline.write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[Audio direction] {len(report['voiceScenes'])} scenes at shared {report['commonActiveRmsDbfs']:.2f} dBFS active RMS; "
          f"{len(report['pauses'])} real pauses; source WAVs unchanged; score gain applied once.")


if __name__ == "__main__":
    main()
