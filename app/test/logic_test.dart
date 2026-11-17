import 'package:ai_trend_radar/logic/ask_prompt.dart';
import 'package:ai_trend_radar/logic/interest_ranker.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:flutter_test/flutter_test.dart';

Paper paper(String id, {String title = 'T', String oneLiner = '', List<String> keywords = const [], Topic topic = Topic.other,
    Map<String, dynamic>? detail, String? github}) {
  return Paper.fromJson({
    'id': id,
    'title': title,
    'one_liner': oneLiner,
    'keywords': keywords,
    'topic': topic.slug,
    'detail': detail,
    'github_url': github,
    'date': '2026-11-13',
  });
}

void main() {
  group('관심 키워드 (BR-A05)', () {
    test('제목 · 요약 · 키워드 · 주제 이름에서 대소문자 무시 부분 일치', () {
      expect(paperInterests(paper('1', title: 'Web AGENTS'), ['agent']), ['agent']);
      expect(paperInterests(paper('2', oneLiner: '음성 합성 모델'), ['음성']), ['음성']);
      expect(paperInterests(paper('3', keywords: ['rag']), ['RAG', 'x']), ['RAG']);
      expect(paperInterests(paper('4', topic: Topic.roboticsPhysical), ['로보틱스']), ['로보틱스']);
      expect(paperInterests(paper('5', title: 'Diffusion'), ['agent']), isEmpty);
      expect(paperInterests(paper('6'), ['  ']), isEmpty);
    });

    test('맞는 항목을 위로, 그룹 안 순서는 유지 (AC-04-2)', () {
      final ranked = rankByInterest([1, 2, 3, 4, 5], (int n) => n.isEven);
      expect(ranked, [2, 4, 1, 3, 5]);
    });
  });

  group('AI 에게 묻기 (BR-A08)', () {
    test('상세가 있으면 4항목과 질문 틀', () {
      final text = buildAskPrompt(paper('2611.1', title: 'SO-Arena', oneLiner: '요약', github: 'https://github.com/a/b',
          detail: {'what': 'W', 'novelty': 'N', 'why': 'Y', 'apply': 'A'}));
      expect(text, contains('제목: SO-Arena'));
      expect(text, contains('링크: https://huggingface.co/papers/2611.1'));
      expect(text, contains('코드: https://github.com/a/b'));
      expect(text, contains('실무 적용: A'));
      expect(text, contains('2. 우리 업무에 적용하려면'));
    });

    test('상세가 없으면 요약만', () {
      final text = buildAskPrompt(paper('2611.2', oneLiner: '한 줄'));
      expect(text, contains('요약: 한 줄'));
      expect(text, isNot(contains('무엇을 했나')));
      expect(text, isNot(contains('코드:')));
    });
  });
}
