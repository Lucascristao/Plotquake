"""Create bounded review samples from the assembled film in GitHub Actions.

This produces evidence for a person to inspect. It performs no editorial scoring
and does not claim that sampled pictures or clips constitute a full-film review.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import time
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


MAX_FRAMES = 96
CONTACT_COLUMNS = 6
CONTACT_ROWS = 4
THUMBNAIL_SIZE = (320, 180)
CLIP_SECONDS = 12.0
SHOWINFO_TIME = re.compile(r"\bn:\s*0\b.*?\bpts_time:\s*(-?[\d.]+)")
DOCUMENT_NAME = re.compile(
    r"document|senate|frus|ledger|clipping|newspaper|report[-_ ]page", re.I
)


def timestamp(seconds: float) -> str:
    milliseconds = max(0, round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    whole_seconds, milliseconds = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{whole_seconds:02d}.{milliseconds:03d}"


def number(value, default=0.0) -> float:
    try:
        result = float(value)
        return result if math.isfinite(result) else default
    except (TypeError, ValueError):
        return default


def frame_rate(value) -> float:
    try:
        result = float(Fraction(str(value)))
        return result if 0 < result < 1000 else 30.0
    except (ValueError, ZeroDivisionError):
        return 30.0


def spread(items: list, count: int) -> list:
    if len(items) <= count:
        return items[:]
    return [items[round(index * (len(items) - 1) / (count - 1))]
            for index in range(count)]


class ReviewOutput:
    def __init__(self, output_dir: Path, inputs: list[Path], budget: int):
        self.root = output_dir.resolve()
        self.inputs = {path.resolve() for path in inputs}
        self.deadline = time.monotonic() + budget
        self.root.mkdir(parents=True, exist_ok=True)
        self.errors: list[dict] = []

    def path(self, name: str) -> Path:
        destination = (self.root / name).resolve()
        if not destination.is_relative_to(self.root) or destination in self.inputs:
            raise ValueError("Review output must remain separate from input files.")
        destination.parent.mkdir(parents=True, exist_ok=True)
        return destination

    def run(self, command: list[str], label: str, timeout: int) -> str | None:
        remaining = self.deadline - time.monotonic()
        if remaining < 1:
            self.errors.append({"operation": label, "reason": "time budget exhausted"})
            return None
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, check=True,
                timeout=min(timeout, remaining),
            )
            return result.stdout + "\n" + result.stderr
        except (OSError, subprocess.SubprocessError) as error:
            detail = getattr(error, "stderr", "") or str(error)
            if isinstance(detail, bytes):
                detail = detail.decode("utf-8", errors="replace")
            self.errors.append({"operation": label, "reason": detail[-1400:]})
            return None

    def image(self, video: Path, seconds: float, name: str,
              size: tuple[int, int], source_start: float) -> dict:
        destination = self.path(name)
        width, height = size
        result = self.run([
            "ffmpeg", "-hide_banner", "-loglevel", "info", "-nostdin", "-y",
            "-ss", f"{seconds:.6f}", "-copyts", "-i", str(video),
            "-map", "0:v:0", "-frames:v", "1", "-an",
            "-vf", (f"scale={width}:{height}:force_original_aspect_ratio=decrease,"
                    f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,showinfo"),
            "-fps_mode", "passthrough", "-q:v", "2", str(destination),
        ], name, timeout=30)
        match = SHOWINFO_TIME.search(result) if result else None
        observed_pts = number(match.group(1)) if match else None
        return {
            "file": name,
            "requestedTimeSeconds": round(seconds, 6),
            "requestedTimestamp": timestamp(seconds),
            "observedSourcePtsSeconds": observed_pts,
            "observedTimeSeconds": (
                round(observed_pts - source_start, 6)
                if observed_pts is not None else None
            ),
            "success": result is not None and destination.is_file(),
        }


def document_windows(timeline: dict, duration: float) -> list[dict]:
    fps = frame_rate(timeline.get("fps", 30))
    windows = []
    for act in timeline.get("acts", []):
        for scene in act.get("scenes", []):
            base = number(act.get("startFrame")) + number(scene.get("startFrame"))
            newspaper = scene.get("newspaper") or {}
            if newspaper.get("mode") == "clipping" and newspaper.get("imageSrc"):
                start = (base + number(newspaper.get("from"))) / fps
                length = number(newspaper.get("durationInFrames")) / fps
                if length > 0 and start < duration:
                    windows.append({
                        "sceneId": scene.get("id"), "source": newspaper.get("imageSrc"),
                        "startSeconds": max(0.0, start),
                        "endSeconds": min(duration, start + length),
                        "selectionReason": "timeline newspaper clipping window",
                        "priority": 0,
                    })
            for shot in scene.get("shots", []):
                if (shot.get("type") != "image" or shot.get("reconstruction")
                        or shot.get("origin") == "generated"):
                    continue
                description = " ".join(str(shot.get(key, ""))
                                       for key in ("src", "caption", "sourceLabel"))
                if not DOCUMENT_NAME.search(description):
                    continue
                start = (base + number(shot.get("from"))) / fps
                length = number(shot.get("durationInFrames")) / fps
                if length > 0 and start < duration:
                    windows.append({
                        "sceneId": scene.get("id"), "source": shot.get("src"),
                        "startSeconds": max(0.0, start),
                        "endSeconds": min(duration, start + length),
                        "selectionReason": "timeline document image candidate",
                        "priority": 1,
                    })
    # Keep distinct sources when possible, preferring explicit clipping windows.
    unique = {}
    for window in sorted(windows, key=lambda value: value["priority"]):
        unique.setdefault(window["source"], window)
    return sorted(unique.values(), key=lambda value: value["startSeconds"])


def font(size: int):
    for name in ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            pass
    return ImageFont.load_default()


def contact_sheets(output: ReviewOutput, samples: list[dict]) -> list[dict]:
    successful = [sample for sample in samples if sample["success"]]
    if not successful:
        return []
    # A normal documentary gets three or four 6x4 sheets. Unused cells stay empty.
    sheet_count = min(len(successful), max(3, math.ceil(len(successful) / 24)))
    per_sheet = math.ceil(len(successful) / sheet_count)
    sheets = []
    for index in range(sheet_count):
        subset = successful[index * per_sheet:(index + 1) * per_sheet]
        if not subset:
            continue
        sheet = Image.new("RGB", (1944, 900), "#05070c")
        draw = ImageDraw.Draw(sheet)
        draw.text((12, 10), f"Assembled film — sampled frames {index + 1}/{sheet_count}",
                  fill="#F6C383", font=font(22))
        for cell, sample in enumerate(subset):
            x = 12 + (cell % CONTACT_COLUMNS) * 320
            y = 52 + (cell // CONTACT_COLUMNS) * 208
            with Image.open(output.path(sample["file"])) as source:
                sheet.paste(source.convert("RGB"), (x, y))
            observed = sample.get("observedTimeSeconds")
            label = timestamp(observed if observed is not None
                              else sample["requestedTimeSeconds"])
            draw.text((x + 6, y + 184), label, fill="white", font=font(17))
        name = f"contact-sheet-{index + 1:02d}.jpg"
        sheet.save(output.path(name), quality=90)
        sheets.append({"file": name, "samples": [item["file"] for item in subset]})
    return sheets


def generate(args, output: ReviewOutput) -> dict:
    report = {
        "createdAtUtc": datetime.now(timezone.utc).isoformat(),
        "video": str(args.video), "timeline": str(args.timeline),
        "contactSheets": [], "frameSamples": [], "documentFrames": [],
        "soundClips": [], "errors": output.errors,
        "limits": [
            "Samples come from the assembled MP4, not source media or preview renders.",
            "The film has not been watched or heard by this sampling program.",
            "Contact sheets and four short sound clips do not replace full-film review.",
            "Document candidates are selected from timeline metadata; authenticity and "
            "legibility require inspection of the exported images and the film.",
            "No automatic editorial score or approval is produced.",
            "Observed source PTS is recorded where ffmpeg showinfo exposes it; otherwise "
            "the timestamp is only the requested seek time.",
        ],
    }
    if not args.video.is_file():
        output.errors.append({"operation": "input", "reason": "Final MP4 not found"})
        return report
    probe_text = output.run([
        "ffprobe", "-v", "error", "-show_format", "-show_streams",
        "-of", "json", str(args.video),
    ], "probe final MP4", timeout=30)
    try:
        probe = json.loads(probe_text or "{}")
        streams = probe.get("streams", [])
        video_stream = next(item for item in streams if item.get("codec_type") == "video")
    except (ValueError, StopIteration):
        output.errors.append({"operation": "probe", "reason": "No usable video stream"})
        return report
    duration = number(probe.get("format", {}).get("duration"),
                      number(video_stream.get("duration")))
    if duration <= 0:
        output.errors.append({"operation": "probe", "reason": "No positive duration"})
        return report
    fps = frame_rate(video_stream.get("avg_frame_rate", "30/1"))
    source_start = number(video_stream.get("start_time"))
    last_time = max(0.0, duration - max(0.1, 1 / fps))
    report["actualDurationSeconds"] = duration
    report["probe"] = probe
    try:
        timeline = json.loads(args.timeline.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as error:
        timeline = {}
        output.errors.append({"operation": "timeline", "reason": str(error)})
    report["timelineDurationSeconds"] = (
        number(timeline.get("durationInFrames")) / frame_rate(timeline.get("fps", fps))
        if timeline else None
    )
    desired_count = max(1, math.ceil(duration / 20.0) + 1)
    count = min(MAX_FRAMES, args.max_frames, desired_count)
    times = [last_time * index / max(1, count - 1) for index in range(count)]
    report["sampling"] = {
        "plannedFrameCount": count, "maximumFrameCount": min(MAX_FRAMES, args.max_frames),
        "intervalSeconds": times[1] - times[0] if len(times) > 1 else None,
        "timeBudgetSeconds": args.time_budget_seconds,
    }
    for index, seconds in enumerate(times):
        if time.monotonic() >= output.deadline:
            output.errors.append({"operation": "frame samples", "reason": "time budget exhausted"})
            break
        report["frameSamples"].append(output.image(
            args.video, seconds, f"thumbs/frame-{index + 1:03d}.jpg",
            THUMBNAIL_SIZE, source_start,
        ))
    report["contactSheets"] = contact_sheets(output, report["frameSamples"])

    selected = spread(document_windows(timeline, duration), 6)
    for fraction in (0.12, 0.38, 0.63, 0.87):
        if len(selected) >= 4:
            break
        point = last_time * fraction
        selected.append({
            "startSeconds": point, "endSeconds": point,
            "selectionReason": "representative frame; insufficient document windows",
        })
    for index, window in enumerate(selected):
        if time.monotonic() >= output.deadline:
            output.errors.append({"operation": "document frames", "reason": "time budget exhausted"})
            break
        point = min(last_time, window["startSeconds"]
                    + 0.5 * (window["endSeconds"] - window["startSeconds"]))
        sample = output.image(
            args.video, point, f"document-frame-{index + 1:02d}.png",
            (1920, 1080), source_start,
        )
        report["documentFrames"].append({**window, **sample})

    for index, fraction in enumerate((0.04, 0.32, 0.61, 0.86)):
        start = min(max(0.0, duration - CLIP_SECONDS), duration * fraction)
        length = min(CLIP_SECONDS, duration - start)
        name = f"sound-sample-{index + 1:02d}.mp4"
        destination = output.path(name)
        result = output.run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-y",
            "-ss", f"{start:.6f}", "-i", str(args.video), "-t", f"{length:.6f}",
            "-map", "0:v:0", "-map", "0:a:0?", "-c:v", "libx264",
            "-preset", "fast", "-crf", "24", "-threads", "2",
            "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart",
            str(destination),
        ], name, timeout=150)
        report["soundClips"].append({
            "file": name, "requestedStartSeconds": round(start, 6),
            "requestedEndSeconds": round(start + length, 6),
            "startTimestamp": timestamp(start), "durationSeconds": round(length, 6),
            "success": result is not None and destination.is_file(),
            "method": "accurate input seek and video/audio re-encode from final MP4",
        })
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--max-frames", type=int, default=MAX_FRAMES)
    parser.add_argument("--time-budget-seconds", type=int, default=600)
    args = parser.parse_args()
    args.max_frames = max(1, min(MAX_FRAMES, args.max_frames))
    args.time_budget_seconds = max(30, min(900, args.time_budget_seconds))
    output = None
    try:
        output = ReviewOutput(args.output_dir, [args.video, args.timeline],
                              args.time_budget_seconds)
        report = generate(args, output)
    except Exception as error:
        # Sampling is auxiliary: preserve the film and report concrete failures.
        report = {"errors": [{"operation": "review samples", "reason": str(error)}],
                  "limits": ["Sampling failed; no audiovisual review is claimed."]}
    if output is not None:
        report["status"] = "partial" if report.get("errors") else "samples-created"
        try:
            output.path("review-samples.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8",
            )
        except (OSError, ValueError) as error:
            report["status"] = "unavailable"
            print(f"[Final review samples] Could not save the sampling record: {error}",
                  flush=True)
    print(f"[Final review samples] {report.get('status', 'unavailable')}: {args.output_dir}",
          flush=True)
    # No editorial approval or quality gate: final-file integrity checks live elsewhere.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
