import 'package:ai_trend_radar/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

import 'helpers.dart';

void main() {
  group('예시 응답 파싱 (NFR-A02)', () {
    test('일일 요약', () {
      final d = Digest.fromJson(sample('digest_latest'));
      expect(d.date, '2026-11-13');
      expect(d.headline, hasLength(3));
      expect(d.featured.map((p) => p.id), contains('2611.15777'));
      final so = d.papers.firstWhere((p) => p.id == '2611.15777');
      expect(so.topic, Topic.evaluationBenchmark);
      expect(so.detail?.apply, isNotEmpty);
      expect(so.hasCode, isTrue);
      expect(so.hfUrl, 'https://huggingface.co/papers/2611.15777');
      expect(d.hub.where((h) => h.kind == HubKind.space), isNotEmpty);
      expect(d.topics.first.index, lessThanOrEqualTo(d.topics.last.index));
    });

    test('날짜 목록 · 상세 · 검색', () {
      expect(DigestSummary.listFromJson(sample('digests')).first.date, '2026-11-13');
      final detail = PaperWithRelated.fromJson(sample('paper_detail'));
      expect(detail.paper.id, '2611.10439');
      expect(detail.related, isNotEmpty);
      final search = SearchResult.fromJson(sample('search'));
      expect(search.total, greaterThanOrEqualTo(search.items.length));
    });

    test('트렌드', () {
      final w = TrendReport.fromJson(sample('trend_weekly'));
      expect(w.period, 'week');
      expect(w.key, '2026-W46');
      expect(w.baselineReady, isTrue);
      expect(w.risingKeywords.first.keyword, 'memory');
      expect(w.narrative, isNotNull);
      final series = TopicSeries.fromJson(sample('trend_series'));
      expect(series.weeks, hasLength(8));
      expect(series.counts.values.every((v) => v.length == 8), isTrue);
      expect(series.topTopics(5).length, lessThanOrEqualTo(5));
      expect(Periods.fromJson(sample('trend_periods')).weeks.first, '2026-W46');
    });
  });

  group('너그러운 읽기', () {
    test('모르는 필드는 무시하고 빠진 필드는 기본값', () {
      final p = Paper.fromJson({'id': 'x1', 'title': 'T', 'new_field': 123, 'topic': 'quantum-stuff'});
      expect(p.topic, Topic.other);
      expect(p.oneLiner, '');
      expect(p.authors, isEmpty);
      expect(p.detail, isNull);
      expect(p.abstractBased, isTrue);
      expect(p.hfUrl, 'https://huggingface.co/papers/x1');
    });

    test('타입이 틀린 값은 기본값', () {
      final p = Paper.fromJson({'id': 'x', 'upvotes': '많음', 'keywords': [1, 'a', null], 'detail': 'oops'});
      expect(p.upvotes, 0);
      expect(p.keywords, ['a']);
      expect(p.detail, isNull);
      final h = HubItem.fromJson({'id': 'a/b', 'kind': 'robot'});
      expect(h.kind, HubKind.model);
      expect(h.url, 'https://huggingface.co/a/b');
    });

    test('빈 detail 은 없음으로', () {
      expect(PaperDetail.fromJson({'what': '', 'novelty': ''}), isNull);
    });

    test('길이가 다른 시계열은 버린다', () {
      final s = TopicSeries.fromJson({
        'weeks': ['2026-W45', '2026-W46'],
        'topics': {
          'agents': [1, 2],
          'other': [1],
        },
      });
      expect(s.counts.keys, [Topic.agents]);
      expect(s.topTopics(5), [Topic.agents]);
    });

    test('보관함 요약 왕복', () {
      final brief = PaperBrief.fromJson({'id': 'a', 'title': 't', 'date': '2026-11-13', 'topic': 'agents'});
      final again = PaperBrief.fromJson(brief.toJson());
      expect(again.topic, Topic.agents);
      expect(again.date, '2026-11-13');
    });
  });
}
