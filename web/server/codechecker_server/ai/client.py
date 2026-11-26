# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Asks a model through LiteLLM.
"""

import functools
import json
import os
import shlex
import subprocess
import threading
import time
from typing import Any, Optional

from authlib.common.encoding import to_bytes, urlsafe_b64decode

from codechecker_common.logger import get_logger
from codechecker_common.util import clamp

from .config import AIModelConfig
from .prompt import answer_schema

LOG = get_logger('server')

# Busy or briefly down, rather than refusing the request.
# Not left to LiteLLM, which retries every error without waiting.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

MAX_ATTEMPTS = 3


class AIProviderError(Exception):
    """
    The model could not produce a usable answer. The message is shown to the
    user, so it must not contain details of the server's environment.
    """


class TokenCommandCache:
    """ Access tokens printed by a ``token_command``, reused until expiry. """

    # Renew this long before expiry, so a token never lapses mid-request.
    EXPIRY_MARGIN = 120  # seconds

    # Assumed when a token does not tell its own expiry.
    DEFAULT_LIFETIME = 3000  # seconds

    def __init__(self):
        self._lock = threading.Lock()
        self._tokens: dict[tuple, tuple[str, float]] = {}

    @staticmethod
    def _key(model: AIModelConfig) -> tuple:
        return (model.token_command, model.token_command_dir)

    def get(self, model: AIModelConfig, timeout: float) -> str:
        # Held while the command runs, so concurrent requests wait for one
        # token rather than each fetching their own.
        with self._lock:
            cached = self._tokens.get(self._key(model))
            if cached and cached[1] > time.monotonic() + self.EXPIRY_MARGIN:
                return cached[0]

            token = self._run_token_command(model, timeout)
            self._tokens[self._key(model)] = \
                (token, time.monotonic() + self._jwt_lifetime(token))
            return token

    def invalidate(self, model: AIModelConfig):
        with self._lock:
            self._tokens.pop(self._key(model), None)

    @staticmethod
    def _run_token_command(model: AIModelConfig, timeout: float) -> str:
        """
        The command prints the token on its standard output. It must not
        wait for an interactive login, which nobody would ever complete.
        """
        cwd = model.token_command_dir
        try:
            result = subprocess.run(shlex.split(model.token_command),
                                    capture_output=True,
                                    text=True,
                                    timeout=timeout,
                                    cwd=os.path.expanduser(cwd)
                                    if cwd else None,
                                    check=False)
        except (OSError, ValueError, subprocess.TimeoutExpired) as ex:
            LOG.warning("Could not run the token command of AI model '%s': "
                        "%s", model.id, ex)
            raise AIProviderError(
                f"The token command of AI model '{model.id}' failed. See the "
                "server log for details.") from ex

        # Never the output: it is the token, or part of one.
        if result.returncode != 0:
            LOG.warning("The token command of AI model '%s' failed with exit "
                        "code %d: %s", model.id, result.returncode,
                        (result.stderr or '').strip()[-300:])
            raise AIProviderError(
                f"The token command of AI model '{model.id}' failed. See the "
                "server log for details.")

        lines = (result.stdout or '').strip().splitlines()
        token = lines[-1].strip() if lines else ''
        if not token:
            raise AIProviderError(
                f"The token command of AI model '{model.id}' did not print a "
                "token.")

        return token

    @classmethod
    def _jwt_lifetime(cls, token: str) -> float:
        """ Seconds until the ``exp`` claim, read without verification. """
        try:
            payload = urlsafe_b64decode(to_bytes(token.split('.')[1]))
            return json.loads(payload)['exp'] - time.time()
        except (IndexError, KeyError, TypeError, ValueError):
            return cls.DEFAULT_LIFETIME


TOKEN_CACHE = TokenCommandCache()


@functools.cache
def _litellm() -> Any:
    """ Imported on the first request: it is optional and slow to import. """
    # Otherwise LiteLLM downloads its model price list from GitHub on import,
    # which slows down or fails on a server without internet access.
    os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')

    try:
        import litellm
    except ImportError as ex:
        raise AIProviderError(
            "The 'litellm' package is required for AI report explanation. "
            "Install web/requirements_py/ai/requirements.txt.") from ex

    litellm.suppress_debug_info = True
    return litellm


def request_completion(model: AIModelConfig,
                       system_prompt: str,
                       user_prompt: str,
                       timeout: float,
                       ca_bundle: Optional[str] = None) -> str:
    """
    Ask ``model`` and return its raw answer. Retries and a renewed token all
    fit into ``timeout`` seconds.
    """
    litellm = _litellm()

    if ca_bundle:
        # LiteLLM takes it only globally.
        litellm.ssl_verify = ca_bundle

    messages = [{'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}]
    deadline = time.monotonic() + timeout

    try:
        response = _completion_with_retries(model, messages, deadline,
                                            timeout)
    except litellm.exceptions.AuthenticationError as ex:
        LOG.warning("AI model '%s' rejected the credentials: %s", model.id, ex)
        if not model.token_command:
            raise AIProviderError(
                f"{model.provider} rejected the API key of model "
                f"'{model.id}'.") from ex

        # A token can be revoked before it expires; fetch a new one and try
        # once more.
        TOKEN_CACHE.invalidate(model)
        try:
            response = _completion_with_retries(model, messages, deadline,
                                                timeout)
        except litellm.exceptions.AuthenticationError as retry_ex:
            raise AIProviderError(
                f"{model.provider} rejected the access token.") from retry_ex

    return _answer_text(model, response)


def _completion_with_retries(model: AIModelConfig,
                             messages: list[dict],
                             deadline: float,
                             timeout: float) -> Any:
    """
    The completion, sent again while the provider is busy. An
    AuthenticationError is raised as it is, every other failure as an
    AIProviderError.
    """
    litellm = _litellm()

    for attempt in range(MAX_ATTEMPTS):
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise AIProviderError(
                f"{model.provider} did not answer within {timeout} seconds.")

        try:
            return litellm.completion(
                model=model.litellm_model,
                messages=messages,
                response_format=_response_format(model),
                timeout=remaining,
                max_retries=0,
                drop_params=True,
                api_key=_api_key(model, remaining),
                api_base=model.api_base,
                temperature=model.temperature)
        except litellm.exceptions.AuthenticationError:
            raise
        except AIProviderError:
            raise
        except Exception as ex:
            delay = _retry_delay(ex, attempt)
            if delay is None or attempt == MAX_ATTEMPTS - 1 or \
                    time.monotonic() + delay >= deadline:
                raise _provider_error(model, ex, timeout) from ex

            LOG.info("AI model '%s' answered with HTTP %s; retrying in %.1fs "
                     "(attempt %d of %d).", model.id, ex.status_code, delay,
                     attempt + 1, MAX_ATTEMPTS)
            time.sleep(delay)

    raise AssertionError("unreachable")


def _api_key(model: AIModelConfig, timeout: float) -> Optional[str]:
    if model.token_command:
        return TOKEN_CACHE.get(model, timeout)
    else:
        return model.api_key


def _response_format(model: AIModelConfig) -> dict:
    """ The answer schema where supported, else plain JSON. """
    # LiteLLM cannot tell what the models behind a proxy support.
    if model.provider != 'litellm_proxy':
        try:
            strict = _litellm().supports_response_schema(
                model=model.litellm_model)
        except Exception:
            strict = False

        if strict:
            return {'type': 'json_schema',
                    'json_schema': {'name': 'report_explanation',
                                    'schema': answer_schema(),
                                    'strict': True}}

    return {'type': 'json_object'}


def _retry_delay(ex: Exception, attempt: int) -> Optional[float]:
    """
    Seconds to wait before sending a failed request again, or None when it
    is not worth sending again.
    """
    if getattr(ex, 'status_code', None) not in RETRYABLE_STATUS:
        return None

    response = getattr(ex, 'response', None)
    headers = getattr(response, 'headers', None) or {}
    try:
        return clamp(0.0, float(headers['Retry-After']), 30.0)
    except (KeyError, ValueError):
        # No Retry-After, or one with a date instead of a number of seconds.
        pass

    # Waits before the 2nd and the 3rd attempt.
    backoff = (1.0, 3.0)
    return backoff[min(attempt, len(backoff) - 1)]


def _provider_error(model: AIModelConfig,
                    ex: Exception,
                    timeout: float) -> AIProviderError:
    """ What the user is told about a failed request. """
    LOG.warning("Request to AI model '%s' failed: %s", model.id, ex)
    exceptions = _litellm().exceptions

    if isinstance(ex, exceptions.Timeout):
        return AIProviderError(
            f"{model.provider} did not answer within {timeout} seconds.")

    if isinstance(ex, exceptions.RateLimitError):
        return AIProviderError(
            f"{model.provider} refused the request: rate limit or quota "
            "reached.")

    if isinstance(ex, exceptions.APIConnectionError):
        return AIProviderError(f"Could not reach {model.provider}.")

    status = getattr(ex, 'status_code', None)
    return AIProviderError(
        f"{model.provider} answered with "
        f"{f'HTTP {status}' if status else 'an error'}. See the server log "
        "for details.")


def _answer_text(model: AIModelConfig, response: Any) -> str:
    try:
        choice = response.choices[0]
        content = choice.message.content
    except (AttributeError, IndexError, TypeError) as ex:
        raise AIProviderError(
            f"The {model.provider} response did not contain a "
            "completion.") from ex

    if getattr(choice, 'finish_reason', None) == 'length':
        LOG.warning("The answer of '%s' was truncated at the token limit.",
                    model.id)

    return content


def parse_json_response(text: str) -> Any:
    """ Decode the answer, unwrapping a Markdown fence if one is there. """
    if not text:
        raise AIProviderError("The model returned an empty answer.")

    cleaned = text.strip()

    if cleaned.startswith('```'):
        lines = cleaned.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith('```'):
            lines = lines[:-1]
        cleaned = '\n'.join(lines).strip()

    try:
        return json.loads(cleaned)
    except ValueError as ex:
        LOG.debug("Unparsable AI answer: %s", cleaned[:1000])
        raise AIProviderError(
            "The model did not return valid JSON.") from ex
