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
import tempfile
import time
import wave


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


def load_timeline(timeline: dict | Path | str | None = None, props: str | None = None) -> dict:
    """Use the same episode props as video rendering, without starting a browser."""
    if props:
        value = json.loads(Path(props).read_text(encoding="utf-8-sig"))
        return value["episode"]
    if isinstance(timeline, dict):
        return timeline
    return json.loads(Path(timeline or "src/episodes/renderEpisode.json").read_text(encoding="utf-8-sig"))


def _media_path(src: str, public_root: Path) -> str:
    if src.startswith(("http://", "https://")):
        return src
    path = Path(src)
    if not path.is_absolute():
        path = public_root / src.replace("\\", "/").lstrip("/")
    if not path.is_file() or not path.stat().st_size:
        raise FileNotFoundError(f"Required audio file is missing or empty: {path}")
    return str(path.resolve())


def _audio_seconds(src: str) -> float:
    if not src.startswith(("http://", "https://")) and Path(src).suffix.lower() == ".wav":
        with wave.open(src, "rb") as audio:
            return audio.getnframes() / audio.getframerate()
    info = probe(Path(src)) if not src.startswith(("http://", "https://")) else json.loads(
        subprocess.check_output(["ffprobe", "-v", "error", "-show_streams", "-show_format", "-of", "json", src],
                                text=True))
    streams = [stream for stream in info["streams"] if stream["codec_type"] == "audio"]
    if not streams:
        raise ValueError(f"Audio source has no audio stream: {src}")
    return float(streams[0].get("duration", info["format"].get("duration", 0)))


def _number(value: float) -> str:
    return f"{value:.12f}".rstrip("0").rstrip(".") or "0"


def _gain(value: float, context: str) -> float:
    value = float(value)
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{context} must be a finite, nonnegative gain.")
    return value


def _frame(value: int, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or int(value) != value or value < 0:
        raise ValueError(f"{context} must be a nonnegative integer frame.")
    return int(value)


def _merged_windows(windows: list[tuple[int, int]]) -> list[tuple[int, int]]:
    merged = []
    for start, end in sorted(windows):
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    return merged


def _master_graph(episode: dict, public_root: Path, working_dir: Path) -> tuple[list[str], str, int]:
    """Mix full narration at sample-accurate offsets; no viewport or video-frame traversal."""
    fps, frames, rate = float(episode["fps"]), int(episode["durationInFrames"]), 48000
    duration, total_samples = frames / fps, round(frames * rate / fps)
    inputs, filters, labels, voiced = [], [], [], []

    def add_track(src: str, start: int, volume: float, *, length: int | None = None,
                  trim: float = 0, speed: float = 1, loop: bool = False, music: bool = False) -> str:
        index = len(labels)
        path = _media_path(src, public_root)
        if loop:
            seconds = _audio_seconds(path)
            if not math.isfinite(seconds) or seconds <= 0:
                raise ValueError("The looped score must contain a positive amount of audio.")
            # An explicit finite concat also works with Remotion's reduced FFmpeg build,
            # where WAV -stream_loop can stop after the first pass. No long PCM copy is needed.
            count = max(1, math.ceil(duration / seconds))
            escaped = path.replace("\\", "/").replace("'", "'\\''")
            playlist = working_dir / f"loop-{index}.ffconcat"
            playlist.write_text("ffconcat version 1.0\n" +
                                (f"file '{escaped}'\nduration {_number(seconds)}\n" * count), encoding="utf-8")
            inputs.extend(["-f", "concat", "-safe", "0", "-i", str(playlist)])
        else:
            inputs.extend(["-i", path])
        chain = ["aresample=48000", "aformat=sample_fmts=fltp:channel_layouts=stereo"]
        if trim or length is not None:
            settings = [f"start={_number(trim)}"]
            if length is not None:
                settings.append(f"duration={_number(length / fps * speed)}")
            chain.append("atrim=" + ":".join(settings))
        chain.append("asetpts=PTS-STARTPTS")
        if speed != 1:
            remaining = speed
            while remaining > 2:
                chain.append("atempo=2")
                remaining /= 2
            while remaining < .5:
                chain.append("atempo=0.5")
                remaining *= 2
            chain.append(f"atempo={_number(remaining)}")
        if not music:
            chain.append(f"volume={_number(volume)}")
        offset = round(start * rate / fps)
        label = f"track{index}"
        if offset:
            # adelay allocates a PCM ring buffer as long as the offset for every track.
            # Dozens of late scenes in a long film can exceed a runner's RAM. Virtual
            # silence through concat is streamed in small frames instead.
            content, silence = f"content{index}", f"silence{index}"
            filters.append(f"[{index}:a:0]" + ",".join(chain) + f"[{content}]")
            filters.append(f"anullsrc=r=48000:cl=stereo,atrim=end_sample={offset},"
                           f"aformat=sample_fmts=fltp[{silence}]")
            filters.append(f"[{silence}][{content}]concat=n=2:v=0:a=1[{label}]")
        else:
            filters.append(f"[{index}:a:0]" + ",".join(chain) + f"[{label}]")
        labels.append(label)
        return label

    def add_voice(src: str, start: int, length: int, context: str) -> None:
        start, length = _frame(start, context + " start"), _frame(length, context + " duration")
        if not length or start + length > frames:
            raise ValueError(f"Narration window is outside the complete timeline: {context}")
        path = _media_path(src, public_root)
        seconds = _audio_seconds(path)
        # A final trim must never conceal an overlong or incorrectly placed spoken file.
        if seconds <= 0 or seconds > length / fps + 1 / rate:
            raise ValueError(f"Complete narration exceeds its scene window: {context}")
        add_track(src, start, 1)
        voiced.append((start, start + length))

    audio = episode.get("audio") or {}
    if audio.get("narration"):
        add_voice(audio["narration"], 0, frames, "master narration")
    for act in episode.get("acts", []):
        act_start = _frame(act["startFrame"], "Act start")
        for scene in act.get("scenes", []):
            scene_start = act_start + _frame(scene["startFrame"], "Scene start")
            if scene.get("audioSrc"):
                add_voice(scene["audioSrc"], scene_start, scene["durationInFrames"], scene["id"])
            # Preserve any deliberately audible footage as well as the separate narration/effects.
            shots = scene.get("shots", [])
            for index, shot in enumerate(shots):
                if shot.get("type") != "video" or shot.get("muted", True) or not shot.get("src"):
                    continue
                src = _media_path(shot["src"], public_root)
                info = probe(Path(src)) if not src.startswith(("http://", "https://")) else None
                if info is not None and not any(s["codec_type"] == "audio" for s in info["streams"]):
                    continue
                speed = float(shot.get("playbackRate", 1))
                if not math.isfinite(speed) or speed <= 0:
                    raise ValueError("Footage playbackRate must be finite and positive.")
                overlap = 12 if index + 1 < len(shots) and shots[index + 1].get("transition") == "dissolve" else 0
                length = min(scene["durationInFrames"] - shot["from"], shot["durationInFrames"] + overlap)
                add_track(shot["src"], scene_start + _frame(shot["from"], "Footage start"),
                          _gain(shot.get("volume", .2), "Footage volume"), length=length,
                          trim=float(shot.get("trimBefore", 0)) / fps, speed=speed)

    music = audio.get("music")
    if music:
        music = {"src": music, "volume": .13} if isinstance(music, str) else music
        base = _gain(music.get("volume", .13), "Music volume")
        label = add_track(music["src"], 0, base, length=frames, loop=music.get("loop", True), music=True)
        gain = _number(base)
        # Cues use global frame intervals and absolute gains; the last matching cue wins.
        for cue in music.get("cues", []):
            start = _frame(cue["from"], "Music cue start")
            length = _frame(cue["durationInFrames"], "Music cue duration")
            volume = _gain(cue["volume"], "Music cue volume")
            condition = f"gte(t,{_number(start / fps)})*lt(t,{_number((start + length) / fps)})"
            gain = f"if({condition},{_number(volume)},{gain})"
        windows = _merged_windows(voiced)
        if windows:
            condition = "+".join(f"gte(t,{_number(start / fps)})*lt(t,{_number(end / fps)})" for start, end in windows)
            gain += f"*if(gt({condition},0),1,1.22)"
        else:
            gain += "*1.22"
        gain += f"*min(1,t/1.7)*max(0,min(1,({_number(duration)}-t)/{_number(min(3, duration))}))"
        filters.append(f"[{label}]volume='if(isnan(t),0,{gain})':eval=frame[music]")
        labels[-1] = "music"
    for effect in audio.get("effects", []):
        start = _frame(effect["from"], "Effect start")
        length = None if effect.get("durationInFrames") is None else _frame(effect["durationInFrames"], "Effect duration")
        add_track(effect["src"], start, _gain(effect.get("volume", .16), "Effect volume"), length=length)
    if not labels:
        filters.append(f"anullsrc=r=48000:cl=stereo,atrim=end_sample={total_samples}[master]")
    else:
        filters.append("".join(f"[{label}]" for label in labels) +
                       f"amix=inputs={len(labels)}:duration=longest:dropout_transition=0:normalize=0,"
                       f"apad=whole_len={total_samples},atrim=end_sample={total_samples},asetpts=PTS-STARTPTS[master]")
    return inputs, ";\n".join(filters), total_samples


def render_master(plan: dict, output: Path, browser: str | None = None, props: str | None = None,
                  *, timeline: dict | Path | str | None = None, public_root: Path | None = None) -> None:
    # browser is retained for callers of the previous API; audio never starts Remotion or Chrome.
    episode = load_timeline(timeline, props)
    if (episode["id"] != plan["episodeId"] or episode["durationInFrames"] != plan["durationInFrames"]
            or float(episode["fps"]) != float(plan["fps"])):
        raise ValueError("Audio timeline and render plan must describe the same complete episode.")
    output.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    partial = output.with_name(f".{output.stem}.partial.m4a")
    try:
        with tempfile.TemporaryDirectory(prefix="audio-mix-", dir=output.parent) as temporary:
            inputs, graph, samples = _master_graph(episode, public_root or Path("public"), Path(temporary))
            script = Path(temporary) / "mix.ffgraph"
            script.write_text(graph + "\n", encoding="utf-8")
            subprocess.run(["ffmpeg", "-y", "-v", "warning", *inputs, "-filter_complex_script", str(script),
                            "-map", "[master]", "-vn", "-c:a", "aac", "-b:a", "320k", "-ar", "48000",
                            "-ac", "2", "-movflags", "+faststart", "-f", "mp4", str(partial)], check=True)
        check_audio(partial, plan)
        partial.replace(output)
    finally:
        partial.unlink(missing_ok=True)
    print(f"[Audio master ready] {samples} samples mixed directly from complete scene audio; "
          f"one M4A encode in {time.monotonic() - started:.2f}s, without browser frames.", flush=True)


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
    parser.add_argument("--props-file", "--props", dest="props_file")
    args = parser.parse_args()
    manifest = Path(args.manifest)
    if args.command == "plan":
        timeline = load_timeline(args.timeline, args.props_file)
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
        render_master(plan, Path(args.master), args.browser_executable, args.props_file, timeline=args.timeline)
    elif args.command == "render-worker":
        render_worker(plan, args.worker, Path(args.chunks_dir), args.browser_executable, args.props_file)
    else:
        assemble(plan, Path(args.chunks_dir), Path(args.master), Path(args.output))


if __name__ == "__main__":
    main()
