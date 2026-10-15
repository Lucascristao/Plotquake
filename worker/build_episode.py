"""Build the documentary timeline from the actual, complete scene WAV files."""
from __future__ import annotations
import argparse
import copy
import json
import math
from pathlib import Path
from synthesize_narration import cache_fingerprint, cached_scene, safe_id, write_json

FPS = 30


def normalize_chart(chart: dict) -> dict:
    result = copy.deepcopy(chart)
    if "values" not in result:
        result["values"] = [{"label": item["label"], "value": item.get("value", item.get("percentage", 0)),
                              "highlight": item.get("highlight", index == 0)}
                             for index, item in enumerate(result.pop("data", []))]
    return result


def build_episode(source: dict, catalog: dict, audio_dir: Path, public_root: Path) -> dict:
    assets = {}
    for asset in catalog["assets"]:
        assets.setdefault(asset["key"], []).append(asset)
    result = {key: source.get(key, "") for key in ("id", "title", "subtitle", "description")}
    result.update({"fps": FPS, "acts": [], "sources": source.get("sources", []), "tags": source.get("tags", []),
                   "audio": {"music": {"src": "assets/audio/tension_score.wav", "volume": .13}, "effects": []},
                   "chapters": [], "metadata": {"timing": "measured-scene-audio", "model": "gemini-3.8-live",
                                                 "voice": source.get("voice", "Charon"), "pitchSemitones": source.get("pitchSemitones", -1)}})
    cursor, measured_seconds, global_scene_index = 0, 0.0, 0
    media_credits = {}
    for act_index, act in enumerate(source["acts"]):
        output_act = {"id": act["id"], "actNumber": act_index + 1, "actTitle": act["title"],
                      "subtitle": act.get("subtitle", ""), "startFrame": cursor, "scenes": []}
        result["chapters"].append({"title": act["title"], "startFrame": cursor})
        if act_index:
            result["audio"]["effects"].append({"src": "assets/audio/chapter_transition.wav", "from": cursor,
                                                "durationInFrames": 75, "volume": .15})
        act_cursor = 0
        for scene in act["scenes"]:
            scene_id = safe_id(scene["id"])
            path = audio_dir / f"{scene_id}.wav"
            fingerprint = cache_fingerprint(scene["narration"].strip(), source.get("voice", "Charon"), float(source.get("pitchSemitones", -1)))
            audio = cached_scene(path, fingerprint)
            if audio is None:
                raise ValueError(f"Narration missing or stale for {scene_id}; run synthesize_narration.py --episode first.")
            seconds = float(audio["durationSeconds"])
            measured_seconds += seconds
            frames = math.ceil(seconds * FPS)
            keys = scene.get("visualKeys") or []
            if not keys:
                raise ValueError(f"No visual media selected for scene {scene_id}.")
            missing = [key for key in keys if key not in assets]
            if missing:
                raise ValueError(f"Unknown visualKeys in {scene_id}: {missing}")
            count = max(1, math.ceil(frames / (4.7 * FPS)))
            boundaries = [round(index * frames / count) for index in range(count + 1)]
            shots = []
            for shot_index in range(count):
                variants = assets[keys[shot_index % len(keys)]]
                asset = variants[(global_scene_index + shot_index) % len(variants)]
                src = asset["src"]
                media_credits[src] = {key: asset[key] for key in
                                      ("src", "credit", "origin", "license", "licenseUrl", "changes") if key in asset}
                if not src.startswith(("https://", "http://")):
                    local = (public_root / src).resolve()
                    if not local.is_relative_to(public_root.resolve()) or not local.is_file():
                        raise ValueError(f"Selected media does not exist: {src}")
                origin = asset.get("origin", "documentary")
                shot = {"id": f"{scene_id}-shot-{shot_index + 1}", "type": asset["kind"], "src": src,
                        "from": boundaries[shot_index], "durationInFrames": boundaries[shot_index + 1] - boundaries[shot_index],
                        "sourceLabel": asset.get("credit", ""), "origin": origin,
                        "reconstruction": bool(asset.get("reconstruction") or origin in ("generated", "reconstruction", "ai-generated")),
                        "motion": asset.get("motion", ("push", "pan-left", "pull", "pan-right")[shot_index % 4]),
                        "focus": asset.get("focus", {"x": .5, "y": .5}), "transition": asset.get("transition", "cut"),
                        "fit": asset.get("fit", "cover"), "muted": True,
                        "zoomStart": asset.get("zoomStart", 1.03 if shot_index % 2 == 0 else 1.13),
                        "zoomEnd": asset.get("zoomEnd", 1.13 if shot_index % 2 == 0 else 1.03)}
                if asset["kind"] == "video":
                    available = asset.get("durationSeconds")
                    shot_seconds = shot["durationInFrames"] / FPS
                    start = float(asset.get("trimStartSeconds", asset.get("trimStart", 0)))
                    if available:
                        start += min(max(0, float(available) - start - shot_seconds - .1), (shot_index // len(keys)) * 5.0)
                    shot["trimBefore"] = round(start * FPS)
                    shot["playbackRate"] = float(asset.get("playbackRate", 1))
                shots.append(shot)
            if scene.get("chart"):
                index = min(len(shots) - 1, max(1, len(shots) // 2))
                shots[index] = {**shots[index], "id": f"{scene_id}-chart", "type": "chart",
                                "chart": normalize_chart(scene["chart"])}
            if scene.get("quote"):
                value = scene["quote"]
                quote = {"text": value} if isinstance(value, str) else value
                shots[-1] = {**shots[-1], "id": f"{scene_id}-quote", "type": "quote", "quote": quote}
                result["audio"]["effects"].append({"src": "assets/audio/reveal_accent.wav",
                    "from": cursor + act_cursor + shots[-1]["from"], "durationInFrames": 60, "volume": .11})
            output_scene = {"id": scene_id, "startFrame": act_cursor, "durationInFrames": frames,
                            "narration": scene["narration"], "caption": scene.get("caption", ""),
                            "audioSrc": path.resolve().relative_to(public_root.resolve()).as_posix(), "shots": shots}
            if scene.get("chapter"):
                result["chapters"].append({"title": str(scene["chapter"]), "startFrame": cursor + act_cursor})
            output_act["scenes"].append(output_scene)
            act_cursor += frames
            global_scene_index += 1
        output_act["durationInFrames"] = act_cursor
        result["acts"].append(output_act)
        cursor += act_cursor
    minimum = max(900, float(source.get("minimumDurationSeconds", 900)))
    if measured_seconds < minimum:
        raise ValueError(f"Narration totals {measured_seconds:.2f}s; episode requires at least {minimum:.0f}s. "
                         "Expand the actual script. No repeated footage or silence is added to stretch runtime.")
    result["durationInFrames"] = cursor
    result["metadata"]["narrationSeconds"] = measured_seconds
    result["mediaCredits"] = list(media_credits.values())
    result["chapters"] = sorted(result["chapters"], key=lambda item: item["startFrame"])
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", default="episodes/blackberry.json")
    parser.add_argument("--catalog", default="public/assets/media/catalog.json")
    parser.add_argument("--audio-dir")
    parser.add_argument("--output", default="src/episodes/renderEpisode.json")
    args = parser.parse_args()
    source = json.loads(Path(args.episode).read_text(encoding="utf-8-sig"))
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8-sig"))
    audio_dir = Path(args.audio_dir or f"public/generated-audio/{safe_id(source['id'])}")
    result = build_episode(source, catalog, audio_dir, Path("public"))
    write_json(Path(args.output), result)
    print(f"[Timeline ready] {result['durationInFrames'] / FPS:.2f}s, {len(result['acts'])} acts, "
          f"{sum(len(act['scenes']) for act in result['acts'])} narrated scenes.")


if __name__ == "__main__":
    main()
