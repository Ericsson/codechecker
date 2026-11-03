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

import base64
import json
import os
import re
import shlex
import subprocess
import threading
import time

from codechecker_common.logger import get_logger

from .prompt import answer_schema

LOG = get_logger('server')

# Busy or briefly down, rather than refusing the request.
# Not left to LiteLLM, which retries every error without waiting.
RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})

MAX_ATTEMPTS = 3
BACKOFF_SCHEDULE = (1.0, 3.0)  # before the 2nd and 3rd


class AIProviderError(Exception):
    """ Raised when the model could not produce a usable answer. """


class OAuth2TokenCache:
    """ Tokens of a ``token_command``, shared until they near expiry. """

    # Renew this long before expiry, so a token never lapses mid-request.
    EXPIRY_MARGIN = 120  # seconds

    def __init__(self):
        self._lock = threading.Lock()
        self._tokens = {}

    # Assumed when a token does not tell its own expiry.
    DEFAULT_LIFETIME = 3000  # seconds

    @staticmethod
    def _key(model):
        return (model.token_command, model.token_command_dir)

    def get(self, model, timeout):
        # Held during the request, so concurrent explanations wait for one
        # token rather than each fetching their own.
        with self._lock:
            cached = self._tokens.get(self._key(model))
            if cached and cached[1] > time.monotonic() + self.EXPIRY_MARGIN:
                return cached[0]

            token, lifetime = self._run_token_command(
                model.token_command, timeout, model.token_command_dir)
            self._tokens[self._key(model)] = \
                (token, time.monotonic() + lifetime)
            return token

    def invalidate(self, model):
        with self._lock:
            self._tokens.pop(self._key(model), None)

    @classmethod
    def _run_token_command(cls, command, timeout, cwd=None):
        """
        The command prints the token on its standard output. It must not
        wait for an interactive login, which nobody would ever complete.
        """
        try:
            result = subprocess.run(shlex.split(command),
                                    capture_output=True,
                                    text=True,
                                    timeout=timeout,
                                    cwd=os.path.expanduser(cwd)
                                    if cwd else None,
                                    check=False)
        except (OSError, ValueError, subprocess.TimeoutExpired) as ex:
            raise AIProviderError(
                f"Could not run the token command: {ex}") from ex

        # Never the output: it is the token, or part of one.
        if result.returncode != 0:
            detail = (result.stderr or '').strip()[-300:]
            raise AIProviderError(
                "The token command failed with exit code "
                f"{result.returncode}. {detail}".strip())

        lines = (result.stdout or '').strip().splitlines()
        token = lines[-1].strip() if lines else ''
        if not token:
            raise AIProviderError(
                "The token command did not print a token.")

        return token, cls._jwt_lifetime(token)

    @classmethod
    def _jwt_lifetime(cls, token):
        """ Seconds until the ``exp`` claim, read without verification. """
        try:
            payload = token.split('.')[1]
            payload += '=' * (-len(payload) % 4)
            claims = json.loads(base64.urlsafe_b64decode(payload))
            return int(claims['exp'] - time.time())
        except (IndexError, KeyError, TypeError, ValueError):
            return cls.DEFAULT_LIFETIME


OAUTH2_TOKENS = OAuth2TokenCache()


def _litellm():
    """ Imported late: optional and slow to import. """
    # Otherwise it downloads its price list on import.
    os.environ.setdefault('LITELLM_LOCAL_MODEL_COST_MAP', 'True')

    try:
        import litellm
    except ImportError as ex:
        raise AIProviderError(
            "The 'litellm' package is required for AI report explanation. "
            "Install web/requirements.txt.") from ex

    litellm.suppress_debug_info = True
    return litellm


def _completion(**kwargs):
    """ Replaced by the tests. """
    return _litellm().completion(**kwargs)


class AIClient:
    """ Asks one model for a completion. """

    def __init__(self, model_config, timeout, ca_bundle=None):
        self._model = model_config
        self._timeout = timeout
        self._ca_bundle = ca_bundle

    @property
    def _where(self):
        return self._model.provider

    def complete(self, system_prompt, user_prompt):
        """ Send the prompts, return the raw answer as a JSON string. """
        if not self._model.token_command:
            return self._complete(system_prompt, user_prompt)

        try:
            return self._complete(system_prompt, user_prompt)
        except _TokenRejected:
            # A token can be revoked before it expires; fetch a new one
            # and try once more.
            OAUTH2_TOKENS.invalidate(self._model)

        try:
            return self._complete(system_prompt, user_prompt)
        except _TokenRejected as ex:
            raise AIProviderError(
                f"{self._where} rejected the access token.") from ex

    def _complete(self, system_prompt, user_prompt):
        litellm = _litellm()

        kwargs = {
            'model': self._model.litellm_model,
            'messages': [
                {'role': 'system', 'content': system_prompt},
                {'role': 'user', 'content': user_prompt}
            ],
            'response_format': self._response_format(litellm),
            'timeout': self._timeout,
            # Retried in _call.
            'max_retries': 0,
            'drop_params': True
        }

        if self._model.temperature is not None:
            kwargs['temperature'] = self._model.temperature

        # LiteLLM takes it only globally.
        if self._ca_bundle:
            litellm.ssl_verify = self._ca_bundle

        kwargs['api_key'] = self._model.api_key
        if self._model.token_command:
            kwargs['api_key'] = OAUTH2_TOKENS.get(self._model, self._timeout)
        if self._model.api_base:
            kwargs['api_base'] = self._model.api_base

        return self._send(litellm, kwargs)

    def _response_format(self, litellm):
        """ The answer schema where supported, else plain JSON. """
        # Unknown for the models behind a proxy.
        if self._model.provider != 'litellm_proxy':
            try:
                strict = litellm.supports_response_schema(
                    model=self._model.litellm_model)
            except Exception:
                strict = False

            if strict:
                return {'type': 'json_schema',
                        'json_schema': {'name': 'report_explanation',
                                        'schema': answer_schema(),
                                        'strict': True}}

        return {'type': 'json_object'}

    @staticmethod
    def _is_retryable(ex):
        """ Whether a failed request is worth sending again. """
        return getattr(ex, 'status_code', None) in RETRYABLE_STATUS

    @staticmethod
    def _retry_delay(ex, attempt):
        """ Retry-After when the provider sends one, else the schedule. """
        response = getattr(ex, 'response', None)
        headers = getattr(response, 'headers', None) or {}
        retry_after = headers.get('Retry-After')
        if retry_after:
            try:
                return max(0.0, min(float(retry_after), 30.0))
            except ValueError:
                pass  # an HTTP date rather than seconds

        return BACKOFF_SCHEDULE[min(attempt, len(BACKOFF_SCHEDULE) - 1)]

    def _call(self, kwargs):
        """ litellm.completion, retried on transient failures. """
        for attempt in range(MAX_ATTEMPTS - 1):
            try:
                return _completion(**kwargs)
            except Exception as ex:
                if not self._is_retryable(ex):
                    raise

                delay = self._retry_delay(ex, attempt)
                LOG.info("%s answered with HTTP %s; retrying in %.1fs "
                         "(attempt %d of %d).", self._where, ex.status_code,
                         delay, attempt + 1, MAX_ATTEMPTS)
                time.sleep(delay)

        return _completion(**kwargs)

    def _send(self, litellm, kwargs):
        """ The answer text of the completion. """
        try:
            response = self._call(kwargs)
        except litellm.exceptions.AuthenticationError as ex:
            if self._model.token_command:
                raise _TokenRejected(_reason(ex)) from ex
            raise AIProviderError(
                f"{self._where} rejected the API key of model "
                f"'{self._model.id}'.") from ex
        except litellm.exceptions.Timeout as ex:
            raise AIProviderError(
                f"{self._where} did not answer within {self._timeout} "
                "seconds.") from ex
        except litellm.exceptions.RateLimitError as ex:
            raise AIProviderError(
                f"{self._where} refused the request: rate limit or quota "
                f"reached. {_reason(ex)}".strip()) from ex
        except litellm.exceptions.APIConnectionError as ex:
            raise AIProviderError(
                f"Could not reach {self._where}: {_reason(ex)}") from ex
        except Exception as ex:
            status = getattr(ex, 'status_code', None)
            LOG.debug("LiteLLM request failed.", exc_info=True)
            raise AIProviderError(
                f"{self._where} answered with "
                f"{f'HTTP {status}' if status else 'an error'}. "
                f"{_reason(ex)}".strip()) from ex

        try:
            choice = response.choices[0]
            content = choice.message.content
        except (AttributeError, IndexError, TypeError) as ex:
            raise AIProviderError(
                f"The {self._where} response did not contain a "
                "completion.") from ex

        if getattr(choice, 'finish_reason', None) == 'length':
            LOG.warning("The answer of '%s' was truncated at the token "
                        "limit.", self._model.id)

        return content


class _TokenRejected(Exception):
    """ The provider answered 401. """


def _reason(ex):
    """ The provider's message without LiteLLM's prefixes. """
    message = str(getattr(ex, 'message', None) or ex)
    message = re.sub(r'^.*?\w+Exception - ', '', message, flags=re.DOTALL)
    message = re.sub(r'^((litellm\.)?\w+Error: )+', '', message)
    return message.strip()[:500]


def parse_json_response(text):
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
