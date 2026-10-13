# -------------------------------------------------------------------------
#
#  Part of the CodeChecker project, under the Apache License v2.0 with
#  LLVM Exceptions. See LICENSE for license information.
#  SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
#
# -------------------------------------------------------------------------

""" Test the AI report explanation layer. """


import base64
import json
import os
import shlex
import sys
import tempfile
import time
import unittest
from types import SimpleNamespace
from unittest import mock

import certifi
import httpx
import litellm

from codechecker_server.ai import catalog, client, explain
from codechecker_server.ai.config import AIConfig, AIModelConfig
from codechecker_server.ai.explain import (
    PathEvent, ReportContext, explain_report)
from codechecker_server.ai.prompt import build_source_window, format_bug_path


class SourceWindowTestCase(unittest.TestCase):
    """
    The excerpt handed to the model must be centred on the reported line.
    A prefix truncation would routinely miss the finding altogether.
    """

    def test_window_is_centred_on_the_report(self):
        content = "\n".join(f"line {i}" for i in range(1, 5001))

        text, start, end = build_source_window(content, 4200, 100)

        self.assertLessEqual(start, 4200)
        self.assertGreaterEqual(end, 4200)
        self.assertIn("line 4200", text)
        self.assertEqual(end - start + 1, 100)

    def test_whole_file_returned_when_short(self):
        text, start, end = build_source_window("a\nb\nc", 2, 400)

        self.assertEqual((start, end), (1, 3))
        self.assertTrue(text.splitlines()[1].endswith("| b"))

    def test_window_shifts_back_at_end_of_file(self):
        content = "\n".join(f"line {i}" for i in range(1, 201))

        _, start, end = build_source_window(content, 199, 50)

        self.assertEqual((start, end), (151, 200))

    def test_missing_source(self):
        self.assertEqual(build_source_window("", 1, 10), ('', 0, 0))
        self.assertEqual(build_source_window(None, 1, 10), ('', 0, 0))


class BugPathTestCase(unittest.TestCase):
    """ The analyser's own reasoning is the key triage context. """

    def setUp(self):
        self.events = [
            PathEvent("a.c", 10, "Assuming 'p' is null"),
            PathEvent("a.c", 12, "Dereference of null pointer")]

    def test_events_are_numbered_with_locations(self):
        out = format_bug_path(self.events, 50)

        self.assertIn("1. [a.c:10] Assuming 'p' is null", out)
        self.assertIn("2. [a.c:12] Dereference of null pointer", out)

    def test_long_paths_are_truncated(self):
        out = format_bug_path(self.events, 1)

        self.assertIn("1 further steps omitted", out)

    def test_empty_path_is_stated_explicitly(self):
        self.assertIn("did not record", format_bug_path([], 50))


ERICAI = {"api_url": "https://ericai.example/v1",
          "token_url": "https://login.example/token",
          "client_id": "cid",
          "client_secret": "s3cr3t-value",
          "scope": "api://ai/.default"}


def ai_config(models=None, **ericai):
    return AIConfig({"enabled": True,
                     "ericai": dict(ERICAI, **ericai),
                     "models": [{"id": "m", "model": "llama"}]
                     if models is None else models})


class ShippedConfigTestCase(unittest.TestCase):
    """ The example configuration every new workspace starts from. """

    def setUp(self):
        path = os.path.join(os.environ["REPO_ROOT"], "web", "server",
                            "config", "server_config.json")
        with open(path, encoding="utf-8") as handle:
            self.raw = json.load(handle)["ai"]

    def configured(self):
        """ The template, with the credentials it leaves empty filled in. """
        raw = json.loads(json.dumps(self.raw))
        raw["enabled"] = True
        raw["ericai"].update(client_id="cid", client_secret="secret")
        for model in raw["models"]:
            if "api_key" in model:
                model["api_key"] = "key"
        return AIConfig(raw)

    def test_feature_is_off_by_default(self):
        self.assertFalse(AIConfig(self.raw).is_available)

    def test_empty_credentials_keep_the_feature_off(self):
        self.assertFalse(AIConfig(dict(self.raw, enabled=True)).is_available)

    def test_every_shipped_model_is_offered_once_configured(self):
        self.assertEqual(len(self.configured().models),
                         len(self.raw["models"]))

    def test_shipped_config_has_ericai_and_direct_models(self):
        providers = {m.provider for m in self.configured().models}

        self.assertIn("ericai", providers)
        self.assertTrue(providers - {"ericai"})

    def test_every_shipped_model_is_rated(self):
        for model in self.configured().models:
            self.assertIsNotNone(model.speed, model.id)
            self.assertIsNotNone(model.reliability, model.id)

    def test_default_model_is_one_of_the_models(self):
        cfg = self.configured()

        self.assertTrue(cfg.models)
        self.assertEqual(self.raw["default_model"], cfg.default_model)
        self.assertIn(cfg.default_model, [m.id for m in cfg.models])


class ResponseParsingTestCase(unittest.TestCase):
    """ Models do not always honour a request for raw JSON. """

    def test_plain_json(self):
        self.assertEqual(client.parse_json_response('{"a": 1}'), {"a": 1})

    def test_markdown_fenced_json(self):
        self.assertEqual(
            client.parse_json_response('```json\n{"a": 1}\n```'), {"a": 1})
        self.assertEqual(
            client.parse_json_response('```\n{"a": 1}\n```'), {"a": 1})

    def test_unusable_answers_raise(self):
        for bad in ('', 'not json at all'):
            with self.assertRaises(client.AIProviderError):
                client.parse_json_response(bad)


def provider_error(status, retry_after=None):
    """ A LiteLLM error as a provider's HTTP answer raises it. """
    headers = {'Retry-After': retry_after} if retry_after else {}
    error = litellm.exceptions.APIError(status, "failed", "openai", "m")
    error.response = httpx.Response(
        status, headers=headers, request=httpx.Request("POST", "http://x"))
    return error


class RetryDecisionTestCase(unittest.TestCase):
    """ A busy provider is worth another try; a refused request is not. """

    def setUp(self):
        self.is_retryable = client.AIClient._is_retryable

    def test_transient_failures_are_retried(self):
        for status in (429, 500, 502, 503, 504):
            self.assertTrue(self.is_retryable(provider_error(status)), status)

    def test_client_errors_are_not_retried(self):
        for status in (400, 401, 403, 404, 422):
            self.assertFalse(self.is_retryable(provider_error(status)),
                             status)

    def test_errors_without_status_are_not_retried(self):
        self.assertFalse(self.is_retryable(ValueError("bug")))


class RetryDelayTestCase(unittest.TestCase):
    """ Retry-After wins over the built-in backoff when it is usable. """

    def setUp(self):
        self.retry_delay = client.AIClient._retry_delay

    def test_backoff_schedule_when_no_header(self):
        delay = self.retry_delay(provider_error(503), 0)
        self.assertEqual(delay, client.BACKOFF_SCHEDULE[0])

    def test_retry_after_is_honoured(self):
        self.assertEqual(self.retry_delay(provider_error(429, '7'), 0), 7.0)

    def test_retry_after_is_capped(self):
        self.assertEqual(self.retry_delay(provider_error(429, '9000'), 0),
                         30.0)

    def test_http_date_retry_after_falls_back(self):
        delay = self.retry_delay(
            provider_error(429, 'Wed, 21 Oct 2026 07:28:00 GMT'), 1)
        self.assertEqual(delay, client.BACKOFF_SCHEDULE[1])

    def test_attempt_beyond_schedule_is_clamped(self):
        delay = self.retry_delay(provider_error(503), 99)
        self.assertEqual(delay, client.BACKOFF_SCHEDULE[-1])


class ConfigTestCase(unittest.TestCase):
    """ The feature must stay off unless it is fully configured. """

    def test_absent_section_disables_the_feature(self):
        self.assertFalse(AIConfig({}).is_available)
        self.assertFalse(AIConfig(None).is_available)

    def test_complete_configuration_is_available(self):
        cfg = ai_config()

        self.assertTrue(cfg.is_available)
        self.assertEqual(cfg.default_model, "m")

    def test_incomplete_ericai_section_disables_the_feature(self):
        for field in ("api_url", "token_url", "client_id", "client_secret",
                      "scope"):
            self.assertFalse(ai_config(**{field: ""}).is_available, field)

    def test_no_models_disables_the_feature(self):
        self.assertFalse(ai_config(models=[]).is_available)

    def test_unknown_default_falls_back(self):
        cfg = AIConfig({"enabled": True, "default_model": "nope",
                        "ericai": ERICAI, "models": [{"id": "m"}]})

        self.assertEqual(cfg.default_model, "m")

    def test_invalid_entries_are_skipped(self):
        cfg = ai_config(models=[{"model": "no-id"}, {"id": "good"}])

        self.assertEqual([m.id for m in cfg.models], ["good"])

    def test_ratings_are_read_and_normalised(self):
        model = ai_config(models=[{"id": "m", "speed": "Fast",
                                   "reliability": "high"}]).models[0]

        self.assertEqual((model.speed, model.reliability), ("fast", "high"))

    def test_invalid_or_missing_ratings_are_unset(self):
        rated, unrated = ai_config(models=[
            {"id": "a", "speed": "ludicrous", "reliability": "high"},
            {"id": "b"}]).models

        self.assertEqual((rated.speed, rated.reliability), (None, "high"))
        self.assertEqual((unrated.speed, unrated.reliability), (None, None))

    def test_model_name_defaults_to_id(self):
        self.assertEqual(ai_config(models=[{"id": "m"}]).models[0].model, "m")

    def test_models_go_through_ericai_by_default(self):
        model = ai_config().models[0]

        self.assertEqual(model.provider, "ericai")
        self.assertFalse(model.is_direct)
        self.assertEqual(model.temperature, 0.2)

    def test_missing_litellm_disables_the_feature(self):
        with mock.patch.object(config_module().importlib.util, "find_spec",
                               return_value=None):
            self.assertFalse(ai_config().is_available)


def config_module():
    return sys.modules[AIConfig.__module__]


class DirectProviderConfigTestCase(unittest.TestCase):
    """ Models asked at their own provider, with an API key. """

    @staticmethod
    def config(models, **raw):
        return AIConfig(dict({"enabled": True, "models": models}, **raw))

    def test_direct_model_needs_no_ericai(self):
        cfg = self.config([{"id": "c", "provider": "anthropic",
                            "model": "claude-opus-5-5", "api_key": "k"}])

        self.assertTrue(cfg.is_available)
        self.assertIsNone(cfg.ericai)
        self.assertTrue(cfg.models[0].is_direct)

    def test_direct_model_without_key_is_skipped(self):
        cfg = self.config([{"id": "c", "provider": "anthropic",
                            "api_key": ""}])

        self.assertEqual(cfg.models, [])
        self.assertFalse(cfg.is_available)

    def test_api_base_replaces_the_key(self):
        cfg = self.config([{"id": "local", "provider": "ollama",
                            "model": "llama3",
                            "api_base": "http://localhost:11434"}])

        self.assertEqual([m.id for m in cfg.models], ["local"])

    def test_ericai_model_without_ericai_is_skipped(self):
        cfg = self.config([{"id": "e"},
                           {"id": "d", "provider": "deepseek",
                            "api_key": "k"}])

        self.assertEqual([m.id for m in cfg.models], ["d"])

    def test_ericai_and_direct_models_together(self):
        cfg = self.config([{"id": "e", "model": "openai/gpt-oss-120b"},
                           {"id": "d", "provider": "gemini",
                            "api_key": "k"}], ericai=ERICAI)

        self.assertEqual([m.provider for m in cfg.models],
                         ["ericai", "gemini"])

    def test_litellm_model_names(self):
        def name(**entry):
            return AIModelConfig(dict({"id": "x"}, **entry)).litellm_model

        self.assertEqual(name(model="openai/gpt-oss-120b"),
                         "litellm_proxy/openai/gpt-oss-120b")
        self.assertEqual(name(provider="anthropic", model="claude-opus-5-5",
                              api_key="k"),
                         "anthropic/claude-opus-5-5")
        self.assertEqual(name(provider="Gemini", model="gemini/flash",
                              api_key="k"),
                         "gemini/flash")

    def test_direct_models_send_no_temperature_unless_set(self):
        models = self.config([
            {"id": "a", "provider": "anthropic", "api_key": "k"},
            {"id": "b", "provider": "openai", "api_key": "k",
             "temperature": 0}]).models

        self.assertIsNone(models[0].temperature)
        self.assertEqual(models[1].temperature, 0)


class FakeHTTPResponse:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self._body = body
        self.text = json.dumps(body)
        self.headers = {}

    def json(self):
        return self._body


def completion_response(content='{"a": 1}', finish_reason="stop"):
    """ What litellm.completion returns, trimmed to what is read. """
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content),
                                 finish_reason=finish_reason)])


class LiteLLMTestCase(unittest.TestCase):
    """ Replaces litellm.completion, recording each call's arguments. """

    def setUp(self):
        client.OAUTH2_TOKENS = client.OAuth2TokenCache()
        self.completions = []
        self.failures = []

        def fake_completion(**kwargs):
            self.completions.append(kwargs)
            if self.failures:
                raise self.failures.pop(0)
            return completion_response()

        patcher = mock.patch.object(client, "_completion", fake_completion)
        patcher.start()
        self.addCleanup(patcher.stop)


class EricAIClientTestCase(LiteLLMTestCase):
    """
    Short-lived OAuth2 access tokens of the client credentials flow: shared
    until near expiry and renewed when EricAI rejects them.
    """

    def setUp(self):
        super().setUp()
        self.token_requests = 0

        patcher = mock.patch.object(client.requests, "post", self.fake_post)
        patcher.start()
        self.addCleanup(patcher.stop)

    def fake_post(self, url, **kwargs):
        self.assertEqual(url, ERICAI["token_url"])
        self.token_requests += 1
        self.assertEqual(kwargs["data"]["grant_type"], "client_credentials")
        return FakeHTTPResponse(200, {
            "access_token": f"token-{self.token_requests}",
            "expires_in": 3600})

    @staticmethod
    def client(**ericai):
        cfg = ai_config(**ericai)
        return client.AIClient(cfg.ericai, cfg.models[0], 60)

    def test_api_base_is_the_root_of_chat_completions(self):
        for url in ("https://e.example/v1", "https://e.example/v1/",
                    "https://e.example/v1/chat/completions"):
            self.assertEqual(ai_config(api_url=url).ericai.api_base,
                             "https://e.example/v1")

    def test_request_names_the_model(self):
        ericai = self.client()
        self.assertEqual(ericai.complete("s", "u"), '{"a": 1}')

        sent = self.completions[0]
        self.assertEqual(sent["model"], "litellm_proxy/llama")
        self.assertEqual(sent["api_base"], "https://ericai.example/v1")
        self.assertEqual(sent["response_format"], {"type": "json_object"})
        self.assertEqual(sent["temperature"], 0.2)
        self.assertEqual(sent["messages"][0],
                         {"role": "system", "content": "s"})

    def test_token_is_sent_and_shared(self):
        self.client().complete("s", "u")
        self.client().complete("s", "u")

        self.assertEqual(self.token_requests, 1)
        self.assertEqual([c["api_key"] for c in self.completions],
                         ["token-1", "token-1"])

    def test_rejected_token_is_renewed_once(self):
        self.failures = [litellm.exceptions.AuthenticationError(
            "expired", "litellm_proxy", "llama")]

        self.assertEqual(self.client().complete("s", "u"), '{"a": 1}')

        self.assertEqual(self.token_requests, 2)
        self.assertEqual(self.completions[-1]["api_key"], "token-2")

    def test_token_rejected_twice_is_reported(self):
        self.failures = [litellm.exceptions.AuthenticationError(
            "expired", "litellm_proxy", "llama") for _ in range(2)]

        with self.assertRaises(client.AIProviderError) as ctx:
            self.client().complete("s", "u")

        self.assertIn("rejected the access token", str(ctx.exception))
        self.assertEqual(len(self.completions), 2)

    def test_token_endpoint_failure_is_reported_without_secret(self):
        def failing_post(url, **_):
            return FakeHTTPResponse(401, {
                "error": "invalid_client",
                "error_description": "Invalid client secret."})

        with mock.patch.object(client.requests, "post", failing_post):
            with self.assertRaises(client.AIProviderError) as ctx:
                self.client().complete("s", "u")

        self.assertIn("Invalid client secret", str(ctx.exception))
        self.assertNotIn(ERICAI["client_secret"], str(ctx.exception))

    def test_ca_bundle_is_used_for_every_request(self):
        # httpx loads the bundle, so it must hold real certificates.
        bundle = certifi.where()
        verified = []

        class RecordingClient(httpx.Client):
            def __init__(self, *args, verify=True, **kwargs):
                verified.append(verify)
                super().__init__(*args, verify=verify, **kwargs)

        ericai = self.client(ca_bundle=bundle)
        with mock.patch.object(client.requests, "post",
                               wraps=self.fake_post) as post, \
                mock.patch.object(httpx, "Client", RecordingClient):
            ericai.complete("s", "u")

        self.assertEqual(post.call_args.kwargs["verify"], bundle)
        self.assertEqual(verified, [bundle])
        self.assertEqual(str(self.completions[0]["client"].base_url),
                         "https://ericai.example/v1/")

    def test_requests_ca_bundle_applies_to_completions_too(self):
        verified = []

        class RecordingClient(httpx.Client):
            def __init__(self, *args, verify=True, **kwargs):
                verified.append(verify)
                super().__init__(*args, verify=verify, **kwargs)

        with mock.patch.dict(os.environ,
                             {"REQUESTS_CA_BUNDLE": certifi.where()}), \
                mock.patch.object(httpx, "Client", RecordingClient):
            self.client().complete("s", "u")

        self.assertEqual(verified, [certifi.where()])

    def test_missing_ca_bundle_falls_back_to_the_default(self):
        cfg = ai_config(ca_bundle="/no/such/bundle.crt")

        self.assertTrue(cfg.ericai.verify is True)

    def test_user_is_forwarded_as_email(self):
        ericai = self.client(user_header="X-Authenticated-User",
                             user_email_domain="example.com")
        ericai.on_behalf_of = "jdoe"
        ericai.complete("s", "u")

        self.assertEqual(self.completions[0]["extra_headers"],
                         {"X-Authenticated-User": "jdoe@example.com"})

    def test_user_without_email_is_not_forwarded(self):
        ericai = self.client(user_header="X-Authenticated-User")
        ericai.on_behalf_of = "jdoe"
        ericai.complete("s", "u")

        self.assertNotIn("extra_headers", self.completions[0])


class DirectClientTestCase(LiteLLMTestCase):
    """ A provider asked directly: its API key, and no EricAI specifics. """

    MODEL = {"id": "claude", "provider": "anthropic",
             "model": "claude-opus-5-5", "api_key": "sk-test-key"}

    def client(self, **entry):
        cfg = AIConfig({"enabled": True, "ericai": dict(
                            ERICAI, user_header="X-Authenticated-User"),
                        "models": [dict(self.MODEL, **entry)]})
        ai = client.AIClient(cfg.ericai, cfg.models[0], 30)
        ai.on_behalf_of = "jdoe@example.com"
        return ai

    def complete(self, **entry):
        with mock.patch.object(client.requests, "post") as post:
            answer = self.client(**entry).complete("s", "u")

        post.assert_not_called()  # no EricAI token
        return answer

    def test_request_goes_to_the_provider_with_its_key(self):
        self.assertEqual(self.complete(), '{"a": 1}')

        sent = self.completions[0]
        self.assertEqual(sent["model"], "anthropic/claude-opus-5-5")
        self.assertEqual(sent["api_key"], "sk-test-key")
        for key in ("api_base", "client", "extra_headers", "temperature"):
            self.assertNotIn(key, sent)

    def test_optional_parameters_are_passed_on(self):
        self.complete(api_base="https://proxy.example", temperature=0)

        sent = self.completions[0]
        self.assertEqual(sent["api_base"], "https://proxy.example")
        self.assertEqual(sent["temperature"], 0)

    def test_schema_is_enforced_where_supported(self):
        with mock.patch.object(litellm, "supports_response_schema",
                               return_value=True):
            self.complete()

        response_format = self.completions[0]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertEqual(
            set(response_format["json_schema"]["schema"]["required"]),
            {"background", "verdict", "confidence", "true_positive_case",
             "false_positive_case"})

    def test_json_mode_where_no_schema_is_supported(self):
        with mock.patch.object(litellm, "supports_response_schema",
                               return_value=False):
            self.complete()

        self.assertEqual(self.completions[0]["response_format"],
                         {"type": "json_object"})

    def test_rejected_key_is_reported_without_the_key(self):
        self.failures = [litellm.exceptions.AuthenticationError(
            "invalid x-api-key", "anthropic", "claude-opus-5-5")]

        with self.assertRaises(client.AIProviderError) as ctx:
            self.complete()

        self.assertIn("anthropic rejected the API key", str(ctx.exception))
        self.assertNotIn("sk-test-key", str(ctx.exception))
        self.assertEqual(len(self.completions), 1)

    def test_timeout_is_reported(self):
        self.failures = [litellm.exceptions.Timeout(
            "slow", "claude-opus-5-5", "anthropic")]

        with self.assertRaises(client.AIProviderError) as ctx:
            self.complete()

        self.assertIn("within 30 seconds", str(ctx.exception))

    def test_other_errors_carry_the_status_and_reason(self):
        self.failures = [litellm.exceptions.BadRequestError(
            "model not found", "claude-opus-5-5", "anthropic")]

        with self.assertRaises(client.AIProviderError) as ctx:
            self.complete()

        self.assertEqual(str(ctx.exception),
                         "anthropic answered with HTTP 400. model not found")

    def test_transient_failures_are_retried_with_backoff(self):
        self.failures = [provider_error(503), provider_error(429)]

        with mock.patch.object(client.time, "sleep") as sleep:
            self.assertEqual(self.complete(), '{"a": 1}')

        self.assertEqual(len(self.completions), 3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list],
                         list(client.BACKOFF_SCHEDULE))
        self.assertEqual(self.completions[0]["max_retries"], 0)

    def test_retries_give_up_after_the_last_attempt(self):
        self.failures = [provider_error(503) for _ in range(5)]

        with mock.patch.object(client.time, "sleep"), \
                self.assertRaises(client.AIProviderError) as ctx:
            self.complete()

        self.assertEqual(len(self.completions), client.MAX_ATTEMPTS)
        self.assertIn("HTTP 503", str(ctx.exception))

    def test_refused_request_is_not_retried(self):
        self.failures = [provider_error(400)]

        with mock.patch.object(client.time, "sleep") as sleep, \
                self.assertRaises(client.AIProviderError):
            self.complete()

        self.assertEqual(len(self.completions), 1)
        sleep.assert_not_called()


def fake_jwt(expires_in):
    def part(data):
        raw = base64.urlsafe_b64encode(json.dumps(data).encode())
        return raw.decode().rstrip('=')
    return '.'.join([part({"alg": "none"}),
                     part({"exp": int(time.time()) + expires_in}), "sig"])


class TokenCommandTestCase(unittest.TestCase):
    """
    A signed in user's token, printed by a command such as the ericai
    client's, in place of the service principal's client credentials.
    """

    def setUp(self):
        client.OAUTH2_TOKENS = client.OAuth2TokenCache()

    @staticmethod
    def command(code):
        return f"{shlex.quote(sys.executable)} -c {shlex.quote(code)}"

    def test_token_command_replaces_client_credentials(self):
        cfg = AIConfig({"enabled": True, "models": [{"id": "m"}],
                        "ericai": {"api_url": "https://e.example",
                                   "token_command": "ericai --token"}})

        self.assertTrue(cfg.is_available)

    def test_neither_login_disables_the_feature(self):
        cfg = AIConfig({"enabled": True, "models": [{"id": "m"}],
                        "ericai": {"api_url": "https://e.example"}})

        self.assertFalse(cfg.is_available)

    def test_last_line_of_output_is_the_token(self):
        token, _ = client.OAuth2TokenCache._run_token_command(
            self.command("print('Banner'); print('tok-123')"), 10)

        self.assertEqual(token, "tok-123")

    def test_command_runs_in_the_configured_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            token, _ = client.OAuth2TokenCache._run_token_command(
                self.command("import os; print(os.getcwd())"), 10, tmp)

            self.assertEqual(os.path.realpath(token), os.path.realpath(tmp))

    def test_lifetime_is_read_from_the_jwt(self):
        lifetime = client.OAuth2TokenCache._jwt_lifetime(fake_jwt(1800))

        self.assertTrue(1790 <= lifetime <= 1800, lifetime)

    def test_opaque_token_gets_the_default_lifetime(self):
        self.assertEqual(client.OAuth2TokenCache._jwt_lifetime("opaque"),
                         client.OAuth2TokenCache.DEFAULT_LIFETIME)

    def test_failure_reports_stderr_but_never_stdout(self):
        command = self.command(
            "import sys; print('half-a-token'); "
            "sys.stderr.write('login required'); sys.exit(3)")

        with self.assertRaises(client.AIProviderError) as ctx:
            client.OAuth2TokenCache._run_token_command(command, 10)

        self.assertIn("exit code 3", str(ctx.exception))
        self.assertIn("login required", str(ctx.exception))
        self.assertNotIn("half-a-token", str(ctx.exception))

    def test_token_is_sent_and_shared(self):
        cfg = AIConfig({"enabled": True, "models": [{"id": "m"}],
                        "ericai": {"api_url": "https://e.example",
                                   "token_command": self.command(
                                       "print('user-token')")}})
        sent = []

        def fake_completion(**kwargs):
            sent.append(kwargs["api_key"])
            return completion_response()

        with mock.patch.object(client, "_completion", fake_completion), \
                mock.patch.object(client.subprocess, "run",
                                  wraps=client.subprocess.run) as run:
            for _ in range(2):
                client.AIClient(cfg.ericai, cfg.models[0], 10) \
                    .complete("s", "u")

        self.assertEqual(run.call_count, 1)
        self.assertEqual(sent, ["user-token"] * 2)


def model_entry(model_id, loaded=True, lifecycle="Recommended",
                interfaces=("chat.completions",), banned=False):
    """ One entry of EricAI's model list, trimmed to what is read. """
    return {"id": model_id,
            "rayllm_metadata": {
                "engine_config": {"lifecycle": lifecycle,
                                  "supported_interfaces": list(interfaces)},
                "demand_status": {"loaded": loaded,
                                  "temporary_model_ban": banned}}}


class ModelCatalogTestCase(unittest.TestCase):
    """
    Only loaded EricAI models are offered: asking an unloaded one would
    load it, possibly evicting another team's, while the request times out.
    """

    ENTRIES = [
        model_entry("openai/gpt-oss-120b"),
        model_entry("zai-org/GLM-5.2-FP8", lifecycle="Experimental"),
        model_entry("Qwen/Qwen3.5-397B-A17B-FP8", loaded=False),
        model_entry("tag:fast"),
        model_entry("Qwen/Qwen3-32B", lifecycle="Deprecated"),
        model_entry("Qwen/Qwen3-Coder-480B/PerfTest"),
        model_entry("BAAI/bge-m3", interfaces=("embeddings",)),
        model_entry("Some/Banned", banned=True),
    ]

    def setUp(self):
        self.catalog = catalog.ModelCatalog()
        self.fetches = 0
        self.fail = False

        def fake_fetch(_ericai, _timeout):
            self.fetches += 1
            if self.fail:
                raise client.AIProviderError("down")
            return self.ENTRIES

        patcher = mock.patch.object(catalog, "fetch_models", fake_fetch)
        patcher.start()
        self.addCleanup(patcher.stop)

    @staticmethod
    def config(discover=False):
        return AIConfig({"enabled": True, "ericai": ERICAI,
                         "discover_models": discover,
                         "default_model": "qwen-big",
                         "models": [
                             {"id": "gpt", "model": "openai/gpt-oss-120b"},
                             {"id": "qwen-big",
                              "model": "Qwen/Qwen3.5-397B-A17B-FP8"},
                             {"id": "gone", "model": "Not/Listed"}]})

    def ids(self, cfg):
        return [m.id for m in self.catalog.available_models(cfg)]

    def test_only_loaded_configured_models_are_offered(self):
        self.assertEqual(self.ids(self.config()), ["gpt"])

    def test_default_falls_back_to_a_loaded_model(self):
        cfg = self.config()
        models = self.catalog.available_models(cfg)

        self.assertEqual(cfg.pick_model(None, models).id, "gpt")
        self.assertIsNone(cfg.pick_model("qwen-big", models))

    def test_discovery_adds_other_loaded_chat_models(self):
        self.assertEqual(self.ids(self.config(discover=True)),
                         ["gpt", "zai-org/GLM-5.2-FP8"])

    def test_discovery_alone_makes_the_feature_available(self):
        cfg = AIConfig({"enabled": True, "ericai": ERICAI,
                        "discover_models": True})

        self.assertTrue(cfg.is_available)
        self.assertEqual(self.ids(cfg),
                         ["openai/gpt-oss-120b", "zai-org/GLM-5.2-FP8"])

    def test_list_is_cached(self):
        cfg = self.config()
        self.ids(cfg)
        self.ids(cfg)

        self.assertEqual(self.fetches, 1)

    def test_unreachable_ericai_offers_the_configured_models(self):
        self.fail = True

        self.assertEqual(self.ids(self.config()), ["gpt", "qwen-big", "gone"])

    def test_direct_models_are_always_offered(self):
        cfg = self.config()
        cfg.models.insert(1, AIModelConfig({"id": "claude",
                                            "provider": "anthropic",
                                            "api_key": "k"}))

        self.assertEqual(self.ids(cfg), ["gpt", "claude"])

    def test_direct_only_config_never_asks_ericai(self):
        cfg = AIConfig({"enabled": True, "ericai": ERICAI,
                        "models": [{"id": "claude", "provider": "anthropic",
                                    "api_key": "k"}]})

        self.assertEqual(self.ids(cfg), ["claude"])
        self.assertEqual(self.fetches, 0)

    def test_model_without_status_counts_as_loaded(self):
        statuses = catalog.parse_model_list([{"id": "plain/litellm"}])

        self.assertTrue(statuses["plain/litellm"].loaded)

    def test_status_falls_back_to_running_replicas(self):
        statuses = catalog.parse_model_list([
            {"id": "a", "deployment_status": {"running_replicas": 0}},
            {"id": "b", "deployment_status": {"running_replicas": 2}}])

        self.assertFalse(statuses["a"].loaded)
        self.assertTrue(statuses["b"].loaded)


class FetchModelsTestCase(unittest.TestCase):
    """ The list comes from the /models sibling of /chat/completions. """

    def setUp(self):
        client.OAUTH2_TOKENS = client.OAuth2TokenCache()

    def test_models_endpoint_and_data_envelope(self):
        requested = []

        def fake_post(url, **_):
            return FakeHTTPResponse(200, {"access_token": "t",
                                          "expires_in": 3600})

        def fake_get(url, **kwargs):
            requested.append((url, kwargs["headers"]["Authorization"]))
            return FakeHTTPResponse(200, {"object": "list",
                                          "data": [{"id": "m"}]})

        cfg = ai_config(api_url="https://e.example/v1/chat/completions")
        with mock.patch.object(client.requests, "post", fake_post), \
                mock.patch.object(client.requests, "get", fake_get):
            entries = client.fetch_models(cfg.ericai, 10)

        self.assertEqual(entries, [{"id": "m"}])
        self.assertEqual(requested,
                         [("https://e.example/v1/models", "Bearer t")])


class FakeClient:
    """ Stands in for the model. """

    last_prompts = {}

    def __init__(self, _ericai_config, _model_config, _timeout):
        self.on_behalf_of = None

    def complete(self, system_prompt, user_prompt):
        FakeClient.last_prompts = {'system': system_prompt,
                                   'user': user_prompt}
        return ('```json\n'
                '{"background": "<p>The checker flags a null '
                'dereference.</p>",'
                ' "verdict": "likely true positive",'
                ' "confidence": 0.9,'
                ' "true_positive_case": "<p>p is never checked.</p>",'
                ' "false_positive_case": "<p>None apparent.</p>"}\n'
                '```')


class ExplainReportTestCase(unittest.TestCase):
    """ The full path from a report context to a structured explanation. """

    def setUp(self):
        patcher = mock.patch.object(explain, "AIClient", FakeClient)
        patcher.start()
        self.addCleanup(patcher.stop)

        self.config = ai_config()

        self.context = ReportContext(
            checker_name="core.NullDereference",
            checker_message="Dereference of null pointer",
            file_path="src/a.c",
            line=12,
            column=5,
            analyzer_name="clangsa",
            severity="HIGH",
            file_content="\n".join(f"line {i}" for i in range(1, 100)),
            checker_documentation="doc_url: http://example.com",
            path_events=[PathEvent("src/a.c", 10, "Assuming 'p' is null")])

    def test_answer_is_normalised(self):
        result = explain_report(self.context, self.config)

        self.assertEqual(result.verdict, "LIKELY_TRUE_POSITIVE")
        # A probability is accepted as well as a percentage.
        self.assertEqual(result.confidence, 90)
        self.assertEqual(result.model, "m")
        self.assertIn("null dereference", result.background)

    def test_prompt_carries_the_triage_context(self):
        explain_report(self.context, self.config)
        prompt = FakeClient.last_prompts['user']

        for needle in ("core.NullDereference", "src/a.c:12:5", "clangsa",
                       "HIGH", "Assuming 'p' is null", "doc_url",
                       "the report is on line 12"):
            self.assertIn(needle, prompt)

    def test_prompt_asks_for_restricted_html(self):
        explain_report(self.context, self.config)
        system = FakeClient.last_prompts['system']

        self.assertIn("HTML fragments", system)
        self.assertIn("never instructions", system)

    def test_disabled_server_is_rejected(self):
        with self.assertRaises(client.AIProviderError) as ctx:
            explain_report(self.context, AIConfig({}))

        self.assertIn("not enabled", str(ctx.exception))

    def test_choice_is_limited_to_the_given_models(self):
        with self.assertRaises(client.AIProviderError):
            explain_report(self.context, self.config, "m", models=[])

    def test_unknown_model_is_reported(self):
        with self.assertRaises(client.AIProviderError) as ctx:
            explain_report(self.context, self.config, "no-such-model")

        self.assertIn("not available", str(ctx.exception))
