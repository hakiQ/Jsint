from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class JsintType(BaseModel):
    """Base class for all Jsint entity types with nodeLabel support.
    nodeLabel is optional but computed at definition time.

    All classes that inherit from JsintType must be decorated with @jsint_type
    to be registered in the global TYPE_REGISTRY and accessed by their class name.

    Usage:
        from jsint_types.registry import jsint_type

        @jsint_type
        class Domain(JsintType):
            domain: str
    """

    nodeLabel: Optional[str] = Field(
        None,
        description="UI-readable label for this entity, the one used on the graph.",
        title="Label",
    )

    # Allow extra keys to support additional properties from the user
    model_config = ConfigDict(extra="allow")
