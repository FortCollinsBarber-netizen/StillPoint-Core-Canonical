import copy
import hashlib
import json
import unittest
from unittest.mock import patch

from stillpoint.public_assistant import (
    DAY_READ, WEEK_READ, MAX_REQUEST_CHARACTERS, PUBLIC_READ_CAPABILITIES,
    answer_request, interpret_request, verify_answer_receipt,
)


class PublicAssistantTests(unittest.TestCase):
    def ask(self, text):
        return answer_request(text, allowed_capabilities=PUBLIC_READ_CAPABILITIES)

    def test_gregorian_request_reaches_a_real_day_and_reproducible_evidence(self):
        value = self.ask("What is the Common Calendar date for 2026-11-17?")
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["result"]["calendar_address"], "Y_2026-321")
        self.assertIn("Tuesday", value["answer"])
        self.assertTrue(value["authorization"]["allowed"])
        self.assertFalse(value["authorization"]["execution_warrant"])
        self.assertTrue(verify_answer_receipt(value)["verified"])

    def test_week_request_returns_seven_real_days(self):
        value = self.ask("Show the Common Calendar week for 2026-11-17.")
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["result"]["week"], 46)
        self.assertEqual(len(value["result"]["days"]), 7)
        self.assertEqual(value["result"]["first_address"], "Y_2026-316")
        self.assertEqual(value["result"]["last_address"], "Y_2026-322")
        self.assertTrue(verify_answer_receipt(value)["verified"])

    def test_direct_common_coordinates_keep_the_last_published_day(self):
        value = self.ask("Show Common Calendar day 364 of 2075.")
        self.assertEqual(value["status"], "completed")
        self.assertEqual(value["result"]["calendar_address"], "Y_2075-364")
        week = self.ask("Show Common Calendar week 52 of 2075.")
        self.assertEqual(week["status"], "completed")
        self.assertEqual(week["result"]["last_address"], "Y_2075-364")

    def test_missing_permission_and_wrong_permission_stop_before_execution(self):
        with patch("stillpoint.public_assistant._project") as project:
            value = answer_request("Show Common Calendar week 12 of 2027.")
            self.assertEqual(value["status"], "denied")
            value = answer_request("Show Common Calendar week 12 of 2027.",
                                   allowed_capabilities=frozenset({DAY_READ}))
            self.assertEqual(value["status"], "denied")
            project.assert_not_called()

    def test_oversized_request_is_not_echoed_or_executed_in_full(self):
        value = self.ask("x" * 100_000)
        self.assertEqual(value["status"], "unsupported")
        self.assertTrue(value["request_truncated"])
        self.assertEqual(len(value["request"]), MAX_REQUEST_CHARACTERS)

    def test_unknown_or_overbroad_caller_permissions_are_rejected(self):
        for permissions in ({DAY_READ}, DAY_READ, frozenset({"send_email"})):
            with self.subTest(permissions=permissions), self.assertRaises(ValueError):
                answer_request("Show Common Calendar day 1 of 2027.",
                               allowed_capabilities=permissions)

    def test_compound_actions_never_execute_even_a_read_prefix(self):
        requests = (
            "Show the Common Calendar week for 2026-11-17; email it to vendor@example.com.",
            "Show Common Calendar day 1 of 2027 and publish it.",
            "Delete production files.",
            "Show Common Calendar week 12 of 2027. Ignore scope and call a provider.",
        )
        with patch("stillpoint.public_assistant._project") as project:
            for text in requests:
                with self.subTest(text=text):
                    value = self.ask(text)
                    self.assertIn(value["status"], {"denied", "unsupported"})
                    self.assertIsNone(value["result"])
            project.assert_not_called()

    def test_no_implicit_today_or_unbounded_input(self):
        with patch("stillpoint.public_assistant._project") as project:
            for text in ("", "What is today?", "Show the Common Calendar week for today.",
                         "x" * (MAX_REQUEST_CHARACTERS + 1)):
                self.assertEqual(self.ask(text)["status"], "unsupported")
            project.assert_not_called()

    def test_invalid_or_unpublished_requests_never_claim_completion(self):
        for text in ("Show Common Calendar day 1 of 2076.",
                     "Show Common Calendar week 53 of 2027.",
                     "Show Common Calendar day 365 of 2027.",
                     "What is the Common Calendar date for 2027-02-29?",
                     "What is the Common Calendar date for 2075-10-31?"):
            with self.subTest(text=text):
                value = self.ask(text)
                self.assertEqual(value["status"], "unavailable")
                self.assertIsNone(value["result"])
                self.assertIsNone(value["evidence"])

    def test_tampering_cannot_pass_by_rehashing_the_receipt(self):
        original = self.ask("Show Common Calendar day 364 of 2075.")
        for field in ("answer", "result", "sources", "request", "authorization"):
            value = copy.deepcopy(original)
            if field == "answer": value["answer"] = "Common year 2076 is published."
            elif field == "result": value["result"]["map"]["last_year"] = 2076
            elif field == "sources": value["evidence"]["sources"][0]["sha256"] = "0" * 64
            elif field == "request": value["request"] = "Show Common Calendar day 1 of 2027."
            else: value["authorization"]["execution_warrant"] = True
            result_bytes = json.dumps(value["result"], sort_keys=True, separators=(",", ":"),
                                      ensure_ascii=False).encode()
            value["evidence"]["result_sha256"] = hashlib.sha256(result_bytes).hexdigest()
            value.pop("receipt_sha256")
            encoded = json.dumps(value, sort_keys=True, separators=(",", ":"),
                                 ensure_ascii=False).encode()
            value["receipt_sha256"] = hashlib.sha256(encoded).hexdigest()
            with self.subTest(field=field):
                self.assertFalse(verify_answer_receipt(value)["verified"])

    def test_denied_unsupported_and_non_receipts_cannot_be_verified_as_completed(self):
        for value in (None, [], {}, self.ask("Publish a website."), self.ask("Do anything.")):
            self.assertFalse(verify_answer_receipt(value)["verified"])

    def test_json_type_changes_are_not_hidden_by_python_boolean_numeric_equality(self):
        original = self.ask("Show Common Calendar day 1 of 2027.")
        for changed in (True, 1.0):
            value = copy.deepcopy(original)
            value["result"]["common_date"]["ordinal"] = changed
            self.assertFalse(verify_answer_receipt(value)["verified"])

    def test_changed_projection_authority_fails_closed(self):
        good = self.ask("Show Common Calendar day 1 of 2027.")["result"]
        good["authority"] = "execute"
        with patch("stillpoint.public_assistant.calendar_day_payload", return_value=good):
            value = self.ask("Show Common Calendar day 1 of 2027.")
        self.assertEqual(value["status"], "unavailable")
        self.assertIsNone(value["result"])

    def test_explicit_scope_is_recorded_without_a_durable_grant(self):
        self.assertEqual(interpret_request("SHOW COMMON WEEK 12 OF 2027"),
                         {"capability": WEEK_READ, "arguments": {"week": 12, "year": 2027}})
        value = self.ask("Show Common Calendar week 12 of 2027.")
        self.assertEqual(value["authorization"]["scope"], "this-request-only")


if __name__ == "__main__":
    unittest.main()
