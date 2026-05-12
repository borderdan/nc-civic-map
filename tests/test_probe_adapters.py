import sys
import os
import httpx
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from probe_adapters import (
    probe_url,
    check_primary_domains,
    probe_legistar,
    probe_civicclerk,
    probe_weblink,
    probe_granicus_video,
    probe_boarddocs,
    probe_devnet
)

def test_probe_url_get_success():
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_instance.get.return_value = mock_response

        result = probe_url("https://example.com", method="GET")

        assert result.status_code == 200
        mock_instance.get.assert_called_once_with("https://example.com")

def test_probe_url_head_success():
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_instance.head.return_value = mock_response

        result = probe_url("https://example.com", method="HEAD")

        assert result.status_code == 200
        mock_instance.head.assert_called_once_with("https://example.com")

def test_probe_url_request_error():
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value
        mock_instance.get.side_effect = httpx.RequestError("Error")

        result = probe_url("https://example.com", method="GET")

        assert result is None

@patch("probe_adapters.polite_sleep", return_value=None)
def test_check_primary_domains(mock_sleep):
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value

        def mock_get(url):
            resp = MagicMock()
            if url == "https://charmeck.org":
                raise httpx.RequestError("Error")
            elif url == "https://mecknc.gov":
                resp.status_code = 200
                resp.url = url
                return resp
            elif url == "https://www.mecklenburgcountync.gov":
                resp.status_code = 404
                resp.url = url
                return resp
            elif url == "https://www.mecknc.gov":
                resp.status_code = 200
                resp.url = url
                return resp
            return resp

        mock_instance.get.side_effect = mock_get

        primary_domain, status, alt_domains = check_primary_domains()

        assert primary_domain == "https://mecknc.gov"
        assert status == 200
        assert alt_domains == ["https://www.mecknc.gov"]

@patch("probe_adapters.polite_sleep", return_value=None)
def test_probe_legistar(mock_sleep):
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value

        def mock_get(url):
            resp = MagicMock()
            if "mecklenburg" in url and "mecklenburgnc" not in url and "countync" not in url:
                resp.status_code = 200
                resp.json.return_value = [{"BodyName": "City Council"}]
            else:
                resp.status_code = 404
            return resp

        mock_instance.get.side_effect = mock_get

        result = probe_legistar()

        assert result["status"] == 200
        assert result["tenant_slug"] == "mecklenburg"
        assert result["verified_real"] is True
        assert result["bodies_count"] == 1

@patch("probe_adapters.polite_sleep", return_value=None)
def test_probe_civicclerk(mock_sleep):
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value

        def mock_get(url):
            resp = MagicMock()
            if "mecknc.api.civicclerk.com/v1/Events" in url:
                resp.status_code = 200
            elif "mecknc.api.civicclerk.com/v1/Bodies" in url:
                resp.status_code = 200
                resp.json.return_value = [{"id": 1, "name": "Council"}]
            else:
                resp.status_code = 404
            return resp

        mock_instance.get.side_effect = mock_get

        result = probe_civicclerk()

        assert result["status"] == 200
        assert result["tenant_slug"] == "mecknc"
        assert result["verified_real"] is True

@patch("probe_adapters.polite_sleep", return_value=None)
def test_probe_weblink(mock_sleep):
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value

        def mock_head(url):
            resp = MagicMock()
            if url == "https://records.mecknc.gov":
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        def mock_get(url):
            resp = MagicMock()
            resp.status_code = 404
            return resp

        mock_instance.head.side_effect = mock_head
        mock_instance.get.side_effect = mock_get

        result = probe_weblink()

        assert result["status"] == 200
        assert result["endpoint"] == "https://records.mecknc.gov"

@patch("probe_adapters.polite_sleep", return_value=None)
def test_probe_granicus_video(mock_sleep):
    with patch("httpx.Client") as mock_client:
        mock_instance = mock_client.return_value.__enter__.return_value

        def mock_head(url):
            resp = MagicMock()
            if url == "https://mecknc.granicus.com":
                resp.status_code = 200
            else:
                resp.status_code = 404
            return resp

        def mock_get(url):
            resp = MagicMock()
            resp.status_code = 404
            return resp

        mock_instance.head.side_effect = mock_head
        mock_instance.get.side_effect = mock_get

        result = probe_granicus_video()

        assert result["status"] == 200
        assert result["endpoint"] == "https://mecknc.granicus.com"