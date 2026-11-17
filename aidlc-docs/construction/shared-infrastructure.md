# Shared Infrastructure

| 자원 | 사용 unit | 비고 |
| --- | --- | --- |
| backend 서버 (Docker, 사용자의 Linux 서버) | backend-server, pc-pipeline (업로드), mobile-app (조회) | 단일 HTTPS 주소 |
| 사용자 Mac | pc-pipeline | launchd 예약 실행, 키체인에 비밀 보관 |
| GitHub Actions | 전체 | CI (Operations: Deployment Pipeline) |
