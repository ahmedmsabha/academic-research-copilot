"""Prompt Lab comparison use cases."""

from __future__ import annotations

import asyncio
import time
from uuid import uuid4

from app.core.config import Settings
from app.core.errors import AppError, NotFoundError, ValidationAppError
from app.models.schemas import (
    PromptExperimentResponse,
    PromptExperimentRunListResponse,
    PromptExperimentRunResponse,
    PromptLibraryResponse,
    PromptStrategyGuideResponse,
)
from app.prompts.library import (
    DEFAULT_STRATEGIES,
    TEMPLATE_VERSION,
    PromptStrategy,
    list_strategy_specs,
    render_prompt,
)
from app.prompts.structured import (
    STRUCTURED_PARSE_FAILURE,
    format_structured_answer,
    parse_structured_answer,
)
from app.providers.llm import ChatMessage, LLMProvider, LLMRequest
from app.repositories.memory_store import MemoryStore, PromptExperimentRecord, utc_now
from app.repositories.postgres_store import PostgresStore

Store = MemoryStore | PostgresStore


class PromptLabService:
    def __init__(self, store: Store, llm: LLMProvider, settings: Settings) -> None:
        self._store = store
        self._llm = llm
        self._settings = settings

    def library(self) -> PromptLibraryResponse:
        return PromptLibraryResponse(
            version=TEMPLATE_VERSION,
            strategies=[
                PromptStrategyGuideResponse(
                    id=spec.id,
                    name=spec.name,
                    description=spec.description,
                    when_better=spec.when_better,
                    user_template=spec.user_template,
                    template_version=TEMPLATE_VERSION,
                )
                for spec in list_strategy_specs()
            ],
        )

    async def run_comparison(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        user_input: str,
        strategies: list[PromptStrategy] | None,
    ) -> PromptExperimentRunResponse:
        project = self._store.get_project(project_id=project_id, owner_user_id=owner_user_id)
        if project is None:
            raise NotFoundError("Project not found.")

        cleaned = user_input.strip()
        if not cleaned:
            raise ValidationAppError("Prompt Lab input cannot be blank.")
        if len(cleaned) > self._settings.max_message_chars:
            raise ValidationAppError("Prompt Lab input is too long.")

        selected = strategies or list(DEFAULT_STRATEGIES)
        run_id = str(uuid4())
        results = await asyncio.gather(
            *[
                self._run_strategy(
                    owner_user_id=owner_user_id,
                    project_id=project_id,
                    run_id=run_id,
                    user_input=cleaned,
                    strategy=strategy,
                )
                for strategy in selected
            ]
        )
        return PromptExperimentRunResponse(
            run_id=run_id,
            project_id=project_id,
            input=cleaned,
            results=list(results),
        )

    def list_runs(
        self,
        *,
        owner_user_id: str,
        project_id: str,
    ) -> PromptExperimentRunListResponse:
        project = self._store.get_project(project_id=project_id, owner_user_id=owner_user_id)
        if project is None:
            raise NotFoundError("Project not found.")

        records = self._store.list_prompt_experiments(
            project_id=project_id,
            owner_user_id=owner_user_id,
        )
        grouped: dict[str, list[PromptExperimentRecord]] = {}
        order: list[str] = []
        for record in records:
            if record.run_id not in grouped:
                grouped[record.run_id] = []
                order.append(record.run_id)
            grouped[record.run_id].append(record)

        runs: list[PromptExperimentRunResponse] = []
        for run_id in order:
            items = grouped[run_id]
            items_sorted = sorted(items, key=lambda item: _strategy_order(item.strategy))
            runs.append(
                PromptExperimentRunResponse(
                    run_id=run_id,
                    project_id=project_id,
                    input=items_sorted[0].user_input,
                    results=[_to_response(item) for item in items_sorted],
                )
            )
        return PromptExperimentRunListResponse(runs=runs)

    def update_ratings(
        self,
        *,
        owner_user_id: str,
        experiment_id: str,
        rating_accuracy: int | None,
        rating_clarity: int | None,
        rating_research_usefulness: int | None,
    ) -> PromptExperimentResponse:
        if (
            rating_accuracy is None
            and rating_clarity is None
            and rating_research_usefulness is None
        ):
            raise ValidationAppError("Provide at least one rating.")

        updated = self._store.update_prompt_experiment_ratings(
            experiment_id=experiment_id,
            owner_user_id=owner_user_id,
            rating_accuracy=rating_accuracy,
            rating_clarity=rating_clarity,
            rating_research_usefulness=rating_research_usefulness,
        )
        if updated is None:
            raise NotFoundError("Prompt experiment not found.")
        return _to_response(updated)

    async def _run_strategy(
        self,
        *,
        owner_user_id: str,
        project_id: str,
        run_id: str,
        user_input: str,
        strategy: PromptStrategy,
    ) -> PromptExperimentResponse:
        rendered = render_prompt(strategy=strategy, user_input=user_input)
        started = time.perf_counter()
        try:
            llm_response = await self._llm.generate(
                LLMRequest(
                    messages=[ChatMessage(role="user", content=rendered.user_message)],
                    model=self._settings.llm_model,
                    system_instruction=rendered.system_instruction,
                )
            )
        except AppError as exc:
            elapsed_ms = int((time.perf_counter() - started) * 1000)
            return PromptExperimentResponse(
                run_id=run_id,
                project_id=project_id,
                strategy=strategy,
                template_version=rendered.template_version,
                input=user_input,
                output="",
                model=self._settings.llm_model,
                elapsed_ms=elapsed_ms,
                cost_usd=None,
                error_code=exc.code,
                error_message=exc.message,
            )

        elapsed_ms = int((time.perf_counter() - started) * 1000)
        output = _visible_output(strategy, llm_response.text)
        record = PromptExperimentRecord(
            id=str(uuid4()),
            run_id=run_id,
            project_id=project_id,
            owner_user_id=owner_user_id,
            user_input=user_input,
            strategy=strategy,
            template_version=rendered.template_version,
            model=llm_response.model,
            provider=llm_response.provider,
            generated_output=output,
            elapsed_ms=elapsed_ms,
            created_at=utc_now(),
            updated_at=utc_now(),
            prompt_tokens=llm_response.prompt_tokens,
            completion_tokens=llm_response.completion_tokens,
            total_tokens=llm_response.total_tokens,
        )
        saved = self._store.create_prompt_experiment(record)
        return _to_response(saved)


def _visible_output(strategy: PromptStrategy, raw: str) -> str:
    if strategy != "structured":
        return raw.strip()
    parsed = parse_structured_answer(raw)
    if parsed is None:
        return STRUCTURED_PARSE_FAILURE
    return format_structured_answer(parsed)


def _strategy_order(strategy: str) -> int:
    for index, name in enumerate(DEFAULT_STRATEGIES):
        if name == strategy:
            return index
    return len(DEFAULT_STRATEGIES)


def _to_response(record: PromptExperimentRecord) -> PromptExperimentResponse:
    return PromptExperimentResponse(
        id=record.id,
        run_id=record.run_id,
        project_id=record.project_id,
        strategy=record.strategy,  # type: ignore[arg-type]
        template_version=record.template_version,
        input=record.user_input,
        output=record.generated_output,
        model=record.model,
        provider=record.provider,
        elapsed_ms=record.elapsed_ms,
        prompt_tokens=record.prompt_tokens,
        completion_tokens=record.completion_tokens,
        total_tokens=record.total_tokens,
        cost_usd=None,
        rating_accuracy=record.rating_accuracy,
        rating_clarity=record.rating_clarity,
        rating_research_usefulness=record.rating_research_usefulness,
        created_at=record.created_at,
    )
