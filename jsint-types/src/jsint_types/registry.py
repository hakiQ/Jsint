"""
This module provides an automatic type registration system using decorators.
All JsintType subclasses can be decorated with @jsint_type to automatically
register themselves in the global TYPE_REGISTRY.

Auto-discovery is performed by calling load_all_types() which imports all modules
in the jsint_types package, triggering the @jsint_type decorators.
"""

import importlib
import pkgutil
import sys
from typing import Dict, Optional, Type, TypeVar

from .jsint_base import JsintType

T = TypeVar("T", bound=JsintType)


class TypeRegistry:
    """
    Global registry for Jsint types.

    Stores mappings:
    - Class name (e.g., "Domain") -> Class
    - Lowercase name (e.g., "domain") -> Class (for Neo4j compatibility)
    """

    def __init__(self):
        self._types: Dict[str, Type[JsintType]] = {}
        self._lowercase_types: Dict[str, Type[JsintType]] = {}

    def register(self, cls: Type[T]) -> Type[T]:
        """
        Register a type in the registry.

        Args:
            cls: The class to register

        Returns:
            The same class (for use as a decorator)
        """
        class_name = cls.__name__

        # Register with exact class name
        self._types[class_name] = cls

        # Register with lowercase name for Neo4j compatibility
        lowercase_name = class_name.lower()
        self._lowercase_types[lowercase_name] = cls

        return cls

    def get(self, type_name: str) -> Optional[Type[JsintType]]:
        """
        Get a type by its name (case-sensitive).

        Args:
            type_name: The type name (e.g., "Domain", "Ip")

        Returns:
            The corresponding class, or None if not found
        """
        return self._types.get(type_name)

    def get_lowercase(self, type_name: str) -> Optional[Type[JsintType]]:
        """
        Get a type by its lowercase name (for Neo4j compatibility).

        Args:
            type_name: The type name in lowercase (e.g., "domain", "ip")

        Returns:
            The corresponding class, or None if not found
        """
        return self._lowercase_types.get(type_name.lower())

    def all_types(self) -> Dict[str, Type[JsintType]]:
        """
        Get all registered types.

        Returns:
            Dictionary mapping class names to classes
        """
        return self._types.copy()

    def all_types_lowercase(self) -> Dict[str, Type[JsintType]]:
        """
        Get all registered types with lowercase keys.

        Returns:
            Dictionary mapping lowercase names to classes
        """
        return self._lowercase_types.copy()

    def clear(self):
        """Clear all registered types (mainly for testing)."""
        self._types.clear()
        self._lowercase_types.clear()


# Global type registry instance
TYPE_REGISTRY = TypeRegistry()


def jsint_type(cls: Type[T]) -> Type[T]:
    """
    Decorator to automatically register a JsintType subclass.

    Usage:
        @jsint_type
        class Domain(JsintType):
            domain: str
            ...

    This will automatically register the type in TYPE_REGISTRY with:
    - Key "Domain" -> Domain class
    - Key "domain" -> Domain class (lowercase for Neo4j)

    Args:
        cls: The class to register

    Returns:
        The same class (unmodified)
    """
    return TYPE_REGISTRY.register(cls)


def get_type(
    type_name: str, case_sensitive: bool = False
) -> Optional[Type[JsintType]]:
    """
    Convenience function to get a type from the global registry.

    Args:
        type_name: The type name to look up
        case_sensitive: If True, use exact case; if False, use lowercase lookup

    Returns:
        The corresponding class, or None if not found
    """
    if case_sensitive:
        return TYPE_REGISTRY.get(type_name)
    else:
        return TYPE_REGISTRY.get_lowercase(type_name)


# Auto-discovery cache
_types_loaded = False


def load_all_types() -> None:
    """
    Automatically discover and import all type modules in the jsint_types package.

    This function uses importlib to dynamically import all Python modules in the
    jsint_types package, which triggers the @jsint_type decorators and
    registers all types in TYPE_REGISTRY.

    Features:
    - Only imports modules once (cached via _types_loaded flag)
    - Ignores private modules (starting with _)
    - Only imports .py files
    - Uses pkgutil for high performance iteration

    This function is idempotent - calling it multiple times is safe and efficient.
    """
    global _types_loaded

    # Early return if already loaded
    if _types_loaded:
        return

    # Get the jsint_types package
    import jsint_types

    package = jsint_types
    package_path = package.__path__
    package_name = package.__name__

    # Iterate over all modules in the package
    for importer, modname, ispkg in pkgutil.iter_modules(
        package_path, prefix=f"{package_name}."
    ):
        # Skip private modules
        if modname.split(".")[-1].startswith("_"):
            continue

        # Skip if already imported
        if modname in sys.modules:
            continue

        # Import the module to trigger @jsint_type decorators
        try:
            importlib.import_module(modname)
        except Exception as e:
            # Log but don't fail - some modules might have optional dependencies
            print(f"Warning: Failed to import {modname}: {e}", file=sys.stderr)

    # Mark as loaded
    _types_loaded = True
