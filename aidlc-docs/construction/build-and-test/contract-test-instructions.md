# Contract Test Instructions

| 검사 | 위치 | 결과 |
| --- | --- | --- |
| 파이프라인 업로드가 서버 `DigestIngest` 통과 | `pipeline/tests/test_contract.py` | 통과 |
| 주제 slug 9개 일치 (파이프라인 · 서버) | 같은 파일 | 통과 |
| 예시 응답이 현재 서버 코드로 다시 만들어지는지 | `tool/check.sh`, CI server job (`diff -r`) | 통과 |
| 앱 데모 자산 == 예시 응답 | 같음 | 통과 |
| 앱 모델이 예시 응답을 파싱 | `app/test/models_test.dart` | CI 에서 실행 |
