"""Contract for the documentation browser: reading order and MDX handling."""

import uuid
from pathlib import Path

import pytest

from app.api.routes.docs import docs_root
from jsint_core.core.auth import create_access_token
from jsint_core.core.models import Profile

# The suite runs against a checkout/container that carries the docs folder; a
# stripped environment (no docs mounted) skips rather than fails.
pytestmark = pytest.mark.skipif(
    not docs_root().is_dir(), reason=f"docs/ not present at {docs_root()}"
)


@pytest.fixture
def reader(db_session):
    user = Profile(
        id=uuid.uuid4(),
        email="reader@example.com",
        hashed_password="x",
        status="active",
    )
    db_session.add(user)
    db_session.commit()
    return {"Authorization": f"Bearer {create_access_token({'sub': user.email})}"}


def test_table_of_contents_follows_the_book_order(client, reader):
    res = client.get("/api/docs", headers=reader)

    assert res.status_code == 200
    chapters = res.json()
    slugs = [c["slug"] for c in chapters]

    # Overview opens the book, and a category listed before "Developers" in
    # CATEGORY_ORDER really does sort before it.
    assert slugs[0] == "overview"
    assert slugs.index("getting-started/quickstart") < slugs.index(
        "developers/getting-started"
    )
    assert len(slugs) == len(set(slugs))
    assert {"slug", "title", "description", "category", "order"} <= set(chapters[0])


def test_chapter_body_is_markdown_with_the_frontmatter_stripped(client, reader):
    res = client.get("/api/docs/getting-started/flows", headers=reader)

    assert res.status_code == 200
    doc = res.json()
    assert doc["title"] == "Flows"
    assert doc["category"] == "Getting started"
    assert not doc["content"].startswith("---")
    assert "last_updated_at" not in doc["content"]
    assert "### What are Flows?" in doc["content"]


def test_alert_components_become_markdown_alerts(client, reader):
    """The MDX-only construct has to survive as something markdown can render."""
    content = client.get("/api/docs/overview", headers=reader).json()["content"]

    assert "<Alert" not in content
    assert "<AlertDescription>" not in content
    # Marker on its own line: markdown would otherwise fold it into the title
    # paragraph and the reader could not tell an alert from a plain quote.
    assert "> [!WARNING]\n>\n> **Disclaimer !**" in content


def test_unknown_chapter_is_not_found(client, reader):
    assert client.get("/api/docs/does-not-exist", headers=reader).status_code == 404


def test_docs_require_authentication(client):
    assert client.get("/api/docs").status_code == 401


def test_slug_never_reaches_the_filesystem(client, reader, tmp_path):
    """Only indexed slugs resolve, so a traversal-shaped slug is just unknown."""
    secret = tmp_path / "secret.md"
    secret.write_text("---\ntitle: Secret\n---\nshould not be served\n")

    res = client.get(f"/api/docs/{secret}", headers=reader)

    assert res.status_code in (404, 400)
    assert "should not be served" not in res.text


def test_docs_dir_override_is_honoured(monkeypatch, tmp_path):
    from app.api.routes import docs as docs_route

    book = tmp_path / "docs"
    chapter_dir = book / "getting-started"
    chapter_dir.mkdir(parents=True)
    (chapter_dir / "hello.mdx").write_text(
        "---\ntitle: Hello\ncategory: Getting started\norder: 1\n---\n\nBody text.\n"
    )

    monkeypatch.setenv("DOCS_DIR", str(book))
    docs_route._book.cache_clear()
    try:
        assert docs_route.docs_root() == Path(book)
        chapters, files = docs_route._book()
        assert [c.slug for c in chapters] == ["getting-started/hello"]
        assert files["getting-started/hello"].name == "hello.mdx"
        assert (
            docs_route._markdown_body((chapter_dir / "hello.mdx").read_text())
            == "Body text."
        )
    finally:
        docs_route._book.cache_clear()
