"""명령 (C-P9): radar daily | backfill | news | translate | report | check | token"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import secrets
import sys
from pathlib import Path

import httpx

from radar.analyze import Analyzer
from radar.config import DEFAULT_CONFIG_PATH, Config, environ, load_config, read_token
from radar.hf_client import HFClient
from radar.providers import make_provider
from radar.publish import ServerClient
from radar.runner import BACKFILL_MAX_DAYS, EXIT_CONFIG, EXIT_OK, Runner

HF_BASE = os.environ.get("RADAR_HF_BASE_URL", "https://huggingface.co")  # 시험용 대체 주소
USER_AGENT = "ai-trend-radar/1.0"


def _date(value: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("YYYY-MM-DD 형식이어야 합니다") from exc


def _days(value: str) -> int:
    try:
        n = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("숫자여야 합니다") from exc
    if not 1 <= n <= BACKFILL_MAX_DAYS:
        raise argparse.ArgumentTypeError(f"1 ~ {BACKFILL_MAX_DAYS} 사이여야 합니다")
    return n


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="radar", description="AI Trend Radar PC 파이프라인")
    p.add_argument("--config", default=str(DEFAULT_CONFIG_PATH), help="설정 파일 (기본 %(default)s)")
    sub = p.add_subparsers(dest="command", required=True)
    d = sub.add_parser("daily", help="수집 → 분석 → 업로드 (+ 빠진 날 채우기, 리포트)")
    d.add_argument("--date", type=_date, help="이 날짜만 처리 (YYYY-MM-DD)")
    d.add_argument("--no-backfill", action="store_true", help="빠진 날을 채우지 않음")
    d.add_argument("--dry-run", metavar="FILE", help="업로드하지 않고 결과를 파일로 저장")
    b = sub.add_parser(
        "backfill", help="지난 N 일을 수집 · 업로드 → AI 분석 (최근 날부터) → 주 · 월 리포트. 다시 돌리면 이어서"
    )
    b.add_argument("--days", type=_days, default=90, help="며칠 치 (1~120, 기본 90)")
    b.add_argument("--until", type=_date, help="마지막 날짜 (기본: 한국 시간 어제)")
    b.add_argument("--no-reports", action="store_true", help="주 · 월 리포트를 만들지 않음")
    n = sub.add_parser("news", help="Hugging Face 블로그 새 글 → 본문 원문 → 분석 → 업로드")
    n.add_argument("--days", type=_days, default=3, help="며칠 안의 글 (1~120, 기본 3)")
    t = sub.add_parser("translate", help="서버의 논문 · 뉴스 · 리포트를 한국어 · 영어로 미리 번역해 올림 (이어서 실행)")
    t.add_argument("--days", type=_days, default=None, help="며칠 치 (기본: 설정 [translate] days)")
    t.add_argument("--max-minutes", type=int, default=None, help="시간 상한 (분, 0 = 무제한)")
    sub.add_parser("report", help="오늘이 월요일 · 1일이면 주간 · 월간 리포트 문장 업로드")
    c = sub.add_parser("check", help="설정 · 키 · 서버 연결 확인")
    c.add_argument("--offline", action="store_true", help="서버 연결은 확인하지 않음")
    sub.add_parser("token", help="새 업로드 토큰과 서버용 해시 만들기")
    return p


def build_runner(config: Config) -> Runner:
    env = environ()
    timeout = httpx.Timeout(30.0)
    headers = {"user-agent": USER_AGENT}
    hf = HFClient(httpx.Client(base_url=HF_BASE, timeout=timeout, headers=headers, follow_redirects=True))
    server = ServerClient(
        httpx.Client(base_url=config.server.url, timeout=timeout, headers=headers),
        token=read_token(config.server, env) or "",
    )
    provider = make_provider(config.ai, env)
    analyzer = Analyzer(
        provider=provider,
        max_ai_papers=config.ai.max_ai_papers,
        markdown=lambda pid: hf.paper_markdown(pid, config.collect.markdown_max_chars),
    )
    return Runner(config=config, hf=hf, server=server, analyzer=analyzer)


def cmd_token() -> int:
    token = secrets.token_urlsafe(32)
    print("업로드 토큰 (PC 키체인 · 환경 변수에 저장, 다시 표시되지 않음):")
    print(f"  RADAR_INGEST_TOKEN={token}")
    print("서버 .env 에 넣을 해시:")
    print(f"  INGEST_TOKEN_SHA256={hashlib.sha256(token.encode()).hexdigest()}")
    return EXIT_OK


def cmd_check(config: Config, offline: bool) -> int:
    runner = build_runner(config)
    problems = runner.config_problems()
    if not offline and not problems:
        try:
            health = runner.server.health()
            print(f"서버 연결 확인: 최신 날짜 {health.get('latest_date')}")
        except Exception as exc:  # noqa: BLE001
            problems.append(f"서버에 연결할 수 없습니다: {exc}")
    for p in problems:
        print(f"설정 문제: {p}")
    if not problems:
        print(f"문제 없음 (제공자: {config.ai.provider}, 데이터: {config.data_path})")
    return EXIT_CONFIG if problems else EXIT_OK


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.command == "token":
        return cmd_token()
    path = Path(args.config).expanduser()
    config = load_config(path) if path.exists() else Config()
    if args.command == "check":
        return cmd_check(config, args.offline)
    built = build_runner(config)
    if args.command == "report":
        return built.run_reports() or EXIT_OK
    if args.command == "news":
        problems = built.config_problems()
        for problem in problems:
            print(f"설정 문제: {problem}")
        return EXIT_CONFIG if problems else built.run_news(args.days)
    if args.command == "translate":
        problems = built.config_problems()
        for problem in problems:
            print(f"설정 문제: {problem}")
        return EXIT_CONFIG if problems else built.run_translate(args.days, args.max_minutes)
    if args.command == "backfill":
        return built.run_backfill(days=args.days, until=args.until, reports=not args.no_reports)
    code = built.run_daily(
        explicit=args.date, backfill=not args.no_backfill, dry_run_out=Path(args.dry_run) if args.dry_run else None
    )
    if code == EXIT_OK and not args.dry_run:
        built.run_reports()
        built.run_translate()  # BR-P45: 논문 → 뉴스 → 리포트 → 번역
    return code


if __name__ == "__main__":
    sys.exit(main())
