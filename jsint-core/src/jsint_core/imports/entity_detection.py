"""
Entity type detection utilities for import feature.
Provides basic pattern matching for common entity types.
"""

from typing import Optional, Type

from jsint_types import TYPE_REGISTRY, JsintType


def detect_type(value: str) -> Optional[Type[JsintType]]:
    """Detect entity type from a string value using built-in type patterns.

    Note: This only checks built-in types (TYPE_REGISTRY) since custom types
    don't have detect() methods. For custom type resolution by name, use
    TypeRegistryService.resolve_type().
    """
    for model in TYPE_REGISTRY.all_types().values():
        if hasattr(model, "detect") and model.detect(value):
            return model
    return None
