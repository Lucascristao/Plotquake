"""Prepare episode-specific photographs, documents, graphics and archive excerpts in CI.

This keeps the original source and a checksum receipt. Separate excerpts identify
actual shots/events in the source; changing a crop never creates a new identity.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re
import shutil
import subprocess

from prepare_blackberry_media import download_source, file_hash, fingerprint, probe, read_json, safe_output, write_json
from prepare_itt_revision_media import prepare_document

VERSION = 1


def prepare_plan(plan_path: Path, catalog_path: Path, public_root: Path, cache_dir: Path,
                 ffmpeg: str = "ffmpeg", ffprobe: str = "ffprobe") -> list[dict]:
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    namespace = plan["namespace"]
    if not re.fullmatch(r"[a-z0-9-]+", namespace):
        raise ValueError("Archival namespace must be a simple directory name.")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    sources = {item["id"]: item for item in plan["sources"]}
    prepared_sources = {}
    records = []
    for asset in plan["assets"]:
        key = asset["key"]
        if not re.fullmatch(r"[a-z0-9_]+", key):
            raise ValueError(f"Invalid media key: {key}")
        kind = "video" if asset["method"] == "video" else "image"
        expected = f"assets/{'video' if kind == 'video' else 'images'}/{namespace}/"
        if not asset["src"].startswith(expected):
            raise ValueError(f"Media output must stay in this episode's folder: {asset['src']}")
        destination = safe_output(public_root, asset["src"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        source = sources.get(asset.get("sourceId"))
        original, source_receipt = None, {}
        if source:
            if source["id"] not in prepared_sources:
                if source.get("localSource"):
                    local_source = safe_output(public_root, source["localSource"])
                    if not local_source.is_file() or file_hash(local_source) != source.get("expectedSha256"):
                        raise ValueError(f"Bundled original is missing or corrupted: {source['id']}")
                    prepared_sources[source["id"]] = (local_source, {"sourceId": source["id"],
                        "original": source["original"], "sha256": source["expectedSha256"],
                        "bytes": local_source.stat().st_size, "bundledSource": source["localSource"]})
                else:
                    prepared_sources[source["id"]] = download_source(source, cache_dir, attempts=4, timeout=90)
                if source.get("expectedMd5") and file_hash(prepared_sources[source["id"]][0], "md5") != source["expectedMd5"]:
                    raise ValueError(f"Source checksum does not match the archive metadata: {source['id']}")
            original, source_receipt = prepared_sources[source["id"]]
        recipe = fingerprint({"version": VERSION, "asset": asset, "source": source,
                              "sourceHash": source_receipt.get("sha256")})
        receipt_path = cache_dir / "prepared" / f"{key}.json"
        old = read_json(receipt_path)
        if destination.is_file() and old.get("recipe") == recipe and old.get("sha256") == file_hash(destination):
            records.append(old["catalog"])
            print(f"Reused archival asset {key}", flush=True)
            continue
        dimensions = {}
        if asset["method"] == "document":
            dimensions = prepare_document(original, destination, asset)
        elif asset["method"] == "photo":
            from PIL import Image
            with Image.open(original) as picture:
                picture.load()
                dimensions = {"width": picture.width, "height": picture.height}
                temporary = destination.with_name(destination.stem + ".part.jpg")
                picture.convert("RGB").save(temporary, format="JPEG", quality=95, subsampling=0)
                temporary.replace(destination)
        elif asset["method"] == "svg":
            destination.write_text(asset["svg"], encoding="utf-8")
            dimensions = {"width": 1920, "height": 1080}
        elif asset["method"] == "video":
            start, end = float(asset["startSeconds"]), float(asset["endSeconds"])
            if not 0 <= start < end <= float(source["durationSeconds"]) + .04:
                raise ValueError(f"Excerpt is outside its verified source: {key}")
            stream, _ = probe(original, ffprobe)
            frames = round((end - start) * 30)
            temporary = destination.with_name(destination.stem + ".part.mp4")
            subprocess.run([ffmpeg, "-y", "-v", "error", "-ss", str(start), "-i", str(original),
                            "-map", f"0:{stream['index']}", "-an", "-sn", "-dn", "-t", str(frames / 30),
                            "-vf", "scale='min(1920,iw)':'min(1080,ih)':force_original_aspect_ratio=decrease:force_divisible_by=2,setsar=1",
                            "-r", "30", "-frames:v", str(frames), "-c:v", "libx264", "-preset", "medium",
                            "-crf", "18", "-pix_fmt", "yuv420p", "-threads", "2", "-map_metadata", "-1",
                            "-movflags", "+faststart", str(temporary)], check=True)
            picture, metadata = probe(temporary, ffprobe, count_frames=True)
            if (int(picture.get("nb_read_frames", -1)) != frames or
                    abs(float(picture.get("duration", metadata.get("duration", 0))) - frames / 30) > .04):
                raise ValueError(f"Prepared excerpt is incomplete: {key}")
            temporary.replace(destination)
            dimensions = {"width": picture["width"], "height": picture["height"], "durationSeconds": frames / 30,
                          "originalStartSeconds": start, "originalEndSeconds": end}
        else:
            raise ValueError(f"Unknown archival recipe: {asset['method']}")
        record = {"key": key, "kind": kind, "src": asset["src"], "fit": "contain",
                  "origin": source["original"] if source else asset["origin"],
                  "originalMedia": source["original"] if source else asset["origin"],
                  "sourceId": asset.get("sourceId"), "title": asset.get("title", asset["caption"]),
                  "reuseFamily": asset["reuseFamily"], "author": source["author"] if source else "Plotquake",
                  "credit": source["author"] if source else "Plotquake",
                  "license": source["license"] if source else "Original Plotquake diagram",
                  "licenseUrl": source.get("licenseUrl", "") if source else "",
                  "changes": asset["changes"], "caption": asset["caption"],
                  "sourceSha256": source_receipt.get("sha256"), **dimensions}
        if asset["method"] == "document":
            record.update({"pdfPageOneBased": asset["pdfPageOneBased"], "documentaryEvidence": True,
                           "publication": asset["caption"], "date": asset.get("documentDate", "")})
        record.update(copy.deepcopy(asset.get("display", {})))
        write_json(receipt_path, {"recipe": recipe, "sha256": file_hash(destination), "catalog": record,
                                  "sourceReceipt": source_receipt})
        records.append(record)
        print(f"Prepared archival asset {key}", flush=True)
    keys = {item["key"] for item in records}
    catalog["assets"] = [item for item in catalog["assets"] if item["key"] not in keys] + records
    write_json(catalog_path, catalog)
    write_json(cache_dir / "selected-catalog.json", {"namespace": namespace, "assets": records, "prepared": True})
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, type=Path)
    parser.add_argument("--catalog", type=Path, default=Path("public/assets/media/catalog.json"))
    parser.add_argument("--public-root", type=Path, default=Path("public"))
    parser.add_argument("--cache-dir", required=True, type=Path)
    args = parser.parse_args()
    prepare_plan(args.plan, args.catalog, args.public_root, args.cache_dir)


if __name__ == "__main__":
    main()
