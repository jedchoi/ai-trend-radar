"""AI 제공자 (C-P5, NFR-P01): 모두 `complete(system, user) -> str` 하나만 구현한다.

SDK 없이 HTTP 를 직접 부르고, 구독형 CLI (예: claude, gemini, codex) 는 `cli` 제공자로 부른다.
모델 이름은 설정에서 받는다 (각 제공자 문서에서 현재 이름 확인).
"""

from __future__ import annotations

import subprocess
import time
from collections.abc import Callable, Mapping
from typing import Any

import httpx

from radar.config import AIConfig
from radar.retry import with_retry

PROVIDERS = ("none", "anthropic", "openai", "gemini", "ollama", "cli")
KEY_REQUIRED = {"anthropic", "gemini"}
DEFAULT_BASE = {
    "anthropic": "https://api.anthropic.com",
    "openai": "https://api.openai.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "ollama": "http://localhost:11434",
}


class ProviderError(RuntimeError):
    """메시지에 키 · 프롬프트를 넣지 않는다."""


def check_ai_config(cfg: AIConfig, env: Mapping[str, str]) -> list[str]:
    """BR-P11: 실행 전에 빠진 설정을 모두 알려준다."""
    if cfg.provider not in PROVIDERS:
        return [f"[ai] provider 는 {', '.join(PROVIDERS)} 중 하나여야 합니다 (지금: {cfg.provider})"]
    problems = []
    if cfg.provider == "none":
        return problems
    if cfg.provider == "cli":
        if not cfg.command:
            problems.append('[ai] cli 제공자는 command 가 필요합니다 (예: command = ["claude", "-p"])')
        if cfg.prompt_mode not in ("stdin", "arg"):
            problems.append("[ai] prompt_mode 는 stdin 또는 arg 여야 합니다")
        return problems
    if not cfg.model:
        problems.append(f"[ai] {cfg.provider} 제공자는 model 이 필요합니다")
    needs_key = cfg.provider in KEY_REQUIRED or (cfg.provider == "openai" and not cfg.base_url)
    if needs_key:
        if not cfg.api_key_env:
            problems.append(f"[ai] {cfg.provider} 제공자는 api_key_env (키가 든 환경 변수 이름) 가 필요합니다")
        elif not env.get(cfg.api_key_env):
            problems.append(f"API 키가 없습니다: 환경 변수 {cfg.api_key_env}")
    return problems


class _HTTPProvider:
    name = "http"

    def __init__(self, cfg: AIConfig, http: httpx.Client, api_key: str, sleep: Callable[[float], None]):
        self.cfg = cfg
        self.http = http
        self.api_key = api_key
        self.sleep = sleep
        self.base = (cfg.base_url or DEFAULT_BASE[self.name]).rstrip("/")

    def _post(self, url: str, body: dict, headers: dict[str, str]) -> Any:
        try:
            response = with_retry(
                lambda: self.http.post(url, json=body, headers=headers, timeout=self.cfg.timeout_s), self.sleep
            )
        except httpx.TransportError as exc:
            raise ProviderError(f"{self.name}: 연결 실패 ({type(exc).__name__})") from exc
        if response.status_code >= 400:
            raise ProviderError(f"{self.name}: HTTP {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(f"{self.name}: JSON 아님") from exc

    @staticmethod
    def _pick(data: Any, *path) -> str:
        try:
            for key in path:
                data = data[key]
        except (KeyError, IndexError, TypeError) as exc:
            raise ProviderError("응답 형식이 예상과 다름") from exc
        if not isinstance(data, str):
            raise ProviderError("응답 형식이 예상과 다름")
        return data


class AnthropicProvider(_HTTPProvider):
    name = "anthropic"

    def complete(self, system: str, user: str) -> str:
        data = self._post(
            f"{self.base}/v1/messages",
            {
                "model": self.cfg.model,
                "max_tokens": self.cfg.max_tokens,
                "temperature": self.cfg.temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
            {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"},
        )
        return self._pick(data, "content", 0, "text")


class OpenAIProvider(_HTTPProvider):
    """OpenAI 및 OpenAI 호환 서버 (base_url 로 지정: LM Studio, vLLM, OpenRouter 등)."""

    name = "openai"

    def complete(self, system: str, user: str) -> str:
        headers = {"authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        data = self._post(
            f"{self.base}/chat/completions",
            {
                "model": self.cfg.model,
                "temperature": self.cfg.temperature,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            },
            headers,
        )
        return self._pick(data, "choices", 0, "message", "content")


class GeminiProvider(_HTTPProvider):
    name = "gemini"

    def complete(self, system: str, user: str) -> str:
        data = self._post(
            f"{self.base}/models/{self.cfg.model}:generateContent",
            {
                "systemInstruction": {"parts": [{"text": system}]},
                "contents": [{"role": "user", "parts": [{"text": user}]}],
                "generationConfig": {"temperature": self.cfg.temperature, "responseMimeType": "application/json"},
            },
            {"x-goog-api-key": self.api_key},
        )
        return self._pick(data, "candidates", 0, "content", "parts", 0, "text")


class OllamaProvider(_HTTPProvider):
    name = "ollama"

    def complete(self, system: str, user: str) -> str:
        data = self._post(
            f"{self.base}/api/chat",
            {
                "model": self.cfg.model,
                "stream": False,
                "format": "json",
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "options": {"temperature": self.cfg.temperature},
            },
            {},
        )
        return self._pick(data, "message", "content")


class CLIProvider:
    """구독형 AI CLI 를 부른다. prompt_mode=stdin 이면 표준 입력, arg 면 마지막 인자로 프롬프트를 넘긴다."""

    name = "cli"

    def __init__(self, cfg: AIConfig, runner: Callable[..., subprocess.CompletedProcess] = subprocess.run):
        self.cfg = cfg
        self.runner = runner

    def complete(self, system: str, user: str) -> str:
        prompt = f"{system}\n\n{user}"
        stdin = self.cfg.prompt_mode == "stdin"
        cmd = list(self.cfg.command) + ([] if stdin else [prompt])
        try:
            result = self.runner(
                cmd,
                input=prompt if stdin else None,
                capture_output=True,
                text=True,
                timeout=self.cfg.timeout_s,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise ProviderError(f"cli: {self.cfg.timeout_s}초 안에 끝나지 않음") from exc
        except OSError as exc:
            raise ProviderError(f"cli: 실행 실패 ({type(exc).__name__})") from exc
        if result.returncode != 0:
            raise ProviderError(f"cli: 종료 코드 {result.returncode}")
        return result.stdout


HTTP_PROVIDERS = {
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
    "gemini": GeminiProvider,
    "ollama": OllamaProvider,
}


def make_provider(
    cfg: AIConfig,
    env: Mapping[str, str],
    http: httpx.Client | None = None,
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    sleep: Callable[[float], None] = time.sleep,
):
    """`none` 이면 None (AI 없이 동작)."""
    if cfg.provider == "none":
        return None
    if cfg.provider == "cli":
        return CLIProvider(cfg, runner)
    api_key = env.get(cfg.api_key_env, "") if cfg.api_key_env else ""
    return HTTP_PROVIDERS[cfg.provider](cfg, http or httpx.Client(timeout=cfg.timeout_s), api_key, sleep)
