"""Repository for Profile model."""

from typing import List, Optional

from ..models import Profile
from .base import BaseRepository


class ProfileRepository(BaseRepository[Profile]):
    model = Profile

    def get_by_email(self, email: str) -> Optional[Profile]:
        return self._db.query(Profile).filter(Profile.email == email).first()

    def count_all(self) -> int:
        return self._db.query(Profile).count()

    def list_ordered(self) -> List[Profile]:
        """All accounts, oldest first — the order an administrator expects."""
        return (
            self._db.query(Profile)
            .order_by(Profile.created_at.asc().nulls_last(), Profile.email.asc())
            .all()
        )
