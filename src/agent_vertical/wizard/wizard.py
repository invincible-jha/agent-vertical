"""Template customization wizard for vertical agent templates.

Guides operators through a question-and-answer session to produce a
fully-customised agent configuration dict from a base template.  Each
:class:`WizardQuestion` defines a prompt, validation rules, and an
optional transformer function.  The :class:`WizardSession` drives the
Q&A sequence and the :class:`TemplateCustomizer` merges answers with a
base template to produce the final :class:`CustomizationResult`.

Design principles
-----------------
- Questions are ordered and optionally conditional on earlier answers.
- Each question has a list of validators that gate acceptance of a response.
- A question may be skipped when its ``condition`` callable returns False.
- Templates are never mutated; :class:`CustomizationResult` contains a deep
  copy merged with the collected answers.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


# ---------------------------------------------------------------------------
# Types and enumerations
# ---------------------------------------------------------------------------


class WizardState(str, Enum):
    """State of a :class:`WizardSession`."""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETE = "complete"
    ABORTED = "aborted"


# A validator takes a raw answer string and returns (is_valid, error_message).
Validator = Callable[[str], tuple[bool, str]]

# A condition takes the answers collected so far and returns bool.
Condition = Callable[[dict[str, object]], bool]


# ---------------------------------------------------------------------------
# Wizard question
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WizardQuestion:
    """A single step in a template customisation wizard.

    Attributes
    ----------
    question_id:
        Unique identifier for this question (used as the answer key).
    prompt:
        Human-readable question text shown to the operator.
    answer_type:
        Expected type of the answer: ``"str"``, ``"int"``, ``"bool"``,
        ``"list"`` (comma-separated strings), or ``"float"``.
    default:
        Optional default value returned when the operator provides no input.
    validators:
        Ordered list of validator callables; all must pass for an answer
        to be accepted.
    condition:
        When supplied, the question is only asked when
        ``condition(current_answers)`` is True.
    help_text:
        Extended explanation shown when the operator requests help.
    required:
        When True (default) and no default is set, the question cannot be
        skipped.
    """

    question_id: str
    prompt: str
    answer_type: str = "str"
    default: object = None
    validators: tuple[Validator, ...] = field(default_factory=tuple)
    condition: Condition | None = None
    help_text: str = ""
    required: bool = True

    def is_applicable(self, current_answers: dict[str, object]) -> bool:
        """Return True if this question should be asked given current answers.

        Parameters
        ----------
        current_answers:
            Answers collected so far in the wizard session.

        Returns
        -------
        bool
            True when no condition is set, or when the condition returns True.
        """
        if self.condition is None:
            return True
        return self.condition(current_answers)

    def validate(self, raw: str) -> tuple[bool, list[str]]:
        """Run all validators against *raw*.

        Parameters
        ----------
        raw:
            The raw string answer provided by the operator.

        Returns
        -------
        tuple[bool, list[str]]
            ``(all_passed, list_of_error_messages)``
        """
        errors: list[str] = []
        for validator in self.validators:
            ok, message = validator(raw)
            if not ok:
                errors.append(message)
        return len(errors) == 0, errors

    def coerce(self, raw: str) -> object:
        """Coerce *raw* string to the declared answer type.

        Parameters
        ----------
        raw:
            Validated raw string from the operator.

        Returns
        -------
        Any
            Coerced value; falls back to the raw string on parse error.
        """
        stripped = raw.strip()
        if not stripped:
            return self.default
        try:
            if self.answer_type == "int":
                return int(stripped)
            if self.answer_type == "float":
                return float(stripped)
            if self.answer_type == "bool":
                return stripped.lower() in ("true", "yes", "1", "y")
            if self.answer_type == "list":
                return [item.strip() for item in stripped.split(",") if item.strip()]
        except (ValueError, TypeError):
            pass
        return stripped


# ---------------------------------------------------------------------------
# Wizard session
# ---------------------------------------------------------------------------


class WizardSession:
    """Drives a question-and-answer session for template customisation.

    Questions are asked in order, subject to each question's condition.
    Answers are validated before being stored.

    Parameters
    ----------
    questions:
        Ordered list of :class:`WizardQuestion` objects defining the wizard.
    """

    def __init__(self, questions: list[WizardQuestion]) -> None:
        self._questions = list(questions)
        self._answers: dict[str, object] = {}
        self._current_index: int = 0
        self._state: WizardState = WizardState.NOT_STARTED
        self._skipped: list[str] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def state(self) -> WizardState:
        """Return the current wizard state."""
        return self._state

    @property
    def answers(self) -> dict[str, object]:
        """Return a copy of collected answers."""
        return dict(self._answers)

    @property
    def skipped_questions(self) -> list[str]:
        """Return ids of questions skipped due to conditions."""
        return list(self._skipped)

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------

    def start(self) -> WizardQuestion | None:
        """Start the wizard and return the first applicable question.

        Returns
        -------
        WizardQuestion | None
            The first applicable question, or None if there are no questions.
        """
        self._state = WizardState.IN_PROGRESS
        self._current_index = 0
        return self._advance_to_next()

    def current_question(self) -> WizardQuestion | None:
        """Return the current question without advancing.

        Returns
        -------
        WizardQuestion | None
            The current question or None when session is complete.
        """
        if self._current_index >= len(self._questions):
            return None
        return self._questions[self._current_index]

    def answer(self, raw: str) -> tuple[bool, list[str], WizardQuestion | None]:
        """Submit an answer for the current question.

        Parameters
        ----------
        raw:
            Raw string answer from the operator.

        Returns
        -------
        tuple[bool, list[str], WizardQuestion | None]
            ``(accepted, errors, next_question)``
            When ``accepted`` is True, ``next_question`` is the following
            applicable question (or None when the wizard is complete).
        """
        if self._state != WizardState.IN_PROGRESS:
            return False, ["Wizard is not in progress."], None

        question = self.current_question()
        if question is None:
            return False, ["No current question."], None

        # Use default if answer is empty and default exists
        if not raw.strip() and question.default is not None:
            self._answers[question.question_id] = question.default
            self._current_index += 1
            next_q = self._advance_to_next()
            return True, [], next_q

        # Required + empty + no default
        if not raw.strip() and question.required:
            return False, [f"Answer required for '{question.question_id}'."], question

        ok, errors = question.validate(raw)
        if not ok:
            return False, errors, question

        coerced = question.coerce(raw)
        self._answers[question.question_id] = coerced
        self._current_index += 1
        next_q = self._advance_to_next()
        return True, [], next_q

    def abort(self) -> None:
        """Abort the wizard session."""
        self._state = WizardState.ABORTED

    def progress(self) -> tuple[int, int]:
        """Return ``(answered_count, total_applicable_count)``.

        Returns
        -------
        tuple[int, int]
            Count of answered questions and total applicable questions.
        """
        applicable = sum(
            1 for q in self._questions if q.is_applicable(self._answers)
        )
        answered = len(self._answers)
        return answered, applicable

    def is_complete(self) -> bool:
        """Return True when all applicable questions have been answered."""
        return self._state == WizardState.COMPLETE

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _advance_to_next(self) -> WizardQuestion | None:
        """Skip non-applicable questions and update state."""
        while self._current_index < len(self._questions):
            question = self._questions[self._current_index]
            if question.is_applicable(self._answers):
                return question
            # Skip this question
            self._skipped.append(question.question_id)
            if question.default is not None:
                self._answers[question.question_id] = question.default
            self._current_index += 1

        self._state = WizardState.COMPLETE
        return None


# ---------------------------------------------------------------------------
# Customization result
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CustomizationResult:
    """Output of :class:`TemplateCustomizer.customise`.

    Attributes
    ----------
    template_name:
        Name of the base template that was customised.
    config:
        Merged configuration dict (base template + wizard answers).
    answers:
        The raw answers collected during the wizard session.
    skipped_questions:
        Question IDs that were skipped due to conditions.
    is_complete:
        True when the wizard ran to completion without being aborted.
    """

    template_name: str
    config: dict[str, object]
    answers: dict[str, object]
    skipped_questions: list[str]
    is_complete: bool


# ---------------------------------------------------------------------------
# Template customizer
# ---------------------------------------------------------------------------


class TemplateCustomizer:
    """Merges wizard answers with a base template to produce a customised config.

    Parameters
    ----------
    base_template:
        The starting configuration dict.  It is deep-copied before merging.
    template_name:
        Human-readable name for the template (stored in the result).
    """

    def __init__(
        self, base_template: dict[str, object], template_name: str = "unnamed"
    ) -> None:
        self._base_template = base_template
        self._template_name = template_name

    def customise(self, session: WizardSession) -> CustomizationResult:
        """Merge collected wizard answers with the base template.

        The wizard session must be complete (or aborted) before calling
        this method.  Answers override base template values at the top
        level; nested keys in the base template are not modified unless
        an answer explicitly provides a new value for that key.

        Parameters
        ----------
        session:
            A :class:`WizardSession` that has been run to completion.

        Returns
        -------
        CustomizationResult
            The merged configuration and session metadata.
        """
        merged = copy.deepcopy(self._base_template)
        merged.update(session.answers)

        return CustomizationResult(
            template_name=self._template_name,
            config=merged,
            answers=dict(session.answers),
            skipped_questions=list(session.skipped_questions),
            is_complete=session.is_complete(),
        )

    def run_session(
        self,
        questions: list[WizardQuestion],
        raw_answers: list[str],
    ) -> CustomizationResult:
        """Run a wizard session programmatically using a list of pre-supplied answers.

        This is useful for automated testing and scripted customisation
        flows where interactive prompting is not available.

        Parameters
        ----------
        questions:
            Ordered list of wizard questions.
        raw_answers:
            Pre-supplied raw string answers, one per applicable question.
            Excess answers are ignored; missing answers use question defaults.

        Returns
        -------
        CustomizationResult
            The result after processing all answers.
        """
        session = WizardSession(questions)
        current = session.start()
        answer_iter = iter(raw_answers)

        while current is not None:
            raw = next(answer_iter, "")
            accepted, _errors, current = session.answer(raw)
            if not accepted and not raw.strip():
                # No more answers; accept defaults for remaining required questions
                if current is not None and current.default is not None:
                    _, _, current = session.answer("")
                else:
                    break

        return self.customise(session)


# ---------------------------------------------------------------------------
# Built-in validators
# ---------------------------------------------------------------------------


def non_empty_validator(raw: str) -> tuple[bool, str]:
    """Reject blank answers."""
    ok = bool(raw.strip())
    return ok, "" if ok else "Answer must not be empty."


def min_length_validator(minimum: int) -> Validator:
    """Return a validator that requires at least *minimum* characters."""
    def _validate(raw: str) -> tuple[bool, str]:
        ok = len(raw.strip()) >= minimum
        return ok, "" if ok else f"Answer must be at least {minimum} characters."
    return _validate


def choice_validator(choices: list[str]) -> Validator:
    """Return a validator that requires the answer to be one of *choices*."""
    lowered = [c.lower() for c in choices]
    def _validate(raw: str) -> tuple[bool, str]:
        ok = raw.strip().lower() in lowered
        return ok, "" if ok else f"Answer must be one of: {', '.join(choices)}"
    return _validate


def numeric_range_validator(minimum: float, maximum: float) -> Validator:
    """Return a validator that requires a numeric answer within [minimum, maximum]."""
    def _validate(raw: str) -> tuple[bool, str]:
        try:
            value = float(raw.strip())
            ok = minimum <= value <= maximum
            return ok, "" if ok else f"Answer must be between {minimum} and {maximum}."
        except ValueError:
            return False, "Answer must be a number."
    return _validate


__all__ = [
    "CustomizationResult",
    "TemplateCustomizer",
    "Validator",
    "WizardQuestion",
    "WizardSession",
    "WizardState",
    "choice_validator",
    "min_length_validator",
    "non_empty_validator",
    "numeric_range_validator",
]
