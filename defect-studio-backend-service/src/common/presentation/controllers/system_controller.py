"""System controller — health check endpoint."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/api", tags=["System"])


@router.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": "DefectAgent Backend"}