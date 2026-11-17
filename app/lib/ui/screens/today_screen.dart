import 'package:flutter/material.dart';

import '../../data/read_store.dart';
import '../../data/repository.dart';
import '../../data/settings_store.dart';
import '../../logic/interest_ranker.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../../state/load_controller.dart';
import '../format.dart';
import '../widgets/common.dart';
import '../widgets/hub_section.dart';
import '../widgets/news_widgets.dart';
import '../widgets/paper_widgets.dart';
import 'news_detail_screen.dart';
import 'paper_screen.dart';

/// 뉴스 리스트 (US-01 ~ US-04) + 최신 Hugging Face 소식 (BR-A27).
class TodayScreen extends StatefulWidget {
  const TodayScreen({super.key, this.onOpenNews});

  /// 뉴스 탭으로 이동 (HomeShell 이 준다).
  final VoidCallback? onOpenNews;

  @override
  State<TodayScreen> createState() => _TodayScreenState();
}

class _TodayScreenState extends State<TodayScreen> {
  LoadController<Digest>? _digest;
  LoadController<List<DigestSummary>>? _dates;
  LoadController<NewsList>? _news;
  String? _selectedDate;
  Topic? _topic;
  String? _serverUrl;
  SettingsStore? _settings;
  late RadarRepository _repo;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _repo = Services.of(context).repository;
    if (_digest == null) {
      _digest = LoadController(() => _repo.latestDigest());
      _dates = LoadController(() => _repo.digests());
      _news = LoadController(() => _repo.news(limit: 5));
      final settings = Services.of(context).settings;
      _settings = settings;
      _serverUrl = settings.serverUrl;
      settings.addListener(_onSettings);
      _reload();
    }
  }

  void _onSettings() {
    final url = _settings!.serverUrl;
    if (url != _serverUrl) {
      _serverUrl = url;
      _selectedDate = null;
      _reload();
    }
  }

  Future<void> _reload() async {
    final date = _selectedDate;
    await Future.wait([
      _digest!.load(date == null ? () => _repo.latestDigest() : () => _repo.digest(date)),
      _dates!.load(),
      _news!.load(),
    ]);
  }

  void _selectDate(String date) {
    setState(() {
      _selectedDate = date;
      _topic = null;
    });
    _digest!.load(() => _repo.digest(date));
  }

  @override
  void dispose() {
    _settings?.removeListener(_onSettings);
    _digest?.dispose();
    _dates?.dispose();
    _news?.dispose();
    super.dispose();
  }

  void _open(String id) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PaperScreen(paperId: id)));

  void _openNews(String id) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => NewsDetailScreen(newsId: id)));

  @override
  Widget build(BuildContext context) {
    final services = Services.of(context);
    return ListenableBuilder(
      listenable: Listenable.merge([_digest!, _dates!, _news!, services.settings, services.reads]),
      builder: (context, _) {
        final c = _digest!;
        if (c.status == LoadStatus.loading && c.data == null) {
          return const Center(child: CircularProgressIndicator());
        }
        if (c.status == LoadStatus.error && c.data == null) {
          return ErrorView(message: c.error ?? '오류', onRetry: _reload);
        }
        final digest = c.data!;
        final interests = services.settings.interests;
        final reads = services.reads;
        return RefreshIndicator(
          onRefresh: _reload,
          child: ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              SourceBanner(offline: c.offline),
              _DateChips(
                dates: _dates!.data ?? const [],
                selected: digest.date,
                onSelected: _selectDate,
              ),
              _Headline(date: digest.date, lines: digest.headline, provider: digest.provider),
              ..._latestNews(reads),
              ..._featured(digest, interests, reads),
              ..._all(digest, interests, reads),
              const SectionTitle('Hugging Face 트렌드', subtitle: '오늘 많이 찾는 모델 · 데이터셋 · Spaces'),
              HubSection(items: digest.hub),
            ],
          ),
        );
      },
    );
  }

  /// 최신 소식 가로 카드. 뉴스를 못 받으면 (서버가 이전 버전 등) 조용히 숨긴다.
  List<Widget> _latestNews(ReadStore reads) {
    final items = _news!.data?.items ?? const <NewsBrief>[];
    if (items.isEmpty) return const [];
    return [
      SectionTitle(
        'Hugging Face 소식',
        subtitle: '블로그 새 글 요약',
        trailing: widget.onOpenNews == null
            ? null
            : TextButton(onPressed: widget.onOpenNews, child: const Text('전체 보기')),
      ),
      SizedBox(
        height: 176,
        child: ListView.separated(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 16),
          itemCount: items.length > 3 ? 3 : items.length,
          separatorBuilder: (_, __) => const SizedBox(width: 10),
          itemBuilder: (context, i) => NewsCard(
            news: items[i],
            read: reads.isRead(ReadStore.news(items[i].id)),
            onTap: () => _openNews(items[i].id),
          ),
        ),
      ),
    ];
  }

  List<Widget> _featured(Digest digest, List<String> interests, ReadStore reads) {
    final featured = rankByInterest(digest.featured, (Paper p) => paperInterests(p, interests).isNotEmpty);
    if (featured.isEmpty) return const [];
    return [
      SectionTitle('주목할 논문', subtitle: '추천 수 · 코드 공개 · 관심 분야로 고른 ${featured.length}편'),
      for (final p in featured)
        PaperCard(
          paper: p,
          interests: paperInterests(p, interests),
          read: reads.isRead(ReadStore.paper(p.id)),
          onTap: () => _open(p.id),
        ),
    ];
  }

  List<Widget> _all(Digest digest, List<String> interests, ReadStore reads) {
    final filtered = digest.papers.where((p) => _topic == null || p.topic == _topic).toList();
    final papers = rankByInterest(filtered, (Paper p) => paperInterests(p, interests).isNotEmpty);
    return [
      SectionTitle('전체 논문', subtitle: '${digest.papers.length}편'),
      if (digest.papers.isEmpty) const EmptyNote('이날은 올라온 논문이 없습니다'),
      if (digest.papers.isNotEmpty)
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(
            spacing: 6,
            runSpacing: 6,
            children: [
              ChoiceChip(label: const Text('전체'), selected: _topic == null, onSelected: (_) => setState(() => _topic = null)),
              for (final t in digest.topics)
                ChoiceChip(
                  label: Text(t.label),
                  selected: _topic == t,
                  onSelected: (_) => setState(() => _topic = t),
                ),
            ],
          ),
        ),
      for (final p in papers)
        PaperRow.paper(
          p,
          interests: paperInterests(p, interests),
          read: reads.isRead(ReadStore.paper(p.id)),
          onTap: () => _open(p.id),
        ),
    ];
  }
}

class _DateChips extends StatelessWidget {
  const _DateChips({required this.dates, required this.selected, required this.onSelected});

  final List<DigestSummary> dates;
  final String selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    if (dates.isEmpty) return const SizedBox(height: 8);
    return SizedBox(
      height: 60,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
        itemCount: dates.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (context, i) {
          final d = dates[i];
          return ChoiceChip(
            label: Text(shortDay(d.date)),
            selected: d.date == selected,
            onSelected: (_) => onSelected(d.date),
          );
        },
      ),
    );
  }
}

class _Headline extends StatelessWidget {
  const _Headline({required this.date, required this.lines, required this.provider});

  final String date;
  final List<String> lines;
  final String provider;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 8, 16, 0),
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(16),
        gradient: LinearGradient(
          colors: [scheme.primaryContainer, scheme.tertiaryContainer],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(dayLabel(date), style: text.labelMedium?.copyWith(color: scheme.onPrimaryContainer)),
          const SizedBox(height: 4),
          Text('오늘의 세 줄',
              style: text.titleLarge?.copyWith(fontWeight: FontWeight.w800, color: scheme.onPrimaryContainer)),
          const SizedBox(height: 10),
          if (lines.isEmpty)
            Text('요약할 논문이 없는 날입니다.', style: TextStyle(color: scheme.onPrimaryContainer)),
          for (var i = 0; i < lines.length; i++)
            Padding(
              padding: const EdgeInsets.only(bottom: 8),
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('${i + 1}', style: text.titleMedium?.copyWith(fontWeight: FontWeight.w800, color: scheme.primary)),
                  const SizedBox(width: 10),
                  Expanded(
                    child: Text(lines[i], style: text.bodyMedium?.copyWith(color: scheme.onPrimaryContainer, height: 1.4)),
                  ),
                ],
              ),
            ),
          Text(provider == 'none' ? '요약: Hugging Face AI 요약 기반' : '요약: $provider',
              style: text.labelSmall?.copyWith(color: scheme.onPrimaryContainer.withValues(alpha: 0.7))),
        ],
      ),
    );
  }
}
