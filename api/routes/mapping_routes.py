from __future__ import annotations

from fastapi import APIRouter

from api.schemas.mapping_schema import (
    MappingBulkCreateRequest,
    MappingCreateRequest,
    MappingUpdateRequest,
)
from live.repository.mapping_repository import MappingRepository
from services.mapping_validation_service import (
    MappingValidationError,
    MappingValidationService,
)


router = APIRouter(prefix="/mapping", tags=["Mapping"])

repo = MappingRepository()
validator = MappingValidationService()


@router.get("/test")
def test():
    return {"status": "mapping route working"}


@router.get("/")
def get_all_mappings():
    return repo.get_all()


@router.get("/group/{signal}/{regime}")
def get_mapping_group(signal: str, regime: str, active_only: bool = False):
    rows = repo.get_group(signal=signal, regime=regime, active_only=active_only)
    return {
        "signal": signal,
        "regime": regime,
        "count": len(rows),
        "rows": rows,
    }


@router.post("/")
def create_mapping(request: MappingCreateRequest):
    try:
        data = request.dict()
        validator.validate_create(data)

        mapping_id = repo.create_mapping(data)

        return {
            "status": "created",
            "id": mapping_id,
        }

    except MappingValidationError as e:
        return {
            "status": "error",
            "message": "validation_failed",
            "details": e.errors,
        }


@router.post("/bulk")
def create_mapping_bulk(request: MappingBulkCreateRequest):
    try:
        normalized_rows = []
        for row in request.rows:
            row_data = row.dict()

            row_data["signal"] = request.signal
            row_data["regime"] = request.regime

            normalized_rows.append(row_data)

        validator.validate_bulk(normalized_rows)

        deactivated_count = repo.deactivate_group(
            signal=request.signal,
            regime=request.regime,
        )

        inserted_ids = repo.create_many(normalized_rows)

        return {
            "status": "created",
            "mode": "bulk",
            "signal": request.signal,
            "regime": request.regime,
            "deactivated_previous_rows": deactivated_count,
            "inserted_count": len(inserted_ids),
            "ids": inserted_ids,
        }

    except MappingValidationError as e:
        return {
            "status": "error",
            "message": "validation_failed",
            "details": e.errors,
        }


@router.patch("/{mapping_id}")
def update_mapping(mapping_id: int, request: MappingUpdateRequest):
    try:
        data = request.dict(exclude_unset=True)

        if "theme_weight" in data:
            validator.validate_create(
                {
                    "signal": "tmp",
                    "regime": "tmp",
                    "theme": "tmp",
                    "theme_weight": data["theme_weight"],
                    "asset": "tmp",
                    "asset_weight": data.get("asset_weight", 0.5),
                }
            )
        elif "asset_weight" in data:
            validator.validate_create(
                {
                    "signal": "tmp",
                    "regime": "tmp",
                    "theme": "tmp",
                    "theme_weight": data.get("theme_weight", 0.5),
                    "asset": "tmp",
                    "asset_weight": data["asset_weight"],
                }
            )

        updated = repo.update_mapping(mapping_id, data)

        return {
            "status": "updated",
            "success": updated,
        }

    except MappingValidationError as e:
        return {
            "status": "error",
            "message": "validation_failed",
            "details": e.errors,
        }


@router.delete("/{mapping_id}")
def delete_mapping(mapping_id: int):
    deleted = repo.delete_mapping(mapping_id)

    return {
        "status": "deleted",
        "success": deleted,
    }