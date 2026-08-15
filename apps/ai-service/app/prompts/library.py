"""Prompt Lab template library.

Templates are versioned application assets. The user-facing library describes
technique and when it tends to work; it does not expose chat/RAG hidden prompts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

PromptStrategy = Literal[
    "zero_shot",
    "one_shot",
    "few_shot",
    "chain_of_thought",
    "structured",
]

TEMPLATE_VERSION = "prompt-lab-v1"

DEFAULT_STRATEGIES: tuple[PromptStrategy, ...] = (
    "zero_shot",
    "one_shot",
    "few_shot",
    "chain_of_thought",
    "structured",
)

_INPUT_TOKEN = "{{input}}"

_SHARED_RULES = (
    "You are Academic Research Copilot helping a student or researcher. "
    "Be accurate and concise. Do not invent citations, filenames, page numbers, "
    "or sources. If you are unsure, say so."
)

_EXAMPLE_ONE_INPUT = "What is the difference between a literature review and a systematic review?"
_EXAMPLE_ONE_OUTPUT = (
    "A literature review surveys published work on a topic, often as a narrative. "
    "A systematic review follows a predefined protocol to search, appraise, and "
    "synthesize studies, which reduces selection bias compared with an informal survey."
)

_EXAMPLE_TWO_INPUT = "When should a student cite a source in a lab report?"
_EXAMPLE_TWO_OUTPUT = (
    "Cite whenever you use another author's words, data, or distinctive ideas, "
    "including paraphrases. Everyday facts that are common knowledge in the course "
    "do not need a citation."
)


@dataclass(frozen=True, slots=True)
class StrategySpec:
    id: PromptStrategy
    name: str
    description: str
    when_better: str
    user_template: str
    system_instruction: str


@dataclass(frozen=True, slots=True)
class RenderedPrompt:
    strategy: PromptStrategy
    template_version: str
    system_instruction: str
    user_message: str


_SPECS: dict[PromptStrategy, StrategySpec] = {
    "zero_shot": StrategySpec(
        id="zero_shot",
        name="Zero-shot",
        description="Direct instruction plus the question. No worked examples.",
        when_better=(
            "Best for familiar, well-specified tasks where the model already knows "
            "the format. Fastest and cheapest; weaker on unusual academic formats."
        ),
        system_instruction=_SHARED_RULES,
        user_template=(
            f"Answer the following research question directly.\n\nQuestion:\n{_INPUT_TOKEN}"
        ),
    ),
    "one_shot": StrategySpec(
        id="one_shot",
        name="One-shot",
        description="The same task plus one representative example of a good answer.",
        when_better=(
            "Best when you need a specific tone or shape and one example is enough "
            "to lock it in (short definitions, compare-and-contrast)."
        ),
        system_instruction=_SHARED_RULES + " Match the style of the example.",
        user_template=(
            "Answer the research question in the same style as the example.\n\n"
            f"Example question:\n{_EXAMPLE_ONE_INPUT}\n\n"
            f"Example answer:\n{_EXAMPLE_ONE_OUTPUT}\n\n"
            f"Question:\n{_INPUT_TOKEN}"
        ),
    ),
    "few_shot": StrategySpec(
        id="few_shot",
        name="Few-shot",
        description="The task plus two or more curated examples.",
        when_better=(
            "Best when the desired structure is easy to miss (definitions vs. "
            "advice vs. caveats). Extra examples stabilize format more than zero-shot."
        ),
        system_instruction=_SHARED_RULES + " Match the style of the examples.",
        user_template=(
            "Answer the research question in the same style as the examples.\n\n"
            f"Example 1 question:\n{_EXAMPLE_ONE_INPUT}\n\n"
            f"Example 1 answer:\n{_EXAMPLE_ONE_OUTPUT}\n\n"
            f"Example 2 question:\n{_EXAMPLE_TWO_INPUT}\n\n"
            f"Example 2 answer:\n{_EXAMPLE_TWO_OUTPUT}\n\n"
            f"Question:\n{_INPUT_TOKEN}"
        ),
    ),
    "chain_of_thought": StrategySpec(
        id="chain_of_thought",
        name="Visible step-by-step",
        description=(
            "Asks for numbered working a student can read, then a final answer. "
            "This is pedagogical chain-of-thought in the answer — not hidden model scratchpad."
        ),
        when_better=(
            "Best for multi-step academic reasoning (method choice, evaluating a claim). "
            "Weaker when you only need a short definition; can be verbose."
        ),
        system_instruction=(
            f"{_SHARED_RULES} "
            "The numbered steps are part of the student-facing answer. "
            "Do not write private scratchpad, hidden reasoning, or phrases such as "
            "'let me think internally'."
        ),
        user_template=(
            "Explain the answer with short numbered working a student could follow, "
            "then one line starting with 'Final answer:'.\n\n"
            f"Question:\n{_INPUT_TOKEN}"
        ),
    ),
    "structured": StrategySpec(
        id="structured",
        name="Structured output",
        description=(
            "Requires a concise JSON object. Only the parsed fields are shown — "
            "never hidden chain-of-thought."
        ),
        when_better=(
            "Best when you need comparable, machine-checkable fields (answer, "
            "key points, confidence, limitations) for a lab or rubric."
        ),
        system_instruction=(
            f"{_SHARED_RULES} "
            "Return only the JSON object. No markdown fences, commentary, or chain-of-thought."
        ),
        user_template=(
            "Return ONLY a JSON object with these keys:\n"
            '- "answer": string (concise final answer)\n'
            '- "key_points": array of 2 to 5 short strings\n'
            '- "confidence": one of "high", "medium", "low"\n'
            '- "limitations": string (what the answer does not cover)\n\n'
            f"Question:\n{_INPUT_TOKEN}"
        ),
    ),
}


def list_strategy_specs() -> list[StrategySpec]:
    return [_SPECS[key] for key in DEFAULT_STRATEGIES]


def get_strategy_spec(strategy: PromptStrategy) -> StrategySpec:
    return _SPECS[strategy]


def render_prompt(*, strategy: PromptStrategy, user_input: str) -> RenderedPrompt:
    spec = get_strategy_spec(strategy)
    # Replace rather than str.format so braces in the user input cannot break rendering.
    user_message = spec.user_template.replace(_INPUT_TOKEN, user_input.strip())
    return RenderedPrompt(
        strategy=strategy,
        template_version=TEMPLATE_VERSION,
        system_instruction=spec.system_instruction,
        user_message=user_message,
    )
