# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Orchestration of the report explanation. Independent of Thrift and of the
database, so it is testable without a server.
"""

from dataclasses import dataclass, field
from typing import Any, Optional

from codechecker_common.logger import get_logger

from .client import AIProviderError, parse_json_response, request_completion
from .config import AIConfig
from .prompt import CONFIDENCES, SYSTEM_PROMPT, VERDICTS, build_user_prompt

LOG = get_logger('server')


@dataclass
class PathEvent:
    """ One step of the analyser's bug path. """
    file_path: str
    line: int
    message: str


@dataclass
class MacroExpansion:
    """ A macro on the bug path, as the analyser expanded it. """
    file_path: str
    line: int
    text: str


@dataclass
class ReportContext:
    """ Everything the model is told about a report. """
    checker_name: str
    checker_message: str
    file_path: str
    line: int
    column: int = 0
    analyzer_name: Optional[str] = None
    severity: Optional[str] = None
    file_content: Optional[str] = None
    checker_documentation: Optional[str] = None
    path_events: list[PathEvent] = field(default_factory=list)
    # The files the bug path passes through: path -> content.
    path_files: dict[str, str] = field(default_factory=dict)
    macro_expansions: list[MacroExpansion] = field(default_factory=list)


@dataclass
class Explanation:
    """ The structured answer rendered by the GUI. """
    background: str
    verdict: str
    confidence: str
    true_positive_case: str
    false_positive_case: str
    model: str


def _coerce_choice(value: Any, allowed: tuple, fallback: str) -> str:
    """ ``value`` as one of ``allowed``, tolerating case and spacing. """
    if isinstance(value, str):
        choice = value.strip().upper().replace(' ', '_').replace('-', '_')
        if choice in allowed:
            return choice

    LOG.debug("AI answer had an unknown value %r, using %s.", value, fallback)
    return fallback


def explain_report(context: ReportContext,
                   ai_config: AIConfig,
                   model_id: Optional[str] = None) -> Explanation:
    """
    Ask the configured model to explain ``context``. The default model is
    asked when ``model_id`` is empty.
    """
    model_config = ai_config.get_model(model_id)
    if not model_config:
        raise AIProviderError(
            f"The AI model '{model_id}' is not available on this server.")

    user_prompt = build_user_prompt(context,
                                    ai_config.max_source_lines,
                                    ai_config.max_path_events,
                                    ai_config.max_path_context_lines)

    if not ai_config.request_slots.acquire(block=False):
        raise AIProviderError(
            "The server is busy with other AI explanations. Try again in a "
            "minute.")

    LOG.debug("Requesting an explanation of %s from '%s'.",
              context.checker_name, model_config.id)
    try:
        raw = request_completion(model_config, SYSTEM_PROMPT, user_prompt,
                                 ai_config.timeout, ai_config.ca_bundle)
    finally:
        ai_config.request_slots.release()

    answer = parse_json_response(raw)
    if not isinstance(answer, dict):
        raise AIProviderError(
            "The model did not return a JSON object.")

    background = answer.get('background')
    if not background:
        raise AIProviderError(
            "The AI answer did not contain an explanation.")

    return Explanation(
        background=background,
        verdict=_coerce_choice(answer.get('verdict'), VERDICTS, 'UNCERTAIN'),
        confidence=_coerce_choice(answer.get('confidence'), CONFIDENCES,
                                  'LOW'),
        true_positive_case=answer.get('true_positive_case', ''),
        false_positive_case=answer.get('false_positive_case', ''),
        model=model_config.id)
