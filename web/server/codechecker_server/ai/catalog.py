# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------
"""
Which models can be asked right now. Direct models always can; EricAI's
are checked.

Most EricAI models are elastic: they are only loaded onto GPUs on demand,
which takes several minutes and may evict another team's model. A request
to an unloaded model would time out here while still causing that load, so
only the loaded ones are offered.
"""

import threading
import time
from dataclasses import dataclass

from codechecker_common.logger import get_logger

from .client import AIProviderError, fetch_models
from .config import AIModelConfig

LOG = get_logger('server')


@dataclass
class ModelStatus:
    """ What EricAI reports about one of its models. """
    id: str
    loaded: bool
    chat: bool = True
    lifecycle: str = None
    banned: bool = False

    @property
    def discoverable(self):
        """ Worth offering without being configured. """
        return (self.loaded and self.chat and not self.banned
                and self.lifecycle != 'Deprecated'
                # Aliases of other models, e.g. 'tag:fast'.
                and not self.id.startswith('tag:')
                # Test instances, e.g. 'Org/Model/PerfTest'.
                and self.id.count('/') <= 1)


def parse_model_list(entries):
    """
    The status of each model in an OpenAI style model list, as EricAI
    extends it. A model without status information counts as loaded: a
    plain LiteLLM proxy cannot tell, and serves whatever it lists.
    """
    statuses = {}

    for entry in entries or []:
        if not isinstance(entry, dict) or not entry.get('id'):
            continue

        metadata = entry.get('rayllm_metadata') or {}
        engine = metadata.get('engine_config') or {}
        demand = metadata.get('demand_status') or {}
        deployment = entry.get('deployment_status') or {}

        if 'loaded' in demand:
            loaded = bool(demand['loaded'])
        elif deployment:
            loaded = (deployment.get('running_replicas') or 0) > 0
        else:
            loaded = True

        interfaces = engine.get('supported_interfaces')

        statuses[entry['id']] = ModelStatus(
            id=entry['id'],
            loaded=loaded,
            chat=interfaces is None or 'chat.completions' in interfaces,
            lifecycle=engine.get('lifecycle'),
            banned=bool(demand.get('temporary_model_ban')))

    return statuses


class ModelCatalog:
    """ EricAI's model list, shared by every request for a short while. """

    # Loading and unloading take minutes, so this is fresh enough.
    TTL = 60  # seconds

    # An unreachable EricAI is asked again sooner, but not on every call.
    FAILURE_TTL = 15  # seconds

    # Listing must not hold up opening the explanation panel for long.
    MAX_TIMEOUT = 10  # seconds

    def __init__(self):
        self._lock = threading.Lock()
        self._key = None
        self._statuses = None
        self._expires_at = 0.0

    @staticmethod
    def _cache_key(ericai):
        return (ericai.api_url, ericai.token_command, ericai.client_id)

    def statuses(self, ai_config):
        """ Model id to ModelStatus, or None if EricAI could not tell. """
        key = self._cache_key(ai_config.ericai)

        # Held during the request, so concurrent callers wait for one list
        # rather than each fetching their own.
        with self._lock:
            if key == self._key and time.monotonic() < self._expires_at:
                return self._statuses

            timeout = min(ai_config.timeout, self.MAX_TIMEOUT)
            try:
                statuses = parse_model_list(
                    fetch_models(ai_config.ericai, timeout))
                ttl = self.TTL
            except AIProviderError as ex:
                LOG.warning("Could not get the EricAI model list, offering "
                            "the configured models unchecked: %s", ex)
                statuses = None
                ttl = self.FAILURE_TTL

            self._key = key
            self._statuses = statuses
            self._expires_at = time.monotonic() + ttl
            return statuses

    def available_models(self, ai_config):
        """
        The models to offer: the direct ones, the configured EricAI ones
        that are loaded, and with ``discover_models`` any other loaded chat
        model of EricAI.
        """
        ericai_models = [m for m in ai_config.models if not m.is_direct]
        if not ericai_models and not ai_config.discovers_models:
            return list(ai_config.models)

        statuses = self.statuses(ai_config)
        if statuses is None:
            return list(ai_config.models)

        def is_loaded(name):
            status = statuses.get(name)
            return bool(status and status.loaded and not status.banned)

        models = [m for m in ai_config.models
                  if m.is_direct or is_loaded(m.model)]

        if ai_config.discovers_models:
            configured = {m.model for m in ericai_models} | \
                {m.id for m in ai_config.models}
            models += [AIModelConfig({'id': status.id})
                       for status in sorted(statuses.values(),
                                            key=lambda s: s.id.lower())
                       if status.discoverable
                       and status.id not in configured]

        return models


MODEL_CATALOG = ModelCatalog()
