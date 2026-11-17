import 'json.dart';
import 'topic.dart';

export 'topic.dart';

class PaperDetail {
  const PaperDetail({required this.what, required this.novelty, required this.why, required this.apply});

  final String what;
  final String novelty;
  final String why;
  final String apply;

  static PaperDetail? fromJson(Json? j) {
    if (j == null) return null;
    final detail = PaperDetail(
      what: str(j, 'what'),
      novelty: str(j, 'novelty'),
      why: str(j, 'why'),
      apply: str(j, 'apply'),
    );
    return [detail.what, detail.novelty, detail.why, detail.apply].every((s) => s.isEmpty) ? null : detail;
  }
}

class GlossaryItem {
  const GlossaryItem(this.term, this.explanation);

  final String term;
  final String explanation;

  factory GlossaryItem.fromJson(Json j) => GlossaryItem(str(j, 'term'), str(j, 'explanation'));
}

/// 목록용 요약 (검색 · 관련 논문 · 화제 논문 · 보관함).
class PaperBrief {
  const PaperBrief({
    required this.id,
    required this.title,
    required this.date,
    required this.topic,
    required this.oneLiner,
    required this.upvotes,
    required this.featured,
    this.githubUrl,
  });

  final String id;
  final String title;
  final String date;
  final Topic topic;
  final String oneLiner;
  final int upvotes;
  final bool featured;
  final String? githubUrl;

  factory PaperBrief.fromJson(Json j) => PaperBrief(
        id: str(j, 'id'),
        title: str(j, 'title'),
        date: str(j, 'date'),
        topic: Topic.fromSlug(strOrNull(j, 'topic')),
        oneLiner: str(j, 'one_liner'),
        upvotes: integer(j, 'upvotes'),
        featured: boolean(j, 'featured'),
        githubUrl: strOrNull(j, 'github_url'),
      );

  Json toJson() => {
        'id': id,
        'title': title,
        'date': date,
        'topic': topic.slug,
        'one_liner': oneLiner,
        'upvotes': upvotes,
        'featured': featured,
        'github_url': githubUrl,
      };
}

class Paper {
  const Paper({
    required this.id,
    required this.title,
    required this.date,
    required this.topic,
    required this.oneLiner,
    required this.upvotes,
    required this.featured,
    required this.authors,
    required this.abstract,
    required this.keywords,
    required this.glossary,
    required this.hfUrl,
    required this.summarySource,
    this.detail,
    this.githubUrl,
    this.githubStars,
    this.projectUrl,
    this.organization,
  });

  final String id;
  final String title;
  final String date;
  final Topic topic;
  final String oneLiner;
  final int upvotes;
  final bool featured;
  final List<String> authors;
  final String abstract;
  final List<String> keywords;
  final List<GlossaryItem> glossary;
  final String hfUrl;
  final String summarySource;
  final PaperDetail? detail;
  final String? githubUrl;
  final int? githubStars;
  final String? projectUrl;
  final String? organization;

  bool get hasCode => githubUrl != null;
  bool get abstractBased => detail == null;

  factory Paper.fromJson(Json j) {
    final id = str(j, 'id');
    return Paper(
      id: id,
      title: str(j, 'title'),
      date: str(j, 'date'),
      topic: Topic.fromSlug(strOrNull(j, 'topic')),
      oneLiner: str(j, 'one_liner'),
      upvotes: integer(j, 'upvotes'),
      featured: boolean(j, 'featured'),
      authors: strings(j, 'authors'),
      abstract: str(j, 'abstract'),
      keywords: strings(j, 'keywords'),
      glossary: list(j, 'glossary', GlossaryItem.fromJson),
      hfUrl: strOrNull(j, 'hf_url') ?? 'https://huggingface.co/papers/$id',
      summarySource: str(j, 'summary_source', 'hf'),
      detail: PaperDetail.fromJson(objOrNull(j, 'detail')),
      githubUrl: strOrNull(j, 'github_url'),
      githubStars: intOrNull(j, 'github_stars'),
      projectUrl: strOrNull(j, 'project_url'),
      organization: strOrNull(j, 'organization'),
    );
  }

  PaperBrief toBrief() => PaperBrief(
        id: id,
        title: title,
        date: date,
        topic: topic,
        oneLiner: oneLiner,
        upvotes: upvotes,
        featured: featured,
        githubUrl: githubUrl,
      );
}

enum HubKind {
  model('model', '모델'),
  dataset('dataset', '데이터셋'),
  space('space', 'Spaces');

  const HubKind(this.slug, this.label);

  final String slug;
  final String label;

  static HubKind fromSlug(String? slug) =>
      HubKind.values.firstWhere((k) => k.slug == slug, orElse: () => HubKind.model);
}

class HubItem {
  const HubItem({
    required this.kind,
    required this.rank,
    required this.id,
    required this.likes,
    required this.isNew,
    required this.streakDays,
    required this.url,
    this.downloads,
    this.task,
  });

  final HubKind kind;
  final int rank;
  final String id;
  final int likes;
  final bool isNew;
  final int streakDays;
  final String url;
  final int? downloads;
  final String? task;

  factory HubItem.fromJson(Json j) => HubItem(
        kind: HubKind.fromSlug(strOrNull(j, 'kind')),
        rank: integer(j, 'rank'),
        id: str(j, 'id'),
        likes: integer(j, 'likes'),
        isNew: boolean(j, 'is_new'),
        streakDays: integer(j, 'streak_days', 1),
        url: strOrNull(j, 'url') ?? 'https://huggingface.co/${str(j, 'id')}',
        downloads: intOrNull(j, 'downloads'),
        task: strOrNull(j, 'task'),
      );
}

class Digest {
  const Digest({required this.date, required this.headline, required this.provider, required this.papers, required this.hub});

  final String date;
  final List<String> headline;
  final String provider;
  final List<Paper> papers;
  final List<HubItem> hub;

  List<Paper> get featured => papers.where((p) => p.featured).toList(growable: false);

  /// BR-A03: 그날 등장한 주제 (주제 순서).
  List<Topic> get topics => Topic.values.where((t) => papers.any((p) => p.topic == t)).toList(growable: false);

  factory Digest.fromJson(Json j) => Digest(
        date: str(j, 'date'),
        headline: strings(j, 'headline'),
        provider: str(j, 'provider', 'none'),
        papers: list(j, 'papers', Paper.fromJson),
        hub: list(j, 'hub', HubItem.fromJson),
      );
}

class DigestSummary {
  const DigestSummary({required this.date, required this.headline, required this.paperCount, required this.featuredCount});

  final String date;
  final List<String> headline;
  final int paperCount;
  final int featuredCount;

  factory DigestSummary.fromJson(Json j) => DigestSummary(
        date: str(j, 'date'),
        headline: strings(j, 'headline'),
        paperCount: integer(j, 'paper_count'),
        featuredCount: integer(j, 'featured_count'),
      );

  static List<DigestSummary> listFromJson(Json j) => list(j, 'items', DigestSummary.fromJson);
}

class PaperWithRelated {
  const PaperWithRelated(this.paper, this.related);

  final Paper paper;
  final List<PaperBrief> related;

  factory PaperWithRelated.fromJson(Json j) =>
      PaperWithRelated(Paper.fromJson(obj(j, 'paper')), list(j, 'related', PaperBrief.fromJson));
}

class SearchResult {
  const SearchResult(this.items, this.total);

  final List<PaperBrief> items;
  final int total;

  factory SearchResult.fromJson(Json j) => SearchResult(list(j, 'items', PaperBrief.fromJson), integer(j, 'total'));
}

class TopicCount {
  const TopicCount(this.topic, this.count, this.prevCount, this.delta);

  final Topic topic;
  final int count;
  final int prevCount;
  final int delta;

  factory TopicCount.fromJson(Json j) => TopicCount(
        Topic.fromSlug(strOrNull(j, 'topic')),
        integer(j, 'count'),
        integer(j, 'prev_count'),
        integer(j, 'delta'),
      );
}

class RisingKeyword {
  const RisingKeyword(this.keyword, this.count, this.baseline, this.ratio);

  final String keyword;
  final int count;
  final double baseline;
  final double ratio;

  factory RisingKeyword.fromJson(Json j) =>
      RisingKeyword(str(j, 'keyword'), integer(j, 'count'), dbl(j, 'baseline'), dbl(j, 'ratio'));
}

class HubNew {
  const HubNew(this.kind, this.id, this.firstSeen, this.days);

  final HubKind kind;
  final String id;
  final String firstSeen;
  final int days;

  factory HubNew.fromJson(Json j) =>
      HubNew(HubKind.fromSlug(strOrNull(j, 'kind')), str(j, 'id'), str(j, 'first_seen'), integer(j, 'days'));
}

class HubSteady {
  const HubSteady(this.kind, this.id, this.streakDays);

  final HubKind kind;
  final String id;
  final int streakDays;

  factory HubSteady.fromJson(Json j) =>
      HubSteady(HubKind.fromSlug(strOrNull(j, 'kind')), str(j, 'id'), integer(j, 'streak_days'));
}

class TrendReport {
  const TrendReport({
    required this.period,
    required this.key,
    required this.start,
    required this.end,
    required this.paperCount,
    required this.topics,
    required this.risingKeywords,
    required this.baselineReady,
    required this.topPapers,
    required this.hubNew,
    required this.hubSteady,
    this.narrative,
  });

  final String period;
  final String key;
  final String start;
  final String end;
  final int paperCount;
  final List<TopicCount> topics;
  final List<RisingKeyword> risingKeywords;
  final bool baselineReady;
  final List<PaperBrief> topPapers;
  final List<HubNew> hubNew;
  final List<HubSteady> hubSteady;
  final String? narrative;

  factory TrendReport.fromJson(Json j) => TrendReport(
        period: str(j, 'period', 'week'),
        key: str(j, 'key'),
        start: str(j, 'start'),
        end: str(j, 'end'),
        paperCount: integer(j, 'paper_count'),
        topics: list(j, 'topics', TopicCount.fromJson),
        risingKeywords: list(j, 'rising_keywords', RisingKeyword.fromJson),
        baselineReady: boolean(j, 'baseline_ready'),
        topPapers: list(j, 'top_papers', PaperBrief.fromJson),
        hubNew: list(j, 'hub_new', HubNew.fromJson),
        hubSteady: list(j, 'hub_steady', HubSteady.fromJson),
        narrative: strOrNull(j, 'narrative'),
      );
}

class TopicSeries {
  const TopicSeries(this.weeks, this.counts);

  final List<String> weeks;
  final Map<Topic, List<int>> counts;

  /// 기간 합계 상위 [n] 개 주제 (0 인 주제 제외).
  List<Topic> topTopics(int n) {
    final totals = {for (final e in counts.entries) e.key: e.value.fold<int>(0, (a, b) => a + b)};
    final ranked = totals.entries.where((e) => e.value > 0).toList()
      ..sort((a, b) => b.value != a.value ? b.value.compareTo(a.value) : a.key.index.compareTo(b.key.index));
    return ranked.take(n).map((e) => e.key).toList(growable: false);
  }

  factory TopicSeries.fromJson(Json j) {
    final weeks = strings(j, 'weeks');
    final raw = obj(j, 'topics');
    final counts = <Topic, List<int>>{};
    raw.forEach((slug, values) {
      if (values is List) {
        final topic = Topic.fromSlug(slug);
        final series = values.map((v) => v is num ? v.toInt() : 0).toList(growable: false);
        if (series.length == weeks.length) counts[topic] = series;
      }
    });
    return TopicSeries(weeks, counts);
  }
}

class Periods {
  const Periods(this.weeks, this.months);

  final List<String> weeks;
  final List<String> months;

  factory Periods.fromJson(Json j) => Periods(strings(j, 'weeks'), strings(j, 'months'));
}
