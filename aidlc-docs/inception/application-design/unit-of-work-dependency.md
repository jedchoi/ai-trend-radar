# Unit 의존 관계

| Unit | 의존 대상 | 의존 내용 |
| --- | --- | --- |
| backend-server | 없음 | - |
| pc-pipeline | backend-server | 업로드 API (`DigestIngest`, 리포트), 통계 API |
| mobile-app | backend-server | 공개 읽기 API, `contract/samples/` 예시 응답 |

순환 없음. pc-pipeline 과 mobile-app 은 서로 의존하지 않는다 (backend-server 완료 후 병행 가능).
