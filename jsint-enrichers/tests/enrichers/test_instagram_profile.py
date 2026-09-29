"""Instagram (Apify) enricher: registry wiring and dataset-item mapping."""

from jsint_enrichers import ENRICHER_REGISTRY
from jsint_enrichers.social.to_instagram_profile import InstagramProfileEnricher

PROFILE_ITEM = {
    "username": "nasa",
    "fullName": "NASA",
    "url": "https://www.instagram.com/nasa",
    "biography": "Exploring the universe and our home planet.",
    "profilePicUrl": "https://cdn.example/nasa.jpg",
    "followersCount": 96323377,
    "followsCount": 80,
    "postsCount": 4519,
    "verified": True,
    "private": False,
    "about": {"country": "United States", "date_joined": "August 2013"},
}


def test_enricher_is_registered_with_its_types():
    enricher = ENRICHER_REGISTRY.get_enricher("username_to_instagram_profile", "1", "1")

    assert enricher.name() == "username_to_instagram_profile"
    assert InstagramProfileEnricher.category() == "social"
    assert InstagramProfileEnricher.key() == "username"
    assert InstagramProfileEnricher.input_schema()["type"] == "Username"
    assert InstagramProfileEnricher.output_schema()["type"] == "SocialAccount"


def test_dataset_item_becomes_a_social_account():
    enricher = InstagramProfileEnricher(sketch_id="test")

    account = enricher._to_social_account("nasa", PROFILE_ITEM)

    assert account.username.value == "nasa"
    assert account.id == "nasa@instagram.com"
    assert account.display_name == "NASA"
    assert account.profile_url == "https://www.instagram.com/nasa"
    assert account.bio == PROFILE_ITEM["biography"]
    assert account.followers_count == 96323377
    assert account.following_count == 80
    assert account.posts_count == 4519
    assert account.verified is True
    assert account.is_private is False
    assert account.location == "United States"
    assert account.created_at == "August 2013"


def test_item_without_optional_fields_still_maps():
    enricher = InstagramProfileEnricher(sketch_id="test")

    account = enricher._to_social_account("@nasa", {"username": "@nasa"})

    assert account.username.value == "nasa"
    assert account.profile_url == "https://www.instagram.com/nasa"
    assert account.followers_count is None
    assert account.created_at is None


def test_non_object_items_are_dropped():
    enricher = InstagramProfileEnricher(sketch_id="test")

    assert enricher._to_social_account("nasa", "not-an-item") is None
