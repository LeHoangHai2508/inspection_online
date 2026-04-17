from __future__ import annotations

from src.api._compat import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {"status": "ok"}
