# 인계 (Handoff) — 다른 AI 도구 · 사람이 이어서 작업하기

이 문서만 읽고 이어갈 수 있게 쓴다 (NFR-12). 순서: 이 문서 → `aidlc-state.md` → 필요한 산출물.
마지막 갱신: 2026-11-18 (3주기 한국어 · 영어 전환 완료).

## 1. 지금 상태 한눈에

| 항목 | 상태 |
| --- | --- |
| 무엇 | Hugging Face 의 논문 · Hub 트렌드 · 블로그 뉴스를 PC 에서 매일 06:00 수집 · AI 분석 → 서버 (Docker: PostgreSQL + FastAPI) 저장 → Flutter 앱에서 보기 |
| 주기 | 1주기 (기본 시스템) → 2주기 (Postgres · 뉴스 · 원문 · 06:00 · 설치 즉시 동작 · 앱 개선) → 3주기 (한국어 · 영어 전환: PC 가 원문 본문까지 미리 번역해 서버에 저장, 앱은 lang 으로 읽음) 구현 · 검증 완료 |
| 실행 | 사용자 Mac 에서 `tool/radar-up.sh` 한 번 (아래 3장). 이 저장소를 만든 세션은 Mac 의 Docker · 휴대폰 · huggingface.co 에 접근할 수 없어 실행은 사용자 몫 |
| 남은 확인 | ① `cd app && flutter test` (앱 61개, 2 · 3주기 분 미실행) ② 서버 갱신 (`tool/radar-up.sh --server-only`, 06:00 실행이 자동으로도 함) ③ 번역 채우기 (`tool/radar-daily.sh --translate 90`) ④ 새 APK 설치 (`tool/build-apk.sh --install`) ⑤ 영어 · 한국어 화면 확인 |
| 승인 방식 | 사용자 위임 (Standing Approval). 사용자가 "모든 과정은 너의 추천대로" 라고 함 (audit.md 2026-11-17T16:20:00Z) |

## 2. 구조

```text
Hugging Face ─┬─ Daily Papers (+ 원본 JSON, 주목 논문 본문)       PC (macOS)
              ├─ 트렌딩 모델 · 데이터셋 · Spaces                    pipeline/ (uv, Python 3.11+)
              └─ 블로그 RSS + 글 본문 (뉴스)                        launchd 06:00 → tool/radar-daily.sh
                                │ 업로드 (토큰, http://127.0.0.1:8000)
                                ▼
                    Docker Desktop: deploy/local/compose.yml
                    ├─ db  : postgres:16-alpine (볼륨 radar-pg, 127.0.0.1:5433)
                    └─ api : server/ (FastAPI, 0.0.0.0:8000)
                                ▲ 조회 (http://<PC IP>:8000, 같은 Wi-Fi)
                    휴대폰 앱 app/ (Flutter, profile 빌드에 서버 주소 내장)
```

| 폴더 | 핵심 파일 |
| --- | --- |
| `server/app/` | `schemas.py` (계약 정본), `repository.py` (Postgres), `i18n.py` (lang 응답), `routes_public.py` · `routes_ingest.py`, `trends.py` |
| `pipeline/radar/` | `runner.py` (일일 · 백필 · 뉴스 · 원문 · 번역), `news.py` (RSS · 본문 추출 · 뉴스 분석), `translate.py` (번역), `hf_client.py`, `analyze.py`, `providers.py`, `prompts/*.md` |
| `app/lib/` | `app.dart` (5개 탭 · 언어 전환), `l10n/strings.dart` (`tr(한, 영)`), `ui/screens/` (today · news · news_detail · paper · trend · search · library · settings), `data/` (repository · settings · library · read · cache) |
| `tool/` | `radar-up.sh` (한 번에 켜기), `radar-daily.sh` (06:00 실행), `test-db.sh` (테스트용 Postgres), `check.sh` (전체 점검), `local-app.sh` |
| `deploy/` | `local/` (Docker Desktop · launchd plist), `server/` (원격 운영: Postgres + API + Caddy HTTPS) |
| `aidlc-docs/` | 요구 · 스토리 · 설계 · 감사 기록 · 이 문서 |

## 3. 실행 방법 (사용자 Mac)

준비: Docker Desktop (실행 중, 로그인 시 자동 시작 권장), `uv` (`brew install uv`), Flutter 3.41.7 (앱 설치 시), 휴대폰 USB 연결 (Android: USB 디버깅).

```sh
cd /Volumes/Mac990/Project/ai-trend-radar
tool/radar-up.sh                 # 서버 → (비어 있으면) 90일 채우기 (백그라운드) → 06:00 일정 → 앱 설치
tool/radar-up.sh --status        # 상태 · 최근 실행
tool/radar-daily.sh --translate 90   # 지난 90일 한국어 · 영어 번역 채우기 (몇 시간, 끊겨도 이어서)
tail -f .local/logs/backfill.log # 첫 채우기 진행
```

- 이미 쓰고 있는 Postgres 가 있으면: `tool/radar-up.sh --database-url postgresql://user:pw@localhost:5432/radar` (DB 가 없으면 만든다)
- 분석 AI 는 처음 실행 때 자동 선택 (claude CLI → gemini CLI → Ollama → 없음). 바꾸려면 `.local/pipeline.toml` 의 `[ai]` (형식: `pipeline/deploy/config.example.toml`)
- 비밀: `.local/ingest-token` (권한 600), `.local/.env` (DB 비밀번호 · 토큰 해시). git 제외
- 릴리즈 APK 파일: `tool/build-apk.sh` → `dist/ai-trend-radar-<버전>-<날짜>.apk` (`--install` 로 USB 기기에 설치). http 서버 주소면 그 빌드에만 http 허용 (빌드 중에만 `android/app/src/release/AndroidManifest.xml` 을 만들고 지움), 서명은 Flutter 기본 debug 키 (직접 설치용)
- `radar-up.sh` 가 설치하는 앱은 profile 빌드 (로컬 http 허용). 서버 주소는 빌드 때 `RADAR_SERVER_URL` 로 들어가고 앱 설정에서 바꿀 수 있다. PC 의 IP 가 바뀌면 `tool/local-app.sh` 로 다시 설치하거나 앱 설정에서 고친다

## 4. 점검 (변경 후 반드시)

```sh
tool/check.sh                    # 테스트 DB (Docker) 자동 → server · pipeline · 통합 · 예시 응답 · app
TEST_DATABASE_URL=postgresql://... tool/check.sh --skip-app   # 이미 있는 Postgres 로
```

마지막 결과 (`construction/build-and-test/build-and-test-summary.md`): server 96 · pipeline 127 · 통합 5 passed, 커버리지 97% · 93%, p95 127 ms. 앱 61개는 미실행.

## 5. 규칙 (깨면 안 되는 것)

- 계약 정본은 `server/app/schemas.py`. 필드는 추가만 (`/api/v1`). 바꾸면 `pipeline/radar/models.py` · `pipeline/radar/news.py` (NewsPayloadItem) · `app/lib/models/` · `contract/samples/` (`cd server && python -m tools.make_samples`) 를 같은 커밋에서
- AI 호출은 `providers.complete(system, user)` 하나. 프롬프트 첫 줄 = 작업 이름 (BRIEF · DETAIL · HEADLINE · REPORT · NEWS · TRANSLATE · TRANSLATE_TEXT)
- 앱 화면 글자는 반드시 `tr('한국어', 'English')` 로 두 언어를 함께 쓴다. 번역은 원래 표를 바꾸지 않고 `translations` 표에만 (BR-S40 ~ S43)
- 원문 요청 사이 3초 (NFR-10), 원문 200,000자 · 원본 JSON 100 KB 한도, 원본 JSON 은 공개 응답에 넣지 않음 (BR-S31)
- 비밀은 저장소 · 로그에 두지 않는다. 서버는 토큰 해시만
- AI-DLC: 새 기능은 Requirements Analysis 부터, `audit.md` 는 덧붙이기만 (사용자 입력 원문 그대로)

## 6. 결정 기록 (왜 이렇게 했나)

| 결정 | 이유 | 근거 |
| --- | --- | --- |
| DB = PostgreSQL 16 (Docker) | 사용자 요청 (Docker Desktop 의 Postgres), 원문 · JSONB 저장 | FR-23, audit 16:00 |
| 뉴스 = Hugging Face 블로그 | HF 에 별도 뉴스 API 없음, RSS 는 본문이 없어 글 페이지에서 본문 추출 | FR-25, cycle2-design BR-P30 · P31 |
| 논문 본문 = HF 논문 페이지 본문 (`/papers/{id}.md`) | arXiv 원문을 HF 가 변환한 것, 1주기 분석 입력과 같은 경로 · 호스트 하나 | BR-P31 |
| 스케줄 = PC launchd 06:00 (서버 컨테이너 아님) | 분석 AI (구독형 CLI · Ollama) 가 PC 에 있음 | FR-28, BR-P35 |
| 앱 = profile 빌드 + 주소 내장 | "설치하면 바로 동작", 로컬 http 허용은 debug · profile 만 (release 는 https) | FR-29, BR-A20 |
| 테스트 DB = 실제 Postgres (Docker, 메모리) | SQLite 와 동작 차이를 숨기지 않기 위해 | `tool/test-db.sh` |
| 번역 = PC 가 미리 만들어 서버 `translations` 표에 저장 | 사용자 선택 (확인 질문). 서버에는 AI 가 없고, 앱은 언어를 바꿔도 즉시 표시 | FR-33 ~ FR-35, cycle3-design |
| 번역 범위 = 원문 본문까지 | 사용자 선택. AI 사용량이 커서 시간 상한 (180분/회) · 짧은 것 먼저 · 이어서 하기 | FR-34, NFR-13 |
| 앱 언어 전환 = 전체 다시 그리기 (상태 유지) | 화면 위치 · 열린 화면을 잃지 않고 바로 바뀜 | BR-A30 |

## 7. 다음에 할 만한 일 (우선순위)

1. 사용자 Mac 실행 결과 확인 → 실패 시 `docs`가 아니라 `audit.md` 에 원문 기록 후 수정 (버그는 실패 테스트 먼저)
2. 앱 테스트 결과 반영 (실패 시 `app/test` 기준으로 수정)
3. 다음 주기 후보 (requirements.md 범위 밖 목록): 푸시 알림 (06:00 갱신 후 요약 알림), 밀린 날 따라잡기, 모델 · 조직 팔로우, 듣기 모드, 공개 배포 (deploy/server + release 빌드)
