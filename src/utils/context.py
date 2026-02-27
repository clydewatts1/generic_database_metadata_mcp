"""Profile and domain-scope injection utilities."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RequestContext:
    """Carries the calling agent's identity and domain scope through the call stack."""

    profile_id: str
    domain_scope: str = "Global"
    prompt_hash: str = "SYSTEM_GENERATED"
    session_id: str = ""

    def is_global(self) -> bool:
        return self.domain_scope.lower() == "global"


def default_context() -> RequestContext:
    """Return a sensible default context for system-initiated operations."""
    return RequestContext(profile_id="SYSTEM", domain_scope="Global")


def make_context(
    profile_id: str,
    domain_scope: str = "Global",
    prompt_hash: str = "SYSTEM_GENERATED",
    session_id: str = "",
) -> RequestContext:
    return RequestContext(
        profile_id=profile_id,
        domain_scope=domain_scope,
        prompt_hash=prompt_hash,
        session_id=session_id,
    )
