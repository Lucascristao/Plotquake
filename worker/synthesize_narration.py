"""Narrate an episode scene by scene, with recoverable audio and the Plotquake voice."""
from __future__ import annotations
import argparse
import asyncio
from difflib import SequenceMatcher
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import wave

PRIMARY_LIVE_MODEL = "gemini-3.8-live"
DEFAULT_VOICE = "Charon"
DEFAULT_PITCH_SEMITONES = -1.0
SAMPLE_RATE = 24000
PROMPT_VERSION = "plotquake-documentary-us-v2"
DOCUMENTARY_VOICE_PROMPT = """You are the male narrator of a premium Plotquake historical business documentary.
Read the provided script exactly, in native United States English. Never introduce yourself, comment on the text,
summarize it, or add any words. Use a warm, resonant chest baritone: serious, grounded and authoritative.
Sustain quiet tension rather than trailer shouting. Speak at approximately 145 words per minute, with natural
breaths and short dramatic pauses before revelations, changes of fortune and major figures. Keep precisely
the same voice, tone and microphone distance throughout. Direction is not part of the script to be spoken.
"""
DYNAMIC_NARRATION_STYLE = "documentary-dynamic-v1"
DYNAMIC_VOICE_PROMPT = """You are the male narrator of a premium Plotquake documentary.
Read the provided script exactly, in native United States English. Never introduce yourself, comment on the text,
summarize it, or add any words. Use the selected Charon voice with a warm, resonant chest baritone: grounded,
clear and authoritative. Keep the same vocal identity, timbre and microphone distance throughout the episode.
Let pace, emphasis and emotional intensity follow the meaning of each passage. Move naturally between curiosity,
concentration, uncertainty, discovery, relief and reflection when the words support them. Speak fluent, natural
American English at an overall documentary pace near 145 words per minute, varying sentence rhythm rather than
giving every sentence the same solemn delivery. Use breaths and pauses where the meaning needs them. Allow
important consequences to register without adding words, repetitive dramatic pauses or exaggerated danger.
Avoid constant suspense, trailer delivery, shouting or a compulsory dramatic finish to every paragraph.
These directions guide performance and must never be spoken as part of the script.
"""


def narration_profile(narration_style: str | None = None) -> tuple[str, str]:
    if not narration_style:
        return PROMPT_VERSION, DOCUMENTARY_VOICE_PROMPT
    if narration_style == DYNAMIC_NARRATION_STYLE:
        return DYNAMIC_NARRATION_STYLE, DYNAMIC_VOICE_PROMPT
    raise ValueError(f"Unknown narrationStyle: {narration_style}")


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temporary.replace(path)


def safe_id(value: str) -> str:
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9_-]{0,119}", value):
        raise ValueError(f"Episode/scene id must be a simple filename: {value!r}")
    return value


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as audio:
        if (audio.getframerate(), audio.getnchannels(), audio.getsampwidth()) != (SAMPLE_RATE, 1, 2):
            raise ValueError(f"Expected PCM16 mono {SAMPLE_RATE} Hz narration: {path}")
        return audio.getnframes() / audio.getframerate()


def find_ffmpeg_executable() -> str:
    executable = shutil.which("ffmpeg")
    if executable:
        return executable
    local = Path(__file__).resolve().parents[1] / "node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe"
    if local.is_file():
        return str(local)
    raise RuntimeError("FFmpeg is required for the canonical voice pitch. Install ffmpeg first.")


def apply_baritone_pitch_calibration(source: Path, target: Path, semitones: float) -> None:
    """Compensate tempo and preserve the exact source sample count."""
    with wave.open(str(source), "rb") as audio:
        samples, rate = audio.getnframes(), audio.getframerate()
    factor = 2 ** (semitones / 12)
    filters = (f"asetrate={rate * factor:.8f},aresample={rate},atempo={1 / factor:.8f},"
               f"apad=whole_len={samples},atrim=end_sample={samples}")
    command = [find_ffmpeg_executable(), "-hide_banner", "-loglevel", "error", "-y", "-i", str(source),
               "-af", filters, "-ac", "1", "-ar", str(rate), "-c:a", "pcm_s16le", str(target)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(f"Pitch calibration failed: {result.stderr[-1500:]}")
    with wave.open(str(target), "rb") as audio:
        if audio.getnframes() != samples:
            raise RuntimeError("Pitch calibration changed the narration duration.")


def speech_tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.casefold().replace("’", "'"))


def cache_fingerprint(text: str, voice: str, pitch: float, narration_style: str | None = None) -> str:
    prompt_version, _ = narration_profile(narration_style)
    # Preserve the exact legacy serialization when the episode has no opt-in.
    value = json.dumps([PRIMARY_LIVE_MODEL, voice, pitch, prompt_version, text], ensure_ascii=False)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cached_scene(path: Path, fingerprint: str) -> dict | None:
    sidecar = path.with_suffix(".json")
    if not path.is_file() or not sidecar.is_file():
        return None
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
        duration = wav_seconds(path)
        if (metadata["fingerprint"] == fingerprint and metadata["audioSha256"] == digest(path)
                and math.isfinite(duration) and duration > 0
                and abs(metadata["durationSeconds"] - duration) < .001):
            return metadata
    except (ValueError, KeyError, OSError, wave.Error):
        pass
    return None


async def receive_narration(client, text: str, voice: str, narration_style: str | None = None) -> tuple[bytes, str]:
    _, voice_prompt = narration_profile(narration_style)
    config = {"response_modalities": ["AUDIO"], "output_audio_transcription": {},
              "speech_config": {"voice_config": {"prebuilt_voice_config": {"voice_name": voice}}},
              "system_instruction": {"parts": [{"text": voice_prompt}]}}
    chunks, transcript = [], []
    completed = False
    async with client.aio.live.connect(model=PRIMARY_LIVE_MODEL, config=config) as session:
        await session.send_client_content(
            turns={"role": "user", "parts": [{"text": f"Narrate only this script, verbatim:\n\n{text}"}]},
            turn_complete=True)
        async for response in session.receive():
            content = getattr(response, "server_content", None)
            if content is None:
                continue
            transcription = getattr(content, "output_transcription", None)
            if transcription and transcription.text:
                transcript.append(transcription.text)
            turn = getattr(content, "model_turn", None)
            for part in getattr(turn, "parts", []) or []:
                inline = getattr(part, "inline_data", None)
                if inline and inline.data and "audio" in (inline.mime_type or "audio"):
                    chunks.append(inline.data)
            if getattr(content, "turn_complete", False):
                completed = True
                break
    if not completed or not chunks:
        raise RuntimeError("Gemini Live did not finish a complete narration turn.")
    pcm = b"".join(chunks)
    if len(pcm) / (SAMPLE_RATE * 2) < max(1, len(text.split()) / 280 * 60):
        raise RuntimeError("Gemini Live returned short/truncated scene audio; retrying this scene.")
    spoken = "".join(transcript).strip()
    if spoken:
        similarity = SequenceMatcher(None, speech_tokens(text), speech_tokens(spoken), autojunk=False).ratio()
        if similarity < .88:
            raise RuntimeError(f"Narration differs from the script (similarity {similarity:.2f}).")
    return pcm, spoken


async def synthesize_scene(client, text: str, target: Path, voice: str, pitch: float, *, force: bool = False,
                           narration_style: str | None = None) -> dict:
    fingerprint = cache_fingerprint(text, voice, pitch, narration_style)
    cached = None if force else cached_scene(target, fingerprint)
    if cached:
        print(f"[Voice cache] {target.stem}: {cached['durationSeconds']:.2f}s", flush=True)
        return cached
    target.parent.mkdir(parents=True, exist_ok=True)
    raw = target.with_name(target.stem + ".raw.wav")
    raw_fingerprint = cache_fingerprint(text, voice, 0.0, narration_style)
    raw_cache = None if force else cached_scene(raw, raw_fingerprint)
    if raw_cache:
        transcript = raw_cache.get("transcript", "")
    else:
        for attempt in range(1, 7):
            try:
                print(f"[Voice] {target.stem}: {voice}, {PRIMARY_LIVE_MODEL}, attempt {attempt}/6", flush=True)
                pcm, transcript = await asyncio.wait_for(receive_narration(client, text, voice, narration_style), timeout=210)
                break
            except Exception as exc:
                message = str(exc)
                if attempt == 6 or any(code in message.lower() for code in
                                       ("not_found", "not found", "permission_denied", "api_key_invalid", "403", "404")):
                    raise RuntimeError(f"Narration failed for {target.stem} with {PRIMARY_LIVE_MODEL}: {message}") from exc
                delay = (5, 12, 25, 40, 55)[attempt - 1]
                print(f"[Voice retry] {target.stem}: {type(exc).__name__}; retry in {delay}s", flush=True)
                await asyncio.sleep(delay)
        with wave.open(str(raw), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(SAMPLE_RATE)
            audio.writeframes(pcm)
        raw_metadata = {"fingerprint": raw_fingerprint, "audioSha256": digest(raw),
                        "durationSeconds": wav_seconds(raw), "transcript": transcript}
        if narration_style:
            raw_metadata["narrationStyle"] = narration_style
        write_json(raw.with_suffix(".json"), raw_metadata)
    # Processing failures reuse this raw scene instead of purchasing another generation.
    if pitch:
        apply_baritone_pitch_calibration(raw, target, pitch)
    else:
        shutil.copyfile(raw, target)
    metadata = {"fingerprint": fingerprint, "model": PRIMARY_LIVE_MODEL, "voice": voice,
                "pitchSemitones": pitch, "durationSeconds": wav_seconds(target),
                "audioSha256": digest(target), "rawAudioSha256": digest(raw), "transcript": transcript}
    if narration_style:
        metadata["narrationStyle"] = narration_style
    write_json(target.with_suffix(".json"), metadata)
    print(f"[Voice ready] {target.stem}: {metadata['durationSeconds']:.2f}s", flush=True)
    return metadata


async def synthesize_episode(episode: dict, output_dir: Path, api_key: str, force: bool = False) -> None:
    from google import genai
    episode_id = safe_id(episode["id"])
    voice, pitch = episode.get("voice", DEFAULT_VOICE), float(episode.get("pitchSemitones", DEFAULT_PITCH_SEMITONES))
    narration_style = episode.get("narrationStyle")
    narration_profile(narration_style)
    if voice not in ("Charon", "Fenrir"):
        raise ValueError("Plotquake requires the canonical male Charon/Fenrir voice.")
    jobs = [scene for act in episode["acts"] for scene in act["scenes"]]
    if not jobs or len({scene["id"] for scene in jobs}) != len(jobs):
        raise ValueError("Episode scenes must be present and have unique ids.")
    for scene in jobs:
        safe_id(scene["id"])
        if not scene.get("narration", "").strip():
            raise ValueError(f"Empty narration in {scene['id']}")
    find_ffmpeg_executable()
    client, total = genai.Client(api_key=api_key), 0.0
    for number, scene in enumerate(jobs, 1):
        print(f"[Episode {episode_id}] Scene {number}/{len(jobs)}", flush=True)
        result = await synthesize_scene(client, scene["narration"].strip(), output_dir / f"{scene['id']}.wav", voice, pitch,
                                        force=force, narration_style=narration_style)
        total += result["durationSeconds"]
    print(f"[Voice complete] {len(jobs)} scenes, {total:.2f}s ({total / 60:.2f} minutes).", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--episode")
    parser.add_argument("--output-dir")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--text")
    parser.add_argument("--script-file")
    parser.add_argument("--output", default="public/assets/audio/narration.wav")
    parser.add_argument("--voice", default=DEFAULT_VOICE)
    parser.add_argument("--pitch-shift", type=float, default=DEFAULT_PITCH_SEMITONES)
    args = parser.parse_args()
    key = os.getenv("GEMINI_API_KEY", "").strip()
    if not key:
        raise RuntimeError("GEMINI_API_KEY is required; configure the existing GitHub Actions secret.")
    if args.episode:
        episode = json.loads(Path(args.episode).read_text(encoding="utf-8-sig"))
        directory = Path(args.output_dir or f"public/generated-audio/{safe_id(episode['id'])}")
        asyncio.run(synthesize_episode(episode, directory, key, args.force))
    else:
        text = args.text
        if not text and args.script_file:
            text = Path(args.script_file).read_text(encoding="utf-8-sig")
        if not text or not text.strip():
            parser.error("Pass --episode or explicit --text/--script-file. No demo paragraph is substituted.")
        from google import genai
        asyncio.run(synthesize_scene(genai.Client(api_key=key), text.strip(), Path(args.output), args.voice, args.pitch_shift, force=args.force))


if __name__ == "__main__":
    main()
