"""Documentation browser: serve the repository's ``docs/`` folder as a book.

The files are MDX written for Mintlify, but the only MDX constructs they use
are the frontmatter block and ``<Alert>`` callouts. Both are normalised here
so the frontend can render plain markdown instead of shipping an MDX
pipeline of its own.
"""

import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import yaml
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from jsint_core.core.models import Profile

router = APIRouter()

# Reading order of the book. A category missing from this list still shows up,
# sorted by name after the known ones, so adding a docs folder needs no code
# change here.
CATEGORY_ORDER = ("Overview", "Getting started", "Sources", "Developers")

_FRONTMATTER_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)
_ALERT_RE = re.compile(
    r"<Alert(?:\s+variant=\"(?P<variant>[A-Za-z]+)\")?\s*>(?P<body>.*?)</Alert>",
    re.DOTALL,
)
_ALERT_TITLE_RE = re.compile(r"<AlertTitle>(?P<title>.*?)</AlertTitle>", re.DOTALL)
_ALERT_DESCRIPTION_RE = re.compile(
    r"<AlertDescription>(?P<description>.*?)</AlertDescription>", re.DOTALL
)


class DocChapter(BaseModel):
    """A chapter as it appears in the table of contents."""

    slug: str
    title: str
    description: Optional[str] = None
    category: str
    order: int


class DocRead(DocChapter):
    """A chapter plus its markdown body."""

    content: str


def docs_root() -> Path:
    """Where the documentation lives.

    ``DOCS_DIR`` wins when set; otherwise the folder sits next to the
    application payload — ``/app/docs`` in the container, ``<checkout>/docs``
    when running from source, since both nest the routes package the same way.
    """
    configured = os.getenv("DOCS_DIR")
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[4] / "docs"


def _frontmatter(text: str) -> Tuple[Dict[str, object], str]:
    """Split a leading YAML block off the body; never raises on bad YAML."""
    match = _FRONTMATTER_RE.match(text)
    if not match:
        return {}, text

    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return meta, text[match.end() :]


def _alert_to_callout(match: "re.Match[str]") -> str:
    """Turn a Mintlify ``<Alert>`` into an admonition-style blockquote alert.

    The blank ``>`` after the marker matters: without it markdown folds the
    marker and the title into a single paragraph, and the renderer can no
    longer tell an alert apart from an ordinary quote.
    """
    variant = (match.group("variant") or "info").upper()
    body = match.group("body")
    quoted: List[str] = [f"> [!{variant}]", ">"]

    title = _ALERT_TITLE_RE.search(body)
    if title:
        quoted.append(f"> **{title.group('title').strip()}**")
        quoted.append(">")

    description = _ALERT_DESCRIPTION_RE.search(body)
    inner = description.group("description") if description else body
    quoted.extend(f"> {line}".rstrip() for line in inner.strip().splitlines())

    return "\n".join(quoted)


def _markdown_body(raw: str) -> str:
    """The chapter body a markdown renderer can display as-is."""
    _, body = _frontmatter(raw)
    return _ALERT_RE.sub(_alert_to_callout, body).strip()


def _chapter(path: Path, root: Path) -> DocChapter:
    meta, _ = _frontmatter(path.read_text(encoding="utf-8"))
    return DocChapter(
        slug=path.relative_to(root).with_suffix("").as_posix(),
        title=str(meta.get("title") or path.stem.replace("-", " ").title()),
        description=str(meta["description"]) if meta.get("description") else None,
        category=str(meta.get("category") or "Other"),
        order=int(meta.get("order") or 0),  # type: ignore[arg-type]
    )


def _sort_key(chapter: DocChapter) -> Tuple[int, int, str]:
    group = (
        CATEGORY_ORDER.index(chapter.category)
        if chapter.category in CATEGORY_ORDER
        else len(CATEGORY_ORDER)
    )
    return group, chapter.order, chapter.title


# Both halves are read-only after construction: callers must not mutate them.
@lru_cache(maxsize=1)
def _book() -> Tuple[Tuple[DocChapter, ...], Dict[str, Path]]:
    """The whole table of contents plus slug → file, read once per process."""
    root = docs_root()
    paths = sorted(root.rglob("*.mdx")) + sorted(root.rglob("*.md"))
    chapters: List[DocChapter] = []
    files: Dict[str, Path] = {}

    for path in paths:
        if any(part.startswith("_") for part in path.parts):
            continue
        chapter = _chapter(path, root)
        chapters.append(chapter)
        files[chapter.slug] = path

    chapters.sort(key=_sort_key)
    return tuple(chapters), files


@router.get("", response_model=List[DocChapter])
def list_docs(
    current_user: Profile = Depends(get_current_user),
) -> List[DocChapter]:
    """The table of contents, in reading order."""
    chapters, _ = _book()
    return list(chapters)


@router.get("/{slug:path}", response_model=DocRead)
def read_doc(slug: str, current_user: Profile = Depends(get_current_user)) -> DocRead:
    """One chapter, with its MDX normalised down to plain markdown.

    The slug is resolved against the index built from disk, so no request
    string ever reaches the filesystem — a traversal-shaped slug is simply an
    unknown chapter.
    """
    chapters, files = _book()
    wanted = slug.strip("/")
    path = files.get(wanted)
    if path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Unknown chapter '{slug}'"
        )

    chapter = next(chapter for chapter in chapters if chapter.slug == wanted)
    return DocRead(
        **chapter.model_dump(), content=_markdown_body(path.read_text(encoding="utf-8"))
    )
