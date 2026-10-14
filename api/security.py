"""
api/security.py
───────────────
Centralized API-key authentication and security dependencies for UEHIS FastAPI services.

Enforces fail-closed authentication in production environments while preserving
local testability and developer workflows.
"""

from __future__ import annotations

import os
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

API_KEY_HEADER_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=False)


def is_production() -> bool:
    """Return True if the service is running in production mode."""
    return os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")


def validate_startup_security() -> None:
    """
    Validate that required security configuration is present on service startup.
    Fails startup with a clear configuration error if running in production
    without a configured UEHIS_API_KEY.
    """
    if is_production():
        key = os.getenv("UEHIS_API_KEY")
        if not key or not key.strip():
            raise RuntimeError(
                "CRITICAL SECURITY CONFIGURATION ERROR: UEHIS_API_KEY must be set to a "
                "non-empty secret token when ENVIRONMENT=production."
            )


def verify_internal_api_key(api_key: str = Security(api_key_header)) -> str:
    """
    FastAPI dependency validating the internal service API key.

    - Production Mode:
        Fails closed. If UEHIS_API_KEY is unset or empty, rejects requests with HTTP 500.
        If the provided API key does not match, rejects with HTTP 403.
    - Development / Testing Mode:
        If UEHIS_API_KEY is configured, validates it strictly (rejecting missing/invalid keys with HTTP 403).
        If UEHIS_API_KEY is unset or empty, permits local unauthenticated development calls.
    """
    expected_key = os.getenv("UEHIS_API_KEY")

    if is_production():
        if not expected_key or not expected_key.strip():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Server configuration error: UEHIS_API_KEY must be configured in production mode.",
            )
        if not api_key or api_key.strip() != expected_key.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate API key",
            )
        return api_key

    # Non-production (development / test)
    if expected_key and expected_key.strip():
        if not api_key or api_key.strip() != expected_key.strip():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Could not validate API key",
            )

    return api_key or ""
