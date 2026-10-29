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

from codechecker_common.logger import get_logger

LOG = get_logger('server')

DEFAULT_TIMEOUT = 90  # seconds
DEFAULT_MAX_SOURCE_LINES = 400
DEFAULT_MAX_PATH_EVENTS = 50

# The ratings an administrator may give a model, shown in the GUI.
SPEEDS = ('slow', 'medium', 'fast')
RELIABILITIES = ('low', 'medium', 'high')


class AIModelConfig:
    """ One model the GUI may offer. """

    def __init__(self, raw):
        if not raw.get('id'):
            raise ValueError("An AI model entry is missing the 'id' field.")

        self.id = raw['id']
        self.display_name = raw.get('display_name', self.id)

        # A LiteLLM provider, e.g. 'anthropic'.
        self.provider = str(raw.get('provider') or '').strip().lower()
        if not self.provider:
            raise ValueError(f"AI model '{self.id}' has no 'provider'.")

        # The provider's own model name.
        self.model = raw.get('model', self.id)

        # Or a command that prints an access token.
        self.token_command = raw.get('token_command') or None
        self.token_command_dir = raw.get('token_command_dir') or None

        # A self-hosted api_base may not need a key.
        self.api_key = raw.get('api_key') or None
        self.api_base = raw.get('api_base') or None
        if not (self.api_key or self.token_command or self.api_base):
            raise ValueError(
                f"AI model '{self.id}' of provider '{self.provider}' has no "
                "'api_key'.")

        # Some models, e.g. Claude, reject a temperature.
        self.temperature = raw.get('temperature')

        # How quick and how trustworthy its answers have proven, as rated
        # by the administrator. None when not rated.
        self.speed = self._rating(raw, 'speed', SPEEDS)
        self.reliability = self._rating(raw, 'reliability', RELIABILITIES)

    @property
    def litellm_model(self):
        """ The model name with the provider prefix LiteLLM routes by. """
        # Proxy model names may contain slashes.
        if self.provider != 'litellm_proxy' and \
                self.model.startswith(f"{self.provider}/"):
            return self.model

        return f"{self.provider}/{self.model}"

    def _rating(self, raw, key, allowed):
        value = raw.get(key)
        if value is None:
            return None

        value = str(value).strip().lower()
        if value not in allowed:
            LOG.warning("Ignoring the %s '%s' of AI model '%s'; use one of: "
                        "%s.", key, raw[key], self.id, ', '.join(allowed))
            return None

        return value


class AIConfig:
    def __init__(self, raw=None):
        raw = raw or {}

        self.enabled = raw.get('enabled', False)
        self.timeout = raw.get('timeout', DEFAULT_TIMEOUT)
        self.max_source_lines = raw.get('max_source_lines',
                                        DEFAULT_MAX_SOURCE_LINES)
        self.max_path_events = raw.get('max_path_events',
                                       DEFAULT_MAX_PATH_EVENTS)

        # CA certificates for every provider.
        self.ca_bundle = raw.get('ca_bundle') or None
        if self.ca_bundle:
            self.ca_bundle = os.path.expanduser(self.ca_bundle)
            if not os.path.exists(self.ca_bundle):
                LOG.warning("The AI 'ca_bundle' %s does not exist, "
                            "using the default certificates.", self.ca_bundle)
                self.ca_bundle = None

        self.models = []
        for entry in raw.get('models', []):
            try:
                model = AIModelConfig(entry)
            except ValueError as ex:
                # The shipped config has empty keys.
                if self.enabled:
                    LOG.warning("Ignoring AI model: %s", ex)
                continue

            self.models.append(model)

        # Only looked up here, as it is slow to import.
        self.has_litellm = importlib.util.find_spec('litellm') is not None
        if self.enabled and not self.has_litellm:
            LOG.warning("AI report explanation is enabled but the 'litellm' "
                        "package is not installed; the feature stays turned "
                        "off. Install web/requirements.txt.")

        configured_default = raw.get('default_model')
        if configured_default and not self.get_model(configured_default):
            if self.enabled:
                LOG.warning(
                    "The configured default AI model '%s' is not available, "
                    "falling back to the first model.",
                    configured_default)
            configured_default = None

        self.default_model = configured_default or (
            self.models[0].id if self.models else None)

        if self.enabled and not self.models:
            LOG.warning("AI report explanation is enabled but no model is "
                        "configured; the feature stays turned off.")

    @property
    def is_available(self):
        """ On, with LiteLLM installed and a model to offer. """
        return self.enabled and self.has_litellm and \
            bool(self.models)

    def get_model(self, model_id):
        """ ``model_id``, or the default when empty. None if unknown. """
        return self.pick_model(model_id, self.models)

    def pick_model(self, model_id, models):
        """
        ``model_id`` from ``models``. When empty, the default model if it
        is among them, else the first. None if there is no such model.
        """
        if model_id:
            return next((m for m in models if m.id == model_id), None)

        return next((m for m in models if m.id == self.default_model),
                    models[0] if models else None)
