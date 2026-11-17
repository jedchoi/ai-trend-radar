// 3주기 (FR-32 ~ FR-37): 한국어 · 영어 전환.
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/l10n/strings.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:ai_trend_radar/ui/format.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

void main() {
  group('언어 설정 · 요청 (BR-A30, BR-A31)', () {
    test('기본 한국어, 바꾸면 유지 · 화면 글자 언어도 바뀜', () async {
      SharedPreferences.setMockInitialValues({});
      final prefs = await SharedPreferences.getInstance();
      final s = SettingsStore(prefs);
      expect(s.language, 'ko');
      expect(AppLang.english, isFalse);
      expect(tr('오늘', 'Today'), '오늘');
      final before = s.sourceKey;
      await s.toggleLanguage();
      expect(s.language, 'en');
      expect(AppLang.english, isTrue);
      expect(tr('오늘', 'Today'), 'Today');
      expect(s.sourceKey, isNot(before));
      expect(SettingsStore(prefs).language, 'en');
      await s.setLanguage('fr');
      expect(s.language, 'ko');
    });

    test('요청마다 lang 을 붙인다 (기간 · 시계열은 언어와 무관)', () async {
      final requests = <String>[];
      final services = await makeServices(client: sampleServer(requests: requests));
      await services.settings.setLanguage('en');
      await services.repository.latestDigest();
      await services.repository.paper('2611.10439');
      await services.repository.newsDetail('ggml-org/llama-cpp-v1');
      await services.repository.periods();
      expect(requests, [
        '/api/v1/digests/latest?lang=en',
        '/api/v1/papers/2611.10439?lang=en',
        '/api/v1/news/ggml-org/llama-cpp-v1?lang=en',
        '/api/v1/trends/periods',
      ]);
      await services.settings.setLanguage('ko');
    });

    test('날짜 · 주차 · 수 · 주제 이름도 언어별 (BR-A32)', () {
      AppLang.english = true;
      expect(dayLabel('2026-11-13'), 'Fri, Nov 13');
      expect(periodLabel('2026-W46'), 'Week 46');
      expect(periodLabel('2026-11'), 'Nov 2026');
      expect(compact(158598), '158.6K');
      expect(Topic.agents.label, 'Agents');
      AppLang.english = false;
      expect(dayLabel('2026-11-13'), '11월 13일 (금)');
      expect(compact(158598), '15.9만');
      expect(Topic.agents.label, '에이전트');
    });

    test('번역 응답 파싱: untranslated', () {
      final en = Digest.fromJson(sample('digest_latest_en'));
      expect(en.untranslated, isFalse);
      expect(en.headline.first, startsWith('A new evaluation'));
      expect(en.papers.firstWhere((p) => p.id == '2611.10439').untranslated, isFalse);
      expect(en.papers.where((p) => p.untranslated), isNotEmpty);
      expect(News.fromJson(sample('news_detail_en')).brief.summary, startsWith('llama.cpp reached 1.0'));
      expect(TrendReport.fromJson(sample('trend_weekly_en')).narrative, startsWith('Agent papers led'));
    });
  });

  group('화면 (AC-28 ~ AC-29)', () {
    testWidgets('언어 버튼으로 영어 ↔ 한국어 (AC-28-1, AC-29-2)', (tester) async {
      final services = await pumpApp(tester);
      expect(find.text('오늘의 세 줄'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(services.settings.language, 'en');
      expect(find.text('Today in three lines'), findsOneWidget);
      expect(find.textContaining('A new evaluation finds'), findsOneWidget);
      expect(find.text('Featured papers'), findsOneWidget);
      expect(find.text('Today'), findsOneWidget); // 하단 탭
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(find.text('오늘의 세 줄'), findsOneWidget);
      expect(find.textContaining('A new evaluation finds'), findsNothing);
    });

    testWidgets('영어 논문 상세 · 번역 없는 논문은 표시 (AC-28-3, AC-29-2)', (tester) async {
      final services = await makeServices();
      await services.settings.setLanguage('en');
      await pumpApp(tester, services: services);
      await tester.tap(find.textContaining('Who Remembers What?').first);
      await tester.pumpAndSettle();
      expect(find.text('Paper summary'), findsOneWidget);
      expect(find.text('What they did'), findsOneWidget);
      expect(find.textContaining('A memory extraction method'), findsOneWidget);
      expect(find.text('Translation pending'), findsNothing);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await services.settings.setLanguage('ko');
      await tester.pumpAndSettle();
      await tester.tap(find.textContaining('Who Remembers What?').first);
      await tester.pumpAndSettle();
      // 한국어: 논문 제목은 번역, 원문 (초록 · 본문) 은 영어 그대로 (FR-34 개정, AC-29-1)
      expect(find.textContaining('누가 무엇을 기억하나?'), findsOneWidget);
      await tester.scrollUntilVisible(find.text('원문'), 300, scrollable: find.byType(Scrollable).first);
      expect(find.text('원문'), findsOneWidget);
      await tester.pageBack();
      await tester.pumpAndSettle();
      await services.settings.setLanguage('en');
      await tester.pumpAndSettle();
      final other = find.textContaining('G-STAR');
      await tester.scrollUntilVisible(other, 400, scrollable: find.byType(Scrollable).first);
      await tester.tap(other.first);
      await tester.pumpAndSettle();
      expect(find.text('Translation pending'), findsOneWidget);
      await services.settings.setLanguage('ko');
    });

    testWidgets('상세 화면에서 바꾸면 그 화면이 새 언어로 (AC-29-1)', (tester) async {
      await pumpApp(tester);
      await tester.tap(find.text('뉴스'));
      await tester.pumpAndSettle();
      await tester.tap(find.text('llama.cpp v1'));
      await tester.pumpAndSettle();
      expect(find.textContaining('멀티모달 LLM'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
      expect(find.text('Key points'), findsOneWidget);
      expect(find.text('Original'), findsOneWidget);
      expect(find.textContaining('llama.cpp reached 1.0'), findsOneWidget);
      await tester.tap(find.byKey(const Key('language-button')));
      await tester.pumpAndSettle();
    });
  });
}
