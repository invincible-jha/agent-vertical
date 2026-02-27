"""Tests for agent_vertical.wizard.wizard."""
from __future__ import annotations

from typing import Any

import pytest

from agent_vertical.wizard.wizard import (
    CustomizationResult,
    TemplateCustomizer,
    WizardQuestion,
    WizardSession,
    WizardState,
    choice_validator,
    min_length_validator,
    non_empty_validator,
    numeric_range_validator,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def basic_questions() -> list[WizardQuestion]:
    return [
        WizardQuestion(question_id="domain", prompt="Domain?", answer_type="str"),
        WizardQuestion(question_id="version", prompt="Version?", answer_type="str", default="1.0.0"),
        WizardQuestion(question_id="max_tokens", prompt="Max tokens?", answer_type="int", default=512),
    ]


@pytest.fixture()
def base_template() -> dict[str, Any]:
    return {
        "template_name": "base",
        "version": "0.0.1",
        "settings": {"timeout": 30},
    }


# ---------------------------------------------------------------------------
# WizardQuestion
# ---------------------------------------------------------------------------


class TestWizardQuestion:
    def test_is_frozen(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?")
        with pytest.raises((AttributeError, TypeError)):
            q.question_id = "other"  # type: ignore[misc]

    def test_is_applicable_no_condition(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?")
        assert q.is_applicable({}) is True

    def test_is_applicable_condition_true(self) -> None:
        q = WizardQuestion(
            question_id="q1",
            prompt="Test?",
            condition=lambda answers: answers.get("flag") is True,
        )
        assert q.is_applicable({"flag": True}) is True

    def test_is_applicable_condition_false(self) -> None:
        q = WizardQuestion(
            question_id="q1",
            prompt="Test?",
            condition=lambda answers: answers.get("flag") is True,
        )
        assert q.is_applicable({"flag": False}) is False

    def test_validate_passes_with_no_validators(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?")
        ok, errors = q.validate("any answer")
        assert ok is True
        assert errors == []

    def test_validate_fails_on_validator_rejection(self) -> None:
        q = WizardQuestion(
            question_id="q1",
            prompt="Test?",
            validators=(non_empty_validator,),
        )
        ok, errors = q.validate("   ")
        assert ok is False
        assert len(errors) == 1

    def test_coerce_int(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="int")
        assert q.coerce("42") == 42

    def test_coerce_float(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="float")
        assert q.coerce("3.14") == pytest.approx(3.14)

    def test_coerce_bool_true(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="bool")
        for truthy in ["true", "yes", "1", "y"]:
            assert q.coerce(truthy) is True

    def test_coerce_bool_false(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="bool")
        assert q.coerce("no") is False

    def test_coerce_list(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="list")
        assert q.coerce("a, b, c") == ["a", "b", "c"]

    def test_coerce_empty_returns_default(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="int", default=99)
        assert q.coerce("") == 99

    def test_coerce_invalid_int_returns_raw(self) -> None:
        q = WizardQuestion(question_id="q1", prompt="Test?", answer_type="int")
        assert q.coerce("not_a_number") == "not_a_number"


# ---------------------------------------------------------------------------
# WizardSession
# ---------------------------------------------------------------------------


class TestWizardSessionBasic:
    def test_initial_state_not_started(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        assert session.state == WizardState.NOT_STARTED

    def test_start_returns_first_question(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        q = session.start()
        assert q is not None
        assert q.question_id == "domain"

    def test_state_in_progress_after_start(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        assert session.state == WizardState.IN_PROGRESS

    def test_answer_accepted(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        accepted, errors, _next = session.answer("healthcare")
        assert accepted is True
        assert errors == []

    def test_answer_stores_coerced_value(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        session.answer("healthcare")
        assert session.answers["domain"] == "healthcare"

    def test_complete_session(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        session.answer("healthcare")
        session.answer("2.0.0")
        session.answer("1024")
        assert session.state == WizardState.COMPLETE
        assert session.is_complete() is True

    def test_default_used_on_empty_answer(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        session.answer("finance")
        session.answer("")  # should use default "1.0.0"
        assert session.answers.get("version") == "1.0.0"

    def test_abort_sets_state(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        session.abort()
        assert session.state == WizardState.ABORTED

    def test_progress_tracking(self, basic_questions: list[WizardQuestion]) -> None:
        session = WizardSession(basic_questions)
        session.start()
        answered, total = session.progress()
        assert answered == 0
        assert total == 3
        session.answer("finance")
        answered, total = session.progress()
        assert answered == 1

    def test_no_questions_completes_immediately(self) -> None:
        session = WizardSession([])
        result = session.start()
        assert result is None
        assert session.state == WizardState.COMPLETE


class TestWizardSessionConditions:
    def test_conditional_question_skipped(self) -> None:
        questions = [
            WizardQuestion(question_id="domain", prompt="Domain?"),
            WizardQuestion(
                question_id="hipaa_enabled",
                prompt="Enable HIPAA mode?",
                condition=lambda a: a.get("domain") == "healthcare",
            ),
            WizardQuestion(question_id="version", prompt="Version?", default="1.0.0"),
        ]
        session = WizardSession(questions)
        session.start()
        session.answer("finance")  # domain = finance
        # hipaa_enabled should be skipped since domain != healthcare
        q = session.current_question()
        assert q is not None
        assert q.question_id == "version"
        assert "hipaa_enabled" in session.skipped_questions

    def test_conditional_question_asked(self) -> None:
        questions = [
            WizardQuestion(question_id="domain", prompt="Domain?"),
            WizardQuestion(
                question_id="hipaa_enabled",
                prompt="Enable HIPAA mode?",
                condition=lambda a: a.get("domain") == "healthcare",
                default="yes",
            ),
        ]
        session = WizardSession(questions)
        session.start()
        session.answer("healthcare")
        q = session.current_question()
        assert q is not None
        assert q.question_id == "hipaa_enabled"


class TestWizardSessionValidation:
    def test_invalid_answer_rejected(self) -> None:
        q = WizardQuestion(
            question_id="domain",
            prompt="Domain?",
            validators=(choice_validator(["healthcare", "finance"]),),
        )
        session = WizardSession([q])
        session.start()
        accepted, errors, _next = session.answer("invalid_domain")
        assert accepted is False
        assert len(errors) > 0

    def test_valid_answer_accepted_after_validation(self) -> None:
        q = WizardQuestion(
            question_id="domain",
            prompt="Domain?",
            validators=(choice_validator(["healthcare", "finance"]),),
        )
        session = WizardSession([q])
        session.start()
        accepted, errors, _next = session.answer("healthcare")
        assert accepted is True


# ---------------------------------------------------------------------------
# TemplateCustomizer
# ---------------------------------------------------------------------------


class TestTemplateCustomizer:
    def test_customise_merges_answers(
        self, base_template: dict[str, Any], basic_questions: list[WizardQuestion]
    ) -> None:
        customizer = TemplateCustomizer(base_template, "test_template")
        result = customizer.run_session(basic_questions, ["healthcare", "2.0.0", "1024"])
        assert result.config["domain"] == "healthcare"
        assert result.config["version"] == "2.0.0"
        assert result.config["max_tokens"] == 1024

    def test_base_template_not_mutated(
        self, base_template: dict[str, Any], basic_questions: list[WizardQuestion]
    ) -> None:
        customizer = TemplateCustomizer(base_template, "test_template")
        customizer.run_session(basic_questions, ["finance", "3.0.0", "2048"])
        # Original template should still have its original version
        assert base_template["version"] == "0.0.1"

    def test_base_template_values_preserved(
        self, base_template: dict[str, Any], basic_questions: list[WizardQuestion]
    ) -> None:
        customizer = TemplateCustomizer(base_template, "test_template")
        result = customizer.run_session(basic_questions, ["finance", "1.0.0", "512"])
        assert result.config["settings"]["timeout"] == 30

    def test_result_is_frozen(
        self, base_template: dict[str, Any], basic_questions: list[WizardQuestion]
    ) -> None:
        customizer = TemplateCustomizer(base_template, "test_template")
        result = customizer.run_session(basic_questions, ["finance", "1.0.0", "512"])
        assert isinstance(result, CustomizationResult)
        with pytest.raises((AttributeError, TypeError)):
            result.template_name = "other"  # type: ignore[misc]

    def test_template_name_in_result(
        self, base_template: dict[str, Any], basic_questions: list[WizardQuestion]
    ) -> None:
        customizer = TemplateCustomizer(base_template, "healthcare_template")
        result = customizer.run_session(basic_questions, ["healthcare", "1.0.0", "512"])
        assert result.template_name == "healthcare_template"

    def test_skipped_questions_reported(self) -> None:
        questions = [
            WizardQuestion(question_id="domain", prompt="Domain?"),
            WizardQuestion(
                question_id="conditional",
                prompt="Conditional?",
                condition=lambda a: False,
                default="n/a",
            ),
        ]
        customizer = TemplateCustomizer({})
        result = customizer.run_session(questions, ["healthcare"])
        assert "conditional" in result.skipped_questions


# ---------------------------------------------------------------------------
# Built-in validators
# ---------------------------------------------------------------------------


class TestValidators:
    def test_non_empty_passes(self) -> None:
        ok, msg = non_empty_validator("hello")
        assert ok is True

    def test_non_empty_fails_on_whitespace(self) -> None:
        ok, msg = non_empty_validator("   ")
        assert ok is False

    def test_min_length_passes(self) -> None:
        validator = min_length_validator(5)
        ok, msg = validator("hello")
        assert ok is True

    def test_min_length_fails(self) -> None:
        validator = min_length_validator(10)
        ok, msg = validator("short")
        assert ok is False

    def test_choice_validator_passes(self) -> None:
        validator = choice_validator(["healthcare", "finance"])
        ok, msg = validator("healthcare")
        assert ok is True

    def test_choice_validator_case_insensitive(self) -> None:
        validator = choice_validator(["Healthcare"])
        ok, msg = validator("HEALTHCARE")
        assert ok is True

    def test_choice_validator_fails_invalid(self) -> None:
        validator = choice_validator(["healthcare", "finance"])
        ok, msg = validator("education")
        assert ok is False

    def test_numeric_range_passes(self) -> None:
        validator = numeric_range_validator(1, 100)
        ok, msg = validator("50")
        assert ok is True

    def test_numeric_range_fails_below(self) -> None:
        validator = numeric_range_validator(10, 100)
        ok, msg = validator("5")
        assert ok is False

    def test_numeric_range_fails_above(self) -> None:
        validator = numeric_range_validator(1, 10)
        ok, msg = validator("99")
        assert ok is False

    def test_numeric_range_fails_non_numeric(self) -> None:
        validator = numeric_range_validator(1, 100)
        ok, msg = validator("abc")
        assert ok is False
