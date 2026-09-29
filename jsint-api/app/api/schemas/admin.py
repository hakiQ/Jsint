"""Schemas for the administrator user-management endpoints."""

from datetime import datetime
from typing import Literal, Optional

from pydantic import UUID4, BaseModel, EmailStr, Field

AccountStatus = Literal["pending", "active", "suspended"]


class AdminUserRead(BaseModel):
    """A user row as shown in the admin dashboard."""

    id: UUID4
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    status: str
    is_admin: bool
    created_at: Optional[datetime] = None
    # Case counts for this user.
    investigations: int = 0
    sketches: int = 0
    analyses: int = 0


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    is_admin: bool = False
    status: AccountStatus = "active"


class AdminUserUpdate(BaseModel):
    """Partial update: role, account status and/or password reset."""

    is_admin: Optional[bool] = None
    status: Optional[AccountStatus] = None
    password: Optional[str] = Field(default=None, min_length=6, max_length=128)
