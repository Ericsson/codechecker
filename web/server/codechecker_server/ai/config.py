# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
The ``ai`` section of ``server_config.json``.
See docs/web/server_config.md for the reference.
"""

import importlib.util
import os
from typing import Optional

from codechecker_common.compatibility.multiprocessing import BoundedSemaphore
from codechecker_common.logger import get_logger

LOG = get_logger('server')

DEFAULT_TIMEOUT = 90  # seconds
DEFAULT_MAX_SOURCE_LINES = 400
DEFAULT_MAX_PATH_EVENTS = 50
DEFAULT_MAX_PATH_CONTEXT_LINES = 200
DEFAULT_MAX_CONCURRENT_REQUESTS = 2


class AIModelConfig:
    """ One model the GUI may offer. """

    def __init__(self, raw: dict):
        self.id: str = raw['id']
        self.display_name: str = raw.get('display_name', self.id)

        # A LiteLLM provider, e.g. 'anthropic'.
        self.provider: str = str(raw.get('provider') or '').strip().lower()

        # The provider's own model name.
        self.model: str = raw.get('model', self.id)

        self.api_key: Optional[str] = raw.get('api_key') or None
        self.api_base: Optional[str] = raw.get('api_base') or None

        # Instead of an api_key, a command that prints a short-lived access
        # token, for providers that do not hand out long-lived keys.
        self.token_command: Optional[str] = raw.get('token_command') or None
        self.token_command_dir: Optional[str] = \
            raw.get('token_command_dir') or None

        # Some models, e.g. Claude, reject a temperature.
        self.temperature: Optional[float] = raw.get('temperature')

    @property
    def litellm_model(self) -> str:
        """ The model name with the provider prefix LiteLLM routes by. """
        # Proxy model names may contain slashes.
        if self.provider != 'litellm_proxy' and \
                self.model.startswith(f"{self.provider}/"):
            return self.model

        return f"{self.provider}/{self.model}"


def model_config_problem(raw: dict) -> Optional[str]:
    """ Why the model entry ``raw`` cannot be used, None if it can. """
    if not raw.get('id'):
        return "An AI model entry is missing the 'id' field."

    if not str(raw.get('provider') or '').strip():
        return f"AI model '{raw['id']}' has no 'provider'."

    # A self-hosted api_base may not need a key.
    if not (raw.get('api_key') or raw.get('token_command') or
            raw.get('api_base')):
        return f"AI model '{raw['id']}' has no 'api_key'."

    return None


class AIConfig:
    def __init__(self, raw: Optional[dict] = None):
        raw = raw or {}

        self.enabled: bool = raw.get('enabled', False)
        self.timeout: float = raw.get('timeout', DEFAULT_TIMEOUT)
        self.max_source_lines: int = raw.get('max_source_lines',
                                             DEFAULT_MAX_SOURCE_LINES)
        self.max_path_events: int = raw.get('max_path_events',
                                            DEFAULT_MAX_PATH_EVENTS)
        self.max_path_context_lines: int = raw.get(
            'max_path_context_lines', DEFAULT_MAX_PATH_CONTEXT_LINES)

        # Created before the API worker processes are started, so they all
        # share it. A request holds an API worker until the model answers.
        self.request_slots = BoundedSemaphore(
            max(1, raw.get('max_concurrent_requests',
                           DEFAULT_MAX_CONCURRENT_REQUESTS)))

        # CA certificates for every provider.
        self.ca_bundle: Optional[str] = raw.get('ca_bundle') or None
        if self.ca_bundle:
            self.ca_bundle = os.path.expanduser(self.ca_bundle)
            if not os.path.exists(self.ca_bundle):
                LOG.warning("The AI 'ca_bundle' %s does not exist, "
                            "using the default certificates.", self.ca_bundle)
                self.ca_bundle = None

        self.models: list[AIModelConfig] = []
        for entry in raw.get('models', []):
            problem = model_config_problem(entry)
            if problem:
                # The shipped config has empty keys.
                if self.enabled:
                    LOG.warning("Ignoring AI model: %s", problem)
                continue

            self.models.append(AIModelConfig(entry))

        # Only looked up here, as it is slow to import.
        self.has_litellm: bool = \
            importlib.util.find_spec('litellm') is not None
        if self.enabled and not self.has_litellm:
            LOG.warning("AI report explanation is enabled but the 'litellm' "
                        "package is not installed; the feature stays turned "
                        "off. Install "
                        "web/requirements_py/ai/requirements.txt.")

        self.default_model: Optional[str] = raw.get('default_model')
        if self.default_model and not any(m.id == self.default_model
                                          for m in self.models):
            if self.enabled:
                LOG.warning(
                    "The configured default AI model '%s' is not available, "
                    "falling back to the first model.", self.default_model)
            self.default_model = None

        if not self.default_model and self.models:
            self.default_model = self.models[0].id

        if self.enabled and not self.models:
            LOG.warning("AI report explanation is enabled but no model is "
                        "configured; the feature stays turned off.")

    @property
    def is_available(self) -> bool:
        """ On, with LiteLLM installed and a model to offer. """
        return self.enabled and self.has_litellm and bool(self.models)

    def get_model(self, model_id: Optional[str] = None) \
            -> Optional[AIModelConfig]:
        """ ``model_id``, or the default model when empty. None if unknown. """
        model_id = model_id or self.default_model
        return next((m for m in self.models if m.id == model_id), None)
