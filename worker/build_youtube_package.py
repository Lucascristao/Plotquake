"""Prepare the dedicated cover and publication text from the finished timeline."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import subprocess
from synthesize_narration import find_ffmpeg_executable, write_json


def timestamp(seconds: int) -> str:
    minutes, second = divmod(seconds, 60)
    hours, minute = divmod(minutes, 60)
    return f"{hours}:{minute:02d}:{second:02d}" if hours else f"{minute:02d}:{second:02d}"


def make_package(source: dict, timeline: dict) -> dict:
    fps = timeline["fps"]
    duration = timeline["durationInFrames"] / fps
    chapters = []
    for chapter in timeline["chapters"]:
        seconds = int(chapter["startFrame"] / fps)
        if chapters and seconds - chapters[-1]["seconds"] < 10:
            continue
        if seconds >= duration - 10:
            continue
        chapters.append({"seconds": seconds, "time": timestamp(seconds), "title": chapter["title"]})
    if len(chapters) < 3:
        chapters = []
    chapter_text = "\n".join(f"{item['time']} {item['title']}" for item in chapters)
    sources = source.get("sources", [])
    # Keep the complete bibliography in the technical package, even if public description space is short.
    body = str(source.get("description", source.get("subtitle", ""))).strip()
    sections = [body]
    if chapter_text:
        sections.append("CHAPTERS\n" + chapter_text)
    source_lines = [f"{item['title']} — {item['url']}" for item in sources]
    if source_lines:
        sections.append("SOURCES\n" + "\n".join(source_lines))
    sections.append("Plotquake • Stories That Shake Empires\n#Plotquake #BusinessHistory #Documentary")
    description = "\n\n".join(sections)
    if len(description) > 5000:
        short_sources = "\n".join(source_lines[:4])
        description = "\n\n".join([body[:2400], "CHAPTERS\n" + chapter_text,
                                     "SELECTED SOURCES\n" + short_sources, sections[-1]])
    if len(description) > 5000:
        raise ValueError("Episode description is too long for YouTube; shorten the editorial description.")
    return {"title": source["title"], "description": description, "tags": source.get("tags", []),
            "chapters": chapters, "sources": sources, "durationSeconds": duration,
            "mediaCredits": timeline.get("mediaCredits", []),
            "voice": source.get("voice", "Charon"), "pitchSemitones": source.get("pitchSemitones", -1)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode", default="episodes/blackberry.json")
    parser.add_argument("--render-input", default="src/episodes/renderEpisode.json")
    parser.add_argument("--output-dir", default="renders")
    args = parser.parse_args()
    source = json.loads(Path(args.episode).read_text(encoding="utf-8-sig"))
    timeline = json.loads(Path(args.render_input).read_text(encoding="utf-8-sig"))
    if source["id"] != timeline["id"]:
        raise ValueError("Episode and render timeline do not match.")
    destination = Path(args.output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    cover = Path(source.get("thumbnail", "public/assets/images/thumbnail_concept.jpg"))
    if not cover.is_file():
        raise FileNotFoundError(f"Dedicated thumbnail is required: {cover}. A video frame is never used.")
    command = [find_ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(cover),
               "-vf", "scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720", "-frames:v", "1",
               "-q:v", "2", str(destination / "thumbnail.jpg")]
    subprocess.run(command, check=True)
    package = make_package(source, timeline)
    write_json(destination / "youtube_package.json", package)
    source_text = "\n".join(f"[{item.get('id', index + 1)}] {item['title']}\n{item['url']}\n{item.get('note', '')}"
                             for index, item in enumerate(package["sources"]))
    text = (f"TITLE\n{package['title']}\n\nDESCRIPTION\n{package['description']}\n\n"
            f"TAGS\n{', '.join(package['tags'])}\n\nRESEARCH SOURCES\n{source_text}\n")
    credit_text = "\n\n".join("\n".join(str(item[key]) for key in
        ("src", "credit", "origin", "licenseUrl", "changes") if item.get(key)) for item in package["mediaCredits"])
    if credit_text:
        text += "\nVISUAL CREDITS\n" + credit_text + "\n"
        (destination / "visual_credits.txt").write_text(credit_text + "\n", encoding="utf-8")
    (destination / "youtube_package.txt").write_text(text, encoding="utf-8")
    print(f"[Package ready] Dedicated 1280x720 thumbnail, {len(package['chapters'])} real chapters, metadata and sources.")


if __name__ == "__main__":
    main()
