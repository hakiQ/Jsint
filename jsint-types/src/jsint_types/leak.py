from typing import Dict, List, Optional, Self

from pydantic import Field, model_validator

from .jsint_base import JsintType
from .registry import jsint_type


@jsint_type
class Leak(JsintType):
    """Represents a data leak or breach with associated data."""

    name: str = Field(
        ...,
        description="The name of the leak or service brea",
        title="Leak Name",
        json_schema_extra={"primary": True},
    )
    leak: Optional[List[Dict]] = Field(
        None, description="List of data leaks found", title="Leak Data"
    )

    @model_validator(mode="after")
    def compute_label(self) -> Self:
        self.nodeLabel = self.name
        return self

    @classmethod
    def from_string(cls, line: str):
        """Parse a leak from a raw string."""
        return cls(name=line.strip())

    @classmethod
    def detect(cls, line: str) -> bool:
        """Leak cannot be reliably detected from a single line of text."""
        return False
