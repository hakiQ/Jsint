"""
Authentication service for user login and registration.

Accounts have a lifecycle: a new registration is created as ``pending`` and
cannot sign in until an administrator approves it (``active``). ``suspended``
accounts are blocked again. The first account on a fresh install — and every
address listed in ``ADMIN_EMAILS`` — is created as an active administrator so a
deployment can never lock itself out.
"""

import os
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..auth import create_access_token, get_password_hash, verify_password
from ..models import Profile
from ..repositories import ProfileRepository
from .base import BaseService
from .exceptions import (
    AccountPendingError,
    AccountSuspendedError,
    AuthenticationError,
    ConflictError,
)

ACTIVE = "active"
PENDING = "pending"
SUSPENDED = "suspended"


def configured_admin_emails() -> set[str]:
    """Addresses from ``ADMIN_EMAILS`` (comma separated) that are always admins."""
    raw = os.getenv("ADMIN_EMAILS", "")
    return {entry.strip().lower() for entry in raw.split(",") if entry.strip()}


class AuthService(BaseService):
    """
    Service for user authentication and registration.
    """

    def __init__(self, db: Session, profile_repo: ProfileRepository, **kwargs):
        super().__init__(db, **kwargs)
        self._profile_repo = profile_repo

    # --- helpers ---------------------------------------------------------

    @staticmethod
    def _normalize(email: str) -> str:
        return email.strip().lower()

    def _apply_configured_admin(self, user: Profile) -> None:
        """Promote/activate an account explicitly listed in ``ADMIN_EMAILS``.

        Runs on every sign-in so setting the variable on an existing deployment
        is enough to recover (or hand over) administrator access.
        """
        if user.email.lower() not in configured_admin_emails():
            return
        if user.is_admin and user.status == ACTIVE:
            return
        user.is_admin = True
        user.status = ACTIVE
        self._commit()
        self._refresh(user)

    def _user_payload(self, user: Profile) -> Dict[str, Any]:
        return {
            "id": str(user.id),
            "email": user.email,
            "username": user.email.split("@")[0],
            "first_name": user.first_name,
            "last_name": user.last_name,
            "avatar_url": user.avatar_url,
            "is_admin": bool(user.is_admin),
            "status": user.status,
        }

    # --- API -------------------------------------------------------------

    def authenticate(self, email: str, password: str) -> Dict[str, Any]:
        user = self._profile_repo.get_by_email(self._normalize(email))

        if not user or not verify_password(password, user.hashed_password):
            raise AuthenticationError("Incorrect email or password")

        self._apply_configured_admin(user)

        if user.status == PENDING:
            raise AccountPendingError(
                "Account pending approval by an administrator."
            )
        if user.status != ACTIVE:
            raise AccountSuspendedError("Account suspended by an administrator.")

        access_token = create_access_token(data={"sub": user.email})

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "user": self._user_payload(user),
        }

    def register(self, email: str, password: str) -> Dict[str, Any]:
        normalized = self._normalize(email)

        existing_user = self._profile_repo.get_by_email(normalized)

        if existing_user:
            raise ConflictError("Email already registered")

        # Only the very first account of an installation bootstraps itself —
        # "no administrators yet" would let any registration escalate while the
        # intended admin has not signed in yet.
        is_bootstrap = self._profile_repo.count_all() == 0
        is_admin = is_bootstrap or normalized in configured_admin_emails()
        status = ACTIVE if is_admin else PENDING

        hashed_password = get_password_hash(password)
        new_user = Profile(
            email=normalized,
            hashed_password=hashed_password,
            status=status,
            is_admin=is_admin,
        )

        try:
            self._profile_repo.add(new_user)
            self._commit()
            self._refresh(new_user)
        except IntegrityError:
            self._rollback()
            raise ConflictError("Email already registered")

        return {
            "message": (
                "Administrator account registered successfully"
                if is_admin
                else "User registered successfully, awaiting administrator approval"
            ),
            "email": new_user.email,
            "status": new_user.status,
            "is_admin": bool(new_user.is_admin),
        }


def create_auth_service(db: Session) -> AuthService:
    return AuthService(
        db=db,
        profile_repo=ProfileRepository(db),
    )


def create_auth_service_with_repo(
    db: Session, profile_repo: Optional[ProfileRepository] = None
) -> AuthService:
    """Factory used by tests that want to inject a repository."""
    return AuthService(db=db, profile_repo=profile_repo or ProfileRepository(db))
