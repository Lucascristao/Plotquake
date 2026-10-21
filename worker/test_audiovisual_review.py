"""Offline checks for the optional observer; no Gemini request or media render."""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from review_audiovisual import MODEL, ReviewUnavailable, analyze, main, select_input


def client_for(text, status="completed"):
    client = Mock()
    client.files.upload.return_value = SimpleNamespace(name="files/test", uri="private-file-uri", state="ACTIVE")
    client.interactions.create.return_value = iter([
        {"event_type": "step.delta", "delta": {"type": "text", "text": text}},
        {"event_type": "interaction.completed", "interaction": {"status": status, "usage": {"total_input_tokens": 100}}},
    ])
    return client


class AudiovisualReviewTests(unittest.TestCase):
    def test_static_complete_file_request_and_cleanup(self):
        client = client_for('{"observations": [{"start": "00:00", "end": "00:30", "sound": "Narration and music."}]}')
        result = analyze(client, Path("final.mp4"), "Observe actual sound and picture.", MODEL)
        request = client.interactions.create.call_args.kwargs
        self.assertEqual(request["input"][0]["processing"], {"type": "static", "fps": 1})
        self.assertEqual(request["input"][0]["resolution"], "high")
        self.assertFalse(request["store"])
        self.assertEqual(result["responseFormat"], "json")
        self.assertNotIn("private-file-uri", json.dumps(result))
        client.files.delete.assert_called_once_with(name="files/test")

    def test_unstructured_descriptive_completion_is_retained(self):
        client = client_for("00:00-00:30: The narration accompanies the shuttle image.")
        result = analyze(client, Path("final.mp4"), "Observe.", MODEL)
        self.assertEqual(result["responseFormat"], "raw_text")
        self.assertTrue(result["rawDescriptiveResponse"])
        client.files.delete.assert_called_once()

    def test_initial_model_output_text_is_preserved_before_deltas(self):
        client = client_for("Unused")
        client.interactions.create.return_value = iter([
            {"event_type": "step.start", "step": {"type": "thought", "summary": [{"type": "text", "text": "Private thought"}]}},
            {"event_type": "step.start", "step": {"type": "model_output", "content": [{"type": "text", "text": '{"observations": ['}]}},
            {"event_type": "step.delta", "delta": {"type": "text", "text": "]}"}},
            {"event_type": "interaction.completed", "interaction": {"status": "completed"}},
        ])
        result = analyze(client, Path("final.mp4"), "Observe.", MODEL)
        self.assertEqual(result["responseFormat"], "json")
        self.assertEqual(result["rawDescriptiveResponse"], '{"observations": []}')
        self.assertNotIn("Private thought", result["rawDescriptiveResponse"])

    def test_incomplete_output_does_not_become_observations(self):
        client = client_for("Partial text.", status="incomplete")
        cleanup = {}
        with self.assertRaises(ReviewUnavailable):
            analyze(client, Path("final.mp4"), "Observe.", MODEL, cleanup=cleanup)
        self.assertEqual(cleanup["fileDeletion"], "requested_successfully")

    def test_failed_file_processing_is_cleaned_up(self):
        client = client_for("Unused")
        client.files.upload.return_value.state = "FAILED"
        with self.assertRaises(ReviewUnavailable):
            analyze(client, Path("final.mp4"), "Observe.", MODEL)
        client.interactions.create.assert_not_called()
        client.files.delete.assert_called_once()

    def test_proxy_requires_both_explicit_flag_and_ci(self):
        info = {"format": "avi", "durationSeconds": 20, "width": 1920, "height": 1080}
        with patch("review_audiovisual.probe_video", return_value=info), patch("pathlib.Path.stat") as stat, \
                patch("review_audiovisual.os.getenv", return_value="false"), patch("review_audiovisual.subprocess.Popen") as encode:
            stat.return_value.st_size = 100
            with self.assertRaises(ReviewUnavailable):
                select_input(Path("final.avi"), Path("out"), allow_ci_proxy=True, max_upload_bytes=200)
            encode.assert_not_called()

    def test_api_error_text_and_key_are_not_written_or_reported_as_reviewed(self):
        root = Path(__file__).resolve().parents[1] / "out/audiovisual-review-tests"
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as directory:
            folder = Path(directory)
            video = folder / "final.mp4"
            video.write_bytes(b"offline fixture, never uploaded")
            client = client_for("Unused")
            error = ValueError("https://example.test?key=FAKE_SECRET key header")
            error.status_code = 429
            client.interactions.create.side_effect = error
            fake_google = SimpleNamespace(genai=SimpleNamespace(Client=Mock(return_value=client)))
            with patch.dict("sys.modules", {"google": fake_google}), \
                    patch("sys.argv", ["review_audiovisual.py", "--video", str(video), "--output-dir", str(folder)]), \
                    patch("review_audiovisual.select_input", return_value=(video, {"durationSeconds": 20})), \
                    patch("review_audiovisual.os.getenv", return_value="FAKE_SECRET"):
                main()
            output = (folder / "audiovisual_review.json").read_text(encoding="utf-8")
            report = json.loads(output)
            self.assertNotIn("FAKE_SECRET", output)
            self.assertNotIn("example.test", output)
            self.assertEqual(report["availability"], "unavailable")
            self.assertFalse(report["modelAnalysisCompleted"])
            self.assertEqual(report["errorCode"], 429)
            self.assertEqual(report["cleanup"]["fileDeletion"], "requested_successfully")


if __name__ == "__main__":
    unittest.main()
