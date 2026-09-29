"""Apify platform tool.

Runs an Apify actor synchronously and returns the items of its default dataset.
Docs: https://docs.apify.com/api/v2/actor-run-sync-get-dataset-items-post
"""

from typing import Any, Dict, List, Optional
from urllib.parse import quote

import requests

from .base import Tool


class ApifyTool(Tool):
    """Generic runner for Apify actors (https://apify.com/store)."""

    base_url = "https://api.apify.com/v2"
    # A synchronous run waits up to 300s; Apify answers 408 when the run outlives
    # that window, so the HTTP timeout has to allow for it.
    sync_timeout_seconds = 300.0

    @classmethod
    def name(cls) -> str:
        return "apify"

    @classmethod
    def version(cls) -> str:
        return "1.0.0"

    @classmethod
    def description(cls) -> str:
        return (
            "Runs an Apify actor with the given input and returns the items of "
            "its default dataset."
        )

    @classmethod
    def category(cls) -> str:
        return "Automation"

    @staticmethod
    def normalize_actor_id(actor_id: str) -> str:
        """Apify REST paths take "owner~actor-name" while the console shows a slash."""
        return actor_id.strip().replace("/", "~")

    def build_run_url(self, actor_id: str) -> str:
        actor_path = quote(self.normalize_actor_id(actor_id), safe="~")
        return f"{self.base_url}/actors/{actor_path}/run-sync-get-dataset-items"

    def launch(
        self,
        actor_id: str,
        actor_input: Dict[str, Any],
        token: str,
        max_items: Optional[int] = None,
        timeout: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        params: Dict[str, Any] = {"format": "json"}
        if max_items is not None:
            params["maxItems"] = max_items

        try:
            response = requests.post(
                self.build_run_url(actor_id),
                params=params,
                json=actor_input,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Content-Type": "application/json",
                },
                timeout=timeout or self.sync_timeout_seconds,
            )
            response.raise_for_status()
        except requests.HTTPError as e:
            detail = getattr(e.response, "text", "")[:500]
            raise RuntimeError(
                f"Apify actor '{actor_id}' failed: {e}. {detail}"
            ) from e
        except requests.RequestException as e:
            raise RuntimeError(f"Apify request failed for '{actor_id}': {e}") from e

        items = response.json()
        if not isinstance(items, list):
            raise RuntimeError(
                "Apify returned "
                f"{type(items).__name__} instead of a dataset item list"
            )
        return items
