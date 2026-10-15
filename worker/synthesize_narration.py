import argparse
import asyncio
import json
import os
import sys
import wave
from pathlib import Path

# Gemini 3.8 Live constants
PRIMARY_LIVE_MODEL = "gemini-3.8-live"
FALLBACK_TTS_MODEL = "gemini-2.0-flash"
DEFAULT_VOICE = "Charon"  # Deep, authoritative, cinematic American documentary narrator

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
    from google.genai import types

    client = genai.Client(api_key=api_key or os.getenv("GEMINI_API_KEY", ""))

    config = types.LiveConnectConfig(
        response_modalities=[types.LiveServerContentResponseModalities.AUDIO],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice_name)
            )
        ),
        system_instruction=types.Content(
            parts=[types.Part.from_text(text=DOCUMENTARY_VOICE_PROMPT)]
        ),
    )

    pcm_chunks = []
    print(f"[Plotquake Voice] Connecting to Gemini 3.8 Live ({voice_name})...")

    # Connect to Gemini Live WebSocket
    async with client.aio.live.connect(model=PRIMARY_LIVE_MODEL, config=config) as session:
        print("[Plotquake Voice] Sending narration script to Gemini Live...")
        await session.send_client_content(
            turns=[
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=f"Please narrate this script faithfully:\n\n{text}")]
                )
            ],
            turn_complete=True,
        )

        async for response in session.receive():
            server_content = response.server_content
            if server_content is not None:
                model_turn = server_content.model_turn
                if model_turn is not None:
                    for part in model_turn.parts:
                        if part.inline_data and part.inline_data.data:
                            pcm_chunks.append(part.inline_data.data)

                if server_content.turn_complete:
                    print("[Plotquake Voice] Gemini Live narration stream finished.")
                    break

    if not pcm_chunks:
        raise RuntimeError("No audio data received from Gemini 3.8 Live.")

    raw_pcm = b"".join(pcm_chunks)
    print(f"[Plotquake Voice] Received {len(raw_pcm)} bytes of studio audio (24kHz PCM). Saving to {output_path}...")

    # Save as 24kHz, 16-bit Mono WAV
    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(out_file), "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24000)
        wav.writeframes(raw_pcm)

    print(f"[Plotquake Voice] SUCCESS! Narrated audio saved to {output_path}")

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
            # If episode format, join all scene narration strings
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
