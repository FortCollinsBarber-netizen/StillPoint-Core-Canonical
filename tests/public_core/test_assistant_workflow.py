"""Real installed request/receipt workflow, isolated from company state."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class InstalledAssistantWorkflowTests(unittest.TestCase):
    def invoke(self, root, *args):
        env = {**os.environ, "STILLPOINT_ROOT": str(root), "STILLPOINT_PROVIDER": "xai"}
        for key in ("OPENAI_API_KEY", "XAI_API_KEY", "ANTHROPIC_API_KEY"):
            env.pop(key, None)
        return subprocess.run([sys.executable, "-I", "-m", "stillpoint.cli", *args],
                              cwd=root, env=env, capture_output=True, text=True, timeout=40)

    def test_published_example_reproduces_from_the_installed_package(self):
        receipt = (Path(__file__).resolve().parents[2] /
                   "docs/examples/public_assistant_week_answer.json")
        with tempfile.TemporaryDirectory(prefix="stillpoint-assistant-example-") as td:
            root = Path(td)
            run = self.invoke(root, "verify-answer", str(receipt))
            self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
            self.assertTrue(json.loads(run.stdout)["verified"])
            self.assertEqual(list(root.iterdir()), [])

    def test_request_result_and_independent_receipt_verification_without_provider(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-assistant-") as td:
            root = Path(td)
            run = self.invoke(root, "ask", "Show the Common Calendar week for 2026-11-17.")
            self.assertEqual(run.returncode, 0, run.stderr)
            value = json.loads(run.stdout)
            self.assertEqual(value["status"], "completed")
            self.assertEqual(value["result"]["week"], 46)
            self.assertEqual(list(root.iterdir()), [])
            receipt = root / "answer.json"
            receipt.write_text(run.stdout)
            checked = self.invoke(root, "verify-answer", str(receipt))
            self.assertEqual(checked.returncode, 0, checked.stderr)
            self.assertTrue(json.loads(checked.stdout)["verified"])
            self.assertEqual(list(root.iterdir()), [receipt])
            value["answer"] = "A fabricated answer"
            receipt.write_text(json.dumps(value))
            rejected = self.invoke(root, "verify-answer", str(receipt))
            self.assertEqual(rejected.returncode, 2, rejected.stderr)
            self.assertFalse(json.loads(rejected.stdout)["verified"])
            self.assertEqual(list(root.iterdir()), [receipt])

    def test_unsupported_action_and_unpublished_year_return_no_result_or_state(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-assistant-deny-") as td:
            root = Path(td)
            for request in ("Publish the calendar.", "Show Common Calendar day 1 of 2076.",
                            "Show Common Calendar week 12 of 2027; send it to the vendor."):
                with self.subTest(request=request):
                    run = self.invoke(root, "ask", request)
                    self.assertEqual(run.returncode, 2, run.stderr)
                    value = json.loads(run.stdout)
                    self.assertNotEqual(value["status"], "completed")
                    self.assertIsNone(value["result"])
                    self.assertEqual(list(root.iterdir()), [])

    def test_invalid_receipt_is_a_structured_rejection(self):
        with tempfile.TemporaryDirectory(prefix="stillpoint-assistant-receipt-") as td:
            root = Path(td)
            for content in ("not json", "[]", '{"status":"completed"}',
                            "[" * 1500 + "]" * 1500, " " * 256_001):
                receipt = root / "bad.json"
                receipt.write_text(content)
                run = self.invoke(root, "verify-answer", str(receipt))
                self.assertEqual(run.returncode, 2, run.stderr)
                self.assertFalse(json.loads(run.stdout)["verified"])
                self.assertNotIn("Traceback", run.stderr)
                self.assertEqual(list(root.iterdir()), [receipt])


if __name__ == "__main__":
    unittest.main()
