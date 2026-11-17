import '../l10n/strings.dart';
import '../models/models.dart';

/// BR-A08: AI 에게 넘길 질문 글 (화면 언어로).
String buildAskPrompt(Paper p) {
  final buffer = StringBuffer()
    ..writeln(tr('다음 AI 논문에 대해 이야기하고 싶어요.', "I'd like to talk about the following AI paper."))
    ..writeln()
    ..writeln('${tr('제목', 'Title')}: ${p.title}')
    ..writeln('${tr('링크', 'Link')}: ${p.hfUrl}');
  if (p.githubUrl != null) buffer.writeln('${tr('코드', 'Code')}: ${p.githubUrl}');
  buffer
    ..writeln('${tr('주제', 'Topic')}: ${p.topic.label}')
    ..writeln('${tr('요약', 'Summary')}: ${p.oneLiner}');
  final d = p.detail;
  if (d != null) {
    buffer
      ..writeln('${tr('무엇을 했나', 'What they did')}: ${d.what}')
      ..writeln('${tr('새로운 점', "What's new")}: ${d.novelty}')
      ..writeln('${tr('왜 중요한가', 'Why it matters')}: ${d.why}')
      ..writeln('${tr('실무 적용', 'Putting it to use')}: ${d.apply}');
  }
  buffer
    ..writeln()
    ..writeln(tr('질문:', 'Questions:'))
    ..writeln(tr('1. 핵심 아이디어를 쉽게 설명해 주세요.', '1. Explain the core idea simply.'))
    ..writeln(tr('2. 우리 업무에 적용하려면 무엇부터 해 보면 좋을까요? 필요한 자원과 주의점도 알려 주세요.',
        '2. Where should we start to apply this at work? Include the resources needed and caveats.'))
    ..writeln(tr('3. 비슷한 기존 방법과 비교하면 어떤 차이가 있나요?', '3. How does it differ from similar existing methods?'));
  return buffer.toString().trimRight();
}
