"""
Unit tests for ip_info_app.py

These tests use unittest.mock to fake the API responses, so they run
without an internet connection and never use up the API rate limit.

Run with:  python -m unittest -v
These same tests run automatically on GitHub Actions for every push and
pull request (see .github/workflows/ci.yml). A pull request cannot be
merged into main unless every test passes.
"""

import csv
import io
import json
import socket
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import MagicMock, patch

import requests

import ip_info_app as app


def fake_response(json_data, status=200):
    """Build a fake requests.Response object for testing."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = json_data
    if status >= 400:
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError(str(status))
    return resp


class TestValidation(unittest.TestCase):
    """Tests for IP validation helpers."""

    def test_ipv4_version(self):
        self.assertEqual(app.get_ip_version("8.8.8.8"), 4)

    def test_ipv6_version(self):
        self.assertEqual(app.get_ip_version("2001:4860:4860::8888"), 6)

    def test_invalid_ip(self):
        self.assertIsNone(app.get_ip_version("999.1.1.1"))
        self.assertIsNone(app.get_ip_version("hello"))

    def test_private_ip_is_not_public(self):
        self.assertFalse(app.is_public_ip("192.168.1.10"))
        self.assertTrue(app.is_public_ip("8.8.8.8"))


class TestApiFunctions(unittest.TestCase):
    """Tests for the API functions using fake responses."""

    @patch("ip_info_app.requests.get")
    def test_get_public_ipv4(self, mock_get):
        mock_get.return_value = fake_response({"ip": "203.0.113.5"})
        self.assertEqual(app.get_public_ipv4(), "203.0.113.5")

    @patch("ip_info_app.requests.get")
    def test_get_public_ipv6_available(self, mock_get):
        mock_get.return_value = fake_response({"ip": "2001:db8::1"})
        self.assertEqual(app.get_public_ipv6(), "2001:db8::1")

    @patch("ip_info_app.requests.get")
    def test_get_public_ipv6_falls_back_to_none(self, mock_get):
        # api64 returns IPv4 when there is no IPv6 route
        mock_get.return_value = fake_response({"ip": "203.0.113.5"})
        self.assertIsNone(app.get_public_ipv6())

    @patch("ip_info_app.requests.get")
    def test_get_ip_details(self, mock_get):
        mock_get.return_value = fake_response(
            {"ip": "8.8.8.8", "org": "GOOGLE", "asn": "AS15169", "country_code": "US"})
        details = app.get_ip_details("8.8.8.8")
        self.assertEqual(details["asn"], "AS15169")

    @patch("ip_info_app.requests.get")
    def test_get_ip_details_api_error(self, mock_get):
        mock_get.return_value = fake_response({"error": True, "reason": "Reserved IP Address"})
        self.assertIsNone(app.get_ip_details("10.0.0.1"))

    @patch("ip_info_app.requests.get")
    def test_no_internet(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError()
        self.assertIsNone(app.get_public_ipv4())

    @patch("ip_info_app.requests.get")
    def test_timeout(self, mock_get):
        mock_get.side_effect = requests.exceptions.Timeout()
        self.assertIsNone(app.get_public_ipv4())

    @patch("ip_info_app.requests.get")
    def test_rate_limit(self, mock_get):
        mock_get.return_value = fake_response({}, status=429)
        self.assertIsNone(app.get_public_ipv4())


class TestDisplayHelpers(unittest.TestCase):
    """Tests for building table rows."""

    def test_build_details_rows_skips_empty(self):
        rows = app.build_details_rows({"ip": "8.8.8.8", "city": "", "asn": "AS15169"})
        labels = [row[0] for row in rows]
        self.assertIn("IP Address", labels)
        self.assertIn("ASN", labels)
        self.assertNotIn("City", labels)


# ---------------------------------------------------------------------------
# Tests for the new v2.0 features (Project Activity 4)
# ---------------------------------------------------------------------------
SAMPLE_REPORT = {
    "generated_at": "2026-11-11T21:00:00",
    "public_ipv4": "203.0.113.5",
    "public_ipv6": None,
    "hostname": "host.example.net",
    "details": {"ip": "203.0.113.5", "org": "Example ISP", "asn": "AS64500",
                "city": "Manila", "country_name": "Philippines"},
}


class TestReverseDns(unittest.TestCase):
    """Feature 1: reverse DNS lookup (hostname behind an IP)."""

    @patch("ip_info_app.socket.gethostbyaddr")
    def test_hostname_found(self, mock_dns):
        mock_dns.return_value = ("dns.google", [], ["8.8.8.8"])
        self.assertEqual(app.get_hostname("8.8.8.8"), "dns.google")

    @patch("ip_info_app.socket.gethostbyaddr")
    def test_hostname_not_found_returns_none(self, mock_dns):
        mock_dns.side_effect = socket.herror("Unknown host")
        self.assertIsNone(app.get_hostname("203.0.113.5"))

    @patch("ip_info_app.socket.gethostbyaddr")
    def test_empty_ip_skips_lookup(self, mock_dns):
        self.assertIsNone(app.get_hostname(""))
        mock_dns.assert_not_called()


class TestCsvExport(unittest.TestCase):
    """Feature 2: saving reports as CSV (and JSON)."""

    def test_report_to_rows_includes_hostname_and_details(self):
        rows = dict(app.report_to_rows(SAMPLE_REPORT))
        self.assertEqual(rows["Public IPv4"], "203.0.113.5")
        self.assertEqual(rows["Public IPv6"], "Not available")
        self.assertEqual(rows["Hostname"], "host.example.net")
        self.assertEqual(rows["ASN"], "AS64500")

    def test_write_csv_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = app.write_report(SAMPLE_REPORT, "csv", folder)
            self.assertTrue(path.endswith(".csv"))
            with open(path, encoding="utf-8-sig", newline="") as file:
                rows = list(csv.reader(file))
            self.assertEqual(rows[0], ["Field", "Value"])
            self.assertIn(["City", "Manila"], rows)

    def test_write_json_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = app.write_report(SAMPLE_REPORT, "json", folder)
            with open(path, encoding="utf-8") as file:
                self.assertEqual(json.load(file)["hostname"], "host.example.net")

    def test_unknown_format_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(ValueError):
                app.write_report(SAMPLE_REPORT, "xml", folder)


class TestCommandLine(unittest.TestCase):
    """Feature 3: command-line arguments."""

    def test_no_arguments_opens_menu(self):
        args = app.parse_args([])
        self.assertFalse(app.run_cli(args))

    def test_lookup_argument(self):
        args = app.parse_args(["--lookup", "8.8.8.8"])
        self.assertEqual(args.lookup, "8.8.8.8")

    def test_save_accepts_csv(self):
        self.assertEqual(app.parse_args(["--save", "csv"]).save, "csv")

    def test_save_rejects_unknown_format(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            app.parse_args(["--save", "xml"])

    def test_only_one_option_at_a_time(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            app.parse_args(["--ipv4", "--ipv6"])

    @patch("ip_info_app.show_ipv4")
    def test_ipv4_argument_runs_ipv4(self, mock_show):
        self.assertTrue(app.run_cli(app.parse_args(["--ipv4"])))
        mock_show.assert_called_once()


class TestLookupValidation(unittest.TestCase):
    """Bad input must be rejected before any API call is made."""

    @patch("ip_info_app.get_ip_details")
    def test_invalid_ip_never_calls_api(self, mock_details):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(app.show_ip_lookup("hello"))
        mock_details.assert_not_called()

    @patch("ip_info_app.get_ip_details")
    def test_private_ip_never_calls_api(self, mock_details):
        with redirect_stdout(io.StringIO()):
            self.assertFalse(app.show_ip_lookup("192.168.1.1"))
        mock_details.assert_not_called()

    @patch("ip_info_app.get_hostname", return_value="dns.google")
    @patch("ip_info_app.get_ip_details", return_value={"ip": "8.8.8.8", "org": "GOOGLE"})
    def test_public_ip_shows_hostname(self, mock_details, mock_dns):
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertTrue(app.show_ip_lookup("8.8.8.8"))
        self.assertIn("dns.google", out.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
