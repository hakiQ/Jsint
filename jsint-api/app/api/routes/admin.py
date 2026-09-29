"""Administrator endpoints: user management and registration approval."""

from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.api.schemas.admin import AdminUserCreate, AdminUserRead, AdminUserUpdate
from jsint_core.core.models import Profile
from jsint_core.core.postgre_db import get_db
from jsint_core.core.services import (
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
    create_admin_service,
)

router = APIRouter()


@router.get("/users", response_model=List[AdminUserRead])
def list_users(
    db: Session = Depends(get_db),
    current_admin: Profile = Depends(get_current_admin),
):
    """Every account, with how many cases each one owns."""
    return create_admin_service(db).list_users()


@router.post(
    "/users", response_model=AdminUserRead, status_code=status.HTTP_201_CREATED
)
def create_user(
    payload: AdminUserCreate,
    db: Session = Depends(get_db),
    current_admin: Profile = Depends(get_current_admin),
):
    """Create an account directly — admin-created accounts are pre-approved."""
    service = create_admin_service(db)
    try:
        return service.create_user(
            email=payload.email,
            password=payload.password,
            is_admin=payload.is_admin,
            status=payload.status,
        )
    except ConflictError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/users/{user_id}", response_model=AdminUserRead)
def update_user(
    user_id: UUID,
    payload: AdminUserUpdate,
    db: Session = Depends(get_db),
    current_admin: Profile = Depends(get_current_admin),
):
    """Approve/suspend an account, change its role, or reset its password."""
    service = create_admin_service(db)
    try:
        return service.update_user(
            actor_id=current_admin.id,
            user_id=user_id,
            is_admin=payload.is_admin,
            status=payload.status,
            password=payload.password,
        )
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_admin: Profile = Depends(get_current_admin),
):
    """Delete an account and everything it owns (cases, sketches, graph data)."""
    service = create_admin_service(db)
    try:
        service.delete_user(actor_id=current_admin.id, user_id=user_id)
    except NotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except PermissionDeniedError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
