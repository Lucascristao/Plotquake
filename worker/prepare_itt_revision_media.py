"""Prepare the authored ITT archive in CI; retain originals and checksum receipts.

This is asset preparation only. It never synthesizes speech, renders a film,
changes a narration, or uploads anything. Document pictures are actual PDF pixels.
"""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import re

from prepare_blackberry_media import download_source, file_hash, fingerprint, read_json, safe_output, write_json

VERSION = 1


def normalize(text):
    return re.sub(r"\W+", "", text.casefold().replace("\u00ad", ""))


def prepare_document(original, destination, asset):
    import fitz
    with fitz.open(original) as document:
        page = document[int(asset["pdfPageOneBased"]) - 1]
        blocks = [b for b in page.get_text("blocks") if len(b) > 4 and str(b[4]).strip()]
        anchors = asset.get("cropTextAnchors", [])
        selected = [b for b in blocks if any(normalize(a) in normalize(str(b[4])) for a in anchors)]
        if selected:
            clip = fitz.Rect(selected[0][:4])
            for block in selected[1:]:
                clip |= fitz.Rect(block[:4])
            # Keep complete text blocks, including their surrounding white margin.
            clip = fitz.Rect(clip.x0 - 14, clip.y0 - 13, clip.x1 + 14, clip.y1 + 13) & page.rect
        else:
            # Never fabricate a replacement when OCR differs; preserve the source page.
            clip = page.rect
        highlights, missed = [], []
        for anchor in asset.get("highlightTextAnchors", []):
            matches = page.search_for(anchor)
            matches = [r for r in matches if r.intersects(clip)]
            if not matches:
                missed.append(anchor)
            for rect in matches:
                page.draw_rect(rect, color=None, fill=(229/255, 161/255, 88/255), fill_opacity=.28, overlay=True)
                highlights.append({"x": (rect.x0-clip.x0)/clip.width, "y": (rect.y0-clip.y0)/clip.height,
                                   "width": rect.width/clip.width, "height": rect.height/clip.height})
        scale = min(3, 2500 / max(clip.width, clip.height))
        pixmap = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=clip, alpha=False)
        temporary = destination.with_name(destination.stem + ".part.png")
        pixmap.save(temporary)
        temporary.replace(destination)
        return {"width": pixmap.width, "height": pixmap.height,
                "documentCropPoints": list(clip), "highlightBoxes": highlights,
                "unmatchedHighlightAnchors": missed, "cropAnchorMatched": bool(selected)}


def prepare_plan(plan_path, catalog_path, public_root, cache_dir):
    plan = json.loads(plan_path.read_text(encoding="utf-8-sig"))
    catalog = json.loads(catalog_path.read_text(encoding="utf-8-sig"))
    old_assets = catalog["assets"]
    sources = {item["id"]: item for item in plan.get("sources", [])}
    records = []
    for asset in plan["assets"]:
        key = asset["key"]
        if not re.fullmatch(r"itt_rev_[a-z0-9_]+", key):
            raise ValueError(f"Invalid ITT media key: {key}")
        if asset["method"] == "existing":
            matches = [item for item in old_assets if item["src"] == asset["existingSrc"] and item["key"] != key]
            if not matches:
                raise ValueError(f"Missing original catalog asset: {asset['existingSrc']}")
            record = copy.deepcopy(matches[0])
            path = safe_output(public_root, record["src"])
            if not path.is_file():
                raise ValueError(f"Missing original file: {path}")
            record["key"] = key
            record["reuseFamily"] = asset["reuseFamily"]
            record["originalMedia"] = record.get("originalMedia") or record.get("origin")
            record["sourceSha256"] = file_hash(path)
            record.update(asset.get("display", {}))
            records.append(record)
            continue
        destination = safe_output(public_root, asset["src"])
        destination.parent.mkdir(parents=True, exist_ok=True)
        receipt_path = cache_dir / "prepared" / f"{key}.json"
        source = sources.get(asset.get("sourceId"))
        original, source_receipt = (None, {})
        if source:
            if source.get("localSource"):
                original = safe_output(public_root, source["localSource"])
                if not original.is_file() or not source.get("expectedSha256") or file_hash(original) != source["expectedSha256"]:
                    raise ValueError(f"Bundled source missing or checksum mismatch: {source['id']}")
                source_receipt = {"sourceId": source["id"], "original": source["original"],
                                  "reuseFamily": source["reuseFamily"], "bytes": original.stat().st_size,
                                  "sha256": source["expectedSha256"], "bundledSource": source["localSource"]}
            else:
                original, source_receipt = download_source(source, cache_dir, attempts=4, timeout=90)
        recipe = fingerprint({"version": VERSION, "asset": asset, "sourceHash": source_receipt.get("sha256")})
        old = read_json(receipt_path)
        if destination.is_file() and old.get("recipe") == recipe and old.get("sha256") == file_hash(destination):
            records.append(old["catalog"])
            print(f"Reused ITT asset {key}", flush=True)
            continue
        if asset["method"] == "document":
            dimensions = prepare_document(original, destination, asset)
        elif asset["method"] == "photo":
            from PIL import Image
            with Image.open(original) as picture:
                picture.load()
                dimensions = {"width": picture.width, "height": picture.height}
                # No enlargement, generative modification, or restoration of source photographs.
                temporary = destination.with_name(destination.stem + ".part.jpg")
                picture.convert("RGB").save(temporary, format="JPEG", quality=95, subsampling=0)
                temporary.replace(destination)
        elif asset["method"] == "svg":
            destination.write_text(asset["svg"], encoding="utf-8")
            dimensions = {"width": 1920, "height": 1080}
        else:
            raise ValueError(f"Unknown preparation method: {asset['method']}")
        record = {"key": key, "kind": "image", "src": asset["src"], "fit": "contain",
                  "origin": source["original"] if source else asset["origin"],
                  "originalMedia": source["original"] if source else asset["origin"],
                  "reuseFamily": asset["reuseFamily"], "credit": source["author"] if source else "Plotquake editorial graphic",
                  "license": source["license"] if source else "Original Plotquake artwork",
                  "licenseUrl": source.get("licenseUrl", "") if source else "",
                  "changes": asset["changes"], "caption": asset["caption"],
                  "motion": "push", "zoomStart": 1, "zoomEnd": 1.025,
                  "sourceSha256": source_receipt.get("sha256"), **dimensions}
        if asset["method"] == "document":
            record.update({"pdfPageOneBased": asset["pdfPageOneBased"], "publication": asset["caption"],
                           "date": asset.get("documentDate", ""), "documentaryEvidence": True})
        record.update(asset.get("display", {}))
        write_json(receipt_path, {"recipe": recipe, "sha256": file_hash(destination), "catalog": record,
                                  "sourceReceipt": source_receipt})
        records.append(record)
        print(f"Prepared ITT asset {key}", flush=True)
    keys = {item["key"] for item in records}
    catalog["assets"] = [item for item in old_assets if item["key"] not in keys] + records
    write_json(catalog_path, catalog)
    write_json(cache_dir / "selected-catalog.json", {"assets": records, "prepared": True,
                                                    "plan": plan_path.as_posix(), "version": VERSION})
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", type=Path, default=Path("episodes/itt-revision-media-plan.json"))
    parser.add_argument("--catalog", type=Path, default=Path("public/assets/media/catalog.json"))
    parser.add_argument("--public-root", type=Path, default=Path("public"))
    parser.add_argument("--cache-dir", type=Path, default=Path("out/media-cache/itt-revision"))
    args = parser.parse_args()
    records = prepare_plan(args.plan, args.catalog, args.public_root, args.cache_dir)
    print(f"Prepared and catalogued {len(records)} authored ITT assets.", flush=True)


if __name__ == "__main__":
    main()
