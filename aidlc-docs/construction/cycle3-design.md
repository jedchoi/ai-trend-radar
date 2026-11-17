# 3주기 설계 — 한국어 · 영어 전환 (Functional · NFR · Infrastructure Design, 3 unit 공통)

근거: `inception/requirements/requirements.md` 3주기 (FR-32 ~ FR-37, NFR-13 ~ NFR-15), `inception/user-stories/stories.md` Epic G (US-28 ~ US-31).
승인: 확인 질문 3개 답 (audit.md 2026-11-18T00:20:00Z) + 사용자 위임.

## 1. 데이터 · 계약 (필드 추가만, NFR-07)

### 번역 표 `translations`

| 열 | 내용 |
| --- | --- |
| `kind` | `paper` · `news` · `digest` · `report` |
| `key` | 논문 id · 뉴스 id · 날짜 (`2026-11-17`) · `week:2026-W47` / `month:2026-11` |
| `lang` | `ko` · `en` |
| `fields` | 번역된 필드 JSON (아래 표의 키만). 업로드할 때마다 키 단위로 합친다 (`fields || 새 fields`) |
| `provider` | 번역에 쓴 AI |

| kind | 번역 필드 (허용 키 · 길이) |
| --- | --- |
| paper | `title` ≤500, `one_liner` ≤400, `abstract` ≤20000, `full_text` ≤200000, `detail` {what, novelty, why, apply 각 ≤1500}, `glossary` [{term ≤80, explanation ≤400}] ≤5 |
| news | `title` ≤500, `summary` ≤800, `key_points` [≤300] ≤6, `content` ≤200000 |
| digest | `headline` [≤300] ≤3 |
| report | `narrative` ≤3000 |

### API

| API | 설명 |
| --- | --- |
| `POST /api/v1/ingest/translations` `{provider, items[1..50]: {kind, key, lang, fields}}` | 토큰 필요. 키 형식 · 필드 검사 (BR-S41). 응답 `{translations: n}` |
| 조회 API 의 `?lang=ko|en` | `/digests`, `/digests/latest`, `/digests/{day}`, `/papers`, `/papers/{id}`, `/news`, `/news/{id}`, `/trends/weekly/*`, `/trends/monthly/*`. 번역 필드로 바꿔서 같은 모양으로 응답 (BR-S40) |
| 응답 추가 필드 | `Paper.untranslated`, `News.untranslated`, `Digest.untranslated`, `TrendReport.untranslated` (bool) — 그 항목의 `lang` 번역 행이 없으면 true |

## 2. 업무 규칙

### backend-server
- **BR-S40** `lang` 이 있으면 응답의 각 항목에 그 언어 번역 필드를 덮어쓴다 (없는 필드는 원래 값). `lang` 이 없으면 바꾸지 않는다. 목록 · 일일 요약에는 긴 필드 (`full_text`, `content`) 를 가져오지 않는다
- **BR-S41** 번역 업로드: kind 별 키 형식 (paper = 논문 id, news = 뉴스 id, digest = 날짜, report = `week:YYYY-Www` · `month:YYYY-MM`), 허용 키 외 · 빈 필드 → 422. 한 트랜잭션, ingest_log `translation` 1행
- **BR-S42** 검색 (BR-S10, BR-S33) 은 번역문도 본다: 논문 · 뉴스의 `search_i18n` (번역 필드 전체를 소문자로 이은 글) 을 번역 업로드 · 원본 재업로드 때 다시 만든다
- **BR-S43** 원본 (논문 · 뉴스) 을 지워도 번역은 남는다 (같은 id 로 다시 올라오면 그대로 쓰임). 원본이 바뀌었는지는 파이프라인이 판단한다 (BR-P43)

### pc-pipeline
- **BR-P40** 번역 단계 (`radar translate --days N`): 서버의 공개 조회 API 로 원본을 읽어 (lang 없이), 필요한 번역을 만들어 올린다. 순서 = ① 짧은 항목 (최근 날부터: 일일 요약의 논문 · 세 줄, 뉴스 요약 · 제목, 리포트) ② 긴 본문 (뉴스 본문, 주목 논문 본문, 최근 것부터)
- **BR-P41** 묶음: 논문 한국어 (제목 · 초록) 5편씩, 논문 영어 (한 줄 요약 · 상세 · 용어) 5편씩, 세 줄 · 리포트 · 뉴스 짧은 항목은 1건씩. 긴 본문은 문단 경계로 약 6,000자씩 나눠 차례로 번역해 이어 붙인다
- **BR-P42** 형식 검사 (NFR-14): JSON 번역은 같은 키 구조 · 빈 문자열 없음, 긴 글 조각은 비어 있지 않고 원문 길이의 15% 이상. 실패하면 1회 재요청, 그래도 실패하면 그 항목만 건너뛴다 (표시 안 함 → 다음 실행에서 다시)
- **BR-P43** 한 번만: `data_dir/translated.json` 에 `{kind}:{key}:{lang}:{part}` → 원본 해시 · 제공자. 해시가 같으면 건너뛰고, 원본이 바뀌면 다시 번역한다. AI 없음 (`none`) 이면 번역 단계를 건너뛴다
- **BR-P44** 시간 상한 (NFR-13): `[translate] max_minutes` (기본 180) 를 넘으면 지금 항목을 마치고 멈춘다. 0 = 무제한
- **BR-P45** 매일 실행 (`radar daily`) 은 논문 → 뉴스 → 리포트 뒤에 `translate --days [translate] days` (기본 90) 를 한다. 이미 번역된 것은 해시 비교만 하므로 빠르다. 백필도 끝에 번역한다
- 프롬프트: `prompts/translate.md` (TRANSLATE, JSON 값만 번역), `prompts/translate_text.md` (TRANSLATE_TEXT, 긴 글 조각, 번역문만 출력). 둘 다 대상 언어 · 원칙 (모델 · 제품 이름, 코드, 수식, URL, 마크다운 기호 유지) 을 적는다

### mobile-app
- **BR-A30** 언어 설정 `ko` (기본) · `en`, 기기에 저장. 바꾸면 열려 있는 화면이 그 언어로 다시 불러온다
- **BR-A31** 모든 내용 요청에 `lang` 을 붙인다 (오프라인 저장본도 언어별)
- **BR-A32** 화면 글자는 `lib/l10n/strings.dart` 의 `S` (한 · 영 두 값을 같이 둔다). 주제 · 보관 상태 · Hub 종류 이름, 날짜 · 주차 표기도 언어별
- **BR-A33** 오늘 화면 · 논문 상세 · 뉴스 상세 위쪽에 언어 버튼 (`한` / `EN`). 설정에도 같은 선택
- **BR-A34** `untranslated` 인 항목은 "번역 준비 중" (영어: "Translation pending") 표시
- **BR-A35** 원문 영역 이름: 영어 = "Original", 한국어 = 번역이 있으면 "본문 (번역)", 없으면 "원문"

## 3. 인프라

변경 없음 (표 1개 · 열 2개 추가는 서버 시작 때 `IF NOT EXISTS` 로). `tool/radar-daily.sh --translate N` 추가 (지난 데이터 채우기, 시간 상한 없음).

## 4. 테스트 계획 (TDD)

| 대상 | 테스트 |
| --- | --- |
| server | `tests/test_i18n.py`: 업로드 검증 (BR-S41), 합치기, 각 조회 API 의 lang 적용 (BR-S40), 목록에 긴 필드 없음, untranslated, 한국어 검색 (BR-S42), 원본 재업로드 후에도 번역 · 검색 유지, lang 없으면 그대로 |
| pipeline | `tests/test_translate.py`: 순서 (짧은 것 먼저 · 최근 날부터), 묶음 크기, 긴 글 나누기 · 이어 붙이기, 형식 검사 · 재요청 · 건너뛰기, 해시로 한 번만 · 원본 바뀌면 다시, 시간 상한, none 이면 건너뜀, 계약 (서버 스키마로 검사) |
| integration | 파이프라인 번역 → 실제 서버 → `lang=en` · `lang=ko` 조회 |
| app | 언어 저장 · 요청에 lang, 영어 화면 글자 · 내용, 번역 준비 중 표시, 언어 버튼 전환 |
