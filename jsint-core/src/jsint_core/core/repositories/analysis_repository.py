"""Repository for Analysis model."""

from typing import List, Optional
from uuid import UUID

from ..models import Analysis
from ..types import Role
from .base import BaseRepository


class AnalysisRepository(BaseRepository[Analysis]):
    model = Analysis

    def get_accessible_by_user(
        self, user_id: UUID, allowed_roles: Optional[List[Role]] = None
    ) -> List[Analysis]:
        inv_ids = self._get_accessible_investigation_ids(user_id, allowed_roles)
        if not inv_ids:
            return []

        # No DISTINCT: PostgreSQL has no equality operator for the `json` column
        # `analyses.content`, so SELECT DISTINCT over the full row fails with
        # "could not identify an equality operator for type json". It is also
        # redundant — inv_ids is a set of investigation ids and each analysis
        # belongs to exactly one investigation.
        return (
            self._db.query(Analysis)
            .filter(Analysis.investigation_id.in_(inv_ids))
            .all()
        )

    def get_by_investigation(self, investigation_id: UUID) -> List[Analysis]:
        return (
            self._db.query(Analysis)
            .filter(Analysis.investigation_id == investigation_id)
            .all()
        )

    def get_by_id_and_permission(
        self, analysis_id: UUID, user_id: UUID
    ) -> Optional[Analysis]:
        """Get an analysis if user has access via investigation roles."""
        analysis = self._db.query(Analysis).filter(Analysis.id == analysis_id).first()
        return analysis
