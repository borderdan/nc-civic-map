import sys
import os
import pytest
import csv
from unittest.mock import patch, AsyncMock, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

from crawl_locale import CSVSink, bfs_crawl, sequential_id_walk

def test_csv_sink_append_and_flush(tmp_path):
    csv_file = tmp_path / "test_site_map.csv"
    sink = CSVSink(str(csv_file))

    # Append first record
    record1 = {"url": "https://example.com/1", "status_code": 200, "locale_id": "test"}
    sink.append(record1)

    # Should not write to file yet (buffer < 10 and time < 5s)
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) == 1 # Only header

    # Manually flush
    sink.flush()

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["url"] == "https://example.com/1"

    # Test deduplication
    sink.append(record1)
    sink.flush()

    with open(csv_file, "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        assert len(rows) == 1 # Still 1 row due to deduplication

@pytest.mark.asyncio
async def test_bfs_crawl():
    mock_sink = MagicMock()

    with patch("crawl_locale.AsyncWebCrawler") as mock_crawler_class:
        mock_crawler = AsyncMock()
        mock_crawler_class.return_value.__aenter__.return_value = mock_crawler

        # Setup mock result
        mock_result = MagicMock()
        mock_result.status_code = 200
        mock_result.html = "<html><body><a href='/DocumentCenter/View/123'>Doc</a></body></html>"
        mock_result.metadata = {"title": "Test Page"}

        mock_crawler.arun.return_value = mock_result

        # Call function
        with patch("crawl_locale.POLITE_DELAY_BFS", 0):
            with patch("crawl_locale.MAX_DEPTH", 0):  # To prevent deep crawling
                # Send a URL that includes /DocumentCenter/ to trigger the doccenter pattern
                # because the logic parses the visited URLs, not the content of the HTML body
                found_patterns = await bfs_crawl("https://example.com/DocumentCenter/view/123", mock_sink)

        assert found_patterns["doccenter"] is True
        assert found_patterns["civicalerts"] is False
        mock_sink.append.assert_called()
        mock_sink.flush.assert_called()

@pytest.mark.asyncio
async def test_sequential_id_walk():
    mock_sink = MagicMock()

    with patch("httpx.AsyncClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value.__aenter__.return_value = mock_client

        mock_resp_head = MagicMock()
        mock_resp_head.status_code = 200
        mock_client.head.return_value = mock_resp_head

        mock_resp_get = MagicMock()
        mock_resp_get.status_code = 200
        mock_resp_get.headers = {"Content-Type": "application/pdf"}
        mock_resp_get.content = b"PDF data"
        mock_client.get.return_value = mock_resp_get

        patterns = {"doccenter": True, "civicalerts": False, "calendar": False}

        # Limit max_id to 2 for faster test
        original_id_walks = {
            "doccenter": {
                "path": "/DocumentCenter/View/{id}",
                "max_id": 2,
                "delay": 0,
            }
        }

        with patch("crawl_locale.ID_WALKS", original_id_walks):
            await sequential_id_walk("https://example.com", patterns, mock_sink)

        # Should call head 2 times
        assert mock_client.head.call_count == 2
        # Should call get 2 times because both heads return 200
        assert mock_client.get.call_count == 2
        # Should append 2 records
        assert mock_sink.append.call_count == 2