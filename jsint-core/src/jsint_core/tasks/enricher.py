import asyncio
import uuid
from typing import Any, Dict, List, Optional

from celery import Task, states
from sqlalchemy.orm import Session

from jsint_core.utils import to_json_serializable
from jsint_enrichers import ENRICHER_REGISTRY, load_all_enrichers

from ..core.celery import celery
from ..core.enums import EventLevel
from ..core.logger import Logger
from ..core.models import Scan
from ..core.postgre_db import SessionLocal, get_db
from ..core.services import create_vault_service

# Auto-discover and register all enrichers
load_all_enrichers()

db: Session = next(get_db())


@celery.task(name="run_enricher", bind=True)
def run_enricher(
    self: Task,
    enricher_name: str,
    serialized_objects: List[dict],
    sketch_id: str | None,
    owner_id: Optional[str] = None,
    params: Optional[dict] = None,
) -> Dict[str, Any]:
    session = SessionLocal()

    try:
        scan_id = uuid.UUID(self.request.id)

        scan = Scan(
            id=scan_id,
            status=EventLevel.PENDING,
            sketch_id=uuid.UUID(sketch_id) if sketch_id else None,
        )
        session.add(scan)
        session.commit()

        # Create vault instance if owner_id is provided
        vault = None
        if owner_id:
            try:
                vault = create_vault_service(session).for_user(uuid.UUID(owner_id))
            except Exception as e:
                # Logger.error's signature omits None even though the column
                # it writes is nullable and a sketch-less scan is legal here.
                Logger.error(
                    sketch_id,  # type: ignore[arg-type]
                    {"message": f"Failed to create vault: {str(e)}"},
                )

        if not ENRICHER_REGISTRY.enricher_exists(enricher_name):
            raise ValueError(f"Enricher '{enricher_name}' not found in registry")

        enricher = ENRICHER_REGISTRY.get_enricher(
            name=enricher_name,
            sketch_id=sketch_id,
            scan_id=scan_id,
            vault=vault,
            params=params or {},
        )

        # Deserialize objects back into Pydantic models
        # The preprocess method in Enricher will handle these already-parsed objects
        results = asyncio.run(enricher.execute(values=serialized_objects))

        scan.status = EventLevel.COMPLETED
        scan.details = to_json_serializable(results)
        session.commit()

        return {"result": scan.details}

    except Exception as ex:
        session.rollback()
        error_logs = f"An error occurred: {str(ex)}"
        print(f"Error in task: {error_logs}")

        failed_scan = (
            session.query(Scan).filter(Scan.id == uuid.UUID(self.request.id)).first()
        )
        if failed_scan:
            failed_scan.status = EventLevel.FAILED
            # Scan.error is a legacy Column(), not Mapped[], so the stubs read
            # it as Column[str] rather than str.
            failed_scan.error = error_logs  # type: ignore[assignment]
            session.commit()

        self.update_state(state=states.FAILURE)
        raise ex

    finally:
        session.close()
