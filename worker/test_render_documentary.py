"""Check full-frame coverage, resumable chunks and continuous-audio assembly offline."""
import copy
import json
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import unittest
import wave

from render_documentary import (assemble, cached_chunk, file_hash, make_plan, probe,
                                validate_plan, write_json)


class RenderDocumentaryTests(unittest.TestCase):
    def test_long_story_is_not_limited_to_four_chunks_or_256_jobs(self):
        plan = make_plan({"id": "long-story", "fps": 30, "durationInFrames": 30 * 60 * 12 * 60},
                         target_seconds=60, workers=4)
        validate_plan(plan)
        self.assertGreater(len(plan["chunks"]), 256)
        self.assertEqual(plan["matrix"], {"worker": [0, 1, 2, 3]})
        self.assertEqual(plan["chunks"][-1]["endFrame"], plan["durationInFrames"] - 1)
        self.assertLessEqual(max(part["frames"] for part in plan["chunks"])
                             - min(part["frames"] for part in plan["chunks"]), 1)

    def test_missing_or_duplicate_boundary_is_rejected(self):
        plan = make_plan({"id": "uneven", "fps": 30, "durationInFrames": 97}, .7, 3)
        validate_plan(plan)
        changed = copy.deepcopy(plan)
        changed["chunks"][1]["startFrame"] -= 1
        with self.assertRaisesRegex(ValueError, "discontinuous"):
            validate_plan(changed)
        changed = copy.deepcopy(plan)
        changed["chunks"].pop()
        with self.assertRaisesRegex(ValueError, "every timeline frame"):
            validate_plan(changed)

    def test_mux_preserves_all_frames_and_continuous_audio_packets(self):
        output_root = Path(__file__).resolve().parents[1] / "renders/render-tests"
        output_root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=output_root) as temporary:
            directory = Path(temporary)
            plan = make_plan({"id": "sound-across-cuts", "fps": 30, "durationInFrames": 97}, .7, 3)
            plan["renderKey"] = "test-render"
            picture = Path(__file__).resolve().parents[1] / "public/assets/images/blackberry-thumbnail.png"
            for part in plan["chunks"]:
                path = directory / part["file"]
                subprocess.run(["ffmpeg", "-y", "-v", "error", "-loop", "1", "-framerate", "30",
                                "-i", str(picture), "-vf", "scale=1920:1080", "-frames:v", str(part["frames"]),
                                "-an", "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
                                str(path)], check=True)
                write_json(path.with_suffix(".json"), {"renderKey": plan["renderKey"], "sha256": file_hash(path)})
                self.assertTrue(cached_chunk(path, part, plan))
            master = directory / "master_audio.m4a"
            pcm = directory / "sound.wav"
            with wave.open(str(pcm), "wb") as output:
                output.setnchannels(1)
                output.setsampwidth(2)
                output.setframerate(48000)
                output.writeframes(b"".join(struct.pack("<h", round(8000 * math.sin(i * 2 * math.pi * 220 / 48000)))
                                           for i in range(97 * 1600)))
            subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(pcm),
                            "-c:a", "aac", "-b:a", "192k", "-f", "mp4", str(master)], check=True)
            output = directory / "documentary_final.mp4"
            assemble(plan, directory, master, output)
            streams = probe(output)["streams"]
            self.assertEqual(next(s for s in streams if s["codec_type"] == "video")["nb_frames"], "97")
            # A bitstream hash proves the master AAC was copied whole, rather than joined or re-encoded.
            def audio_hash(path):
                result = subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "a:0",
                                                  "-show_packets", "-show_data_hash", "sha256", "-show_entries",
                                                  "packet=data_hash", "-of", "json", str(path)], text=True)
                return [packet["data_hash"] for packet in json.loads(result)["packets"]]
            self.assertEqual(audio_hash(master), audio_hash(output))
            first = plan["chunks"][0]
            receipt = directory / first["file"]
            saved = json.loads(receipt.with_suffix(".json").read_text())
            saved["renderKey"] = "old-render"
            write_json(receipt.with_suffix(".json"), saved)
            self.assertFalse(cached_chunk(receipt, first, plan))
            with self.assertRaisesRegex(ValueError, "different render"):
                assemble(plan, directory, master, output)
            saved["renderKey"] = plan["renderKey"]
            write_json(receipt.with_suffix(".json"), saved)
            (directory / plan["chunks"][-1]["file"]).unlink()
            with self.assertRaises(FileNotFoundError):
                assemble(plan, directory, master, output)


if __name__ == "__main__":
    unittest.main()
