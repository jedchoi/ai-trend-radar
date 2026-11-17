# Business Logic Model — mobile-app

```text
RadarRepository.get(path)
  serverUrl 비었음 → DemoApi (assets/demo/*.json)           # BR-A13
  아니면 HTTP GET serverUrl + path (10초)
     성공 → 캐시 저장 → (data, offline=false)                # BR-A12
     실패 → 캐시 있음 → (data, offline=true)
            캐시 없음 → 오류
```

화면별 상태 = `LoadController<T>` (loading · ready · error, offline 여부). 관심 정렬 (BR-A05) 과 묻기 글 (BR-A08) 은 순수 함수로 분리해 단위 테스트한다.
