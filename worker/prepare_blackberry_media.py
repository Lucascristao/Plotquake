"""Fetch selected archival media and prepare short silent clips, normally in CI.

Source downloads and output receipts live in --cache-dir. The source family is
kept in the catalog even when several distinct excerpts share one recording.
This prepares assets only; it never starts a documentary render or uploads one.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import shutil
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request

VERSION = 2
USER_AGENT = "Plotquake-Archival-Preparation/1.0 (documentary research; public media)"


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def file_hash(path: Path, algorithm: str = "sha256") -> str:
    result = hashlib.new(algorithm)
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()


def fingerprint(value: dict) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def safe_output(public_root: Path, relative: str) -> Path:
    candidate = (public_root / relative).resolve()
    if not candidate.is_relative_to(public_root.resolve()):
        raise ValueError(f"Media output escapes public root: {relative}")
    return candidate


def validate_manifest(manifest: dict) -> None:
    sources = manifest.get("sources", [])
    ids = [source["id"] for source in sources]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate source id in media manifest.")
    by_id = {source["id"]: source for source in sources}
    for source in sources:
        if not re.fullmatch(r"[a-z0-9-]+", source["id"]):
            raise ValueError(f"Invalid source id: {source['id']}")
        if urllib.parse.urlsplit(source["downloadUrl"]).scheme not in ("https", "http"):
            raise ValueError(f"Expected a public HTTP(S) source: {source['id']}")
        if not source.get("original") or not source.get("reuseFamily") or not source.get("license"):
            raise ValueError(f"Missing provenance for {source['id']}")
    assets = manifest.get("assets", [])
    asset_ids = [asset["id"] for asset in assets]
    if len(asset_ids) != len(set(asset_ids)):
        raise ValueError("Duplicate prepared asset id.")
    for asset in assets:
        if not re.fullmatch(r"[a-z0-9-]+", asset["id"]):
            raise ValueError(f"Invalid asset id: {asset['id']}")
        source = by_id[asset["sourceId"]]
        expected = f"assets/{'images' if asset['kind'] == 'image' else 'video'}/blackberry-redo/"
        if not asset["src"].startswith(expected) or ".." in Path(asset["src"]).parts:
            raise ValueError(f"Unexpected output path: {asset['src']}")
        if asset["kind"] == "video":
            first, until = float(asset["startSeconds"]), float(asset["endSeconds"])
            if not math.isfinite(first + until) or first < 0 or until <= first:
                raise ValueError(f"Invalid excerpt: {asset['id']}")
            if until > float(source["durationSeconds"]):
                raise ValueError(f"Excerpt exceeds source: {asset['id']}")
        elif asset["kind"] != "image":
            raise ValueError(f"Unknown asset kind: {asset['kind']}")


def download_source(source: dict, cache_dir: Path, attempts: int = 4, timeout: float = 60) -> tuple[Path, dict]:
    """Resume interrupted HTTP transfers; reuse only a checksum-matching cache."""
    identity = {key: source.get(key) for key in ("downloadUrl", "expectedBytes", "expectedSha1")}
    key = fingerprint(identity)
    target = cache_dir / "sources" / f"{source['id']}-{key[:16]}.bin"
    target.parent.mkdir(parents=True, exist_ok=True)
    receipt_path = target.with_suffix(".json")
    receipt = read_json(receipt_path)
    if (target.is_file() and receipt.get("identity") == identity
            and receipt.get("sha256") == file_hash(target)):
        return target, receipt
    partial = target.with_suffix(".part")
    maximum = int(source.get("maxDownloadBytes", source.get("expectedBytes") or
                             (30 * 1024 * 1024 if source.get("kind") == "image" else 512 * 1024 * 1024)))
    last_error: Exception | None = None
    for attempt in range(attempts):
        offset = partial.stat().st_size if partial.is_file() else 0
        headers = {"User-Agent": USER_AGENT, "Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(source["downloadUrl"], headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                status = response.status
                if "text/html" in response.headers.get("Content-Type", "").lower():
                    raise ValueError(f"Received an HTML page instead of media: {source['id']}")
                if status == 206:
                    match = re.fullmatch(r"bytes (\d+)-(\d+)/(\d+|\*)", response.headers.get("Content-Range", ""))
                    if not match or int(match.group(1)) != offset:
                        raise ValueError("Server returned an unexpected byte range.")
                    total = None if match.group(3) == "*" else int(match.group(3))
                else:
                    # A server ignoring Range must replace the partial, never append duplicate bytes.
                    offset = 0
                    total = int(response.headers["Content-Length"]) if response.headers.get("Content-Length") else None
                if (total is not None and total > maximum) or offset > maximum:
                    raise ValueError(f"Source exceeds download limit: {source['id']}")
                with partial.open("ab" if offset else "wb") as stream:
                    for block in iter(lambda: response.read(1024 * 1024), b""):
                        if stream.tell() + len(block) > maximum:
                            raise ValueError(f"Source exceeds download limit: {source['id']}")
                        stream.write(block)
                size = partial.stat().st_size
                expected = source.get("expectedBytes") or total
                if size < 100 or (expected is not None and size != int(expected)):
                    raise ValueError(f"Incomplete media download {source['id']}: {size}/{expected} bytes")
                if source.get("expectedSha1") and file_hash(partial, "sha1") != source["expectedSha1"]:
                    partial.unlink()
                    raise ValueError(f"Source SHA-1 mismatch: {source['id']}")
                partial.replace(target)
                receipt = {"identity": identity, "sourceId": source["id"], "original": source["original"],
                           "reuseFamily": source["reuseFamily"], "bytes": size, "sha256": file_hash(target),
                           "etag": response.headers.get("ETag"), "lastModified": response.headers.get("Last-Modified")}
                write_json(receipt_path, receipt)
                return target, receipt
        except (OSError, ValueError, urllib.error.URLError) as error:
            last_error = error
            # A stale/complete partial can produce 416; discard only this generated partial.
            if isinstance(error, urllib.error.HTTPError) and error.code == 416 and partial.exists():
                partial.unlink()
            if attempt + 1 < attempts:
                delay = min(20, 2 ** (attempt + 1))
                if isinstance(error, urllib.error.HTTPError) and error.code == 429:
                    retry_after = error.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        delay = min(30, max(delay, int(retry_after)))
                print(f"Retry {attempt + 1}/{attempts} {source['id']}: {error}", flush=True)
                time.sleep(delay)
    raise RuntimeError(f"Could not download {source['id']}: {last_error}") from last_error


def probe(path: Path, ffprobe: str, count_frames: bool = False) -> tuple[dict, dict]:
    command = [ffprobe, "-v", "error"] + (["-count_frames"] if count_frames else [])
    result = subprocess.run(command + ["-show_streams", "-show_format", "-of", "json", str(path)],
                            check=True, capture_output=True, text=True)
    data = json.loads(result.stdout)
    video = next((stream for stream in data.get("streams", [])
                  if stream.get("codec_type") == "video" and not stream.get("disposition", {}).get("attached_pic")), None)
    if not video or int(video.get("width", 0)) < 1 or int(video.get("height", 0)) < 1:
        raise ValueError(f"No decodable picture in {path}")
    return video, data.get("format", {})


def catalog_record(source: dict, asset: dict) -> dict:
    photo = asset["kind"] == "image"
    record = {"key": "bb_redo_" + asset["id"].replace("-", "_"), "kind": asset["kind"], "src": asset["src"],
              "origin": source["original"], "sourceId": source["id"], "reuseFamily": source["reuseFamily"],
              "originalMedia": source["original"], "credit": source["author"], "license": source["license"],
              "licenseUrl": source.get("licenseUrl", ""), "captureDate": source.get("captureDate", ""),
              "displayLabel": asset["label"], "editorialNote": asset.get("note", ""),
              "changes": "Source JPEG retained without enlargement; editorial framing/movement in film."
                         if photo else "Distinct excerpt trimmed to stated interval; original aspect ratio; muted; H.264 CRF18, 30 fps.",
              "width": source.get("preparedWidth", source.get("width")),
              "height": source.get("preparedHeight", source.get("height")), "fit": "contain"}
    if not photo:
        record.update({"durationSeconds": round(asset["endSeconds"] - asset["startSeconds"], 6),
                       "originalStartSeconds": asset["startSeconds"], "originalEndSeconds": asset["endSeconds"],
                       "trimStartSeconds": 0, "muted": True})
    return record


def prepare_asset(source: dict, asset: dict, public_root: Path, cache_dir: Path,
                  ffmpeg: str, ffprobe: str, attempts: int = 4, timeout: float = 60) -> dict:
    destination = safe_output(public_root, asset["src"])
    # Selected original JPEGs can travel in Git with a source/provenance manifest.
    # Verify their exact bytes instead of requesting the same public thumbnail again.
    if asset["kind"] == "image" and destination.is_file() and asset.get("preparedSha256"):
        if file_hash(destination) != asset["preparedSha256"]:
            raise ValueError(f"Versioned source photo checksum mismatch: {asset['id']}")
        from PIL import Image
        with Image.open(destination) as image:
            image.load()
            if image.format != "JPEG":
                raise ValueError(f"Expected original JPEG: {asset['id']}")
            record = catalog_record(source, asset)
            record.update({"width": image.width, "height": image.height})
        print(f"Verified versioned source photo {asset['id']}", flush=True)
        return record
    original, source_receipt = download_source(source, cache_dir, attempts, timeout)
    destination.parent.mkdir(parents=True, exist_ok=True)
    recipe = fingerprint({"version": VERSION, "asset": asset, "sourceSha256": source_receipt["sha256"],
                          "encoding": "JPEG-original-or-mjpeg-q2 / H264-crf18-medium-yuv420p-30fps-max1080"})
    receipt_path = cache_dir / "prepared" / (asset["id"] + ".json")
    old = read_json(receipt_path)
    if destination.is_file() and old.get("recipe") == recipe and old.get("sha256") == file_hash(destination):
        print(f"Reused {asset['id']}", flush=True)
        return old["catalog"]
    temporary = destination.with_name(destination.stem + ".part" + destination.suffix)
    if asset["kind"] == "image":
        # JPEG validation must not depend on the locally bundled minimal FFmpeg.
        # Load pixels as well as parsing the header to catch truncated downloads.
        from PIL import Image
        with Image.open(original) as image:
            image.load()
            if image.format != "JPEG":
                raise ValueError(f"Expected a source JPEG: {asset['id']}")
            picture = {"codec_name": "mjpeg", "width": image.width, "height": image.height}
        shutil.copyfile(original, temporary)
    else:
        stream, _ = probe(original, ffprobe)
        frames = round((asset["endSeconds"] - asset["startSeconds"]) * 30)
        scale = "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1"
        command = [ffmpeg, "-y", "-v", "error", "-ss", str(asset["startSeconds"]), "-i", str(original),
                   "-map", f"0:{stream['index']}", "-an", "-sn", "-dn", "-t", str(frames / 30),
                   "-vf", scale, "-r", "30", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium",
                   "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", "-map_metadata", "-1",
                   "-movflags", "+faststart", "-f", "mp4", str(temporary)]
        subprocess.run(command, check=True)
        picture, metadata = probe(temporary, ffprobe, count_frames=True)
        duration = float(picture.get("duration", metadata.get("duration", 0)))
        if (picture.get("codec_name") != "h264" or int(picture.get("nb_read_frames", -1)) != frames
                or abs(duration - frames / 30) > .04 or picture["width"] > 1920 or picture["height"] > 1080):
            raise ValueError(f"Prepared clip is incomplete or outside the output profile: {asset['id']}")
    temporary.replace(destination)
    record = catalog_record(source, asset)
    record.update({"width": picture["width"], "height": picture["height"]})
    write_json(receipt_path, {"recipe": recipe, "sha256": file_hash(destination), "catalog": record,
                              "sourceSha256": source_receipt["sha256"], "sourceReceipt": source_receipt,
                              "originalInterval": None if asset["kind"] == "image" else
                              [asset["startSeconds"], asset["endSeconds"]]})
    print(f"Prepared {asset['id']} ({record['width']}x{record['height']})", flush=True)
    return record


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("episodes/blackberry-media-manifest.json"))
    parser.add_argument("--public-root", type=Path, default=Path("public"))
    parser.add_argument("--cache-dir", type=Path, default=Path("out/media-cache/blackberry-redo"))
    parser.add_argument("--catalog-output", type=Path, default=Path("out/blackberry-redo-media/selected-catalog.json"))
    parser.add_argument("--only", nargs="+", help="Prepare only these asset ids; for focused retries or a small smoke check")
    parser.add_argument("--catalog-only", action="store_true", help="Write catalog records without downloading; not a readiness claim")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--attempts", type=int, default=4)
    parser.add_argument("--timeout", type=float, default=60)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    sources = {source["id"]: source for source in manifest["sources"]}
    assets = manifest["assets"]
    if args.only:
        unknown = set(args.only) - {asset["id"] for asset in assets}
        if unknown:
            raise ValueError(f"Unknown asset ids: {sorted(unknown)}")
        assets = [asset for asset in assets if asset["id"] in args.only]
    records = []
    for asset in assets:
        source = sources[asset["sourceId"]]
        records.append(catalog_record(source, asset) if args.catalog_only else
                       prepare_asset(source, asset, args.public_root, args.cache_dir,
                                     args.ffmpeg, args.ffprobe, args.attempts, args.timeout))
    write_json(args.catalog_output, {"assets": records, "prepared": not args.catalog_only,
                                     "manifest": args.manifest.as_posix(), "version": VERSION})
    print(f"{'Listed' if args.catalog_only else 'Prepared'} {len(records)} assets; catalog: {args.catalog_output}", flush=True)


if __name__ == "__main__":
    main()
