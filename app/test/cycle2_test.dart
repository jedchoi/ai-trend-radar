// 2주기 (FR-25 ~ FR-30): 뉴스 · 원문 · 읽음 · 글자 크기 · 기본 서버 주소 · 보관함 뉴스.
import 'package:ai_trend_radar/data/library_store.dart';
import 'package:ai_trend_radar/data/read_store.dart';
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

void main() {
  group('뉴스 · 원문 파싱 (예시 응답)', () {
    test('뉴스 목록 · 상세', () {
      final list = NewsList.fromJson(sample('news_list'));
      expect(list.total, 3);
      expect(list.items.first.id, 'nvidia/simready-assets-robot-pick-and-place');
      expect(list.items.first.topic, Topic.roboticsPhysical);
      expect(list.items.first.publishedAt, DateTime.utc(2026, 11, 13, 18, 0, 39));
      final news = News.fromJson(sample('news_detail'));
      expect(news.id, 'ggml-org/llama-cpp-v1');
      expect(news.brief.organization, 'ggml-org');
      expect(news.content, contains('llama.cpp'));
      expect(news.keyPoints, hasLength(2));
      expect(news.aiSummary, isTrue);
    });

    test('논문 본문 원문 · arXiv · 일일 요약에는 본문 없음', () {
      final detail = PaperWithRelated.fromJson(sample('paper_detail')).paper;
      expect(detail.fullText, startsWith('1 Introduction'));
      expect(detail.hasFullText, isTrue);
      expect(detail.arxivUrl, 'https://arxiv.org/abs/2611.10439');
      final inDigest = Digest.fromJson(sample('digest_latest')).papers.firstWhere((p) => p.id == '2611.10439');
      expect(inDigest.fullText, isNull);
      expect(inDigest.hasFullText, isTrue);
    });

    test('빠진 필드는 기본값', () {
      final n = NewsBrief.fromJson({'id': 'a/b'});
      expect(n.url, 'https://huggingface.co/blog/a/b');
      expect(n.topic, Topic.other);
      expect(n.day, '');
      expect(News.fromJson({'id': 'x'}).aiSummary, isFalse);
    });

    test('원문 블록: 소제목 · 항목 · 문단', () {
      final blocks = textBlocks('## Intro\nline one\nline two\n\n- a\n* b\n\n# Title\ntext');
      expect(blocks.map((b) => b.kind), [
        TextBlockKind.heading,
        TextBlockKind.paragraph,
        TextBlockKind.bullet,
        TextBlockKind.bullet,
        TextBlockKind.heading,
        TextBlockKind.paragraph,
      ]);
      expect(blocks[1].text, 'line one\nline two');
      expect(blocks[4].text, 'Title');
      expect(textBlocks(''), isEmpty);
    });
  });

  group('기기 저장', () {
    late SharedPreferences prefs;

    setUp(() async {
      SharedPreferences.setMockInitialValues({});
      prefs = await SharedPreferences.getInstance();
    });

    test('읽음 표시 유지 · 최대 개수 (BR-A23)', () async {
      final reads = ReadStore(prefs);
      var notified = 0;
      reads.addListener(() => notified++);
      await reads.mark(ReadStore.paper('2611.1'));
      await reads.mark(ReadStore.paper('2611.1'));
      await reads.mark(ReadStore.news('a/b'));
      expect(notified, 2);
      final again = ReadStore(prefs);
      expect(again.isRead('p:2611.1'), isTrue);
      expect(again.isRead('n:a/b'), isTrue);
      expect(again.isRead('p:a/b'), isFalse);
      for (var i = 0; i < ReadStore.maxItems + 3; i++) {
        await again.mark('p:$i');
      }
      expect(again.length, ReadStore.maxItems);
      expect(again.isRead('p:2611.1'), isFalse); // 오래된 것부터 지움
      expect(again.isRead('p:${ReadStore.maxItems + 2}'), isTrue);
    });

    test('글자 크기 (BR-A25)', () async {
      final s = SettingsStore(prefs);
      expect(s.textScale, 1.0);
      await s.setTextScale(1.3);
      expect(SettingsStore(prefs).textScale, 1.3);
      await s.setTextScale(7);
      expect(s.textScale, 1.0);
    });

    test('기본 서버 주소: 사용자가 저장한 주소가 우선, 비우면 기본값 (BR-A20)', () async {
      const builtIn = 'http://192.168.0.10:8000';
      final s = SettingsStore(prefs, defaultServerUrl: builtIn);
      expect(s.serverUrl, builtIn);
      expect(s.configured, isTrue);
      await s.setServerUrl('https://radar.example.com');
      expect(SettingsStore(prefs, defaultServerUrl: builtIn).serverUrl, 'https://radar.example.com');
      await s.setServerUrl('');
      expect(s.serverUrl, builtIn);
      expect(SettingsStore(prefs, defaultServerUrl: builtIn).serverUrl, builtIn);
    });

    test('보관함에 뉴스 · 논문이 같은 id 여도 따로 (BR-A26)', () async {
      final lib = LibraryStore(prefs);
      final news = NewsBrief.fromJson(sample('news_list')['items'][0] as Map<String, dynamic>);
      await lib.toggle(newsAsBrief(news), kind: LibraryKind.news);
      await lib.toggle(PaperBrief.fromJson({'id': news.id, 'title': 'paper', 'date': '2026-11-13'}));
      expect(lib.items(), hasLength(2));
      expect(lib.contains(news.id, kind: LibraryKind.news), isTrue);
      final saved = LibraryStore(prefs).entry(news.id, kind: LibraryKind.news)!;
      expect(saved.kind, LibraryKind.news);
      expect(saved.paper.oneLiner, news.summary);
      await lib.setStatus(saved.key, LibraryStatus.applied);
      expect(lib.entry(news.id, kind: LibraryKind.news)!.status, LibraryStatus.applied);
      expect(lib.entry(news.id)!.status, LibraryStatus.toRead);
    });
  });
}
