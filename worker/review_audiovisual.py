"""Optional descriptive analysis of the actual complete film, never an approval gate.

Google documentation checked on 2026-10-21. Video is sampled at 1 FPS; its
complete real audio track accompanies the request. This is model-assisted
observation, not human listening, full-frame-rate viewing, or audio metrology.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time


MODEL = "gemini-3.8-flash"
MAX_UPLOAD_BYTES = 2_000_000_000  # Conservative limit: official pages disagree above 2 GB.
MAX_INPUT_TOKENS = 500_000
DOCUMENTATION = [
    "https://ai.google.dev/gemini-api/docs/video-understanding",
    "https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash",
    "https://ai.google.dev/gemini-api/docs/files#usage-information",
    "https://ai.google.dev/gemini-api/docs/streaming",
    "https://ai.google.dev/gemini-api/docs/interactions-breaking-changes-may-2026",
    "https://ai.google.dev/gemini-api/docs/pricing#gemini-3.8-flash",
]
LIMITATIONS = [
    "Model-assisted analysis at 1 sampled video frame per second; not human viewing or listening.",
    "The complete file and its real audio are supplied, but the model may miss details, short cuts, sound defects or repetitions.",
    "Google preprocesses audio internally; this is not a check of stereo imaging, loudness compliance or sample accuracy.",
    "Timecodes and descriptions are model observations requiring verification; no score or editorial approval is produced.",
    "Timeline context identifies the intended story; it is not evidence that the corresponding image or sound appears in the file.",
]
PROMPT = """Observe this complete documentary's actual images AND actual sound from beginning through its final credits.
Give descriptive editorial observations in chronological order, using approximate MM:SS start/end timecodes.
Cover the whole supplied duration in intervals of roughly 30-60 seconds, with additional specific moments when useful.
Describe the pictured material, its relationship to the audible narration, the intelligibility and variation of vocal delivery,
and how audible music changes, enters, recedes or competes with speech. Note visible repeated imagery/movements,
documents and their practical readability, captions, credits, and any concrete image/sound mismatch you can observe.
Distinguish observed detail from uncertainty. Do not guess music audibility, spoken words, factual correctness or visual
content from the provided timeline. When something cannot be assessed from this sampled representation, say so.
Do not generate scores, grades, pass/fail, approval, release decisions, or a claim of human or full-frame-rate viewing.
Return JSON with keys observations (array of objects with start, end, picture, sound, relation, uncertainty),
overall_description (string) and limitations (array of strings). These are descriptive observations, not an audit.
"""


class ReviewUnavailable(ValueError):
    """A controlled local explanation which contains no remote request details."""


def file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def probe_video(path: Path) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True, timeout=60)
    data = json.loads(result.stdout)
    videos = [s for s in data.get("streams", []) if s.get("codec_type") == "video"]
    audio = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
    duration = float(data.get("format", {}).get("duration", 0))
    if not videos or not audio or not math.isfinite(duration) or duration <= 0:
        raise ReviewUnavailable("The analysis input must contain actual video, audio and a finite positive duration.")
    return {"durationSeconds": duration, "width": videos[0]["width"], "height": videos[0]["height"],
            "audioCodec": audio[0].get("codec_name"), "audioChannels": audio[0].get("channels"),
            "format": data["format"].get("format_name", "")}


def select_input(video: Path, destination: Path, *, allow_ci_proxy: bool, max_upload_bytes: int) -> tuple[Path, dict]:
    info = probe_video(video)
    if video.stat().st_size <= max_upload_bytes and "mp4" in info["format"].split(","):
        return video, {**info, "proxy": False, "audioHandling": "Original final MP4 uploaded without rewriting."}
    if not allow_ci_proxy or os.getenv("GITHUB_ACTIONS") != "true":
        raise ReviewUnavailable("Input needs a smaller MP4 proxy; creation requires --allow-ci-proxy inside GitHub Actions.")
    proxy = destination / "audiovisual_review_proxy.mp4"
    command = ["ffmpeg", "-y", "-v", "error", "-i", str(video), "-map", "0:v:0", "-map", "0:a:0",
                    "-vf", "scale='min(960,iw)':'min(540,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1",
                    "-c:v", "libx264", "-preset", "fast", "-crf", "28", "-pix_fmt", "yuv420p",
               "-threads", "2", "-c:a", "copy", "-movflags", "+faststart", str(proxy)]
    started = time.monotonic()
    with subprocess.Popen(command) as process:
        while True:
            try:
                if process.wait(timeout=60):
                    raise ReviewUnavailable("The optional review proxy could not be encoded.")
                break
            except subprocess.TimeoutExpired:
                if time.monotonic() - started > 1800:
                    process.kill()
                    process.wait(timeout=60)
                    raise ReviewUnavailable("The optional proxy exceeded its encoding time budget.")
    derived = probe_video(proxy)
    if (proxy.stat().st_size > max_upload_bytes or derived["height"] > 540 or derived["width"] > 960
            or abs(derived["durationSeconds"] - info["durationSeconds"]) > .2
            or derived["audioCodec"] != info["audioCodec"] or derived["audioChannels"] != info["audioChannels"]):
        raise ReviewUnavailable("The review proxy does not preserve the required complete duration and copied real audio.")
    return proxy, {**derived, "proxy": True, "audioHandling": "Original audio stream copied; no re-encoding, normalization or muting."}


def timeline_context(path: Path | None) -> str:
    if path is None:
        return ""
    timeline = json.loads(path.read_text(encoding="utf-8-sig"))
    episode = timeline.get("episode", timeline)
    fps = float(episode["fps"])
    scenes = []
    for act in episode.get("acts", []):
        for scene in act.get("scenes", []):
            start = (act.get("startFrame", 0) + scene["startFrame"]) / fps
            scenes.append({"id": scene["id"], "startSeconds": start,
                           "endSeconds": start + scene["durationInFrames"] / fps, "caption": scene.get("caption", "")})
    return "\nIntended-story context only (observe the file independently):\n" + json.dumps({
        "title": episode.get("title"), "description": episode.get("description"), "scenes": scenes,
        "endCredits": episode.get("endCredits")}, ensure_ascii=False)


def value(obj, key, default=None):
    return obj.get(key, default) if isinstance(obj, dict) else getattr(obj, key, default)


def plain(obj):
    return obj.model_dump(mode="json", exclude_none=True) if hasattr(obj, "model_dump") else obj


def analyze(client, path: Path, prompt: str, model: str, *, timeout_seconds: float = 900,
            cleanup: dict | None = None) -> dict:
    uploaded = None
    cleanup = cleanup if cleanup is not None else {}
    cleanup["fileDeletion"] = "not_uploaded"
    started = time.monotonic()
    try:
        uploaded = client.files.upload(file=str(path), config={"mime_type": "video/mp4"})
        while True:
            state = value(value(uploaded, "state"), "name", value(uploaded, "state"))
            if state == "ACTIVE":
                break
            if state == "FAILED":
                raise ReviewUnavailable("The uploaded video could not be processed by the service.")
            if time.monotonic() - started > timeout_seconds:
                raise ReviewUnavailable("Video processing exceeded the optional-analysis time budget.")
            time.sleep(5)
            uploaded = client.files.get(name=value(uploaded, "name"))
        stream = client.interactions.create(model=model, store=False, stream=True,
            input=[{"type": "video", "uri": value(uploaded, "uri"), "mime_type": "video/mp4",
                    "resolution": "high", "processing": {"type": "static", "fps": 1}},
                   {"type": "text", "text": prompt}],
            generation_config={"thinking_level": "low", "thinking_summaries": "none",
                               "max_output_tokens": 12288, "tool_choice": "none"})
        fragments, final = [], None
        try:
            for event in stream:
                if time.monotonic() - started > timeout_seconds:
                    raise ReviewUnavailable("The optional analysis exceeded its elapsed time budget.")
                if value(event, "event_type") == "step.start" and value(value(event, "step"), "type") == "model_output":
                    # The initial event can already carry text; deltas only
                    # contain subsequent fragments, per the May 2026 schema.
                    fragments.extend(value(part, "text", "") or "" for part in (value(value(event, "step"), "content") or [])
                                     if value(part, "type") == "text")
                elif value(event, "event_type") == "step.delta" and value(value(event, "delta"), "type") == "text":
                    fragments.append(value(value(event, "delta"), "text", "") or "")
                elif value(event, "event_type") == "interaction.completed":
                    final = value(event, "interaction")
        finally:
            if hasattr(stream, "close"):
                stream.close()
        text = "".join(fragments).strip()
        if value(final, "status") != "completed" or not text:
            raise ReviewUnavailable("No completed descriptive model response was received; no review is recorded.")
        result = {"rawDescriptiveResponse": text, "usage": plain(value(final, "usage")), "cleanup": cleanup}
        candidate = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        try:
            parsed = json.loads(candidate)
            if not isinstance(parsed, dict) or not isinstance(parsed.get("observations"), list):
                raise ValueError("Response has no observation array.")
            result["descriptiveObservations"] = parsed
            result["responseFormat"] = "json"
        except (ValueError, TypeError):
            result["responseFormat"] = "raw_text"
        return result
    finally:
        if uploaded is not None:
            try:
                client.files.delete(name=value(uploaded, "name"))
                cleanup["fileDeletion"] = "requested_successfully"
            except Exception as error:
                cleanup.update(fileDeletion="unavailable", errorType=type(error).__name__)


def write_report(destination: Path, report: dict) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "audiovisual_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# Model-assisted audiovisual observations", "", f"Availability: {report['availability']}", "",
             f"Model: {report['model']}; static visual sampling: 1 FPS.", "",
             "The complete real audio accompanies the input. This is not human listening or full-frame-rate viewing.", ""]
    if report.get("reason"):
        lines.extend([report["reason"], ""])
    if report.get("rawDescriptiveResponse"):
        lines.extend([report["rawDescriptiveResponse"], ""])
    lines.extend(["## Scope and limitations", "", *[f"- {item}" for item in LIMITATIONS], ""])
    (destination / "audiovisual_review.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("renders/audiovisual-review"))
    parser.add_argument("--timeline", type=Path)
    parser.add_argument("--model", default=MODEL)
    parser.add_argument("--max-upload-bytes", type=int, default=MAX_UPLOAD_BYTES)
    parser.add_argument("--max-input-tokens", type=int, default=MAX_INPUT_TOKENS)
    parser.add_argument("--allow-ci-proxy", action="store_true")
    args = parser.parse_args()
    report = {"availability": "unavailable", "modelAnalysisCompleted": False, "humanListeningPerformed": False,
              "model": args.model, "createdAt": datetime.now(timezone.utc).isoformat(),
              "input": str(args.video), "samplingFps": 1, "processing": "static", "mediaResolution": "high",
              "scope": "Descriptive observations of the supplied complete video and audio, with sampled images.",
              "limitations": LIMITATIONS, "documentationCheckedOn": "2026-10-21", "documentation": DOCUMENTATION}
    write_report(args.output_dir, report)
    try:
        if args.max_upload_bytes <= 0 or args.max_input_tokens <= 0:
            raise ReviewUnavailable("Upload and estimated-token budgets must be positive.")
        path, info = select_input(args.video, args.output_dir, allow_ci_proxy=args.allow_ci_proxy,
                                  max_upload_bytes=args.max_upload_bytes)
        prompt = PROMPT + f"\nSupplied duration: {info['durationSeconds']:.3f} seconds.\n" + timeline_context(args.timeline)
        estimated = math.ceil(info["durationSeconds"] * 300 + len(prompt) / 3 + 1024)
        report.update(inputMedia=info, sourceSha256=file_hash(args.video), uploadedSha256=file_hash(path),
                      uploadedBytes=path.stat().st_size, estimatedInputTokens=estimated,
                      estimatedInputTokenLimit=args.max_input_tokens,
                      tokenEstimateScope="Approximate high-resolution 1 FPS video+audio and prompt; actual metering can differ.")
        if info.get("proxy"):
            report["proxySha256"] = report["uploadedSha256"]
        if estimated > args.max_input_tokens:
            raise ReviewUnavailable("Input exceeds the optional estimated-token budget; no API request was made.")
        key = os.getenv("GEMINI_API_KEY", "")
        if not key:
            raise ReviewUnavailable("GEMINI_API_KEY is unavailable; no API request was made.")
        from google import genai
        client = genai.Client(api_key=key, http_options={"timeout": 60_000})
        try:
            report["cleanup"] = {}
            report.update(analyze(client, path, prompt, args.model, cleanup=report["cleanup"]))
        finally:
            client.close()
        report.update(availability="observations_available", modelAnalysisCompleted=True)
    except Exception as error:
        # API exception text may include request details. Record the type only;
        # controlled local errors provide a useful reason without secret material.
        report["reason"] = (str(error) if isinstance(error, ReviewUnavailable) else
                            f"{type(error).__name__}: optional model analysis unavailable; no completed review recorded.")
        for name in ("code", "status_code"):
            code = getattr(error, name, None)
            if isinstance(code, int) and not isinstance(code, bool):
                report["errorCode"] = code
                break
    write_report(args.output_dir, report)
    print(f"[Optional audiovisual observations] {report['availability']}; no editorial approval or gate.")


if __name__ == "__main__":
    main()
