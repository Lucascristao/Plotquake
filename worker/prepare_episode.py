"""Prepare authored media, the measured timeline and one directed documentary score."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
import sys

from build_episode import build_episode
from prepare_blackberry_media import prepare_asset, validate_manifest
from synthesize_narration import safe_id, write_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=Path("src/episodes/renderEpisode.json"))
    parser.add_argument("--media-only", action="store_true", help="Prepare selected source assets before synthesis.")
    args = parser.parse_args()
    source = json.loads(args.episode.read_text(encoding="utf-8-sig"))
    if source.get("archivalMediaPlan"):
        subprocess.run([sys.executable, "worker/prepare_archival_media.py", "--plan", source["archivalMediaPlan"],
                        "--cache-dir", f"out/media-cache/{safe_id(source['id'])}"], check=True)
    if source.get("mediaPreparationPlan"):
        subprocess.run([sys.executable, "worker/prepare_itt_revision_media.py",
                        "--plan", str(source["mediaPreparationPlan"]),
                        "--catalog", "public/assets/media/catalog.json", "--public-root", "public",
                        "--cache-dir", "out/media-cache/itt-revision"], check=True)
    if args.media_only:
        return
    catalog = json.loads(Path("public/assets/media/catalog.json").read_text(encoding="utf-8-sig"))
    media_manifest = source.get("mediaManifest")
    if media_manifest:
        manifest = json.loads(Path(media_manifest).read_text(encoding="utf-8-sig"))
        validate_manifest(manifest)
        origins = {item["id"]: item for item in manifest["sources"]}
        used = {shot.get("mediaKey") for act in source["acts"] for scene in act["scenes"]
                for shot in scene.get("visualPlan", [])}
        used.update(scene.get("newspaper", {}).get("mediaKey") for act in source["acts"] for scene in act["scenes"])
        records = []
        for asset in manifest["assets"]:
            key = "bb_redo_" + asset["id"].replace("-", "_")
            if key in used:
                records.append(prepare_asset(origins[asset["sourceId"]], asset, Path("public"),
                                             Path("out/media-cache/blackberry-redo"), "ffmpeg", "ffprobe"))
        by_src = {record["src"]: record for record in records}
        catalog["assets"] = [item for item in catalog["assets"] if item.get("src") not in by_src] + records
        print(f"[Media ready] {len(records)} selected photographs/excerpts prepared with provenance.", flush=True)
    episode_id = safe_id(source["id"])
    timeline = build_episode(source, catalog, Path("public/generated-audio") / episode_id, Path("public"))
    write_json(args.output, timeline)
    if source.get("score"):
        score = Path("public/assets/audio") / f"{episode_id}-score.wav"
        directed = score.with_name(f"{episode_id}-score-directed.wav")
        subprocess.run([sys.executable, "worker/generate_documentary_score.py", "--episode", str(args.episode),
                        "--timeline", str(args.output), "--output", str(score)], check=True)
        subprocess.run([sys.executable, "worker/prepare_audio_direction.py", "--episode", str(args.episode),
                        "--timeline", str(args.output), "--score", str(score), "--output", str(directed)], check=True)
    subprocess.run([sys.executable, "worker/build_youtube_package.py", "--episode", str(args.episode),
                    "--render-input", str(args.output)], check=True)
    if source.get("researchDocument"):
        import shutil
        research = Path(source["researchDocument"])
        if not research.is_file():
            raise FileNotFoundError(f"Episode research document is missing: {research}")
        shutil.copyfile(research, Path("renders/research_sources.md"))


if __name__ == "__main__":
    main()
