"""Shared error-handling decorator for API endpoints.

Several endpoints (picking, receiving, delivery_notes) each independently
wrapped their service-layer calls in
``except ValueError as e: raise HTTPException(...)``. This decorator
removes that repeated boilerplate while still letting each endpoint pick
its own status code (most map to 400, one legitimately maps to 404).

``functools.wraps`` sets ``__wrapped__`` on the returned function, which
``inspect.signature`` (used by FastAPI to discover path/query/body params
and dependencies) follows automatically - the decorated endpoint's
signature is still correctly introspected.
"""
from functools import wraps
from typing import Awaitable, Callable, TypeVar

from fastapi import HTTPException, status

F = TypeVar("F", bound=Callable[..., Awaitable])


def translate_value_error(status_code: int = status.HTTP_400_BAD_REQUEST) -> Callable[[F], F]:
    """Catch a ValueError raised by the wrapped endpoint (typically from a
    service-layer call) and turn it into an HTTPException with the given
    status code, using the ValueError's message as the detail."""

    def decorator(func: F) -> F:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except ValueError as e:
                raise HTTPException(status_code=status_code, detail=str(e))

        return wrapper  # type: ignore[return-value]

    return decorator
