import argparse
import asyncio
import json
import os
import sys
import wave
from pathlib import Path

PRIMARY_LIVE_MODEL = "gemini-3.8-live"
DEFAULT_VOICE = "Charon"  # Authoritative, deep, cinematic documentary narrator

DOCUMENTARY_VOICE_PROMPT = """
You are the official voice of Plotquake documentaries.
Tone: Deep, authoritative, captivating American documentary narrator (similar to History Channel, Netflix, and National Geographic).
Cadence: Steady, serious, measured. Add dramatic pauses before key revelations and numbers.
Pacing: Approximately 145 to 155 words per minute.
Emotion: Subtle curiosity in questions, tension in conflicts, gravitas in historical turning points.
Crucial: Read the text exactly as provided without adding greetings, sign-offs, or conversational pleasantries.
"""

async def synthesize_with_live_api(text: str, output_path: str, voice_name: str = DEFAULT_VOICE, api_key: str = ""):
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
    print(f"[Plotquake Voice] Connecting to Gemini 3.8 Live with voice '{voice_name}'...")

    async with client.aio.live.connect(model=PRIMARY_LIVE_MODEL, config=config) as session:
        print("[Plotquake Voice] Sending documentary narration script...")
        await session.send_client_content(
            turns=[
                {
                    "role": "user",
                    "parts": [{"text": f"Please narrate this script faithfully:\n\n{text}"}]
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

    print(f"[Plotquake Voice] SUCCESS! Narrated studio audio saved to {output_path}")

def main():
    parser = argparse.ArgumentParser(description="Synthesize Plotquake narration with Gemini 3.8 Live")
    parser.add_argument("--text", help="Narration text string")
    parser.add_argument("--script-file", help="Path to text or JSON file containing narration")
    parser.add_argument("--output", default="public/assets/audio/narration.wav", help="Output WAV path")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Gemini Live voice (Charon, Fenrir, Aoede)")
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

    asyncio.run(synthesize_with_live_api(narration_text, args.output, voice_name=args.voice, api_key=args.api_key))

if __name__ == "__main__":
    main()
