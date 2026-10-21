"""Render representative scene reviews and small archive proxies from the prepared master.

These 540p extracts are review artifacts only. They never replace the full
documentary, regenerate narration/score, publish to YouTube, or upload to Drive.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import time
from pathlib import Path
import subprocess

from render_documentary import check_audio, load_timeline, make_plan, probe, remotion_command, write_json


def scene_windows(episode: dict, scene_ids: list[str]) -> list[dict]:
    selected = set(scene_ids)
    windows = {}
    for act in episode.get("acts", []):
        for scene in act.get("scenes", []):
            if scene["id"] not in selected:
                continue
            if scene["id"] in windows:
                raise ValueError(f"Duplicate scene id: {scene['id']}")
            first = int(act["startFrame"]) + int(scene["startFrame"])
            frames = int(scene["durationInFrames"])
            if first < 0 or frames < 1 or first + frames > episode["durationInFrames"]:
                raise ValueError(f"Scene lies outside the prepared film: {scene['id']}")
            windows[scene["id"]] = {
                "sceneId": scene["id"], "fromFrame": first, "throughFrame": first + frames - 1,
                "durationInFrames": frames, "fromSeconds": first / episode["fps"],
                "durationSeconds": frames / episode["fps"],
            }
    missing = selected - windows.keys()
    if missing:
        raise ValueError(f"Review scenes absent from the actual timeline: {sorted(missing)}")
    return [windows[scene_id] for scene_id in dict.fromkeys(scene_ids)]


def local_asset(src: str, public_root: Path) -> Path:
    path = (public_root / src.replace(chr(92), "/").lstrip("/")).resolve()
    if not path.is_relative_to(public_root.resolve()) or not path.is_file():
        raise ValueError(f"Prepared local footage is missing or outside public/: {src}")
    return path


def mux_scene_review(silent: Path, master: Path, output: Path, window: dict) -> None:
    # Accurate input seeking decodes/discards the AAC prefix. One short preview
    # encode starts at the measured global frame; final delivery AAC is untouched.
    subprocess.run([
        "ffmpeg", "-y", "-v", "warning", "-ss", f"{window['fromSeconds']:.12f}", "-i", str(master),
        "-i", str(silent), "-map", "1:v:0", "-map", "0:a:0", "-t", f"{window['durationSeconds']:.12f}",
        "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart", str(output),
    ], check=True)
    check_audio(output, {"durationInFrames": window["durationInFrames"],
                         "fps": window["durationInFrames"] / window["durationSeconds"]})
    streams = probe(output)["streams"]
    video = [stream for stream in streams if stream["codec_type"] == "video"]
    if len(video) != 1 or int(video[0].get("nb_frames", -1)) != window["durationInFrames"]:
        raise ValueError(f"Review extract lost video frames: {window['sceneId']}")



def measure_master_audio(master: Path, output: Path) -> dict:
    """Report decoded input levels without changing the master or blocking QA."""
    report = {
        "source": master.as_posix(), "method": "FFmpeg astats and EBU R128 input analysis",
        "scope": "Measurements of the actual decoded master input only. No loudness normalization, source rewrite or subjective listening.",
        "audioRewritten": False, "availability": "unavailable",
        "samplePeakDbfs": None, "rmsDbfs": None, "integratedLufs": None,
        "loudnessRangeLu": None, "truePeakDbtp": None,
    }
    started = time.monotonic()
    try:
        result = subprocess.run([
            "ffmpeg", "-hide_banner", "-nostats", "-v", "info", "-i", str(master), "-vn",
            "-af", "astats=metadata=0:reset=0,ebur128=peak=true:framelog=verbose",
            "-f", "null", "-",
        ], capture_output=True, text=True, errors="replace", timeout=180)
        if result.returncode:
            report.update({"reason": result.stderr[-2000:], "ffmpegReturnCode": result.returncode})
        else:
            overall = result.stderr.rsplit("Overall", 1)[-1]
            patterns = {
                "samplePeakDbfs": (overall, r"Peak level dB:\s*([-+0-9.einf]+)"),
                "rmsDbfs": (overall, r"RMS level dB:\s*([-+0-9.einf]+)"),
                "integratedLufs": (result.stderr, r"Integrated loudness:\s*I:\s*([-+0-9.einf]+)"),
                "loudnessRangeLu": (result.stderr, r"Loudness range:\s*LRA:\s*([-+0-9.einf]+)"),
                "truePeakDbtp": (result.stderr, r"True peak:\s*Peak:\s*([-+0-9.einf]+)"),
            }
            for name, (text, pattern) in patterns.items():
                values = re.findall(pattern, text, re.IGNORECASE)
                if values:
                    value = float(values[-1])
                    report[name] = value if math.isfinite(value) else None
            measured = sum(report[name] is not None for name in patterns)
            report["availability"] = "measured" if measured == len(patterns) else "partial" if measured else "unavailable"
            if not measured:
                report["reason"] = "FFmpeg completed, but this build did not expose recognizable astats/EBU R128 summary measurements."
    except (OSError, subprocess.TimeoutExpired, ValueError) as error:
        report["reason"] = f"{type(error).__name__}: {str(error)[:1500]}"
    report["analysisSeconds"] = round(time.monotonic() - started, 3)
    write_json(output, report)
    print(f"[Master audio analysis] {report['availability']}; measurement only; QA continues.", flush=True)
    return report


def still_reviews(episode: dict, props: Path, destination: Path,
                  requests: list[str], browser: str | None) -> list[dict]:
    records = []
    scene_counts = {}
    for request in requests:
        name = request.partition(":")[0]
        scene_counts[name] = scene_counts.get(name, 0) + 1
    for request in requests:
        scene_id, separator, fraction = request.partition(":")
        if not separator:
            raise ValueError("Still requests use scene-id:fraction, e.g. bb-27:0.70")
        fraction = float(fraction)
        if not math.isfinite(fraction) or not 0 <= fraction <= 1:
            raise ValueError("Still fractions must be between 0 and 1.")
        if not scene_id or Path(scene_id).name != scene_id or "/" in scene_id or chr(92) in scene_id:
            raise ValueError(f"Unsafe still scene id: {scene_id!r}")
        if scene_id == "credits":
            credits = episode.get("endCredits")
            if not credits:
                raise ValueError("A credits still requires actual end credits in the episode.")
            window = {"fromFrame": credits["startFrame"], "durationInFrames": credits["durationInFrames"]}
        else:
            window = scene_windows(episode, [scene_id])[0]
        relative = min(window["durationInFrames"] - 1, math.floor(window["durationInFrames"] * fraction))
        if scene_id == "credits":
            # A fraction can fall on a card boundary; inspect the card's readable
            # center rather than a deliberately black transition frame.
            card = next((card for card in credits["cards"] if card["from"] <= relative < card["from"] + card["durationInFrames"]), None)
            if card:
                relative = card["from"] + card["durationInFrames"] // 2
        frame = window["fromFrame"] + relative
        sample_id = scene_id if scene_counts[scene_id] == 1 else f"{scene_id}-{fraction:g}"
        image = destination / f"{sample_id}-composition.jpg"
        command = [
            shutil.which("node") or "node", "node_modules/@remotion/cli/remotion-cli.js", "still",
            "src/index.ts", "Documentary", str(image), f"--props={props}", f"--frame={frame}",
            "--gl=swangle", "--scale=1", "--jpeg-quality=90",
        ]
        if browser:
            command.append(f"--browser-executable={browser}")
        subprocess.run(command, check=True)
        record = {
            "sceneId": scene_id, "globalFrame": frame, "sceneRelativeFrame": relative,
            "sceneFraction": fraction, "output": image.as_posix(), "width": 1920, "height": 1080,
            "scope": "One full-resolution composition frame from actual episode props. Visual sample only, not a complete-scene viewing.",
        }
        write_json(destination / f"{sample_id}-composition.json", record)
        records.append(record)
    return records

def archive_reviews(episode: dict, public_root: Path, destination: Path) -> list[dict]:
    footage = {}
    for act in episode.get("acts", []):
        for scene in act.get("scenes", []):
            for shot in scene.get("shots", []):
                if shot.get("type") == "video" and shot.get("src"):
                    footage.setdefault(shot["src"], set()).add(scene["id"])
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    scale = "scale='min(640,iw)':'min(360,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1"
    for index, (src, scenes) in enumerate(footage.items(), 1):
        path = local_asset(src, public_root)
        info = probe(path)
        video = next(stream for stream in info["streams"] if stream["codec_type"] == "video")
        duration = float(video.get("duration", info["format"].get("duration", 0)))
        if not math.isfinite(duration) or duration <= 0:
            raise ValueError(f"Prepared footage has no positive duration: {src}")
        name = f"{index:02d}-{path.stem}"
        image, proxy = destination / f"{name}.jpg", destination / f"{name}.mp4"
        first, length = max(0., (duration - 12) / 2), min(12., duration)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{duration / 2:.9f}", "-i", str(path),
            "-map", f"0:{video['index']}", "-frames:v", "1", "-vf", scale, "-q:v", "3", str(image),
        ], check=True)
        subprocess.run([
            "ffmpeg", "-y", "-v", "error", "-ss", f"{first:.9f}", "-i", str(path),
            "-map", f"0:{video['index']}", "-an", "-t", f"{length:.9f}", "-vf", scale, "-r", "15",
            "-c:v", "libx264", "-preset", "fast", "-b:v", "450k", "-maxrate", "600k", "-bufsize", "900k",
            "-pix_fmt", "yuv420p", "-threads", "2", "-movflags", "+faststart", str(proxy),
        ], check=True)
        records.append({"source": src, "sceneIds": sorted(scenes), "sourceDurationSeconds": duration,
                        "midpointJpg": image.as_posix(), "proxyMp4": proxy.as_posix(),
                        "proxyFromSeconds": first, "proxyDurationSeconds": length,
                        "scope": "Silent reduced-resolution source proxy; a centered excerpt of at most 12s, not final film."})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", type=Path, default=Path("src/episodes/renderEpisode.json"))
    parser.add_argument("--master", type=Path, default=Path("renders/master_audio.m4a"))
    parser.add_argument("--output-dir", type=Path, default=Path("renders/review"))
    parser.add_argument("--public-root", type=Path, default=Path("public"))
    parser.add_argument("--scenes", nargs="+", default=["bb-01", "bb-23", "bb-38"])
    parser.add_argument("--stills", nargs="*", default=["bb-27:0.70", "bb-29:0.85"])
    parser.add_argument("--browser-executable")
    args = parser.parse_args()
    episode = load_timeline(args.timeline)
    check_audio(args.master, make_plan(episode))
    windows = scene_windows(episode, args.scenes)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics = measure_master_audio(args.master, args.output_dir / "master-audio-metrics.json")
    props = args.output_dir / "review-props.json"
    write_json(props, {"episode": episode})
    for window in windows:
        scene_id = window["sceneId"]
        # IDs originate in the prepared timeline but must still stay within this
        # review directory when used as filenames.
        if not scene_id or Path(scene_id).name != scene_id or "/" in scene_id or chr(92) in scene_id:
            raise ValueError(f"Unsafe review scene id: {scene_id!r}")
        silent = args.output_dir / f".{scene_id}.silent.mp4"
        output = args.output_dir / f"{scene_id}.mp4"
        subprocess.run(remotion_command(silent, args.browser_executable, str(props)) + [
            f"--frames={window['fromFrame']}-{window['throughFrame']}", "--scale=0.5",
            "--muted", "--codec=h264", "--pixel-format=yuv420p", "--crf=22",
        ], check=True)
        mux_scene_review(silent, args.master, output, window)
        silent.unlink()
        window.update({"output": output.as_posix(), "audioSource": args.master.as_posix(),
                       "scope": "Complete scene at 540p using a slice of the actual continuous audio master; review only."})
        write_json(args.output_dir / f"{scene_id}.json", window)
        print(f"[Review scene ready] {scene_id}: {window['durationSeconds']:.3f}s; actual master audio.", flush=True)
    stills = still_reviews(episode, props, args.output_dir, args.stills, args.browser_executable)
    archive = archive_reviews(episode, args.public_root, args.output_dir / "archive")
    manifest = {
        "episodeId": episode["id"], "title": episode["title"], "fps": episode["fps"],
        "sourceDurationInFrames": episode["durationInFrames"], "scenes": windows, "stills": stills, "archive": archive,
        "masterAudioMetrics": "master-audio-metrics.json", "masterAudioMetricsAvailability": metrics["availability"],
        "scope": "Representative audiovisual samples, not a complete-film viewing or final delivery. No Drive/YouTube publication.",
    }
    write_json(args.output_dir / "review-manifest.json", manifest)
    print(f"[Review package ready] {len(windows)} complete scenes and {len(archive)} source footage proxies.", flush=True)


if __name__ == "__main__":
    main()
