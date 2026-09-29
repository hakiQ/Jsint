"""Administrator service: user management for the admin dashboard.

Only reachable through the ``/api/admin`` routes, which require an account with
``is_admin`` set. Every destructive action guards against locking the
deployment out (no self-demotion, no removing the last administrator).
"""

from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import get_password_hash
from ..graph import create_graph_service
from ..logger import Logger
from ..models import Analysis, Feedback, Investigation, Profile, Sketch
from ..repositories import ProfileRepository
from .base import BaseService
from .exceptions import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

VALID_STATUSES = ("pending", "active", "suspended")


class AdminService(BaseService):
    """User administration: listing, creation, roles, approval and deletion."""

    def __init__(self, db: Session, profile_repo: ProfileRepository, **kwargs):
        super().__init__(db, **kwargs)
        self._profile_repo = profile_repo

    # --- helpers ---------------------------------------------------------

    def _counts_by_owner(self, model) -> Dict[Any, int]:
        rows = (
            self._db.query(model.owner_id, func.count(model.id))
            .group_by(model.owner_id)
            .all()
        )
        return {owner_id: count for owner_id, count in rows if owner_id is not None}

    def _serialize(
        self,
        user: Profile,
        investigations: Dict[Any, int],
        sketches: Dict[Any, int],
        analyses: Dict[Any, int],
    ) -> Dict[str, Any]:
        return {
            "id": user.id,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "status": user.status,
            "is_admin": bool(user.is_admin),
            "created_at": user.created_at,
            "investigations": investigations.get(user.id, 0),
            "sketches": sketches.get(user.id, 0),
            "analyses": analyses.get(user.id, 0),
        }

    def _get_profile(self, user_id: UUID) -> Profile:
        user = self._profile_repo.get_by_id(user_id)
        if not user:
            raise NotFoundError("User not found")
        return user

    def _assert_not_last_admin(self, user: Profile, message: str) -> None:
        if not user.is_admin:
            return
        remaining = (
            self._db.query(Profile)
            .filter(Profile.is_admin.is_(True), Profile.id != user.id)
            .count()
        )
        if remaining == 0:
            raise ValidationError(message)

    # --- API -------------------------------------------------------------

    def list_users(self) -> List[Dict[str, Any]]:
        investigations = self._counts_by_owner(Investigation)
        sketches = self._counts_by_owner(Sketch)
        analyses = self._counts_by_owner(Analysis)

        return [
            self._serialize(user, investigations, sketches, analyses)
            for user in self._profile_repo.list_ordered()
        ]

    def create_user(
        self,
        email: str,
        password: str,
        is_admin: bool = False,
        status: str = "active",
    ) -> Dict[str, Any]:
        normalized = email.strip().lower()
        if status not in VALID_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Expected one of: {', '.join(VALID_STATUSES)}"
            )
        if self._profile_repo.get_by_email(normalized):
            raise ConflictError("Email already registered")

        user = Profile(
            email=normalized,
            hashed_password=get_password_hash(password),
            status=status,
            is_admin=is_admin,
        )
        try:
            self._profile_repo.add(user)
            self._commit()
            self._refresh(user)
        except IntegrityError:
            self._rollback()
            raise ConflictError("Email already registered")

        return self._serialize(user, {}, {}, {})

    def update_user(
        self,
        actor_id: UUID,
        user_id: UUID,
        is_admin: Optional[bool] = None,
        status: Optional[str] = None,
        password: Optional[str] = None,
    ) -> Dict[str, Any]:
        user = self._get_profile(user_id)

        if status is not None and status not in VALID_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Expected one of: {', '.join(VALID_STATUSES)}"
            )

        changes_role = is_admin is not None and bool(is_admin) != bool(user.is_admin)
        changes_status = status is not None and status != user.status

        if user.id == actor_id and (changes_role or changes_status):
            raise PermissionDeniedError(
                "You cannot change your own role or account status"
            )

        if changes_role and not is_admin:
            self._assert_not_last_admin(
                user, "Cannot remove administrator rights from the last administrator"
            )
        if changes_status and status != "active":
            self._assert_not_last_admin(
                user, "Cannot deactivate the last administrator"
            )

        if is_admin is not None:
            user.is_admin = is_admin
        if status is not None:
            user.status = status
        if password:
            user.hashed_password = get_password_hash(password)

        self._commit()
        self._refresh(user)
        return self._serialize(user, {}, {}, {})

    def delete_user(self, actor_id: UUID, user_id: UUID) -> None:
        user = self._get_profile(user_id)

        if user.id == actor_id:
            raise PermissionDeniedError("You cannot delete your own account")
        self._assert_not_last_admin(user, "Cannot delete the last administrator")

        # Graph nodes live in Neo4j, outside the PostgreSQL cascades, so they are
        # soft-deleted explicitly for every sketch the account can reach.
        owned_investigations = self._db.query(Investigation.id).filter(
            Investigation.owner_id == user.id
        )
        sketch_ids = [
            row[0]
            for row in self._db.query(Sketch.id)
            .filter(
                (Sketch.owner_id == user.id)
                | (Sketch.investigation_id.in_(owned_investigations))
            )
            .all()
        ]
        for sketch_id in sketch_ids:
            try:
                create_graph_service(
                    sketch_id=str(sketch_id), enable_batching=False
                ).delete_all_sketch_nodes()
            except Exception as e:
                Logger.warn(
                    str(sketch_id),
                    {
                        "message": f"[ADMIN] Graph cleanup failed for sketch "
                        f"{sketch_id}: {e}"
                    },
                )

        # feedbacks has no ON DELETE rule, so clear it before the profile row.
        self._db.query(Feedback).filter(Feedback.owner_id == user.id).delete()

        self._db.delete(user)
        self._commit()


def create_admin_service(db: Session) -> AdminService:
    return AdminService(db=db, profile_repo=ProfileRepository(db))
