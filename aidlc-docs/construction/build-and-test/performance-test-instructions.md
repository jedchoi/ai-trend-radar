# Performance Test Instructions

- 명령: `cd server && pytest -m perf -s`
- 조건: 논문 10,080건 (180일 × 56편), Hub 3,600행, 경로별 100회
- 결과 (2026-11-17, p95 ms): digests/latest 14.7, 검색 46.8, 필터 12.2, weekly 23.7, monthly 50.2, series 14.2, paper 45.3 → 기준 300 ms 충족 (NFR-02, NFR-S01)
