from __future__ import annotations

try:
    from fastapi import (
        APIRouter,
        Depends,
        FastAPI,
        File,
        Form,
        HTTPException,
        UploadFile,
        Request,
    )
    from fastapi.middleware.cors import CORSMiddleware
except ImportError:  # pragma: no cover - fallback for environments without FastAPI
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str) -> None:
            super().__init__(detail)
            self.status_code = status_code
            self.detail = detail

    class UploadFile:
        filename: str
        content_type: str | None

        def __init__(
            self,
            filename: str = "",
            content_type: str | None = None,
            content: bytes = b"",
        ) -> None:
            self.filename = filename
            self.content_type = content_type
            self._content = content

        async def read(self) -> bytes:
            return self._content

    class APIRouter:
        def __init__(self, *args, **kwargs) -> None:
            self.routes = []

        def _register(self, *args, **kwargs):
            def decorator(fn):
                self.routes.append((args, kwargs, fn))
                return fn
            return decorator

        get = post = put = _register

    class FastAPI:
        def __init__(self, *args, **kwargs) -> None:
            self.routers = []

        def include_router(self, router) -> None:
            self.routers.append(router)

        def add_middleware(self, *args, **kwargs) -> None:
            return None

    class Request:
        pass

    def Depends(dependency):
        return dependency

    def File(default=None):
        return default

    def Form(default=None):
        return default

    class CORSMiddleware:
        pass