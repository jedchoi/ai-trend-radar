// 화면 위젯 테스트 (NFR-A06). 파일 이름은 `flutter create` 가 기본 테스트를 만들지 않도록 widget_test.dart 로 둔다.
import 'package:ai_trend_radar/data/library_store.dart';
import 'package:ai_trend_radar/data/read_store.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  testWidgets('오늘: 세 줄 · 주목 논문 · 전체 · Hub (AC-01, AC-02, AC-03)', (tester) async {
    await pumpApp(tester);
    expect(find.text('오늘의 세 줄'), findsOneWidget);
    expect(find.textContaining('System One'), findsWidgets);
    expect(find.text('주목할 논문'), findsOneWidget);
    expect(find.textContaining('SO-Arena'), findsWidgets);
    expect(find.text('코드 공개'), findsWidgets);
    expect(find.text('11.13'), findsWidgets); // 날짜 칩

    await tester.scrollUntilVisible(find.text('Hugging Face 트렌드'), 400, scrollable: find.byType(Scrollable).first);
    expect(find.text('Qwen/Qwen3.8-Flash-Next'), findsOneWidget);
    await tester.tap(find.text('Spaces'));
    await tester.pumpAndSettle();
    expect(find.text('pollen-robotics/microduck-simulator'), findsOneWidget);
  });

  testWidgets('주제 칩으로 거르기 (AC-02-1)', (tester) async {
    await pumpApp(tester);
    final chip = find.widgetWithText(ChoiceChip, '음성 · 오디오');
    await tester.scrollUntilVisible(chip, 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(chip);
    await tester.pumpAndSettle();
    expect(find.textContaining('Duo: A Reciprocal World Model'), findsOneWidget);
    expect(find.textContaining('G-STAR'), findsNothing);
  });

  testWidgets('관심 키워드가 맞는 논문에 표시 (AC-04-2)', (tester) async {
    final services = await makeServices();
    await services.settings.addInterest('memory');
    await pumpApp(tester, services: services);
    expect(find.textContaining('관심 · memory'), findsWidgets);
  });

  testWidgets('논문 상세: 4항목 · 용어 · 링크 · 관련 논문 · 보관함 (AC-05 ~ AC-07, AC-13-1)', (tester) async {
    final services = await pumpApp(tester);
    await tester.tap(find.textContaining('Who Remembers What?').first);
    await tester.pumpAndSettle();
    expect(find.text('논문 요약'), findsOneWidget);
    expect(find.text('무엇을 했나'), findsOneWidget);
    expect(find.text('실무에 쓰려면'), findsOneWidget);
    expect(find.text('논문 (Hugging Face)'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('이어서 볼 이전 논문'), 400, scrollable: find.byType(Scrollable).last);
    expect(find.textContaining('Actor, Judge, or Teacher?'), findsWidgets);

    await tester.tap(find.byTooltip('보관함에 저장'));
    await tester.pumpAndSettle();
    expect(services.library.contains('2611.10439'), isTrue);
    expect(find.byTooltip('보관함에서 빼기'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('시험 중'), -400, scrollable: find.byType(Scrollable).last);
    await tester.tap(find.text('시험 중'));
    await tester.pumpAndSettle();
    expect(services.library.entry('2611.10439')!.status, LibraryStatus.trying);
  });

  testWidgets('초록 기반 논문 (AC-05-2)', (tester) async {
    await pumpApp(tester);
    final row = find.textContaining('G-STAR');
    await tester.scrollUntilVisible(row, 400, scrollable: find.byType(Scrollable).first);
    await tester.tap(row.first);
    await tester.pumpAndSettle();
    expect(find.text('초록 기반'), findsOneWidget);
    expect(find.text('무엇을 했나'), findsNothing);
  });

  testWidgets('트렌드: 리포트 · 막대 · 급상승 · 월간 (AC-09, AC-11)', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('트렌드'));
    await tester.pumpAndSettle();
    expect(find.textContaining('이번 주는 에이전트 논문이'), findsOneWidget);
    expect(find.text('주제별 논문 수'), findsOneWidget);
    expect(find.text('46주차'), findsWidgets);
    await tester.scrollUntilVisible(find.textContaining('memory ×'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.textContaining('memory ×10.0'), findsOneWidget);
    await tester.scrollUntilVisible(find.text('월간'), -600, scrollable: find.byType(Scrollable).first);
    await tester.tap(find.text('월간'));
    await tester.pumpAndSettle();
    expect(find.textContaining('2026년 11월'), findsWidgets);
  });

  testWidgets('검색 (AC-12-1)', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.text('검색'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'agent');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();
    expect(find.text('검색 결과'), findsOneWidget);
    expect(find.textContaining('Actor, Judge, or Teacher?'), findsOneWidget);
    expect(find.text('더 보기'), findsOneWidget); // total 50 > 5
  });

  testWidgets('보관함 목록 · 상태 필터 (AC-13-2)', (tester) async {
    final services = await makeServices();
    await pumpApp(tester, services: services);
    await tester.tap(find.text('보관함'));
    await tester.pumpAndSettle();
    expect(find.textContaining('저장한 논문이 없습니다'), findsOneWidget);
    final brief = services.repository;
    final paper = (await brief.paper('2611.15777')).data.paper.toBrief();
    await services.library.toggle(paper);
    await tester.pumpAndSettle();
    expect(find.textContaining('SO-Arena'), findsOneWidget);
    await tester.tap(find.text('적용함 0'));
    await tester.pumpAndSettle();
    expect(find.textContaining('SO-Arena'), findsNothing);
  });

  testWidgets('설정: 잘못된 주소 거부 · 키워드 추가 (AC-15-2, AC-04-1)', (tester) async {
    final services = await pumpApp(tester);
    await tester.tap(find.byTooltip('설정'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('server-url')), 'ftp://nope');
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();
    expect(find.textContaining('https:// 로 시작하는'), findsOneWidget);
    expect(services.settings.serverUrl, testServer);

    await tester.enterText(find.byKey(const Key('interest-input')), 'agent');
    await tester.tap(find.byTooltip('키워드 추가'));
    await tester.pumpAndSettle();
    expect(services.settings.interests, ['agent']);
    expect(find.widgetWithText(InputChip, 'agent'), findsOneWidget);
  });

  testWidgets('오프라인이면 저장본 + 안내 (AC-14-1)', (tester) async {
    final online = await makeServices();
    await online.repository.latestDigest();
    await online.repository.digests();
    final offline = await makeServices(
      client: sampleServer(failWith: 503),
      prefs: {
        'settings:server_url': testServer,
        'cache:/api/v1/digests/latest?lang=ko':
            online.repository.cache.prefs.getString('cache:/api/v1/digests/latest?lang=ko')!,
      },
    );
    await pumpApp(tester, services: offline);
    expect(find.textContaining('오프라인'), findsWidgets);
    expect(find.text('오늘의 세 줄'), findsOneWidget);
  });

  testWidgets('저장본도 없으면 오류와 다시 시도 (AC-14-2)', (tester) async {
    await pumpApp(tester, services: await makeServices(client: sampleServer(failWith: 500)));
    expect(find.text('다시 시도'), findsWidgets);
  });

  testWidgets('서버 주소가 없으면 설정 안내, 넣으면 불러옴 (BR-A13)', (tester) async {
    final services = await pumpApp(tester, services: await makeServices(prefs: const {}));
    expect(find.textContaining('서버 주소를 입력하세요'), findsWidgets);
    expect(find.text('오늘의 세 줄'), findsNothing);
    await services.settings.setServerUrl(testServer);
    await tester.pumpAndSettle();
    expect(find.text('오늘의 세 줄'), findsOneWidget);
  });

  testWidgets('글자 크기 1.3 에서도 넘침 없음 (NFR-A05)', (tester) async {
    await pumpApp(tester, textScale: 1.3);
    expect(tester.takeException(), isNull);
    for (final tab in ['뉴스', '트렌드', '검색', '보관함']) {
      await tester.tap(find.text(tab).last);
      await tester.pumpAndSettle();
      expect(tester.takeException(), isNull);
    }
  });

  testWidgets('오늘: 최신 소식 카드 → 뉴스 탭 (BR-A27, AC-22-1)', (tester) async {
    await pumpApp(tester);
    expect(find.text('Hugging Face 소식'), findsOneWidget);
    expect(find.textContaining('SimReady Assets'), findsOneWidget);
    await tester.tap(find.text('전체 보기'));
    await tester.pumpAndSettle();
    expect(find.text('블로그 글 3건 · 최신순'), findsOneWidget);
    expect(find.text('llama.cpp v1'), findsOneWidget);
  });

  testWidgets('뉴스 상세: 요약 · 핵심 · 원문 · 보관 · 읽음 (AC-22-2, AC-26-2, AC-26-4)', (tester) async {
    final services = await pumpApp(tester);
    await tester.tap(find.text('뉴스'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('llama.cpp v1'));
    await tester.pumpAndSettle();
    expect(find.text('요약'), findsOneWidget);
    expect(find.text('AI 요약'), findsOneWidget);
    expect(find.text('핵심'), findsOneWidget);
    expect(find.text('양자화 · 최적화 백엔드'), findsOneWidget);
    expect(find.text('본문 (번역)'), findsOneWidget); // 3주기: 한국어 번역 본문 (news_detail_ko)
    expect(find.textContaining('멀티모달 LLM'), findsOneWidget);
    expect(services.reads.isRead(ReadStore.news('ggml-org/llama-cpp-v1')), isTrue);
    await tester.tap(find.byTooltip('보관함에 저장'));
    await tester.pumpAndSettle();
    expect(services.library.contains('ggml-org/llama-cpp-v1', kind: LibraryKind.news), isTrue);

    await tester.pageBack();
    await tester.pumpAndSettle();
    expect(find.text('읽음'), findsOneWidget);
    await tester.tap(find.text('보관함'));
    await tester.pumpAndSettle();
    expect(find.textContaining('뉴스 · 읽을 것'), findsOneWidget);
    await tester.tap(find.text('llama.cpp v1'));
    await tester.pumpAndSettle();
    expect(find.text('핵심'), findsOneWidget);
  });

  testWidgets('뉴스 검색 (AC-22-3)', (tester) async {
    final requests = <String>[];
    await pumpApp(tester, services: await makeServices(client: sampleServer(requests: requests)));
    await tester.tap(find.text('뉴스'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byKey(const Key('news-search')), 'llama');
    await tester.testTextInput.receiveAction(TextInputAction.search);
    await tester.pumpAndSettle();
    expect(requests.where((r) => r.startsWith('/api/v1/news?q=llama')), isNotEmpty);
  });

  testWidgets('논문 원문: 초록 펼치기 · 본문 읽기 화면 · arXiv (AC-23-1)', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.textContaining('Who Remembers What?').first);
    await tester.pumpAndSettle();
    final abstractTile = find.text('초록 (Abstract)');
    await tester.scrollUntilVisible(abstractTile, 300, scrollable: find.byType(Scrollable).first);
    await tester.tap(abstractTile);
    await tester.pumpAndSettle();
    expect(find.textContaining('(예시 번역)'), findsWidgets); // 3주기: 한국어 번역 초록 (paper_detail_ko)
    final reader = find.text('본문 원문 읽기');
    await tester.scrollUntilVisible(reader, 300, scrollable: find.byType(Scrollable).first);
    await tester.scrollUntilVisible(find.text('arXiv'), 300, scrollable: find.byType(Scrollable).first);
    expect(find.text('arXiv'), findsOneWidget);
    await tester.scrollUntilVisible(reader, -300, scrollable: find.byType(Scrollable).first);
    await tester.tap(reader);
    await tester.pumpAndSettle();
    expect(find.text('방법'), findsNothing); // '2 방법' 은 문단 (소제목 표시는 ## 만)
    expect(find.textContaining('1 서론'), findsOneWidget);
  });

  testWidgets('읽은 논문은 목록에 읽음 표시 (AC-26-2)', (tester) async {
    final services = await makeServices();
    await services.reads.mark(ReadStore.paper('2611.15777'));
    await pumpApp(tester, services: services);
    expect(find.text('읽음'), findsWidgets);
  });

  testWidgets('글자 크기 설정이 앱 전체에 적용 (AC-26-3)', (tester) async {
    final services = await pumpApp(tester);
    await tester.tap(find.byTooltip('설정'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('아주 크게'));
    await tester.pumpAndSettle();
    expect(services.settings.textScale, 1.3);
    final context = tester.element(find.text('아주 크게'));
    expect(MediaQuery.of(context).textScaler.scale(10), closeTo(13, 0.001));
    expect(tester.takeException(), isNull);
  });
}
