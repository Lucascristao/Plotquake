"""Plan unlimited video chunks, render them on a few workers, and mux one continuous audio master."""
from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def file_hash(path: Path) -> str:
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def make_plan(timeline: dict, target_seconds: float = 300, workers: int = 4) -> dict:
    frames, fps = int(timeline["durationInFrames"]), float(timeline["fps"])
    if frames < 1 or not math.isfinite(fps) or fps <= 0:
        raise ValueError("Timeline must have positive duration and fps.")
    if workers < 1 or not math.isfinite(target_seconds) or target_seconds <= 0:
        raise ValueError("Worker count and target chunk duration must be positive.")
    workers = min(workers, frames)
    target_frames = max(1, math.floor(target_seconds * fps))
    # Whole batches keep each worker's load balanced. This never truncates the episode.
    count = min(frames, workers * math.ceil(frames / (target_frames * workers)))
    chunks = []
    for index in range(count):
        start, until = index * frames // count, (index + 1) * frames // count
        chunks.append({"index": index, "worker": index % workers, "startFrame": start,
                       "endFrame": until - 1, "frames": until - start,
                       "file": f"chunk_{index:06d}.mp4"})
    return {"version": 1, "episodeId": timeline["id"], "fps": fps, "width": 1920, "height": 1080,
            "durationInFrames": frames, "workerCount": workers, "chunks": chunks,
            "matrix": {"worker": list(range(workers))}}


def validate_plan(plan: dict) -> None:
    cursor = 0
    for index, chunk in enumerate(plan["chunks"]):
        if (chunk["index"] != index or chunk["startFrame"] != cursor or chunk["frames"] < 1
                or chunk["endFrame"] != cursor + chunk["frames"] - 1
                or chunk["file"] != f"chunk_{index:06d}.mp4"
                or chunk["worker"] != index % plan["workerCount"]):
            raise ValueError(f"Invalid or discontinuous chunk at index {index}.")
        cursor += chunk["frames"]
    if cursor != plan["durationInFrames"] or not cursor:
        raise ValueError("Chunks must cover every timeline frame exactly once.")


def render_fingerprint(plan: dict, root: Path) -> str:
    fingerprint = hashlib.sha256(json.dumps(plan, sort_keys=True).encode())
    files = [root / value for value in ("package-lock.json", "remotion.config.ts", "worker/render_documentary.py")]
    audio_root = (root / "public/generated-audio").resolve()
    episode_audio = (audio_root / str(plan["episodeId"])).resolve()
    if not episode_audio.is_relative_to(audio_root) or episode_audio == audio_root:
        raise ValueError("Episode narration must stay inside its own generated-audio directory.")
    for directory in (root / "src", root / "public/assets", episode_audio):
        files.extend(path for path in directory.rglob("*") if path.is_file())
    for path in sorted(set(files)):
        if path.is_file():
            fingerprint.update(path.relative_to(root).as_posix().encode())
            fingerprint.update(file_hash(path).encode())
    return fingerprint.hexdigest()


def probe(path: Path) -> dict:
    if not path.is_file() or path.stat().st_size == 0:
        raise FileNotFoundError(f"Required media file is missing or empty: {path}")
    result = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True)
    return json.loads(result.stdout)


def check_video(path: Path, plan: dict, frames: int, *, silent: bool = True) -> dict:
    info = probe(path)
    video = [stream for stream in info["streams"] if stream["codec_type"] == "video"]
    audio = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
    if len(video) != 1 or (silent and audio):
        raise ValueError(f"Expected one video stream{' without audio' if silent else ''}: {path}")
    stream = video[0]
    expected = frames / plan["fps"]
    if (stream["codec_name"] != "h264" or stream["width"] != plan["width"] or stream["height"] != plan["height"]
            or abs(float(Fraction(stream["r_frame_rate"])) - plan["fps"]) > .0001
            or int(stream.get("nb_frames", -1)) != frames
            or abs(float(stream["duration"]) - expected) > 1 / plan["fps"]):
        raise ValueError(f"Video dimensions, frame count or duration do not match the timeline: {path}")
    return stream


def stream_signature(stream: dict) -> tuple:
    return tuple(stream.get(key) for key in ("codec_name", "profile", "level", "width", "height", "pix_fmt",
                                            "r_frame_rate", "time_base", "codec_tag_string"))


def check_audio(path: Path, plan: dict) -> dict:
    info = probe(path)
    streams = info["streams"]
    audio = [stream for stream in streams if stream["codec_type"] == "audio"]
    expected = plan["durationInFrames"] / plan["fps"]
    if ("mp4" not in info["format"]["format_name"].split(",")
            or len(audio) != 1 or audio[0]["codec_name"] != "aac"
            or abs(float(audio[0]["duration"]) - expected) > .1
            or abs(float(audio[0].get("start_time", 0))) > 1 / plan["fps"]):
        raise ValueError(f"Continuous audio master does not match the complete timeline: {path}")
    return audio[0]


def cached_chunk(path: Path, chunk: dict, plan: dict) -> bool:
    receipt = path.with_suffix(".json")
    if not receipt.is_file() or not path.is_file():
        return False
    try:
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if saved["renderKey"] != plan["renderKey"] or saved["sha256"] != file_hash(path):
            return False
        check_video(path, plan, chunk["frames"])
        return True
    except (ValueError, KeyError, OSError, subprocess.CalledProcessError):
        return False


def remotion_command(output: Path, browser: str | None, props: str | None) -> list[str]:
    command = [shutil.which("node") or "node", "node_modules/@remotion/cli/remotion-cli.js", "render",
               "src/index.ts", "Documentary", str(output), "--gl=swangle", "--concurrency=2"]
    if browser:
        command.append(f"--browser-executable={browser}")
    if props:
        command.append(f"--props={props}")
    return command


def render_master(plan: dict, output: Path, browser: str | None = None, props: str | None = None) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    pcm = output.with_name(".master-audio.wav")
    partial = output.with_name(".master-audio.partial.m4a")
    try:
        # Remotion 4.0.465's audio-only AAC path emits ADTS even with an .m4a filename.
        # Render lossless PCM first, then encode once into a real MP4/M4A container.
        subprocess.run(remotion_command(pcm, browser, props) +
                       ["--codec=wav", "--audio-codec=pcm-16", "--sample-rate=48000"], check=True)
        subprocess.run(["ffmpeg", "-y", "-v", "warning", "-i", str(pcm), "-vn", "-c:a", "aac",
                        "-b:a", "320k", "-ar", "48000", "-movflags", "+faststart", "-f", "mp4",
                        str(partial)], check=True)
        check_audio(partial, plan)
        partial.replace(output)
    finally:
        pcm.unlink(missing_ok=True)
        partial.unlink(missing_ok=True)
    print("[Audio master ready] Complete timeline mixed and encoded once into M4A.", flush=True)


def render_worker(plan: dict, worker: int, directory: Path, browser: str | None = None,
                  props: str | None = None) -> None:
    if worker not in range(plan["workerCount"]):
        raise ValueError("Unknown render worker.")
    directory.mkdir(parents=True, exist_ok=True)
    for chunk in plan["chunks"]:
        if chunk["worker"] != worker:
            continue
        path = directory / chunk["file"]
        if cached_chunk(path, chunk, plan):
            print(f"[Chunk reused] {chunk['index']}", flush=True)
            continue
        partial = directory / f".partial-{chunk['index']:06d}.mp4"
        command = remotion_command(partial, browser, props) + [
            f"--frames={chunk['startFrame']}-{chunk['endFrame']}", "--muted", "--codec=h264",
            "--pixel-format=yuv420p", "--crf=18"]
        print(f"[Chunk render] {chunk['index'] + 1}/{len(plan['chunks'])}: "
              f"frames {chunk['startFrame']}-{chunk['endFrame']}", flush=True)
        try:
            subprocess.run(command, check=True)
            check_video(partial, plan, chunk["frames"])
            partial.replace(path)
            write_json(path.with_suffix(".json"), {"renderKey": plan["renderKey"], "sha256": file_hash(path)})
        finally:
            partial.unlink(missing_ok=True)


def assemble(plan: dict, directory: Path, master: Path, output: Path) -> None:
    validate_plan(plan)
    master_audio = check_audio(master, plan)
    signature, lines = None, []
    for chunk in plan["chunks"]:
        path = directory / chunk["file"]
        stream = check_video(path, plan, chunk["frames"])
        if not cached_chunk(path, chunk, plan):
            raise ValueError(f"Chunk is corrupt or belongs to a different render: {path}")
        current = stream_signature(stream)
        if signature is not None and current != signature:
            raise ValueError(f"Chunk streams are incompatible: {path}")
        signature = current
        escaped = path.resolve().as_posix().replace("'", "'\\''")
        lines.extend([f"file '{escaped}'", f"duration {chunk['frames'] / plan['fps']:.12f}"])
    output.parent.mkdir(parents=True, exist_ok=True)
    file_list = output.parent / "video_chunks.ffconcat"
    file_list.write_text("ffconcat version 1.0\n" + "\n".join(lines) + "\n", encoding="utf-8")
    partial = output.with_name(f".{output.stem}.partial.mp4")
    try:
        # Both streams are copied. No per-chunk AAC joins, re-encoding, padding or -shortest.
        subprocess.run(["ffmpeg", "-y", "-v", "warning", "-f", "concat", "-safe", "0", "-i", str(file_list),
                        "-i", str(master), "-map", "0:v:0", "-map", "1:a:0", "-c", "copy",
                        "-movflags", "+faststart", str(partial)], check=True)
        check_video(partial, plan, plan["durationInFrames"], silent=False)
        final_audio = check_audio(partial, plan)
        if abs(float(final_audio["duration"]) - float(master_audio["duration"])) > 1 / plan["fps"]:
            raise ValueError("Mux changed the duration of the continuous audio master.")
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    print(f"[Film assembled] {len(plan['chunks'])} chunks, {plan['durationInFrames'] / plan['fps']:.2f}s; "
          "one continuous audio master.", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("plan", "master-audio", "render-worker", "assemble"))
    parser.add_argument("--manifest", default="renders/render_plan.json")
    parser.add_argument("--timeline", default="src/episodes/renderEpisode.json")
    parser.add_argument("--target-seconds", type=float, default=300)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--worker", type=int, default=0)
    parser.add_argument("--chunks-dir", default="renders/chunks")
    parser.add_argument("--master", default="renders/master_audio.m4a")
    parser.add_argument("--output", default="renders/documentary_final.mp4")
    parser.add_argument("--browser-executable")
    parser.add_argument("--props-file")
    args = parser.parse_args()
    manifest = Path(args.manifest)
    if args.command == "plan":
        timeline = json.loads(Path(args.timeline).read_text(encoding="utf-8-sig"))
        plan = make_plan(timeline, args.target_seconds, args.workers)
        validate_plan(plan)
        plan["renderKey"] = render_fingerprint(plan, Path.cwd())
        write_json(manifest, plan)
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
                output.write(f"matrix={json.dumps(plan['matrix'], separators=(',', ':'))}\n")
                output.write(f"render_key={plan['renderKey']}\n")
        print(f"[Render plan] {len(plan['chunks'])} chunks; {plan['workerCount']} parallel workers; "
              f"full runtime {plan['durationInFrames'] / plan['fps']:.2f}s.")
        return
    plan = json.loads(manifest.read_text(encoding="utf-8"))
    validate_plan(plan)
    if args.command == "master-audio":
        render_master(plan, Path(args.master), args.browser_executable, args.props_file)
    elif args.command == "render-worker":
        render_worker(plan, args.worker, Path(args.chunks_dir), args.browser_executable, args.props_file)
    else:
        assemble(plan, Path(args.chunks_dir), Path(args.master), Path(args.output))


if __name__ == "__main__":
    main()
