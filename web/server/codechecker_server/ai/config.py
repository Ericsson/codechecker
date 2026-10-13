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

DEFAULT_TIMEOUT = 60  # seconds
DEFAULT_MAX_SOURCE_LINES = 400
DEFAULT_MAX_PATH_EVENTS = 50

# The ratings an administrator may give a model, shown in the GUI.
SPEEDS = ('slow', 'medium', 'fast')
RELIABILITIES = ('low', 'medium', 'high')

# Any other provider is asked directly through LiteLLM.
ERICAI = 'ericai'

# EricAI takes a short-lived access token that is obtained in one of two
# ways.

# As the server's own service principal (OAuth2 client credentials flow).
CLIENT_CREDENTIAL_FIELDS = ('token_url', 'client_id', 'client_secret', 'scope')


class EricAIConfig:
    """ The EricAI endpoint and the credentials to reach it. """

    def __init__(self, raw):
        # The LiteLLM endpoint of EricAI.
        self.api_url = raw.get('api_url')
        if not self.api_url:
            raise ValueError("The 'ericai' section is missing: api_url.")

        # Or as a signed in user: a command that prints an access token,
        # e.g. the ericai client's own, which renews its login by itself.
        self.token_command = raw.get('token_command') or None

        # Where to run it: the ericai client keeps its login record in the
        # working directory it was signed in from.
        self.token_command_dir = raw.get('token_command_dir') or None

        self.token_url = raw.get('token_url')
        self.client_id = raw.get('client_id')
        self.client_secret = raw.get('client_secret')
        self.scope = raw.get('scope')

        if not self.token_command:
            missing = [key for key in CLIENT_CREDENTIAL_FIELDS
                       if not raw.get(key)]
            if missing:
                raise ValueError(
                    "The 'ericai' section needs either 'token_command' or "
                    f"the client credentials; missing: {', '.join(missing)}.")

        # Names the logged in user to EricAI, as an e-mail address.
        self.user_header = raw.get('user_header')
        self.user_email_domain = raw.get('user_email_domain')

        # CA certificates to verify EricAI and the token endpoint with. The
        # Ericsson internal CA is in the system store but not in the bundle
        # Python's requests ships with.
        self.ca_bundle = raw.get('ca_bundle') or None
        if self.ca_bundle:
            self.ca_bundle = os.path.expanduser(self.ca_bundle)
            if not os.path.exists(self.ca_bundle):
                LOG.warning("The EricAI 'ca_bundle' %s does not exist, "
                            "using the default certificates.", self.ca_bundle)
                self.ca_bundle = None

    @property
    def verify(self):
        """ The ``verify`` argument of requests. """
        return self.ca_bundle or True

    @property
    def api_base(self):
        """ The root of the OpenAI style API, under /chat/completions. """
        root = self.api_url.rstrip('/')
        if root.endswith('/chat/completions'):
            root = root[:-len('/chat/completions')]
        return root


class AIModelConfig:
    """ One model the GUI may offer, through EricAI or directly. """

    def __init__(self, raw):
        if not raw.get('id'):
            raise ValueError("An AI model entry is missing the 'id' field.")

        self.id = raw['id']
        self.display_name = raw.get('display_name', self.id)

        self.provider = str(raw.get('provider') or ERICAI).strip().lower()

        # The model name EricAI routes, or the provider's own model name.
        self.model = raw.get('model', self.id)

        # A self-hosted api_base may not need a key.
        self.api_key = raw.get('api_key') or None
        self.api_base = raw.get('api_base') or None
        if self.is_direct and not (self.api_key or self.api_base):
            raise ValueError(
                f"AI model '{self.id}' of provider '{self.provider}' has no "
                "'api_key'.")

        # Some direct models, e.g. Claude, reject a temperature.
        self.temperature = raw.get('temperature',
                                   None if self.is_direct else 0.2)

        # How quick and how trustworthy its answers have proven, as rated
        # by the administrator. None when not rated.
        self.speed = self._rating(raw, 'speed', SPEEDS)
        self.reliability = self._rating(raw, 'reliability', RELIABILITIES)

    @property
    def is_direct(self):
        """ Asked at its provider with an API key, not through EricAI. """
        return self.provider != ERICAI

    @property
    def litellm_model(self):
        """ The model name with the provider prefix LiteLLM routes by. """
        if not self.is_direct:
            # EricAI names contain slashes, e.g. 'openai/gpt-oss-120b'.
            return f"litellm_proxy/{self.model}"

        if self.model.startswith(f"{self.provider}/"):
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

        # Also offer loaded EricAI models that are not listed in 'models'.
        self.discover_models = bool(raw.get('discover_models', False))

        # Optional when every model is direct.
        self.ericai = None
        try:
            if raw.get('ericai'):
                self.ericai = EricAIConfig(raw['ericai'])
        except ValueError as ex:
            # The shipped config leaves the credentials empty on purpose.
            if self.enabled:
                LOG.warning("AI report explanation is enabled but EricAI is "
                            "not configured: %s Set the credentials through "
                            "$ENV:...$ or $SECRET:...$ in "
                            "server_config.json.", ex)

        self.models = []
        for entry in raw.get('models', []):
            try:
                model = AIModelConfig(entry)
            except ValueError as ex:
                # The shipped config has empty keys.
                if self.enabled:
                    LOG.warning("Ignoring AI model: %s", ex)
                continue

            if not model.is_direct and not self.ericai:
                if self.enabled:
                    LOG.warning("Ignoring AI model '%s': EricAI is not "
                                "configured.", model.id)
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

        if self.enabled and not self.models and \
                not (self.ericai and self.discover_models):
            LOG.warning("AI report explanation is enabled but no model is "
                        "configured; the feature stays turned off.")

    @property
    def discovers_models(self):
        """ Whether loaded EricAI models are offered unconfigured. """
        return self.discover_models and bool(self.ericai)

    @property
    def is_available(self):
        """ On, with LiteLLM installed and a model to offer. """
        return self.enabled and self.has_litellm and \
            (bool(self.models) or self.discovers_models)

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
