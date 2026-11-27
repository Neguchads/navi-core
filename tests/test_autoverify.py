import hashlib
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from navi_core import autoverify as av

SHA = "a" * 64
NOW = 1800000000


def sample(**stats):
    return {"data": {"id": SHA, "type": "file", "attributes": {
        "sha256": SHA, "last_analysis_date": NOW - 100,
        "last_analysis_stats": {"malicious": 0, "suspicious": 0,
                                "undetected": 70, "harmless": 0, **stats}}}}


class AutoVerifyTests(unittest.TestCase):
    def test_statuses(self):
        for changes, status in [
            ({}, "no-detections-reported"),
            ({"malicious": 1}, "review-required"),
            ({"suspicious": 1}, "review-required"),
            ({"undetected": 0}, "inconclusive"),
            ({"timeout": 1}, "inconclusive"),
            ({"unexpected": 1}, "inconclusive"),
            ({"malicious": True}, "invalid-response"),
            ({"harmless": -1}, "invalid-response"),
        ]:
            with self.subTest(changes=changes):
                self.assertEqual(av.classify(sample(**changes), SHA, NOW)["status"], status)

    def test_stale_and_identity(self):
        p = sample()
        p["data"]["attributes"]["last_analysis_date"] = NOW - av.MAX_AGE - 1
        self.assertEqual(av.classify(p, SHA, NOW)["status"], "stale")
        self.assertEqual(av.classify(p, "b" * 64, NOW)["status"], "integrity-mismatch")
        self.assertEqual(av.classify({}, SHA, NOW)["status"], "invalid-response")

    def test_lookup_http(self):
        opener = Mock()
        response = opener.open.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = json.dumps(sample()).encode()
        self.assertEqual(av.lookup(SHA, "test-key", opener, NOW)["status"], "no-detections-reported")
        req = opener.open.call_args.args[0]
        self.assertEqual(req.full_url, av.BASE + SHA)
        self.assertEqual(req.get_method(), "GET")
        self.assertIsNone(req.data)
        self.assertEqual(req.get_header("X-apikey"), "test-key")
        opener.open.assert_called_once()

    def test_errors_no_retry(self):
        for code, status in [(404, "unknown-hash"), (429, "quota-exceeded"),
                             (401, "auth-error"), (302, "http-error"), (503, "http-error")]:
            opener = Mock()
            opener.open.side_effect = HTTPError(av.BASE, code, "error", {}, io.BytesIO(b"private"))
            self.assertEqual(av.lookup(SHA, "test-key", opener)["status"], status)
            opener.open.assert_called_once()
        opener = Mock()
        opener.open.side_effect = URLError("sensitive detail")
        self.assertEqual(av.lookup(SHA, "test-key", opener), {"status": "network-error"})

    def test_bad_payload_and_missing_key(self):
        opener = Mock()
        response = opener.open.return_value.__enter__.return_value
        response.status = 200
        response.read.return_value = b"not JSON"
        self.assertEqual(av.lookup(SHA, "test-key", opener)["status"], "invalid-response")
        response.read.return_value = b"x" * (av.MAX_RESPONSE + 1)
        self.assertEqual(av.lookup(SHA, "test-key", opener)["status"], "invalid-response")
        opener.reset_mock()
        self.assertEqual(av.lookup(SHA, "", opener)["status"], "missing-or-invalid-key")
        opener.open.assert_not_called()

    def test_default_offline_and_mismatch(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sample.exe"
            path.write_bytes(b"fixture")
            expected = hashlib.sha256(b"fixture").hexdigest()
            with patch.object(av, "lookup") as lookup, redirect_stdout(io.StringIO()) as out:
                self.assertEqual(av.main([str(path)]), 2)
                report = json.loads(out.getvalue())
                self.assertEqual(report["status"], "local-hash-only")
                self.assertEqual(report["sha256"], expected)
                self.assertFalse(report["upload"])
                lookup.assert_not_called()
            with patch.object(av, "lookup") as lookup, redirect_stdout(io.StringIO()):
                self.assertEqual(av.main([str(path), "--expected-sha256", SHA,
                                          "--lookup-public-noncommercial"]), 2)
                lookup.assert_not_called()
            bad = Path(root) / "game.nds"
            bad.write_bytes(b"fixture")
            with self.assertRaises(ValueError):
                av.fingerprint(bad)

    def test_redirect_refused(self):
        self.assertIsNone(av.NoRedirect().redirect_request(None, None, 302, "", {}, "https://example.org"))

    def test_explicit_lookup_exit_codes(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "sample.exe"
            path.write_bytes(b"fixture")
            for status, code in [("no-detections-reported", 0), ("unknown-hash", 2),
                                 ("review-required", 2), ("quota-exceeded", 2)]:
                with patch.object(av, "lookup", return_value={"status": status}), redirect_stdout(io.StringIO()):
                    self.assertEqual(av.main([str(path), "--lookup-public-noncommercial"]), code)


if __name__ == "__main__":
    unittest.main()
