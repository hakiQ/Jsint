"""
Enricher service for managing enricher operations.
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.orm import Session

from ..models import Sketch
from ..repositories import (
    CustomTypeRepository,
    InvestigationRepository,
    SketchRepository,
)
from .base import BaseService
from .sketch_access import resolve_sketch_for_launch


class EnricherService(BaseService):
    """
    Service for enricher operations and listing.
    """

    def __init__(
        self,
        db: Session,
        custom_type_repo: CustomTypeRepository,
        sketch_repo: SketchRepository,
        investigation_repo: InvestigationRepository,
        **kwargs: Any,
    ):
        super().__init__(db, **kwargs)
        self._custom_type_repo = custom_type_repo
        self._sketch_repo = sketch_repo
        self._investigation_repo = investigation_repo

    def get_sketch_for_launch(self, sketch_id: str, user_id: UUID) -> Sketch:
        """Resolve the target sketch, denying anyone without update rights on
        its investigation. Launching an enricher writes nodes into the
        sketch, so it is an update."""
        return resolve_sketch_for_launch(
            self._sketch_repo, self._check_permission, sketch_id, user_id
        )

    # enricher_registry is jsint_enrichers' EnricherRegistry. That package
    # ships no py.typed marker, so naming the class would resolve to Any
    # anyway; saying Any avoids the cross-package import for no loss.
    def get_enrichers(
        self,
        category: Optional[str],
        user_id: UUID,
        enricher_registry: Any,
    ) -> List[Dict[str, Any]]:
        if not category or category.lower() == "undefined":
            all_enrichers: List[Dict[str, Any]] = enricher_registry.list(
                exclude=["n8n_connector"]
            )
            return all_enrichers

        custom_type = self._custom_type_repo.get_published_by_name_and_owner(
            category, user_id
        )

        if custom_type:
            return []

        by_input_type: List[Dict[str, Any]] = enricher_registry.list_by_input_type(
            category, exclude=["n8n_connector"]
        )
        return by_input_type


def create_enricher_service(db: Session) -> EnricherService:
    return EnricherService(
        db=db,
        custom_type_repo=CustomTypeRepository(db),
        sketch_repo=SketchRepository(db),
        investigation_repo=InvestigationRepository(db),
    )
