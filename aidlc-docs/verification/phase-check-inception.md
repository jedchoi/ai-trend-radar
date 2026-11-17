# Traceability Check 결과 — ① Inception (Inception → Construction)

- **점검 시각**: 2026-11-17T13:20:00Z
- **회차**: 1
- **대상 결정**: 인자 `inception` (사용자 위임에 따라 AI 가 phase 경계에서 실행)
- **입력 파일**:
  - aidlc-docs/inception/requirements/requirements.md
  - aidlc-docs/inception/user-stories/stories.md
  - aidlc-docs/inception/application-design/components.md
  - aidlc-docs/inception/application-design/unit-of-work-story-map.md

## 1. 요약

| 항목 | 값 |
| --- | --- |
| 판정 | 통과 |
| 정방향 대상 수 | 31 (FR 22 · NFR 9) |
| OK | 31 |
| GAP | 0 |
| Deferred | 0 |
| N/A | 0 |
| ORPHAN (역방향) | 0 |
| 커버리지 | 요구 → 스토리 22/22 (FR), AC → Unit 20/20 스토리, NFR → 컴포넌트 9/9 |

## 2. 정방향 추적 (요구 → 하위 산출물)

| ID | 내용 요약 | User Story | 컴포넌트 | Unit | 상태 |
| --- | --- | --- | --- | --- | --- |
| FR-01 | 수집 | US-16 | C-P1 | pc-pipeline | OK |
| FR-02 | 주목 논문 선별 | US-16 | C-P3, C-P2 | pc-pipeline | OK |
| FR-03 | 분류 · 요약 · 용어 · 세 줄 | US-16, US-05 | C-P4, C-P6 | pc-pipeline | OK |
| FR-04 | 제공자 선택 | US-17 | C-P5, C-P9 | pc-pipeline | OK |
| FR-05 | 검사 · 재시도 · 대체 | US-17 | C-P4, C-P10 | pc-pipeline | OK |
| FR-06 | 멱등 업로드 | US-19 | C-P7, C-S2, C-S4 | pc-pipeline, backend-server | OK |
| FR-07 | 빠진 날 채우기 | US-18 | C-P8 | pc-pipeline | OK |
| FR-08 | 주 · 월 리포트 문장 | US-11, US-20 | C-P8, C-P4, C-S2 | pc-pipeline, backend-server | OK |
| FR-09 | 실행 기록 | US-16 | C-P8 | pc-pipeline | OK |
| FR-10 | 토큰 인증 업로드 저장 | US-19 | C-S2, C-S3, C-S4 | backend-server | OK |
| FR-11 | 조회 API | US-01, US-07 | C-S1, C-S4 | backend-server | OK |
| FR-12 | 검색 API | US-12 | C-S1, C-S4 | backend-server | OK |
| FR-13 | 트렌드 API | US-09, US-10 | C-S5 | backend-server | OK |
| FR-14 | 뉴스 리스트 | US-01 ~ US-03 | C-A8, C-A1 | mobile-app | OK |
| FR-15 | 뉴스 요약 | US-05 ~ US-07 | C-A8 | mobile-app | OK |
| FR-16 | 트렌드 분석 화면 | US-09 ~ US-11 | C-A8, C-A9 | mobile-app | OK |
| FR-17 | 검색 화면 | US-12 | C-A8 | mobile-app | OK |
| FR-18 | 보관함 | US-13 | C-A4 | mobile-app | OK |
| FR-19 | 관심 키워드 정렬 | US-04 | C-A6, C-A3 | mobile-app | OK |
| FR-20 | AI 에게 묻기 | US-08 | C-A7 | mobile-app | OK |
| FR-21 | 오프라인 | US-14 | C-A2 | mobile-app | OK |
| FR-22 | 설정 | US-04, US-15 | C-A3 | mobile-app | OK |
| NFR-01 | 이식성 | US-17 | C-P5, C-P6 | pc-pipeline | OK |
| NFR-02 | 응답 성능 | US-09, US-12 | C-S4, C-S5 | backend-server | OK |
| NFR-03 | 실패 격리 | US-19 | C-P8, C-S4 | 둘 다 | OK |
| NFR-04 | 보안 | US-19 | C-S3, C-S7 | backend-server | OK |
| NFR-05 | 비용 상한 | US-17 | C-P4 | pc-pipeline | OK |
| NFR-06 | 테스트 | 전체 | 전체 | 전체 | OK |
| NFR-07 | 호환성 | US-01 | C-S6, C-A5 | backend-server, mobile-app | OK |
| NFR-08 | 실행 시간 | US-16 | C-P8 | pc-pipeline | OK |
| NFR-09 | 언어 | US-05 | C-P6 | pc-pipeline | OK |

## 3. 역방향 추적 (근거 없는 항목)

없음

## 4. 일관성 경고

- 없음 (기획서의 "정적 호스팅" 제안은 사용자 지시 "backend 서버" 로 대체됨, audit.md 기록)

## 5. 보완 제안

없음

## 6. 한계

- AI 가 문서를 대조한 결과이며 기계 검증이 아님

## 7. 사람 확인

- [ ] 점검 결과 검토 완료 (승인자: [ ], 시각: [ ])
