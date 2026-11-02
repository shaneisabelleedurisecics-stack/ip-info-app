"""
Unit tests for ip_info_app.py

These tests use unittest.mock to fake the API responses, so they run
without an internet connection and never use up the API rate limit.

Run with:  python -m unittest test_ip_info_app.py -v
"""

import unittest
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
