"""Unit tests for versioned Prompt Lab templates."""

from app.prompts.library import (
    DEFAULT_STRATEGIES,
    TEMPLATE_VERSION,
    render_prompt,
)


def test_all_default_strategies_render_user_input() -> None:
    question = "Why use retrieval-augmented generation?"
    for strategy in DEFAULT_STRATEGIES:
        rendered = render_prompt(strategy=strategy, user_input=question)
        assert rendered.template_version == TEMPLATE_VERSION
        assert question in rendered.user_message
        assert "{{input}}" not in rendered.user_message


def test_zero_shot_has_no_worked_example() -> None:
    rendered = render_prompt(strategy="zero_shot", user_input="What is a hypothesis?")
    assert "Example question:" not in rendered.user_message
    assert "Example 1" not in rendered.user_message


def test_one_shot_includes_single_example() -> None:
    rendered = render_prompt(strategy="one_shot", user_input="What is peer review?")
    assert "Example question:" in rendered.user_message
    assert "Example 1 question:" not in rendered.user_message


def test_few_shot_includes_two_examples() -> None:
    rendered = render_prompt(strategy="few_shot", user_input="What is peer review?")
    assert "Example 1 question:" in rendered.user_message
    assert "Example 2 question:" in rendered.user_message


def test_user_braces_do_not_break_rendering() -> None:
    rendered = render_prompt(strategy="zero_shot", user_input="Explain {n} and {k} sampling.")
    assert "Explain {n} and {k} sampling." in rendered.user_message


def test_chain_of_thought_forbids_hidden_scratchpad() -> None:
    rendered = render_prompt(strategy="chain_of_thought", user_input="Compare two methods.")
    assert "private scratchpad" in rendered.system_instruction
    assert "numbered working" in rendered.user_message


def test_structured_asks_for_json_fields() -> None:
    rendered = render_prompt(strategy="structured", user_input="Define bias.")
    assert "key_points" in rendered.user_message
    assert "chain-of-thought" in rendered.system_instruction
