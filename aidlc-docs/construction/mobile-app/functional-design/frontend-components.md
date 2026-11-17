# Frontend Components — mobile-app

하단 탭 4개 (오늘 · 트렌드 · 검색 · 보관함) + 설정 (오른쪽 위 아이콘).

| 화면 · 위젯 | 파일 | 구성 | Story |
| --- | --- | --- | --- |
| HomeShell | `lib/app.dart` | NavigationBar, 탭 상태 유지 (IndexedStack) | - |
| TodayScreen | `lib/ui/screens/today_screen.dart` | 날짜 칩 → 세 줄 카드 → 관심 · 주목 카드 → 주제 칩 + 전체 목록 → Hub 탭 | US-01 ~ US-04 |
| PaperScreen | `lib/ui/screens/paper_screen.dart` | 제목 · 메타 → 요약 4항목 (또는 초록) → 용어 → 링크 → 관련 이전 논문, 상단 북마크 · 묻기 | US-05 ~ US-08, US-13 |
| TrendScreen | `lib/ui/screens/trend_screen.dart` | 주간 · 월간 SegmentedButton → 기간 칩 → 리포트 → 주제 막대 → 추이 선 차트 → 급상승 키워드 → 화제 논문 → Hub 신규 · 체류 | US-09 ~ US-11 |
| SearchScreen | `lib/ui/screens/search_screen.dart` | 검색창, 필터 칩 (주제 · 기간 · 주목), 결과 목록 · 더 보기 | US-12 |
| LibraryScreen | `lib/ui/screens/library_screen.dart` | 상태 필터, 저장 목록, 상태 · 메모 편집 시트 | US-13 |
| SettingsScreen | `lib/ui/screens/settings_screen.dart` | 서버 주소, 관심 키워드 칩, 묻기 AI 선택 | US-04, US-08, US-15 |
| 공통 위젯 | `lib/ui/widgets/*.dart` | PaperCard, PaperTile, TopicChip, OfflineBanner, ErrorView, HubSection, 차트 2종 | - |

디자인: Material 3, 시드 색 남색 (Indigo) 계열, 주제마다 고정 색 (차트 · 칩 공통), 라이트 · 다크 모드.
