"""Offline checks for explicit delivery direction and compatible narration caches."""
import hashlib
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch
import wave

from synthesize_narration import (DOCUMENTARY_VOICE_PROMPT, DYNAMIC_NARRATION_STYLE, DYNAMIC_VOICE_PROMPT,
                                  PRIMARY_LIVE_MODEL, PROMPT_VERSION, SAMPLE_RATE, cache_fingerprint,
                                  digest, receive_narration, synthesize_scene, transcript_has_script_ending, write_json)


def run_immediate(coroutine):
    """All test awaits are in-memory fakes; avoid opening a Windows event-loop socket."""
    try:
        coroutine.send(None)
    except StopIteration as completed:
        return completed.value
    finally:
        coroutine.close()
    raise AssertionError("The offline test unexpectedly waited for real I/O.")


async def immediate_wait(awaitable, *, timeout):
    return await awaitable


def transcript_client(spoken):
    """One in-memory completed Live turn; no connection or generated voice."""
    class Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            pass

        async def send_client_content(self, **kwargs):
            pass

        async def receive(self):
            yield SimpleNamespace(server_content=SimpleNamespace(
                output_transcription=SimpleNamespace(text=spoken), turn_complete=True,
                model_turn=SimpleNamespace(parts=[SimpleNamespace(inline_data=SimpleNamespace(
                    data=b"\0\0" * SAMPLE_RATE * 40, mime_type="audio/pcm"))])))

    return SimpleNamespace(aio=SimpleNamespace(live=SimpleNamespace(connect=lambda **kwargs: Session())))


class NarrationStyleTests(unittest.TestCase):
    def test_dynamic_requires_the_ending_while_legacy_keeps_the_same_similarity_guard(self):
        prefix = "The crew prepared the equipment and carefully followed the recovery procedure. " * 4
        expected = prefix + "They preserved that moment in the photograph."
        truncated = prefix + "They preserved that moment"
        # This real failure pattern is too small to cross the existing .88 ratio.
        self.assertFalse(transcript_has_script_ending(expected, truncated))
        run_immediate(receive_narration(transcript_client(truncated), expected, "Charon"))
        with self.assertRaisesRegex(RuntimeError, "script ending"):
            run_immediate(receive_narration(transcript_client(truncated), expected, "Charon", DYNAMIC_NARRATION_STYLE))
        run_immediate(receive_narration(transcript_client(expected), expected, "Charon", DYNAMIC_NARRATION_STYLE))

    def test_compacted_endings_accept_acronyms_and_hyphen_boundaries(self):
        prefix = "The crew prepared the equipment and carefully followed the recovery procedure. " * 4
        for expected_end, spoken_end in (("They returned using the M M U.", "They returned using the MMU."),
                                         ("They recovered the free-flying jetpack.", "They recovered the free flying jet pack.")):
            with self.subTest(ending=expected_end):
                expected, spoken = prefix + expected_end, prefix + spoken_end
                self.assertTrue(transcript_has_script_ending(expected, spoken))
                run_immediate(receive_narration(transcript_client(spoken), expected, "Charon", DYNAMIC_NARRATION_STYLE))

    def test_absent_transcription_does_not_create_an_ending_requirement(self):
        self.assertEqual(run_immediate(receive_narration(transcript_client(""), "The script.", "Charon",
                                                        DYNAMIC_NARRATION_STYLE))[1], "")

    def test_general_similarity_still_rejects_a_changed_body_with_the_correct_ending(self):
        expected = "The crew prepared the equipment and carefully followed the recovery procedure. " * 4 + "Here is the ending."
        spoken = "An unrelated account supplies different words about another subject entirely. " * 4 + "Here is the ending."
        self.assertTrue(transcript_has_script_ending(expected, spoken))
        for style in (None, DYNAMIC_NARRATION_STYLE):
            with self.subTest(style=style), self.assertRaisesRegex(RuntimeError, "similarity"):
                run_immediate(receive_narration(transcript_client(spoken), expected, "Charon", style))

    def test_no_style_keeps_the_exact_legacy_fingerprint_for_raw_and_pitched_audio(self):
        for pitch in (0.0, -1.0):
            payload = json.dumps([PRIMARY_LIVE_MODEL, "Charon", pitch, PROMPT_VERSION, "The script."], ensure_ascii=False)
            legacy = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            self.assertEqual(cache_fingerprint("The script.", "Charon", pitch), legacy)
            self.assertEqual(cache_fingerprint("The script.", "Charon", pitch, None), legacy)
            self.assertNotEqual(cache_fingerprint("The script.", "Charon", pitch, DYNAMIC_NARRATION_STYLE), legacy)

    def test_selected_prompt_reaches_same_live_model_and_voice(self):
        calls = []

        class Session:
            async def __aenter__(self):
                return self

            async def __aexit__(self, *args):
                pass

            async def send_client_content(self, **kwargs):
                pass

            async def receive(self):
                yield SimpleNamespace(server_content=SimpleNamespace(
                    output_transcription=SimpleNamespace(text="The script."), turn_complete=True,
                    model_turn=SimpleNamespace(parts=[SimpleNamespace(inline_data=SimpleNamespace(
                        data=b"\0\0" * SAMPLE_RATE, mime_type="audio/pcm"))])))

        def connect(**kwargs):
            calls.append(kwargs)
            return Session()

        client = SimpleNamespace(aio=SimpleNamespace(live=SimpleNamespace(connect=connect)))
        run_immediate(receive_narration(client, "The script.", "Charon"))
        run_immediate(receive_narration(client, "The script.", "Charon", DYNAMIC_NARRATION_STYLE))
        for call, prompt in zip(calls, (DOCUMENTARY_VOICE_PROMPT, DYNAMIC_VOICE_PROMPT)):
            self.assertEqual(call["model"], PRIMARY_LIVE_MODEL)
            self.assertEqual(call["config"]["speech_config"]["voice_config"]["prebuilt_voice_config"]["voice_name"], "Charon")
            self.assertEqual(call["config"]["system_instruction"]["parts"][0]["text"], prompt)

    def test_new_style_cannot_reuse_legacy_raw_audio_but_reuses_its_own_completed_scene(self):
        root = Path(__file__).resolve().parents[1] / "out/narration-style-tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            target = Path(directory) / "scene.wav"
            raw = target.with_name("scene.raw.wav")
            with wave.open(str(raw), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(SAMPLE_RATE)
                audio.writeframes(b"\0\0" * SAMPLE_RATE)
            write_json(raw.with_suffix(".json"), {"fingerprint": cache_fingerprint("The script.", "Charon", 0.0),
                       "audioSha256": digest(raw), "durationSeconds": 1, "transcript": "The script."})
            with patch("synthesize_narration.receive_narration", new_callable=AsyncMock,
                       return_value=(b"\x01\0" * SAMPLE_RATE, "The script.")) as receive, \
                    patch("synthesize_narration.asyncio.wait_for", new=immediate_wait):
                first = run_immediate(synthesize_scene(None, "The script.", target, "Charon", 0.0,
                                                      narration_style=DYNAMIC_NARRATION_STYLE))
                second = run_immediate(synthesize_scene(None, "The script.", target, "Charon", 0.0,
                                                       narration_style=DYNAMIC_NARRATION_STYLE))
            receive.assert_awaited_once_with(None, "The script.", "Charon", DYNAMIC_NARRATION_STYLE)
            self.assertEqual(first, second)
            self.assertEqual(first["narrationStyle"], DYNAMIC_NARRATION_STYLE)
            metadata = json.loads(raw.with_suffix(".json").read_text(encoding="utf-8"))
            self.assertEqual(metadata["narrationStyle"], DYNAMIC_NARRATION_STYLE)


if __name__ == "__main__":
    unittest.main()
