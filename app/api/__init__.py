"""对外只读 REST API（二期）。

通过 :func:`create_api_router` 暴露 ``/api/v1`` 路由，由 ``app/main.py``
注册到 NiceGUI 底层的 FastAPI 应用。鉴权见 :mod:`app.api.auth`。
"""
from fastapi import APIRouter

from app.api.routes import router as _v1_router


def create_api_router() -> APIRouter:
    """返回组装好的对外 API 路由（当前仅 v1）。"""
    api_router = APIRouter()
    api_router.include_router(_v1_router)
    return api_router


__all__ = ["create_api_router"]
