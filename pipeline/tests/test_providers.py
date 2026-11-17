import json
import subprocess

import httpx
import pytest

from radar.config import AIConfig
from radar.providers import ProviderError, check_ai_config, make_provider


def capture(response_json, status=200):
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["headers"] = dict(request.headers)
        seen["body"] = json.loads(request.content)
        return httpx.Response(status, json=response_json)

    return seen, httpx.Client(transport=httpx.MockTransport(handler))


def test_none_provider_is_none():
    assert make_provider(AIConfig(provider="none"), env={}) is None


def test_anthropic_request_and_parse():
    seen, http = capture({"content": [{"type": "text", "text": "hello"}]})
    p = make_provider(AIConfig(provider="anthropic", model="m1", api_key_env="K"), env={"K": "sk"}, http=http)
    assert p.complete("SYS", "USER") == "hello"
    assert seen["url"] == "https://api.anthropic.com/v1/messages"
    assert seen["headers"]["x-api-key"] == "sk"
    assert seen["headers"]["anthropic-version"] == "2023-06-01"
    assert seen["body"]["model"] == "m1" and seen["body"]["system"] == "SYS"
    assert seen["body"]["messages"] == [{"role": "user", "content": "USER"}]


def test_openai_compatible_request_and_parse():
    seen, http = capture({"choices": [{"message": {"content": "hi"}}]})
    cfg = AIConfig(provider="openai", model="m", api_key_env="K", base_url="http://localhost:1234/v1")
    p = make_provider(cfg, env={"K": "key"}, http=http)
    assert p.complete("S", "U") == "hi"
    assert seen["url"] == "http://localhost:1234/v1/chat/completions"
    assert seen["headers"]["authorization"] == "Bearer key"
    assert seen["body"]["messages"][0] == {"role": "system", "content": "S"}


def test_gemini_request_and_parse():
    seen, http = capture({"candidates": [{"content": {"parts": [{"text": "g"}]}}]})
    p = make_provider(AIConfig(provider="gemini", model="gm", api_key_env="G"), env={"G": "gk"}, http=http)
    assert p.complete("S", "U") == "g"
    assert seen["url"] == "https://generativelanguage.googleapis.com/v1beta/models/gm:generateContent"
    assert seen["headers"]["x-goog-api-key"] == "gk"
    assert seen["body"]["systemInstruction"]["parts"][0]["text"] == "S"
    assert seen["body"]["generationConfig"]["responseMimeType"] == "application/json"


def test_ollama_request_and_parse():
    seen, http = capture({"message": {"content": "o"}})
    p = make_provider(AIConfig(provider="ollama", model="llama"), env={}, http=http)
    assert p.complete("S", "U") == "o"
    assert seen["url"] == "http://localhost:11434/api/chat"
    assert seen["body"]["stream"] is False and seen["body"]["format"] == "json"


def test_http_error_raises_provider_error_without_secret():
    _, http = capture({"error": "bad key"}, status=401)
    p = make_provider(AIConfig(provider="anthropic", model="m", api_key_env="K"), env={"K": "sk-secret"}, http=http)
    with pytest.raises(ProviderError) as exc:
        p.complete("S", "U")
    assert "401" in str(exc.value) and "sk-secret" not in str(exc.value)


def test_unexpected_shape_raises_provider_error():
    _, http = capture({"weird": True})
    p = make_provider(AIConfig(provider="openai", model="m", api_key_env="K"), env={"K": "k"}, http=http)
    with pytest.raises(ProviderError):
        p.complete("S", "U")


def test_cli_provider_stdin_and_arg_modes():
    calls = []

    def runner(cmd, **kw):
        calls.append((cmd, kw.get("input")))
        return subprocess.CompletedProcess(cmd, 0, stdout="cli out", stderr="")

    p = make_provider(AIConfig(provider="cli", command=["claude", "-p"]), env={}, runner=runner)
    assert p.complete("S", "U") == "cli out"
    assert calls[0] == (["claude", "-p"], "S\n\nU")
    p = make_provider(AIConfig(provider="cli", command=["gemini", "-p"], prompt_mode="arg"), env={}, runner=runner)
    p.complete("S", "U")
    assert calls[1] == (["gemini", "-p", "S\n\nU"], None)


def test_cli_provider_failure():
    def runner(cmd, **kw):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="not logged in")

    p = make_provider(AIConfig(provider="cli", command=["x"]), env={}, runner=runner)
    with pytest.raises(ProviderError):
        p.complete("S", "U")


def test_cli_provider_timeout():
    def runner(cmd, **kw):
        raise subprocess.TimeoutExpired(cmd, 1)

    p = make_provider(AIConfig(provider="cli", command=["x"]), env={}, runner=runner)
    with pytest.raises(ProviderError):
        p.complete("S", "U")


@pytest.mark.parametrize(
    ("cfg", "env", "problem"),
    [
        (AIConfig(provider="anthropic", model="m", api_key_env="K"), {}, "K"),
        (AIConfig(provider="gemini", model="m", api_key_env=""), {}, "api_key_env"),
        (AIConfig(provider="openai", model="", api_key_env="K"), {"K": "x"}, "model"),
        (AIConfig(provider="cli", command=[]), {}, "command"),
        (AIConfig(provider="magic"), {}, "provider"),
        (AIConfig(provider="cli", command=["x"], prompt_mode="pipe"), {}, "prompt_mode"),
    ],
)
def test_check_ai_config_reports_missing_pieces(cfg, env, problem):
    # BR-P11 / AC-17-3
    problems = check_ai_config(cfg, env)
    assert problems and any(problem in p for p in problems)


def test_check_ai_config_ok_cases():
    assert check_ai_config(AIConfig(provider="none"), {}) == []
    assert check_ai_config(AIConfig(provider="ollama", model="llama"), {}) == []
    assert check_ai_config(AIConfig(provider="openai", model="m", base_url="http://localhost:1234/v1"), {}) == []
