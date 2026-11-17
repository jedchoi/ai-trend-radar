# E2E Test Instructions (사람이 실기기에서)

1. 서버 배포 후 `curl https://<도메인>/api/v1/health`
2. Mac: `cd pipeline && uv run radar check` → `uv run radar daily --dry-run /tmp/out.json` (실제 Hugging Face 수집 확인) → `uv run radar daily`
3. 앱 설정에 서버 주소 입력 → 오늘 화면에 어제 날짜 요약, 논문 상세, 트렌드 화면 확인
4. 비행기 모드로 앱 재실행 → "오프라인" 표시와 마지막 요약
