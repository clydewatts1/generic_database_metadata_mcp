"""Logging infrastructure for the Stigmergic MCP Metadata Server."""

from __future__ import annotations

import logging
import sys


def get_logger(name: str) -> logging.Logger:
    """Return a named logger with a consistent format."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                datefmt="%Y-%m-%dT%H:%M:%S",
            )
        )
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
    return logger


class AppError(Exception):
    """Base application error."""

    def __init__(self, message: str, code: str = "APP_ERROR") -> None:
        super().__init__(message)
        self.code = code
        self.message = message

    def to_dict(self) -> dict:
        return {"error": self.code, "message": self.message}


class ValidationError(AppError):
    """Raised when Pydantic schema validation fails at insertion."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALIDATION_ERROR")


class NotFoundError(AppError):
    """Raised when a requested entity does not exist in the graph."""

    def __init__(self, entity: str, entity_id: str) -> None:
        super().__init__(f"{entity} not found: {entity_id}", code="NOT_FOUND")


class CircuitBreakerError(AppError):
    """Raised when a MetaType's circuit breaker has fired."""

    def __init__(self, meta_type_name: str) -> None:
        super().__init__(
            f"Circuit breaker open for MetaType '{meta_type_name}'. Human intervention required.",
            code="CIRCUIT_BREAKER_OPEN",
        )


class LockedError(AppError):
    """Raised when a MetaType is permanently locked (health_score <= 0.0)."""

    def __init__(self, meta_type_name: str) -> None:
        super().__init__(
            f"MetaType '{meta_type_name}' is locked (health_score <= 0.0).",
            code="META_TYPE_LOCKED",
        )
