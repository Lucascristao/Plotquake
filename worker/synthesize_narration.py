import argparse
import asyncio
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

PRIMARY_LIVE_MODEL = "gemini-3.8-live"
DEFAULT_VOICE = "Charon"  # Canonical authoritative male documentary narrator (Charon or Fenrir)
DEFAULT_PITCH_SEMITONES = -1.0  # Slightly deeper than default stock voice for cinematic baritone gravitas

DOCUMENTARY_VOICE_PROMPT = """
You are the official male narrator of Plotquake documentaries.
Tone: Deep baritone, authoritative, calm, grounded, captivating American male documentary narrator (similar to high-end History Channel, Netflix, and National Geographic docudramas).
Vocal Placement: Speak strictly in a low, resonant chest register (baritone), perceptibly deeper and lower in pitch than normal everyday conversation.
Cadence: Steady, serious, measured. Add dramatic pauses before key revelations, turning points, and monumental numbers.
Pacing: Approximately 145 to 155 words per minute.
Emotion: Controlled tension, solemn awe at monumental events, sharp gravitas.
Crucial: Read the text exactly as provided without adding greetings, sign-offs, or conversational pleasantries.
"""

def find_ffmpeg_executable() -> str:
    """Finds ffmpeg in system PATH or known Remotion fallback directories."""
    system_ffmpeg = shutil.which("ffmpeg")
    if system_ffmpeg:
        return system_ffmpeg

    fallbacks = [
        r"C:\Users\lucas\.gemini\antigravity-ide\scratch\odinheiroexplica\node_modules\@remotion\compositor-win32-x64-msvc\ffmpeg.exe",
        Path.home() / ".gemini/antigravity-ide/scratch/odinheiroexplica/node_modules/@remotion/compositor-win32-x64-msvc/ffmpeg.exe",
    ]
    for path in fallbacks:
        p = Path(path)
        if p.exists():
            return str(p)

    return ""

def apply_baritone_pitch_calibration(wav_path: str, semitones: float = DEFAULT_PITCH_SEMITONES):
    """
    Calibrates the male voice to be slightly deeper than default (-1.0 semitones)
    while preserving exact duration, timing, and pristine speech intelligibility.
    """
    ffmpeg_exe = find_ffmpeg_executable()
    if not ffmpeg_exe:
        print("[Plotquake Audio] FFmpeg not found. Keeping raw Gemini Live WAV audio.")
        return

    path = Path(wav_path)
    if not path.exists():
        return

    try:
        with wave.open(str(path), "rb") as w:
            sample_rate = w.getframerate()
    except Exception as exc:
        print(f"[Plotquake Audio] Could not read sample rate from {wav_path}: {exc}")
        sample_rate = 24000

    # Calculate pitch scale factor (e.g. -1 semitone = 2^(-1/12) ≈ 0.94387)
    factor = 2.0 ** (semitones / 12.0)
    speedup = 1.0 / factor

    temp_out = path.with_name(f"{path.stem}_deep{path.suffix}")

    # Filter chain:
    # 1. asetrate lowers pitch and stretches time
    # 2. atempo compensates speed so total duration matches the original millisecond-for-millisecond
    # 3. aresample restores canonical sample rate
    audio_filter = f"asetrate={sample_rate}*{factor:.5f},atempo={speedup:.5f},aresample={sample_rate}"

    cmd = [
        ffmpeg_exe,
        "-i", str(path),
        "-af", audio_filter,
        "-y", str(temp_out),
    ]

    print(f"[Plotquake Audio] Applying subtle baritone pitch shift ({semitones:+.1f} semitones) to make voice slightly deeper...")
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode == 0 and temp_out.exists():
        temp_out.replace(path)
        print(f"[Plotquake Audio] SUCCESS: Calibrated deep male narration saved to {path}")
    else:
        print(f"[Plotquake Audio] Pitch shift warning: FFmpeg failed ({res.stderr[:200]}). Keeping raw audio.")

async def synthesize_with_live_api(text: str, output_path: str, voice_name: str = DEFAULT_VOICE, api_key: str = "", pitch_shift: float = DEFAULT_PITCH_SEMITONES):
    from google import genai

    client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY", ""))

    config = {
        "response_modalities": ["AUDIO"],
        "speech_config": {
            "voice_config": {
                "prebuilt_voice_config": {"voice_name": voice_name}
            }
        },
        "system_instruction": {
            "parts": [{"text": DOCUMENTARY_VOICE_PROMPT}]
        },
    }

    pcm_chunks = []
    print(f"[Plotquake Voice] Connecting to Gemini 3.8 Live with male voice '{voice_name}'...")

    async with client.aio.live.connect(model=PRIMARY_LIVE_MODEL, config=config) as session:
        print("[Plotquake Voice] Sending documentary narration script...")
        await session.send_client_content(
            turns=[
                {
                    "role": "user",
                    "parts": [{"text": f"Please narrate this documentary script faithfully in a deep, authoritative baritone voice:\n\n{text}"}]
                }
            ],
            turn_complete=True,
        )

        async for response in session.receive():
            server = getattr(response, "server_content", None)
            if server is None:
                continue

            model_turn = getattr(server, "model_turn", None)
            if model_turn:
                for part in getattr(model_turn, "parts", []):
                    inline = getattr(part, "inline_data", None)
                    if inline and inline.data:
                        pcm_chunks.append(inline.data)

            if getattr(server, "turn_complete", False):
                print("[Plotquake Voice] Narration stream successfully completed!")
                break

    if not pcm_chunks:
        raise RuntimeError("No audio chunks received from Gemini 3.8 Live.")

    raw_pcm = b"".join(pcm_chunks)
    print(f"[Plotquake Voice] Received {len(raw_pcm)} bytes of studio audio (24kHz PCM). Saving to {output_path}...")

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_file), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(raw_pcm)

    # Post-process: apply subtle baritone pitch calibration
    if pitch_shift != 0.0:
        apply_baritone_pitch_calibration(str(out_file), semitones=pitch_shift)

    print(f"[Plotquake Voice] Studio narration ready at {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Synthesize Plotquake narration with Gemini 3.8 Live")
    parser.add_argument("--text", help="Narration text string")
    parser.add_argument("--script-file", help="Path to text or JSON file containing narration")
    parser.add_argument("--output", default="public/assets/audio/narration.wav", help="Output WAV path")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Gemini Live voice (Charon or Fenrir)")
    parser.add_argument("--pitch-shift", type=float, default=DEFAULT_PITCH_SEMITONES, help="Pitch shift in semitones (e.g. -1.0 for deeper)")
    parser.add_argument("--api-key", default=os.getenv("GEMINI_API_KEY", ""), help="Gemini API Key")

    args = parser.parse_args()

    narration_text = args.text
    if not narration_text and args.script_file:
        path = Path(args.script_file)
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            narration_text = data.get("narration") or " ".join(
                scene.get("narration", "") for act in data.get("acts", []) for scene in act.get("scenes", [])
            )
        else:
            narration_text = path.read_text(encoding="utf-8")

    if not narration_text:
        narration_text = (
            "In 2007, BlackBerry was not just a smartphone. It was power. "
            "On Wall Street, in the White House, and across corporate America, "
            "it controlled over fifty percent of the entire market. "
            "No one could imagine the world without it. Until two engineers made a fatal mistake."
        )

    if not args.api_key:
        print("ERROR: GEMINI_API_KEY not found in environment or arguments.")
        sys.exit(1)

    asyncio.run(synthesize_with_live_api(
        narration_text,
        args.output,
        voice_name=args.voice,
        api_key=args.api_key,
        pitch_shift=args.pitch_shift
    ))

if __name__ == "__main__":
    main()
