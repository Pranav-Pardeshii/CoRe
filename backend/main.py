"""ASGI factory entrypoint for ``uvicorn backend.main:create_app --factory``."""

from backend.app.main import create_app

__all__ = ["create_app"]
