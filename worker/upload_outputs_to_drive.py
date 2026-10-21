"""Upload a complete documentary package and save a concrete Drive delivery receipt."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
from drive import uploader_from_env
from synthesize_narration import digest, write_json


def safe_name(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9._ -]+", "", value).strip()[:120] or "episode"


def verify_video(video: Path, timeline: dict, minimum_seconds: float) -> dict:
    result = subprocess.run(["ffprobe", "-v", "error", "-show_format", "-show_streams", "-of", "json", str(video)],
                            check=True, capture_output=True, text=True)
    info = json.loads(result.stdout)
    streams = info.get("streams", [])
    visuals = [item for item in streams if item.get("codec_type") == "video"]
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    if len(visuals) != 1 or not audio:
        raise ValueError("Final MP4 must contain its video and narration audio streams.")
    expected = timeline["durationInFrames"] / timeline["fps"]
    duration = float(info["format"]["duration"])
    if duration < minimum_seconds or abs(expected - duration) > .2:
        raise ValueError(f"Final video is {duration:.2f}s; expected {expected:.2f}s and minimum {minimum_seconds:.0f}s.")
    if (visuals[0].get("width"), visuals[0].get("height")) != (1920, 1080):
        raise ValueError("Final documentary must be Full HD 1920x1080.")
    return {"durationSeconds": duration, "width": 1920, "height": 1080, "sha256": digest(video)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True)
    parser.add_argument("--thumbnail", required=True)
    parser.add_argument("--metadata", required=True)
    parser.add_argument("--episode", default="episodes/blackberry.json")
    parser.add_argument("--render-input", default="src/episodes/renderEpisode.json")
    parser.add_argument("--receipt", default="renders/drive_receipt.json")
    args = parser.parse_args()
    paths = [Path(args.video), Path(args.thumbnail), Path(args.metadata)]
    for path in paths:
        if not path.is_file() or path.stat().st_size == 0:
            raise FileNotFoundError(f"Complete delivery requires this nonempty file: {path}")
    source = json.loads(Path(args.episode).read_text(encoding="utf-8-sig"))
    timeline = json.loads(Path(args.render_input).read_text(encoding="utf-8-sig"))
    if source["id"] != timeline["id"]:
        raise ValueError("Episode id does not match the rendered timeline.")
    video_info = verify_video(paths[0], timeline, max(900, float(source.get("minimumDurationSeconds", 900))))
    uploader = uploader_from_env()
    if uploader is None:
        raise RuntimeError("Google Drive requires GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REFRESH_TOKEN and GOOGLE_DRIVE_FOLDER_ID.")
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    folder_name = f"{safe_name(source['title'])}_{stamp}"
    folder_id = uploader.create_folder(folder_name)
    receipt = {"episodeId": source["id"], "title": source["title"], "status": "uploading",
               "folderId": folder_id, "folderUrl": f"https://drive.google.com/drive/folders/{folder_id}",
               "video": video_info, "files": [], "createdAt": datetime.now(timezone.utc).isoformat()}
    receipt_path = Path(args.receipt)
    write_json(receipt_path, receipt)
    extra = Path(args.metadata).with_suffix(".json")
    if extra.is_file():
        paths.append(extra)
    credits = Path(args.metadata).parent / "visual_credits.txt"
    if credits.is_file():
        paths.append(credits)
    if source.get("publication", {}).get("standard") == "cinematic-v1":
        for name in ("internal_documentation.json", "internal_documentation.txt", "research_sources.md"):
            documentation = Path(args.metadata).parent / name
            if not documentation.is_file() or not documentation.stat().st_size:
                raise FileNotFoundError(f"The new delivery standard requires separate documentation: {name}")
            paths.append(documentation)
    if (source.get("audiovisualReview") or {}).get("enabled") is True:
        for name in ("audiovisual_review.json", "audiovisual_review.md"):
            observation = Path(args.metadata).parent / "audiovisual-review" / name
            if observation.is_file() and observation.stat().st_size:
                paths.append(observation)
    for path in paths:
        print(f"[Drive] Uploading {path.name} ({path.stat().st_size / 1048576:.1f} MB)...", flush=True)
        file_id = uploader.upload(path, name=path.name, folder_id=folder_id,
                                  progress_cb=lambda value: print(f"[Drive] {value:.0%}", flush=True))
        receipt["files"].append({"name": path.name, "id": file_id,
                                 "url": f"https://drive.google.com/file/d/{file_id}/view",
                                 "bytes": path.stat().st_size, "sha256": digest(path)})
        write_json(receipt_path, receipt)
    receipt["status"] = "complete"
    receipt["completedAt"] = datetime.now(timezone.utc).isoformat()
    write_json(receipt_path, receipt)
    uploader.upload(receipt_path, name="drive_receipt.json", folder_id=folder_id)
    print(f"[DELIVERY COMPLETE] {receipt['folderUrl']}", flush=True)


if __name__ == "__main__":
    main()
