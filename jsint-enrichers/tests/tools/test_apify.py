"""Apify tool: actor id handling, request shape and error surfaces."""

from unittest.mock import Mock

import pytest
import requests

from tools.apify import ApifyTool


def test_actor_id_accepts_console_and_api_forms():
    assert (
        ApifyTool.normalize_actor_id("apify/instagram-profile-scraper")
        == "apify~instagram-profile-scraper"
    )
    assert (
        ApifyTool.normalize_actor_id("apify~instagram-profile-scraper")
        == "apify~instagram-profile-scraper"
    )


def test_run_url_targets_the_sync_dataset_endpoint():
    assert ApifyTool().build_run_url("apify/instagram-profile-scraper") == (
        "https://api.apify.com/v2/actors/"
        "apify~instagram-profile-scraper/run-sync-get-dataset-items"
    )


def _stub_response(payload, text=""):
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = payload
    response.text = text
    return response


def test_launch_sends_bearer_token_and_actor_input(monkeypatch):
    captured = {}

    def fake_post(url, params=None, json=None, headers=None, timeout=None):
        captured.update(
            url=url, params=params, json=json, headers=headers, timeout=timeout
        )
        return _stub_response([{"username": "nasa"}])

    monkeypatch.setattr(requests, "post", fake_post)

    items = ApifyTool().launch(
        "apify/instagram-profile-scraper",
        {"usernames": ["nasa"]},
        token="secret",
        max_items=1,
    )

    assert items == [{"username": "nasa"}]
    assert captured["url"] == (
        "https://api.apify.com/v2/actors/"
        "apify~instagram-profile-scraper/run-sync-get-dataset-items"
    )
    assert captured["headers"]["Authorization"] == "Bearer secret"
    assert captured["params"] == {"format": "json", "maxItems": 1}
    assert captured["json"] == {"usernames": ["nasa"]}
    assert captured["timeout"] == ApifyTool.sync_timeout_seconds


def test_launch_rejects_a_non_list_dataset(monkeypatch):
    monkeypatch.setattr(
        requests, "post", lambda *a, **kw: _stub_response({"error": "bad-run"})
    )

    with pytest.raises(RuntimeError, match="dataset item list"):
        ApifyTool().launch("apify/instagram-profile-scraper", {}, token="secret")


def test_launch_reports_http_errors_with_actor_and_body(monkeypatch):
    response = _stub_response(
        {"error": {"type": "invalid-token"}}, text='{"error":{"type":"invalid-token"}}'
    )
    response.raise_for_status.side_effect = requests.HTTPError(
        "401 Client Error", response=response
    )
    monkeypatch.setattr(requests, "post", lambda *a, **kw: response)

    with pytest.raises(RuntimeError, match="invalid-token"):
        ApifyTool().launch("apify/instagram-profile-scraper", {}, token="bad")


def test_launch_reports_transport_failures(monkeypatch):
    def raise_timeout(*args, **kwargs):
        raise requests.Timeout("read timed out")

    monkeypatch.setattr(requests, "post", raise_timeout)

    with pytest.raises(RuntimeError, match="Apify request failed"):
        ApifyTool().launch("apify/instagram-profile-scraper", {}, token="secret")
