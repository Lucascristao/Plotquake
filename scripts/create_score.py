"""Create an original, restrained documentary score and two quiet transition accents.

No stock music, external models, samples, or extra Python dependencies are used.
The 120-second bed uses periodic oscillators and circularly filtered noise, so its
last sample continues into its first without a fade-to-silence every two minutes.

Actions: python scripts/create_score.py
Local:   python scripts/create_score.py --preview
Local runs default to a short preview in renders/score-preview and leave the
tracked production WAV untouched.
"""
from __future__ import annotations

import argparse
from array import array
import math
import os
from pathlib import Path
import random
import sys
import time
import wave

TABLE_SIZE = 32768
TABLE_MASK = TABLE_SIZE - 1
SINE = tuple(math.sin(2 * math.pi * index / TABLE_SIZE) for index in range(TABLE_SIZE))


def periodic_noise(sample_rate: int) -> tuple[list[float], list[float]]:
    """A four-second circular texture with no hard seam or one-sample clicks."""
    rng = random.Random(81729)
    white = [rng.uniform(-1.0, 1.0) for _ in range(sample_rate * 4)]
    dark: list[float] = []
    air: list[float] = []
    low, smooth = 0.0, 0.0
    # The first pass warms the IIR filters; the second captures a periodic state.
    for take in range(2):
        for value in white:
            low += 0.015 * (value - low)
            smooth += 0.28 * (value - smooth)
            if take:
                dark.append(low)
                air.append(smooth - low)
    return dark, air


def pcm_chunk(samples: array) -> bytes:
    if sys.byteorder != "little":
        samples.byteswap()
    return samples.tobytes()


def write_audio(path: Path, sample_rate: int, count: int, sample_function) -> dict:
    path.parent.mkdir(parents=True, exist_ok=True)
    peak, square_sum = 0.0, 0.0
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(2)
        handle.setsampwidth(2)
        handle.setframerate(sample_rate)
        for start in range(0, count, 4096):
            block = array("h")
            for index in range(start, min(start + 4096, count)):
                left, right = sample_function(index)
                # Fixed headroom preserves the gentle sound; no loudness maximizer.
                left = max(-0.8, min(0.8, left))
                right = max(-0.8, min(0.8, right))
                peak = max(peak, abs(left), abs(right))
                square_sum += left * left + right * right
                block.extend((round(left * 32767), round(right * 32767)))
            handle.writeframesraw(pcm_chunk(block))
    rms = math.sqrt(square_sum / max(1, count * 2))
    return {"seconds": count / sample_rate, "peakDbfs": round(20 * math.log10(max(peak, 1e-9)), 2),
            "rmsDbfs": round(20 * math.log10(max(rms, 1e-9)), 2)}


def make_bed(path: Path, seconds: float, sample_rate: int) -> dict:
    count = round(seconds * sample_rate)
    seconds = count / sample_rate
    dark, air = periodic_noise(sample_rate)
    noise_count = len(dark)
    # D-related fundamentals with a distant suspended color. Quantization to
    # whole cycles over the bed makes every oscillator close exactly at the seam.
    voices = [(36.708, .14, 0.0), (73.416, .065, .08), (110.125, .028, -.12),
              (146.833, .023, .2), (130.833, .013, -.18),
              (220.25, .010, .32), (293.667, .006, -.25), (155.583, .004, .14)]
    partials = [(round(frequency * seconds) * TABLE_SIZE / count, amplitude, pan)
                for frequency, amplitude, pan in voices]
    slow_step = TABLE_SIZE / count
    pulse_step = round(seconds * .75) * TABLE_SIZE / count

    def sample(index: int) -> tuple[float, float]:
        slow = SINE[int(index * slow_step) & TABLE_MASK]
        slow_three = SINE[int(index * slow_step * 3 + TABLE_SIZE * .16) & TABLE_MASK]
        envelope = .72 + .13 * slow + .08 * slow_three
        left, right = 0.0, 0.0
        for step, amplitude, pan in partials:
            tone = SINE[int(index * step) & TABLE_MASK] * amplitude * envelope
            left += tone * (1 - pan * .22)
            right += tone * (1 + pan * .22)
        pulse = .5 + .5 * SINE[int(index * pulse_step) & TABLE_MASK]
        pulse *= pulse
        pulse *= pulse
        pulse *= pulse
        low_pulse = SINE[int(index * partials[1][0]) & TABLE_MASK] * pulse * .025
        # The higher bed floats slightly across the stereo field; the bass stays
        # centered so the mix survives phones and mono playback.
        left += low_pulse + dark[index % noise_count] * .015 + air[index % noise_count] * .004
        right += low_pulse + dark[index % noise_count] * .015 + air[(index + sample_rate) % noise_count] * .004
        return left, right

    return write_audio(path, sample_rate, count, sample)


def make_accent(path: Path, sample_rate: int, kind: str) -> dict:
    seconds = 2.5 if kind == "chapter" else 2.0
    count = round(seconds * sample_rate)
    _, air = periodic_noise(sample_rate)
    noise_count = len(air)

    def sample(index: int) -> tuple[float, float]:
        t = index / sample_rate
        end = min(1.0, max(0.0, (seconds - t) / .25))
        attack = min(1.0, t / .012)
        if kind == "chapter":
            body = (.28 * math.sin(2 * math.pi * (61 * t - 4.7 * t * t)) * math.exp(-4.7 * t)
                    + .045 * math.sin(2 * math.pi * 110 * t) * math.exp(-3.2 * t))
            texture = air[index % noise_count] * .018 * math.exp(-4 * t)
        else:
            swell = math.sin(math.pi * min(1.0, t / .72)) ** 2 if t < .72 else 0.0
            body = (.095 * math.sin(2 * math.pi * 146.833 * t) * math.exp(-3.0 * t)
                    + .05 * math.sin(2 * math.pi * 220.25 * t) * math.exp(-4.2 * t))
            texture = air[index % noise_count] * (.025 * swell + .005) * math.exp(-2.5 * t)
        value = (body + texture) * attack * end
        return value, value * .98

    return write_audio(path, sample_rate, count, sample)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview", action="store_true", help="Write an eight-second sample under renders.")
    parser.add_argument("--seconds", type=float, help="Bed duration; production default is 120 seconds.")
    parser.add_argument("--sample-rate", type=int, default=24000)
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    production = os.environ.get("GITHUB_ACTIONS", "").lower() == "true" and not args.preview
    seconds = args.seconds if args.seconds is not None else (120.0 if production else 8.0)
    if args.preview:
        seconds = min(seconds, 8.0)
    if seconds <= 0 or args.sample_rate < 8000:
        parser.error("Choose a positive duration and a sample rate of at least 8000 Hz.")
    output_dir = args.output_dir or Path("public/assets/audio" if production else "renders/score-preview")
    started = time.monotonic()
    outputs = [
        ("tension_score.wav", make_bed(output_dir / "tension_score.wav", seconds, args.sample_rate)),
        ("chapter_transition.wav", make_accent(output_dir / "chapter_transition.wav", args.sample_rate, "chapter")),
        ("reveal_accent.wav", make_accent(output_dir / "reveal_accent.wav", args.sample_rate, "reveal")),
    ]
    for filename, stats in outputs:
        print(f"[Original audio] {output_dir / filename}: {stats['seconds']:.2f}s, "
              f"peak {stats['peakDbfs']:.1f} dBFS, RMS {stats['rmsDbfs']:.1f} dBFS")
    print(f"[Score ready] {'production' if production else 'local preview'}; {time.monotonic() - started:.1f}s")


if __name__ == "__main__":
    main()

