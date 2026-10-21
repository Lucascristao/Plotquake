"""Opt-in publication text, actual-use attribution and film end credits.

This module prepares authored material. It does not approve editorial choices or
infer licenses from a hosting site, an institution's name or a file extension.
"""
from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import re


STANDARD = "cinematic-v1"


def clean_publication(source: dict) -> bool:
    return (source.get("publication") or {}).get("standard") == STANDARD


def media_identity(src: str) -> str:
    value = str(src).replace("\\", "/")
    return value[7:] if value.startswith("public/") else value


def used_media(timeline: dict) -> dict[str, dict]:
    """Read the rendered selections, never the unused portion of a catalog."""
    selected = {}

    def add(src, kind, use):
        if src:
            key = media_identity(src)
            entry = selected.setdefault(key, {"src": src, "kind": kind, "uses": []})
            if use not in entry["uses"]:
                entry["uses"].append(use)

    for act in timeline.get("acts", []):
        for scene in act.get("scenes", []):
            for shot in scene.get("shots", []):
                add(shot.get("src"), "video" if shot.get("type") == "video" else "image",
                    {"scene": scene["id"], "shot": shot["id"]})
            document = scene.get("newspaper") or {}
            add(document.get("imageSrc"), "document", {"scene": scene["id"], "overlay": "document"})
    audio = timeline.get("audio") or {}
    music = audio.get("music")
    add(music if isinstance(music, str) else (music or {}).get("src"), "music", {"track": "music"})
    for index, effect in enumerate(audio.get("effects", [])):
        add(effect.get("src"), "sound", {"effect": index})
    return selected


def selected_credits(source: dict, timeline: dict, catalog: dict | None = None) -> list[dict]:
    records = {}
    # Later, explicit attribution records enrich catalog data without making an
    # unused photo, a cover image or a research reference appear in the film.
    candidates = list((catalog or {}).get("assets", []))
    candidates += timeline.get("mediaCredits", [])
    candidates += timeline.get("filmMediaCredits", [])
    candidates += (source.get("endCredits") or {}).get("assets", [])
    for item in candidates:
        if item.get("src"):
            key = media_identity(item["src"])
            records.setdefault(key, {}).update(copy.deepcopy(item))
    result = []
    for key, usage in used_media(timeline).items():
        record = {**records.get(key, {}), **usage}
        result.append(record)
    return result


def screen_lines(record: dict) -> list[str]:
    explicit = record.get("screenCredit")
    if explicit is False:
        return []
    if explicit is not None:
        return [str(line).strip() for line in
                (explicit if isinstance(explicit, list) else str(explicit).splitlines()) if str(line).strip()]
    if record.get("author") and record.get("title"):
        return [str(record["author"]), str(record["title"])]
    return [str(record["credit"])] if record.get("credit") else []


def apply_publication(source: dict, timeline: dict, catalog: dict | None = None) -> dict:
    """Append only an explicitly enabled credits sequence, after all real speech.

    Idempotent so a final attribution refresh cannot append credits twice.
    Narration timing and the existing acts are never changed.
    """
    config = source.get("endCredits") or {}
    if config.get("enabled") is not True:
        return timeline
    fps = float(timeline["fps"])
    seconds = float(config.get("secondsPerCard", 9))
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError("End-credit card duration must be finite and positive.")
    story_end = int((timeline.get("endCredits") or {}).get("startFrame", timeline["durationInFrames"]))
    timeline["filmMediaCredits"] = selected_credits(source, timeline, catalog)
    entries, seen = [], set()
    for record in timeline["filmMediaCredits"]:
        lines = screen_lines(record)
        identity = tuple(lines)
        if lines and identity not in seen:
            entries.append({"lines": lines})
            seen.add(identity)
    cards = []
    cursor = 0
    for first in range(0, len(entries), 3):
        group = entries[first:first + 3]
        words = sum(len(" ".join(entry["lines"]).split()) for entry in group)
        length = math.ceil(max(seconds, 2 + words / 2.7) * fps)
        cards.append({"from": cursor, "durationInFrames": length,
                      "heading": config.get("heading", "ARCHIVAL FILM AND PHOTOGRAPHY"), "entries": group})
        cursor += length
    if config.get("fullCreditsUrl"):
        length = math.ceil(max(seconds, 9) * fps)
        cards.append({"from": cursor, "durationInFrames": length, "heading": "COMPLETE CREDITS",
                      "entries": [{"lines": [str(config["fullCreditsUrl"])]}]})
        cursor += length
    timeline.setdefault("metadata", {})["storyDurationInFrames"] = story_end
    timeline["metadata"]["endCreditsDurationInFrames"] = cursor
    if cursor:
        timeline["endCredits"] = {"startFrame": story_end, "durationInFrames": cursor,
                                  "fadeInFrames": round(fps), "fadeOutFrames": round(fps), "cards": cards}
    else:
        timeline.pop("endCredits", None)
    timeline["durationInFrames"] = story_end + cursor
    return timeline


def public_description(source: dict) -> str:
    publication = source.get("publication") or {}
    body = str(publication.get("description", source.get("description", ""))).strip()
    embedded = re.findall(r"(?<!\w)#([\w]+)", body)
    body = re.sub(r"(?<!\w)#[\w]+", "", body).strip()
    hashtags = publication.get("hashtags", embedded)
    tags = list(dict.fromkeys(str(tag).strip().lstrip("#") for tag in hashtags if str(tag).strip()))[:2]
    return body + ("\n\n" + " ".join("#" + tag for tag in tags) if tags else "")


def write_clean_delivery(source: dict, timeline: dict, destination: Path, package: dict) -> None:
    """Keep the copy/paste publication TXT separate from the production record."""
    text = (f"TITLE\n{package['title']}\n\nDESCRIPTION\n{package['description']}\n\n"
            f"TAGS\n{', '.join(package['tags'])}\n")
    (destination / "youtube_package.txt").write_text(text, encoding="utf-8")
    records = selected_credits(source, timeline)
    document = {"episodeId": source["id"], "title": source["title"], "publicationStandard": STANDARD,
                "durationSeconds": timeline["durationInFrames"] / timeline["fps"],
                "narrationSeconds": timeline.get("metadata", {}).get("narrationSeconds"),
                "descriptionWordCount": len(re.sub(r"(?<!\w)#[\w]+", "", package["description"]).split()),
                "historicalSources": source.get("sources", []), "filmMedia": records,
                "thumbnailCredits": source.get("thumbnailCredits", []),
                "endCredits": timeline.get("endCredits"),
                "voice": source.get("voice", "Charon"), "pitchSemitones": source.get("pitchSemitones", -1),
                "verificationScope": "Selections and attribution records from the derived timeline; not a claim of final audiovisual review or legal clearance."}
    (destination / "internal_documentation.json").write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [f"# {source['title']} — internal production documentation", "", "## Historical research", ""]
    for index, item in enumerate(document["historicalSources"], 1):
        lines.extend([f"### {item.get('id', index)} — {item.get('title', '')}", str(item.get("url", "")),
                      str(item.get("note", "")), ""])
    lines.extend(["## Media actually selected in the film", ""])
    for item in records:
        lines.append(f"### {item.get('title') or item.get('src')}")
        for key in ("src", "author", "credit", "origin", "sourceUrl", "license", "licenseVersion", "licenseUrl", "changes", "screenCredit"):
            if key in item:
                lines.append(f"- {key}: {item[key]}")
        lines.extend(["- Use: " + json.dumps(item["uses"], ensure_ascii=False), ""])
    if document["thumbnailCredits"]:
        lines.extend(["## Cover artwork (separate from film credits)", "",
                      json.dumps(document["thumbnailCredits"], ensure_ascii=False, indent=2), ""])
    lines.extend(["## Verification scope", "", document["verificationScope"], ""])
    (destination / "internal_documentation.txt").write_text("\n".join(lines), encoding="utf-8")
