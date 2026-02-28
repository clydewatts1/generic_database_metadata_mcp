"""Logging infrastructure for the Stigmergic MCP Metadata Server."""

from __future__ import annotations

import logging
import sys
import structlog


def configure_logging():
    """Configure structlog to output JSON."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.stdlib.add_log_level,
            structlog.stdlib.add_logger_name,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Return a structlog logger."""
    return structlog.get_logger(name)


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
