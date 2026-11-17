// 4주기 (FR-38 ~ FR-42): 같은 응답에 두 언어, 앱이 골라 보여 준다. 원문은 영어 그대로.
import 'package:ai_trend_radar/data/library_store.dart';
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/l10n/strings.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:ai_trend_radar/ui/format.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

void main() {
  tearDown(() => AppLang.english = false);

  group('모델: 언어에 따라 고르기 (BR-A50, BR-A51)', () {
    test('같은 응답의 ko · en 에서 고르고, 원문은 그대로', () {
      final digest = Digest.fromJson(sample('digest_latest'));
      final paper = digest.papers.firstWhere((p) => p.id == '2611.10439');
      final title = paper.title;
      expect(digest.headline.first, contains('System One'));
      expect(paper.oneLiner, startsWith('여러 사용자'));
      expect(paper.detail!.what, startsWith('대화에서'));
      AppLang.english = true;
      expect(digest.headline.first, startsWith('A new evaluation'));
      expect(paper.oneLiner, startsWith('A memory extraction method'));
      expect(paper.detail!.what, startsWith('Proposes'));
      expect(paper.title, title); // FR-41
      expect(paper.untranslated, isFalse);
      expect(digest.untranslated, isFalse);
    });

    test('고른 언어 값이 없으면 다른 언어 + 번역 준비 중', () {
      final digest = Digest.fromJson(sample('digest_latest'));
      final other = digest.papers.firstWhere((p) => p.id != '2611.10439');
      AppLang.english = true;
      expect(other.oneLiner, isNotEmpty);
      expect(other.untranslated, isTrue);
      AppLang.english = false;
      expect(other.untranslated, isFalse);
    });

    test('뉴스 요약 · 핵심, 리포트 문장', () {
      final news = News.fromJson(sample('news_detail'));
      expect(news.keyPoints.first, '양자화 · 최적화 백엔드');
      AppLang.english = true;
      expect(news.brief.summary, startsWith('llama.cpp reached 1.0'));
      expect(news.keyPoints.first, 'Quantization and optimized backends');
      expect(news.content, contains('run multi-modal LLMs')); // 본문은 원문
      expect(TrendReport.fromJson(sample('trend_weekly')).narrative, startsWith('Agent papers led'));
    });

    test('i18n 이 없는 응답 (이전 서버) 은 원래 필드', () {
      final brief = PaperBrief.fromJson({'id': 'x', 'one_liner': '한 줄'});
      AppLang.english = true;
      expect(brief.oneLiner, '한 줄');
      expect(brief.i18n.pending('one_liner'), isFalse);
    });

    test('보관함은 두 언어를 함께 저장 (BR-A53)', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final lib = LibraryStore(prefs);
      final paper = PaperWithRelated.fromJson(sample('paper_detail')).paper;
      await lib.toggle(paper.toBrief());
      final news = NewsBrief.fromJson(sample('news_list')['items'][2] as Map<String, dynamic>);
      await lib.toggle(newsAsBrief(news), kind: LibraryKind.news);
      final again = LibraryStore(prefs);
      AppLang.english = true;
      expect(again.entry('2611.10439')!.paper.oneLiner, startsWith('A memory extraction method'));
      expect(again.entry(news.id, kind: LibraryKind.news)!.paper.oneLiner, startsWith('llama.cpp reached 1.0'));
      AppLang.english = false;
      expect(again.entry('2611.10439')!.paper.oneLiner, startsWith('여러 사용자'));
    });
  });

  group('설정 · 요청', () {
    test('언어 저장 · 화면 글자 · 날짜 표기 (BR-A30, BR-A32)', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final s = SettingsStore(prefs);
      expect(s.language, 'ko');
      final key = s.sourceKey;
      await s.toggleLanguage();
      expect(AppLang.english, isTrue);
      expect(tr('오늘', 'Today'), 'Today');
      expect(dayLabel('2026-11-13'), 'Fri, Nov 13');
      expect(s.sourceKey, key); // 언어를 바꿔도 다시 받지 않는다
      expect(SettingsStore(prefs).language, 'en');
    });

    test('요청에 lang 이 없다 (BR-A50)', () async {
      final requests = <String>[];
      final services = await makeServices(client: sampleServer(requests: requests));
      await services.settings.setLanguage('en');
      await services.repository.latestDigest();
      await services.repository.newsDetail('ggml-org/llama-cpp-v1');
      expect(requests, ['/api/v1/digests/latest', '/api/v1/news/ggml-org/llama-cpp-v1']);
    });
  });

  group('화면 (AC-32, AC-33)', () {
    testWidgets('언어 버튼: 다시 받지 않고 요약이 바로 바뀐다 (AC-32-1)', (tester) async {
      final requests = <String>[];
      final services = await makeServices(client: sampleServer(requests: requests));
      await pumpApp(tester, services: services);
      expect(find.text('오늘의 세 줄'), findsOneWidget);
      expect(find.textContaining('A new evaluation finds'), findsNothing);
      final before = requests.length;
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(requests.length, before);
      expect(find.text('Today in three lines'), findsOneWidget);
      expect(find.textContaining('A new evaluation finds'), findsOneWidget);
      expect(find.text('Featured papers'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(find.text('오늘의 세 줄'), findsOneWidget);
      await services.settings.setLanguage('ko');
    });

    testWidgets('논문 상세: 요약은 언어대로, 원문은 영어 (AC-32-1, AC-33-1)', (tester) async {
      final services = await pumpApp(tester);
      await tester.tap(find.textContaining('Who Remembers What?').first);
      await tester.pumpAndSettle();
      expect(find.text('무엇을 했나'), findsOneWidget);
      expect(find.textContaining('대화에서 개인'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(find.text('What they did'), findsOneWidget);
      expect(find.textContaining('Proposes extracting'), findsOneWidget);
      expect(find.textContaining('Who Remembers What?'), findsOneWidget); // 제목은 원문
      expect(find.text('Translation pending'), findsNothing);
      await services.settings.setLanguage('ko');
    });

    testWidgets('번역이 없는 논문은 다른 언어 + 번역 준비 중 (AC-32-3)', (tester) async {
      final services = await makeServices();
      await services.settings.setLanguage('en');
      await pumpApp(tester, services: services);
      final other = find.textContaining('G-STAR');
      await tester.scrollUntilVisible(other, 400, scrollable: find.byType(Scrollable).first);
      await tester.tap(other.first);
      await tester.pumpAndSettle();
      expect(find.text('Translation pending'), findsOneWidget);
      await services.settings.setLanguage('ko');
    });

    testWidgets('뉴스 상세: 핵심은 언어대로, 본문은 원문 (AC-33-1)', (tester) async {
      final services = await pumpApp(tester);
      await tester.tap(find.text('뉴스'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('llama.cpp v1'));
      await tester.pumpAndSettle();
      expect(find.text('양자화 · 최적화 백엔드'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(find.text('Key points'), findsOneWidget);
      expect(find.text('Quantization and optimized backends'), findsOneWidget);
      expect(find.text('Original'), findsOneWidget);
      expect(find.textContaining('run multi-modal LLMs'), findsOneWidget);
      await services.settings.setLanguage('ko');
    });
  });
}
