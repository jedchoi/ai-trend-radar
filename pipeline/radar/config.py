"""설정 (TOML) 과 비밀 읽기 (C-P9, NFR-P05). 설정 파일에는 비밀 대신 환경 변수 이름만 둔다."""

from __future__ import annotations

import dataclasses
import os
import stat
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

DEFAULT_CONFIG_PATH = Path("~/.config/ai-trend-radar/config.toml")
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class ServerConfig:
    url: str = ""
    token_env: str = "RADAR_INGEST_TOKEN"  # noqa: S105 - 비밀이 아닌 환경 변수 이름
    token_file: str = ""


@dataclass(frozen=True)
class AIConfig:
    provider: str = "none"  # none | anthropic | openai | gemini | ollama | cli
    model: str = ""
    api_key_env: str = ""
    base_url: str = ""
    command: list[str] = field(default_factory=list)
    prompt_mode: str = "stdin"  # cli 제공자: stdin | arg
    max_ai_papers: int = 60
    timeout_s: int = 120
    max_tokens: int = 4096
    temperature: float = 0.2


@dataclass(frozen=True)
class CollectConfig:
    models: int = 10
    datasets: int = 5
    spaces: int = 5
    markdown_max_chars: int = 20000
    full_text: bool = True  # 주목 논문 본문 원문 저장 (FR-26)
    full_text_max_chars: int = 200000
    news: bool = True  # Hugging Face 블로그 뉴스 (FR-25)
    news_days: int = 3  # 매일 실행에서 볼 기간 (BR-P30)


@dataclass(frozen=True)
class SelectConfig:
    max_featured: int = 5
    focus_topics: list[str] = field(default_factory=lambda: ["llm-reasoning", "agents"])


@dataclass(frozen=True)
class TranslateConfig:
    """3주기: 한국어 · 영어 번역 (FR-35, NFR-13)."""

    enabled: bool = True
    days: int = 90  # 매일 실행에서 살펴볼 기간 (이미 번역된 것은 해시 비교만)
    max_minutes: int = 180  # 한 번 실행의 번역 시간 상한, 0 = 무제한
    chunk_chars: int = 6000  # 긴 본문 조각 크기
    full_text: bool = True  # 원문 본문까지 번역


@dataclass(frozen=True)
class PathsConfig:
    data_dir: str = "~/.local/share/ai-trend-radar"


@dataclass(frozen=True)
class Config:
    server: ServerConfig = field(default_factory=ServerConfig)
    ai: AIConfig = field(default_factory=AIConfig)
    collect: CollectConfig = field(default_factory=CollectConfig)
    select: SelectConfig = field(default_factory=SelectConfig)
    paths: PathsConfig = field(default_factory=PathsConfig)
    translate: TranslateConfig = field(default_factory=TranslateConfig)

    @property
    def data_path(self) -> Path:
        return Path(self.paths.data_dir).expanduser().resolve()


SECTIONS = {
    "server": ServerConfig,
    "ai": AIConfig,
    "collect": CollectConfig,
    "select": SelectConfig,
    "paths": PathsConfig,
    "translate": TranslateConfig,
}


def load_config(path: Path | str) -> Config:
    """TOML → Config. 모르는 절 · 키는 오타로 보고 오류 (조용히 무시하지 않음)."""
    data = tomllib.loads(Path(path).expanduser().read_text("utf-8"))
    parts = {}
    for name, value in data.items():
        if name not in SECTIONS:
            raise ValueError(f"알 수 없는 설정 절: [{name}]")
        cls = SECTIONS[name]
        known = {f.name for f in dataclasses.fields(cls)}
        unknown = set(value) - known
        if unknown:
            raise ValueError(f"[{name}] 에 알 수 없는 키: {', '.join(sorted(unknown))}")
        parts[name] = cls(**value)
    return Config(**parts)


def read_token(server: ServerConfig, env: Mapping[str, str]) -> str | None:
    """업로드 토큰: 환경 변수 → 토큰 파일 순. 파일 권한이 넓으면 읽지 않는다."""
    value = env.get(server.token_env, "").strip() if server.token_env else ""
    if value:
        return value
    if server.token_file:
        path = Path(server.token_file).expanduser()
        if path.exists():
            mode = stat.S_IMODE(path.stat().st_mode)
            if mode & 0o077:
                return None
            return path.read_text("utf-8").strip() or None
    return None


def check_server_config(server: ServerConfig, env: Mapping[str, str]) -> list[str]:
    problems = []
    parsed = urlparse(server.url)
    if not server.url or parsed.scheme not in ("https", "http") or not parsed.hostname:
        problems.append("[server] url 이 비었거나 형식이 틀립니다 (예: https://radar.example.com)")
    elif parsed.scheme == "http" and parsed.hostname not in LOCAL_HOSTS:
        problems.append("[server] url 은 https:// 여야 합니다 (http 는 localhost 테스트만 허용)")
    if read_token(server, env) is None:
        hint = f"환경 변수 {server.token_env}" + (
            f" 또는 파일 {server.token_file} (권한 600)" if server.token_file else ""
        )
        problems.append(f"업로드 토큰이 없습니다: {hint}")
    return problems


def environ() -> Mapping[str, str]:
    return os.environ
