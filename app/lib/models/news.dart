import 'json.dart';
import 'topic.dart';

/// 'YYYY-MM-DD' (기기 시간대).
String localDay(DateTime? t) {
  if (t == null) return '';
  final d = t.toLocal();
  return '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}

/// 뉴스 목록 한 줄 (FR-25, `GET /api/v1/news`).
class NewsBrief {
  const NewsBrief({
    required this.id,
    required this.title,
    required this.url,
    required this.summary,
    required this.topic,
    required this.keywords,
    this.publishedAt,
    this.organization,
    this.imageUrl,
  });

  final String id;
  final String title;
  final String url;
  final String summary;
  final Topic topic;
  final List<String> keywords;
  final DateTime? publishedAt;
  final String? organization;
  final String? imageUrl;

  String get day => localDay(publishedAt);

  factory NewsBrief.fromJson(Json j) {
    final id = str(j, 'id');
    return NewsBrief(
      id: id,
      title: str(j, 'title'),
      url: strOrNull(j, 'url') ?? 'https://huggingface.co/blog/$id',
      summary: str(j, 'summary'),
      topic: Topic.fromSlug(strOrNull(j, 'topic')),
      keywords: strings(j, 'keywords'),
      publishedAt: date(j, 'published_at'),
      organization: strOrNull(j, 'organization'),
      imageUrl: strOrNull(j, 'image_url'),
    );
  }
}

/// 뉴스 상세: 요약 · 핵심 · 원문 본문 (FR-26, `GET /api/v1/news/{id}`).
class News {
  const News({
    required this.brief,
    required this.authors,
    required this.content,
    required this.keyPoints,
    required this.summarySource,
    required this.provider,
  });

  final NewsBrief brief;
  final List<String> authors;
  final String content;
  final List<String> keyPoints;
  final String summarySource;
  final String provider;

  String get id => brief.id;
  bool get aiSummary => summarySource == 'ai';

  factory News.fromJson(Json j) => News(
        brief: NewsBrief.fromJson(j),
        authors: strings(j, 'authors'),
        content: str(j, 'content'),
        keyPoints: strings(j, 'key_points'),
        summarySource: str(j, 'summary_source', 'abstract'),
        provider: str(j, 'provider', 'none'),
      );
}

class NewsList {
  const NewsList(this.items, this.total);

  final List<NewsBrief> items;
  final int total;

  factory NewsList.fromJson(Json j) => NewsList(list(j, 'items', NewsBrief.fromJson), integer(j, 'total'));
}

enum TextBlockKind { heading, bullet, paragraph }

class TextBlock {
  const TextBlock(this.kind, this.text);

  final TextBlockKind kind;
  final String text;
}

/// 원문 텍스트 → 블록 (BR-A24). '## ' / '# ' = 소제목, '- ' · '* ' = 항목, 빈 줄 = 문단 구분.
List<TextBlock> textBlocks(String content) {
  final blocks = <TextBlock>[];
  final paragraph = <String>[];
  void flush() {
    if (paragraph.isNotEmpty) {
      blocks.add(TextBlock(TextBlockKind.paragraph, paragraph.join('\n')));
      paragraph.clear();
    }
  }

  for (final raw in content.split('\n')) {
    final line = raw.trimRight();
    final trimmed = line.trimLeft();
    if (trimmed.isEmpty) {
      flush();
    } else if (RegExp(r'^#{1,6} ').hasMatch(trimmed)) {
      flush();
      blocks.add(TextBlock(TextBlockKind.heading, trimmed.replaceFirst(RegExp(r'^#{1,6} '), '')));
    } else if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
      flush();
      blocks.add(TextBlock(TextBlockKind.bullet, trimmed.substring(2)));
    } else {
      paragraph.add(line);
    }
  }
  flush();
  return blocks;
}
