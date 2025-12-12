from fastapi import Request

from .container import ServiceContainer


def get_container(request: Request) -> ServiceContainer:
    container = getattr(request.app.state, "container", None)
    if not container:
        raise RuntimeError("Service container not initialized")
    return container
