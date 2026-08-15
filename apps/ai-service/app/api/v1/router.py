"""Aggregate /api/v1 routers."""

from fastapi import APIRouter

from app.api.v1 import conversations, documents, projects, prompt_experiments

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(projects.router)
api_router.include_router(documents.router)
api_router.include_router(conversations.router)
api_router.include_router(prompt_experiments.router)
