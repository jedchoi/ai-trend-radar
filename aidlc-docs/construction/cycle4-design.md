# 4주기 설계 — 같은 응답에 두 언어 (3주기 설계 개정)

근거: requirements.md 4주기 (FR-38 ~ FR-42), stories.md Epic H (US-32 ~ US-34). 승인: 사용자 위임 ("물어보지말고 완료해", audit 2026-11-18T02:00:00Z).
3주기 설계 (`cycle3-design.md`) 중 바뀌는 것: 조회 API 의 `lang` · `untranslated` (삭제), 번역 범위 (요약류만), 앱 요청 방식. 나머지 (translations 표, 업로드 API, 번역 검색, 파이프라인 상태 · 시간 상한) 는 그대로.

## 1. 계약

### 응답 — 각 항목에 `i18n` (필드 추가)

| 응답 모델 | `i18n.{ko,en}` 에 들어가는 필드 |
| --- | --- |
| `Paper` | `one_liner`, `detail`, `glossary` |
| `PaperBrief` (검색 · 관련 · 화제 논문) | `one_liner` |
| `Digest`, `DigestSummary` | `headline` |
| `NewsBrief`, `News` | `summary` (+ `News` 는 `key_points`) |
| `TrendReport` | `narrative` (+ `top_papers` 각 항목의 `i18n`) |

- 기존 단일 필드 (`one_liner`, `headline` 등) 는 그대로 둔다 (원래 저장된 값, 이전 앱 호환)
- 제목 · 초록 · 본문 (`title`, `abstract`, `full_text`, `content`) 은 `i18n` 에 없다 — 언제나 원문 (FR-41)
- 3주기의 `?lang=` 과 `untranslated` 는 없앤다 (공개 전 개정)

### 번역 업로드 (`POST /api/v1/ingest/translations`) — 허용 필드 축소

| kind | 허용 필드 |
| --- | --- |
| paper | `one_liner`, `detail`, `glossary` |
| news | `summary`, `key_points` |
| digest | `headline` |
| report | `narrative` |

## 2. 업무 규칙

- **BR-S50** 기준 언어: 원래 표의 값에 한글 (가-힣) 이 있으면 `ko`, 없으면 `en`. `i18n[기준 언어]` = 원래 값, `i18n[반대 언어]` = translations 표의 그 언어 값 (있을 때만). translations 에 기준 언어와 같은 언어 값이 있어도 원래 값이 이긴다 (재분석으로 기준 언어가 바뀐 경우)
- **BR-S51** 목록 · 일일 요약도 같은 규칙 (한 번의 조회로 항목 전체의 번역을 가져온다)
- **BR-P50** 번역 대상: 요약류만. 목표 언어 = 기준 언어의 반대. 묶음: 논문 요약 (상세 없음) 10편씩, 상세 있는 논문 3편씩, 뉴스 5건씩, 세 줄 · 리포트 5건씩 (종류별)
- **BR-P51** 같은 원본 · 같은 목표 언어는 한 번만 (3주기 해시 규칙 그대로). 긴 본문 번역 단계는 없앤다 (`[translate] full_text` · `chunk_chars` 는 읽기만 하고 쓰지 않음 — 예전 설정 파일 호환)
- **BR-A50** 앱은 `lang` 없이 요청한다. 모델 값 (한 줄 요약 · 상세 · 용어 · 세 줄 · 뉴스 요약 · 핵심 · 리포트) 은 지금 언어의 `i18n` → 없으면 다른 언어 → 없으면 원래 필드 순으로 고른다
- **BR-A51** 언어를 바꾸면 화면만 다시 그린다 (다시 받지 않음). 고른 언어 값이 없고 다른 언어 값만 있으면 "번역 준비 중"
- **BR-A52** 원문 영역 이름은 언제나 "원문 (영어 원문 그대로)" / "Original"
- **BR-A53** 보관함 항목은 저장할 때 `i18n` 도 함께 저장해 언어를 바꾸면 같이 바뀐다

## 3. 테스트 계획 (TDD)

| 대상 | 테스트 |
| --- | --- |
| server | `tests/test_i18n.py` 다시 작성: 같은 응답에 ko · en, 기준 언어 판별 (한글 / 영어), 번역 없으면 한 언어만, 원문 필드는 i18n 에 없음, 허용 필드 (title · abstract · content → 422), 목록 · 검색 · 관련 · 리포트, 재업로드 후 유지, 번역 검색 |
| pipeline | `tests/test_translate.py` 다시 작성: 목표 언어 = 반대 언어 (영어 요약 → ko), 요약류만 (제목 · 본문 없음), 묶음 크기, 한 번만 · 바뀌면 다시, 형식 검사, 시간 상한, 계약 |
| integration | 번역 후 같은 응답에 ko · en, 제목 · 본문 영어 |
| app | 모델이 언어에 따라 값을 고름 (없으면 다른 언어 + 준비 중), 요청에 lang 없음, 언어 버튼 → 다시 받지 않고 요약 전환, 원문 영어 |
