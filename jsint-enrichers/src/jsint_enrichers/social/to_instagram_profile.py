"""Instagram public-profile enrichment through an Apify actor.

Pivots a Username to the SocialAccount of its public Instagram profile. The
dataset is produced by an Apify actor (default: apify/instagram-profile-scraper,
see https://apify.com/apify/instagram-profile-scraper) because Instagram offers
no unauthenticated public API.
"""

import os
from typing import Any, Dict, List, Optional

from jsint_core.core.enricher_base import Enricher
from jsint_core.core.logger import Logger
from jsint_enrichers.registry import jsint_enricher
from jsint_types import SocialAccount, Username
from tools.apify import ApifyTool

DEFAULT_ACTOR_ID = "apify/instagram-profile-scraper"
INSTAGRAM_PLATFORM = "instagram.com"


@jsint_enricher
class InstagramProfileEnricher(Enricher):
    """[APIFY] Instagram public profile details for a username."""

    InputType = Username
    OutputType = SocialAccount

    def __init__(
        self,
        sketch_id: Optional[str] = None,
        scan_id: Optional[str] = None,
        vault: Any = None,
        params: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            sketch_id=sketch_id,
            scan_id=scan_id,
            params_schema=self.get_params_schema(),
            vault=vault,
            params=params,
        )

    @classmethod
    def get_params_schema(cls) -> List[Dict[str, Any]]:
        """Declare the parameters this enricher accepts."""
        return [
            {
                "name": "APIFY_API_TOKEN",
                "type": "vaultSecret",
                "description": (
                    "Apify API token (console.apify.com → Settings → Integrations). "
                    "Actor runs are billed on your Apify account."
                ),
                "required": True,
            },
            {
                "name": "apify_actor_id",
                "type": "string",
                "description": "Apify actor used for the lookup.",
                "default": DEFAULT_ACTOR_ID,
            },
            {
                "name": "include_about_section",
                "type": "string",
                "description": (
                    "Set to 'true' to request the actor's paid About section "
                    "(join date, country, username changes)."
                ),
                "default": "false",
            },
        ]

    @classmethod
    def name(cls) -> str:
        return "username_to_instagram_profile"

    @classmethod
    def category(cls) -> str:
        return "social"

    @classmethod
    def key(cls) -> str:
        return "username"

    def _to_social_account(
        self, handle: str, item: Dict[str, Any]
    ) -> Optional[SocialAccount]:
        """Map one actor dataset item to a SocialAccount node."""
        if not isinstance(item, dict):
            return None

        about = item.get("about") or {}
        if not isinstance(about, dict):
            about = {}

        username = item.get("username") or handle
        try:
            return SocialAccount(
                username=Username(value=str(username).lstrip("@"), platform="instagram"),
                display_name=item.get("fullName"),
                profile_url=item.get("url") or f"https://www.instagram.com/{handle}",
                profile_picture_url=item.get("profilePicUrl"),
                bio=item.get("biography"),
                location=about.get("country"),
                created_at=about.get("date_joined"),
                followers_count=item.get("followersCount"),
                following_count=item.get("followsCount"),
                posts_count=item.get("postsCount"),
                verified=item.get("verified"),
                is_private=item.get("private"),
                platform=INSTAGRAM_PLATFORM,
            )
        except Exception as e:
            Logger.error(
                self.sketch_id,
                {"message": f"[APIFY] Could not map Instagram profile '{handle}': {e}"},
            )
            return None

    async def scan(self, data: List[InputType]) -> List[OutputType]:
        results: List[OutputType] = []

        token = self.get_secret("APIFY_API_TOKEN", os.getenv("APIFY_API_TOKEN"))
        if not token:
            Logger.error(
                self.sketch_id,
                {
                    "message": (
                        "[APIFY] Missing APIFY_API_TOKEN. Add it to the vault "
                        "(or set the environment variable) to run actor lookups."
                    )
                },
            )
            return results

        actor_id = self.get_params().get("apify_actor_id") or DEFAULT_ACTOR_ID
        include_about = (
            str(self.get_params().get("include_about_section", "false")).lower()
            == "true"
        )
        tool = ApifyTool()

        for username in data:
            handle = username.value.lstrip("@")
            try:
                items = tool.launch(
                    actor_id=actor_id,
                    actor_input={
                        "usernames": [handle],
                        "includeAboutSection": include_about,
                    },
                    token=token,
                    max_items=1,
                )
            except Exception as e:
                Logger.error(
                    self.sketch_id,
                    {
                        "message": f"[APIFY] Instagram lookup failed for {handle}: {e}"
                    },
                )
                continue

            if not items:
                Logger.info(
                    self.sketch_id,
                    {"message": f"[APIFY] No Instagram profile returned for {handle}."},
                )
                continue

            for item in items:
                account = self._to_social_account(handle, item)
                if account is not None:
                    results.append(account)

        return results

    def postprocess(
        self, results: List[OutputType], original_input: List[InputType]
    ) -> List[OutputType]:
        """Create the username, account and relationship nodes."""
        if not self._graph_service:
            return results

        for account in results:
            try:
                if account.username:
                    self.create_node(account.username)
                    self.create_node(account)
                    self.create_relationship(
                        account.username, account, "HAS_SOCIAL_ACCOUNT"
                    )
                    self.log_graph_message(
                        f"{account.username.value} -> {account.followers_count} "
                        "followers on Instagram"
                    )
            except Exception as e:
                Logger.error(
                    self.sketch_id,
                    {
                        "message": f"[APIFY] Failed to create graph nodes for "
                        f"{account.username}: {e}"
                    },
                )
                continue

        return results


# Make types available at module level for easy access
InputType = InstagramProfileEnricher.InputType
OutputType = InstagramProfileEnricher.OutputType
