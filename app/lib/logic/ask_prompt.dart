import '../models/models.dart';

/// BR-A08: AI 에게 넘길 질문 글.
String buildAskPrompt(Paper p) {
  final buffer = StringBuffer()
    ..writeln('다음 AI 논문에 대해 이야기하고 싶어요.')
    ..writeln()
    ..writeln('제목: ${p.title}')
    ..writeln('링크: ${p.hfUrl}');
  if (p.githubUrl != null) buffer.writeln('코드: ${p.githubUrl}');
  buffer
    ..writeln('주제: ${p.topic.label}')
    ..writeln('요약: ${p.oneLiner}');
  final d = p.detail;
  if (d != null) {
    buffer
      ..writeln('무엇을 했나: ${d.what}')
      ..writeln('새로운 점: ${d.novelty}')
      ..writeln('왜 중요한가: ${d.why}')
      ..writeln('실무 적용: ${d.apply}');
  }
  buffer
    ..writeln()
    ..writeln('질문:')
    ..writeln('1. 핵심 아이디어를 쉽게 설명해 주세요.')
    ..writeln('2. 우리 업무에 적용하려면 무엇부터 해 보면 좋을까요? 필요한 자원과 주의점도 알려 주세요.')
    ..writeln('3. 비슷한 기존 방법과 비교하면 어떤 차이가 있나요?');
  return buffer.toString().trimRight();
}
