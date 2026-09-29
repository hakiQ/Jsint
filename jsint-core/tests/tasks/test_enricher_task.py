"""Tests that the enricher Celery tasks forward launch params downstream."""

import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest

from jsint_core.tasks import enricher as enricher_task


class RecordingEnricher:
    """Stands in for a real enricher: records nothing, executes to no results."""

    async def execute(self, values: List[dict]) -> List[Any]:
        return []


@pytest.fixture
def captured_kwargs(monkeypatch):
    """Neutralise the task's DB and vault work, capture the enricher kwargs."""
    monkeypatch.setattr(enricher_task, "SessionLocal", MagicMock())
    monkeypatch.setattr(enricher_task, "create_vault_service", MagicMock())

    captured: Dict[str, Any] = {}

    def fake_get_enricher(**kwargs):
        captured.update(kwargs)
        return RecordingEnricher()

    monkeypatch.setattr(
        enricher_task.ENRICHER_REGISTRY, "enricher_exists", lambda name: True
    )
    monkeypatch.setattr(
        enricher_task.ENRICHER_REGISTRY, "get_enricher", fake_get_enricher
    )
    return captured


def _run(**kwargs):
    return enricher_task.run_enricher.apply(
        args=["some_enricher", [], str(uuid.uuid4()), str(uuid.uuid4())],
        kwargs=kwargs,
        throw=True,
    )


def test_run_enricher_forwards_params_to_the_enricher(captured_kwargs):
    _run(params={"api_key": "abc123", "limit": "10"})

    assert captured_kwargs["params"] == {"api_key": "abc123", "limit": "10"}


def test_run_enricher_without_params_passes_an_empty_dict(captured_kwargs):
    # The shape of a message queued by an API instance that predates `params`.
    _run()

    assert captured_kwargs["params"] == {}
