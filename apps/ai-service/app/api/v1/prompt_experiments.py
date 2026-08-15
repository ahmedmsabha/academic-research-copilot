"""Prompt Lab library and experiment routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_prompt_lab_service
from app.core.security import require_user_id
from app.models.schemas import (
    PromptExperimentCreateRequest,
    PromptExperimentRatingRequest,
    PromptExperimentResponse,
    PromptExperimentRunListResponse,
    PromptExperimentRunResponse,
    PromptLibraryResponse,
)
from app.services.prompt_lab import PromptLabService

router = APIRouter(tags=["prompt-lab"])


@router.get("/prompt-library", response_model=PromptLibraryResponse)
def get_prompt_library(
    user_id: str = Depends(require_user_id),
    service: PromptLabService = Depends(get_prompt_lab_service),
) -> PromptLibraryResponse:
    _ = user_id
    return service.library()


@router.post(
    "/projects/{project_id}/prompt-experiments",
    response_model=PromptExperimentRunResponse,
    status_code=201,
)
async def create_prompt_experiments(
    project_id: str,
    body: PromptExperimentCreateRequest,
    user_id: str = Depends(require_user_id),
    service: PromptLabService = Depends(get_prompt_lab_service),
) -> PromptExperimentRunResponse:
    return await service.run_comparison(
        owner_user_id=user_id,
        project_id=project_id,
        user_input=body.input,
        strategies=body.strategies,
    )


@router.get(
    "/projects/{project_id}/prompt-experiments",
    response_model=PromptExperimentRunListResponse,
)
def list_prompt_experiments(
    project_id: str,
    user_id: str = Depends(require_user_id),
    service: PromptLabService = Depends(get_prompt_lab_service),
) -> PromptExperimentRunListResponse:
    return service.list_runs(owner_user_id=user_id, project_id=project_id)


@router.patch(
    "/prompt-experiments/{experiment_id}",
    response_model=PromptExperimentResponse,
)
def rate_prompt_experiment(
    experiment_id: str,
    body: PromptExperimentRatingRequest,
    user_id: str = Depends(require_user_id),
    service: PromptLabService = Depends(get_prompt_lab_service),
) -> PromptExperimentResponse:
    return service.update_ratings(
        owner_user_id=user_id,
        experiment_id=experiment_id,
        rating_accuracy=body.rating_accuracy,
        rating_clarity=body.rating_clarity,
        rating_research_usefulness=body.rating_research_usefulness,
    )
