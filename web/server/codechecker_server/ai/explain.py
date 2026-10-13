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

from codechecker_common.logger import get_logger

from .prompt import SYSTEM_PROMPT, VERDICTS, build_user_prompt
from .client import AIClient, AIProviderError, parse_json_response

LOG = get_logger('server')


@dataclass
class PathEvent:
    """ One step of the analyser's bug path. """
    file_path: str
    line: int
    message: str


@dataclass
class ReportContext:
    """ Everything the model is told about a report. """
    checker_name: str
    checker_message: str
    file_path: str
    line: int
    column: int = 0
    analyzer_name: str = None
    severity: str = None
    file_content: str = None
    checker_documentation: str = None
    path_events: list = field(default_factory=list)


@dataclass
class Explanation:
    """ The structured answer rendered by the GUI. """
    background: str
    verdict: str
    confidence: int
    true_positive_case: str
    false_positive_case: str
    model: str


def _coerce_confidence(value):
    """ Models answer with a string or a 0-1 float often enough. """
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        LOG.debug("AI answer had an unusable confidence: %r", value)
        return 0

    if 0 < confidence <= 1:  # a probability rather than a percentage
        confidence *= 100

    return max(0, min(100, int(confidence)))


def _coerce_verdict(value):
    if not isinstance(value, str):
        return 'UNCERTAIN'

    verdict = value.strip().upper().replace(' ', '_').replace('-', '_')

    if verdict not in VERDICTS:
        LOG.debug("AI answer had an unknown verdict: %r", value)
        return 'UNCERTAIN'

    return verdict


def explain_report(context, ai_config, model_id=None, user=None,
                   models=None):
    """
    Ask the configured model to explain ``context``. ``user`` is the logged
    in user the request is made for, if EricAI is told about it. ``models``
    are the ones to choose from; the configured ones by default.
    """
    if not ai_config.is_available:
        raise AIProviderError(
            "AI report explanation is not enabled on this server.")

    model_config = ai_config.pick_model(
        model_id, ai_config.models if models is None else models)
    if not model_config:
        raise AIProviderError(
            f"The AI model '{model_id}' is not available on this server.")

    client = AIClient(ai_config.ericai, model_config, ai_config.timeout)
    client.on_behalf_of = user

    user_prompt = build_user_prompt(context,
                                    ai_config.max_source_lines,
                                    ai_config.max_path_events)

    LOG.debug("Requesting an explanation of %s from '%s'.",
              context.checker_name, model_config.id)

    raw = client.complete(SYSTEM_PROMPT, user_prompt)
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
        verdict=_coerce_verdict(answer.get('verdict')),
        confidence=_coerce_confidence(answer.get('confidence')),
        true_positive_case=answer.get('true_positive_case', ''),
        false_positive_case=answer.get('false_positive_case', ''),
        model=model_config.id)
