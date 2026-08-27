"""Agrega os routers de negócio sob /api/v1. Health fica de fora, em `main.py`."""

from fastapi import APIRouter

from wallet.api.routers import auth, users

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(users.router)
