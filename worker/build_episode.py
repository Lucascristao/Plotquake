"""Build the documentary timeline from the actual, complete scene WAV files."""
from __future__ import annotations
import argparse
import copy
import json
import math
from pathlib import Path
from synthesize_narration import cache_fingerprint, cached_scene, safe_id, write_json
from publication import apply_publication

FPS = 30


def normalize_chart(chart: dict) -> dict:
    result = copy.deepcopy(chart)
    if "values" not in result:
        result["values"] = [{"label": item["label"], "value": item.get("value", item.get("percentage", 0)),
                              "highlight": item.get("highlight", index == 0)}
                             for index, item in enumerate(result.pop("data", []))]
    return result


def image_card_background(shot: dict, shots: list[dict]) -> dict:
    """Cards use the image renderer: reuse a still, never an MP4/WebM source."""
    image = shot if shot["type"] == "image" else next((item for item in reversed(shots) if item["type"] == "image"), None)
    result = {key: shot[key] for key in ("id", "from", "durationInFrames", "transition") if key in shot}
    if image:
        result.update({key: image[key] for key in ("src", "sourceLabel", "origin", "reconstruction", "focus",
                      "fit", "zoomStart", "zoomEnd", "motion") if key in image})
    # No still in this scene: omit src and let the renderer use its clean card background.
    return result


def shot_lengths(weights: list[float], frames: int, caps: list[int | None]) -> list[int]:
    """Fit authored relative lengths to the real voice, without running past a clip's end."""
    if not weights or len(weights) > frames or any(not math.isfinite(w) or w <= 0 for w in weights):
        raise ValueError("Visual plan needs positive finite weights and at least one frame per shot.")
    limits = [frames if cap is None else cap for cap in caps]
    if any(cap < 1 for cap in limits) or sum(limits) < frames:
        raise ValueError("Selected video excerpts cannot cover this scene; include a still or a longer excerpt.")
    targets = [0.0] * len(weights)
    remaining, active = frames, set(range(len(weights)))
    while active:
        total = sum(weights[i] for i in active)
        bounded = [i for i in active if remaining * weights[i] / total > limits[i]]
        if not bounded:
            for i in active:
                targets[i] = remaining * weights[i] / total
            break
        for i in bounded:
            targets[i] = float(limits[i])
            remaining -= limits[i]
            active.remove(i)
    lengths = [max(1, math.floor(value)) for value in targets]
    # A one-frame minimum can only need borrowing for exceptionally small weights.
    while sum(lengths) > frames:
        i = max((i for i, n in enumerate(lengths) if n > 1), key=lambda i: lengths[i] - targets[i])
        lengths[i] -= 1
    order = sorted(range(len(weights)), key=lambda i: targets[i] - lengths[i], reverse=True)
    while sum(lengths) < frames:
        for i in order:
            if lengths[i] < limits[i]:
                lengths[i] += 1
                if sum(lengths) == frames:
                    break
    return lengths


def build_shots(scene: dict, assets: dict, frames: int, public_root: Path,
                media_credits: dict, global_scene_index: int) -> list[dict]:
    scene_id = safe_id(scene["id"])
    authored = scene.get("visualPlan")
    keys = scene.get("visualKeys") or []
    if authored is None:
        if not keys:
            raise ValueError(f"No visual media selected for scene {scene_id}.")
        missing = [key for key in keys if key not in assets]
        if missing:
            raise ValueError(f"Unknown visualKeys in {scene_id}: {missing}")
        count = max(1, math.ceil(frames / (4.7 * FPS)))
        plan = [{"mediaKey": keys[i % len(keys)],
                 "variantIndex": (global_scene_index + i) % len(assets[keys[i % len(keys)]])}
                for i in range(count)]
    else:
        if not isinstance(authored, list) or not authored:
            raise ValueError(f"Empty visualPlan in {scene_id}.")
        plan = authored
    prepared, caps = [], []
    for index, entry in enumerate(plan):
        key = entry.get("mediaKey")
        candidates = assets.get(key, [])
        variant = entry.get("variantIndex", 0)
        if key is None and entry.get("type") in ("chart", "quote", "facts"):
            asset = {"kind": "image"}
        elif not candidates or not isinstance(variant, int) or not 0 <= variant < len(candidates):
            raise ValueError(f"Unknown visualPlan asset/variant in {scene_id}: {key}/{variant}.")
        else:
            asset = candidates[variant]
        src = asset.get("src")
        if src:
            if not src.startswith(("https://", "http://")):
                local = (public_root / src).resolve()
                if not local.is_relative_to(public_root.resolve()) or not local.is_file():
                    raise ValueError(f"Selected media does not exist: {src}")
            media_credits[src] = {field: asset[field] for field in
                                  ("src", "credit", "origin", "license", "licenseUrl", "changes") if field in asset}
        kind = entry.get("type", asset["kind"])
        if kind not in ("image", "video", "chart", "quote", "facts"):
            raise ValueError(f"Unknown shot type in {scene_id}: {kind}")
        if kind in ("image", "video") and kind != asset["kind"]:
            raise ValueError(f"Shot type does not match selected media: {scene_id}/{key}.")
        if kind in ("chart", "quote", "facts") and asset["kind"] == "video":
            raise ValueError(f"Card background must be a still: {scene_id}/{key}.")
        origin = asset.get("origin", "documentary")
        shot = {"id": f"{scene_id}-shot-{index + 1}", "type": kind,
                "sourceLabel": asset.get("credit", ""), "origin": origin,
                "mediaIdentity": (asset.get("reuseFamily") or asset.get("originalMedia") or (src if origin in ("generated", "reconstruction") else origin) or src) if src else None,
                "reconstruction": bool(asset.get("reconstruction") or origin in ("generated", "reconstruction", "ai-generated")),
                "motion": asset.get("motion", ("push", "pan-left", "pull", "pan-right")[index % 4]),
                "focus": asset.get("focus", {"x": .5, "y": .5}), "fit": asset.get("fit", "cover"),
                "transition": asset.get("transition", "cut"), "muted": True,
                "zoomStart": asset.get("zoomStart", 1.03 if index % 2 == 0 else 1.13),
                "zoomEnd": asset.get("zoomEnd", 1.13 if index % 2 == 0 else 1.03)}
        if src:
            shot["src"] = src
        for field in ("motion", "focus", "fit", "transition", "zoomStart", "zoomEnd", "caption", "vintageFilter", "displayWidth"):
            if field in entry:
                shot[field] = copy.deepcopy(entry[field])
            elif field in asset:
                shot[field] = copy.deepcopy(asset[field])
        # Explicit motion must control direction, rather than the shot's ordinal position.
        defaults = (1.13, 1.03) if shot["motion"] == "pull" else (1.03, 1.13)
        if shot["motion"] == "still":
            defaults = (1.035, 1.035)
        for field, value in zip(("zoomStart", "zoomEnd"), defaults):
            if field not in entry and field not in asset:
                shot[field] = value
        cap = None
        if kind == "video":
            start = float(entry.get("trimStartSeconds", asset.get("trimStartSeconds", asset.get("trimStart", 0))))
            rate = float(entry.get("playbackRate", asset.get("playbackRate", 1)))
            if not math.isfinite(start) or start < 0 or not math.isfinite(rate) or rate <= 0:
                raise ValueError(f"Invalid video trim/rate in {scene_id}/{key}.")
            shot.update({"trimBefore": round(start * FPS), "playbackRate": rate})
            if asset.get("durationSeconds"):
                # Leave a short tail for the renderer's dissolve overlap.
                cap = math.floor((float(asset["durationSeconds"]) - start) / rate * FPS) - 12
        if kind == "facts":
            shot["facts"] = copy.deepcopy(scene["facts"])
        if kind == "chart":
            shot["chart"] = normalize_chart(scene["chart"])
        elif kind == "quote":
            value = scene["quote"]
            shot["quote"] = {"text": value} if isinstance(value, str) else copy.deepcopy(value)
        prepared.append(shot)
        caps.append(cap)
    lengths = shot_lengths([float(entry.get("weight", 1)) for entry in plan], frames, caps)
    cursor = 0
    for shot, length in zip(prepared, lengths):
        shot.update({"from": cursor, "durationInFrames": length})
        cursor += length
    if authored is None:
        if scene.get("chart"):
            i = min(len(prepared) - 1, max(1, len(prepared) // 2))
            prepared[i] = {**image_card_background(prepared[i], prepared), "id": f"{scene_id}-chart",
                           "type": "chart", "chart": normalize_chart(scene["chart"])}
        if scene.get("quote"):
            value = scene["quote"]
            prepared[-1] = {**image_card_background(prepared[-1], prepared), "id": f"{scene_id}-quote",
                            "type": "quote", "quote": {"text": value} if isinstance(value, str) else value}
    return prepared


def build_newspaper(value: dict, assets: dict, scene_frames: int, public_root: Path,
                    media_credits: dict, scene_id: str) -> dict:
    """An author-timed evidence overlay; it never replaces a visual shot or changes narration."""
    start = float(value.get("atSeconds", 0))
    duration = float(value.get("durationSeconds", 8))
    if not math.isfinite(start) or not math.isfinite(duration) or start < 0 or duration <= 0:
        raise ValueError(f"Invalid newspaper timing in {scene_id}: use finite, nonnegative start and positive duration.")
    first_frame = round(start * FPS)
    if first_frame >= scene_frames:
        raise ValueError(f"Newspaper starts after the scene ends: {scene_id}.")
    result = {key: copy.deepcopy(value[key]) for key in
              ("headline", "subheadline", "date", "source", "sourceUrl", "highlightWords") if key in value}
    mode = value.get("mode", "reconstruction")
    if mode not in ("clipping", "reconstruction"):
        raise ValueError(f"Unknown newspaper mode in {scene_id}: {mode}.")
    result.update({"mode": mode, "from": first_frame,
                   "durationInFrames": min(scene_frames - first_frame, max(1, round(duration * FPS)))})
    boxes = []
    for box in value.get("highlightBoxes", []):
        normalized = {key: float(box[key]) for key in ("x", "y", "width", "height")}
        if (not all(math.isfinite(number) for number in normalized.values())
            or normalized["x"] < 0 or normalized["y"] < 0
            or normalized["width"] <= 0 or normalized["height"] <= 0
            or normalized["x"] + normalized["width"] > 1.000001
            or normalized["y"] + normalized["height"] > 1.000001):
            raise ValueError(f"Newspaper highlight boxes must stay inside the original image (0–1): {scene_id}.")
        boxes.append(normalized)
    if boxes:
        result["highlightBoxes"] = boxes
    key = value.get("mediaKey")
    if mode == "clipping" and not key:
        raise ValueError(f"Newspaper clipping needs an image mediaKey from the catalog: {scene_id}.")
    if key:
        candidates = assets.get(key, [])
        if not candidates or candidates[0].get("kind") != "image":
            raise ValueError(f"Newspaper mediaKey must identify a catalog image: {scene_id}/{key}.")
        asset = candidates[0]
        src = asset["src"]
        if not src.startswith(("https://", "http://")):
            local = (public_root / src).resolve()
            if not local.is_relative_to(public_root.resolve()) or not local.is_file():
                raise ValueError(f"Newspaper clipping does not exist: {src}.")
        result["imageSrc"] = src
        result.setdefault("source", asset.get("publication") or asset.get("credit", "Document clipping"))
        result.setdefault("date", asset.get("date", ""))
        result.setdefault("sourceUrl", asset.get("sourceUrl") or asset.get("origin", ""))
        if asset.get("reconstruction") or asset.get("origin") in ("generated", "reconstruction", "ai-generated"):
            result["mode"] = "reconstruction"
        credit = {field: asset[field] for field in
                  ("src", "credit", "origin", "license", "licenseUrl", "changes") if field in asset}
        credit["credit"] = " · ".join(dict.fromkeys(filter(None, (result.get("source"), credit.get("credit")))))
        if result.get("sourceUrl"):
            credit["origin"] = result["sourceUrl"]
        if result["mode"] == "reconstruction":
            credit["credit"] = "Editorial reconstruction · " + credit["credit"]
        # Separate entry preserves any image's ordinary media credit and document-specific provenance.
        media_credits[f"newspaper:{scene_id}"] = credit
    else:
        if not str(result.get("headline", "")).strip():
            raise ValueError(f"Editorial newspaper reconstruction needs headline text: {scene_id}.")
        media_credits[f"newspaper:{scene_id}"] = {
            "credit": "Editorial reconstruction" + (f" · Research: {result['source']}" if result.get("source") else ""),
            "origin": result.get("sourceUrl", ""),
            "changes": "Original editorial layout, not an archival newspaper page.",
        }
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
            fingerprint = cache_fingerprint(scene["narration"].strip(), source.get("voice", "Charon"),
                                            float(source.get("pitchSemitones", -1)), source.get("narrationStyle"))
            audio = cached_scene(path, fingerprint)
            if audio is None:
                raise ValueError(f"Narration missing or stale for {scene_id}; run synthesize_narration.py --episode first.")
            seconds = float(audio["durationSeconds"])
            measured_seconds += seconds
            pause = float(scene.get("pauseAfterSeconds", 0))
            if not math.isfinite(pause) or pause < 0:
                raise ValueError(f"Invalid authored pause in {scene_id}.")
            # Breathing room is editorial timing, never counted toward minimum spoken duration.
            frames = math.ceil(seconds * FPS) + round(pause * FPS)
            shots = build_shots(scene, assets, frames, public_root, media_credits, global_scene_index)
            for shot in shots:
                if shot["type"] == "quote":
                    result["audio"]["effects"].append({"src": "assets/audio/reveal_accent.wav",
                        "from": cursor + act_cursor + shot["from"], "durationInFrames": 60, "volume": .11})
            if "musicVolume" in scene:
                volume = float(scene["musicVolume"])
                if not math.isfinite(volume) or volume < 0:
                    raise ValueError(f"Invalid musicVolume in {scene_id}.")
                result["audio"]["music"].setdefault("cues", []).append({
                    "from": cursor + act_cursor, "durationInFrames": frames, "volume": volume})
            output_scene = {"id": scene_id, "startFrame": act_cursor, "durationInFrames": frames,
                            "narration": scene["narration"], "caption": scene.get("caption", ""),
                            "audioSrc": path.resolve().relative_to(public_root.resolve()).as_posix(), "shots": shots}
            if scene.get("newspaper"):
                output_scene["newspaper"] = build_newspaper(scene["newspaper"], assets, frames, public_root,
                                                           media_credits, scene_id)
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
    # Record actual selected identities, including aliases/crops, for authoring review.
    usage = {}
    for act in result["acts"]:
        for scene in act["scenes"]:
            for shot in scene["shots"]:
                identity = shot.get("mediaIdentity")
                if identity:
                    usage.setdefault(identity, []).append({"scene": scene["id"], "shot": shot["id"],
                        "kind": shot["type"], "from": act["startFrame"] + scene["startFrame"] + shot["from"]})
    result["metadata"]["mediaUsage"] = usage
    result["mediaCredits"] = list(media_credits.values()) + copy.deepcopy(source.get("thumbnailCredits", []))
    result["chapters"] = sorted(result["chapters"], key=lambda item: item["startFrame"])
    if (source.get("endCredits") or {}).get("enabled") is True and source.get("score"):
        # The next preparation steps write this exact continuous master. Resolve
        # its credit now, so adding a music attribution cannot change film length
        # after the score has already been synthesized.
        result["audio"]["music"] = {"src": f"assets/audio/{safe_id(source['id'])}-score-directed.wav",
                                    "volume": 1, "loop": False, "directed": True}
    return apply_publication(source, result, catalog)


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
