import 'package:flutter/material.dart';

import '../../data/repository.dart';
import '../../data/settings_store.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../../state/load_controller.dart';
import '../format.dart';
import '../widgets/charts.dart';
import '../widgets/common.dart';
import '../widgets/links.dart';
import '../widgets/paper_widgets.dart';
import 'paper_screen.dart';
import '../../l10n/strings.dart';

/// 트렌드 분석 (US-09 ~ US-11).
class TrendScreen extends StatefulWidget {
  const TrendScreen({super.key});

  @override
  State<TrendScreen> createState() => _TrendScreenState();
}

class _TrendScreenState extends State<TrendScreen> {
  final _periods = LoadController<Periods>(() async => const Loaded(Periods([], [])));
  final _report = LoadController<TrendReport>(() async => throw StateError('not ready'));
  final _series = LoadController<TopicSeries>(() async => const Loaded(TopicSeries([], {})));
  String _period = 'week';
  String? _key;
  bool _started = false;
  SettingsStore? _settings;
  String? _serverUrl;
  late RadarRepository _repo;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _repo = Services.of(context).repository;
    if (!_started) {
      _started = true;
      _settings = Services.of(context).settings..addListener(_onSettings);
      _serverUrl = _settings!.sourceKey;
      _reload();
    }
  }

  void _onSettings() {
    if (_settings!.sourceKey != _serverUrl) {
      _serverUrl = _settings!.sourceKey;
      _reload();
    }
  }

  Future<void> _reload() async {
    await Future.wait([_periods.load(() => _repo.periods()), _series.load(() => _repo.series())]);
    final keys = _keys();
    _key = keys.isEmpty ? null : keys.first;
    await _loadReport();
  }

  List<String> _keys() {
    final p = _periods.data;
    if (p == null) return const [];
    return _period == 'week' ? p.weeks : p.months;
  }

  Future<void> _loadReport() {
    final key = _key ?? 'latest';
    return _report.load(() => _repo.trend(_period, key));
  }

  @override
  void dispose() {
    _settings?.removeListener(_onSettings);
    _periods.dispose();
    _report.dispose();
    _series.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: Listenable.merge([_periods, _report, _series]),
      builder: (context, _) {
        final r = _report;
        return RefreshIndicator(
          onRefresh: _reload,
          child: ListView(
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              SourceBanner(offline: r.offline),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: SegmentedButton<String>(
                  segments: [
                    ButtonSegment(
                        value: 'week', label: Text(tr('주간', 'Weekly')), icon: const Icon(Icons.view_week_outlined)),
                    ButtonSegment(
                        value: 'month',
                        label: Text(tr('월간', 'Monthly')),
                        icon: const Icon(Icons.calendar_month_outlined)),
                  ],
                  selected: {_period},
                  onSelectionChanged: (s) {
                    setState(() => _period = s.first);
                    final keys = _keys();
                    _key = keys.isEmpty ? null : keys.first;
                    _loadReport();
                  },
                ),
              ),
              _PeriodChips(
                keys: _keys(),
                selected: r.data?.key ?? _key,
                onSelected: (k) {
                  setState(() => _key = k);
                  _loadReport();
                },
              ),
              ..._content(context),
            ],
          ),
        );
      },
    );
  }

  List<Widget> _content(BuildContext context) {
    final r = _report;
    if (r.status == LoadStatus.loading && r.data == null) {
      return const [Padding(padding: EdgeInsets.all(48), child: Center(child: CircularProgressIndicator()))];
    }
    if (r.status == LoadStatus.error && r.data == null) {
      return [SizedBox(height: 360, child: ErrorView(message: r.error ?? tr('오류', 'Error'), onRetry: _reload))];
    }
    final report = r.data!;
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final span = report.period == 'week' ? tr('전주', 'previous week') : tr('전월', 'previous month');
    return [
      Container(
        margin: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: scheme.secondaryContainer, borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(
              '${periodLabel(report.key)} · ${shortDay(report.start)}~${shortDay(report.end)} · '
              '${tr('논문 ${report.paperCount}편', '${report.paperCount} papers')}',
              style: text.labelMedium?.copyWith(color: scheme.onSecondaryContainer)),
          const SizedBox(height: 8),
          if (report.untranslated && report.narrative != null) ...[const PendingTranslation(), const SizedBox(height: 6)],
          Text(
              report.narrative ??
                  tr('이 기간의 해석 문장은 아직 없습니다. 아래 통계를 참고하세요.', 'No commentary for this period yet. See the statistics below.'),
              style: text.bodyMedium?.copyWith(color: scheme.onSecondaryContainer, height: 1.5)),
        ]),
      ),
      SectionTitle(tr('주제별 논문 수', 'Papers by topic'),
          subtitle: tr('막대 = 이번 기간, 옅은 막대 = $span', 'Bar = this period, faint bar = $span')),
      if (report.topics.isEmpty) EmptyNote(tr('논문이 없습니다', 'No papers')) else TopicBars(rows: report.topics),
      SectionTitle(tr('주제별 추이', 'Topic trends'),
          subtitle: tr('최근 주간 논문 수, 상위 5개 주제', 'Weekly papers, top 5 topics')),
      if (_series.data != null) TopicLines(series: _series.data!),
      SectionTitle(tr('급상승 키워드', 'Rising keywords'),
          subtitle: tr('직전 4개 기간 평균 대비', 'Versus the average of the previous 4 periods')),
      if (!report.baselineReady)
        EmptyNote(tr('비교할 데이터를 모으는 중입니다 (4주 이상 쌓이면 표시)', 'Collecting data to compare (shown after 4+ weeks)'))
      else if (report.risingKeywords.isEmpty)
        EmptyNote(tr('두 배 이상 늘어난 키워드가 없습니다', 'No keyword more than doubled'))
      else
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final k in report.risingKeywords)
              Chip(
                avatar: Icon(Icons.trending_up, size: 16, color: scheme.primary),
                label: Text(tr('${k.keyword} ×${k.ratio.toStringAsFixed(1)} (${k.count}편)',
                    '${k.keyword} ×${k.ratio.toStringAsFixed(1)} (${k.count})')),
              ),
          ]),
        ),
      SectionTitle(tr('화제 논문', 'Top papers'), subtitle: tr('추천 수 상위', 'Most upvoted')),
      for (final p in report.topPapers)
        PaperRow.brief(
          p,
          onTap: () =>
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PaperScreen(paperId: p.id))),
        ),
      SectionTitle(tr('Hub 신규 진입', 'New on the Hub'),
          subtitle: tr('이 기간에 처음 트렌딩에 오른 항목', 'First trended in this period')),
      if (report.hubNew.isEmpty) EmptyNote(tr('없습니다', 'None')),
      for (final h in report.hubNew)
        ListTile(
          dense: true,
          leading: const Icon(Icons.fiber_new_outlined),
          title: Text(h.id, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(tr('${h.kind.label} · ${shortDay(h.firstSeen)} 첫 등장 · ${h.days}일',
              '${h.kind.label} · first seen ${shortDay(h.firstSeen)} · ${h.days} days')),
          onTap: () => openLink(context, _hubUrl(h.kind, h.id)),
        ),
      SectionTitle(tr('Hub 꾸준한 인기', 'Steady on the Hub'),
          subtitle: tr('기간 마지막 날 기준 연속 일수', 'Consecutive days as of the last day')),
      for (final h in report.hubSteady)
        ListTile(
          dense: true,
          leading: const Icon(Icons.whatshot_outlined),
          title: Text(h.id, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text(tr('${h.kind.label} · ${h.streakDays}일 연속', '${h.kind.label} · ${h.streakDays} days in a row')),
          onTap: () => openLink(context, _hubUrl(h.kind, h.id)),
        ),
    ];
  }

  static String _hubUrl(HubKind kind, String id) => switch (kind) {
        HubKind.model => 'https://huggingface.co/$id',
        HubKind.dataset => 'https://huggingface.co/datasets/$id',
        HubKind.space => 'https://huggingface.co/spaces/$id',
      };
}

class _PeriodChips extends StatelessWidget {
  const _PeriodChips({required this.keys, required this.selected, required this.onSelected});

  final List<String> keys;
  final String? selected;
  final ValueChanged<String> onSelected;

  @override
  Widget build(BuildContext context) {
    if (keys.isEmpty) return const SizedBox(height: 8);
    return SizedBox(
      height: 60,
      child: ListView.separated(
        scrollDirection: Axis.horizontal,
        padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
        itemCount: keys.length,
        separatorBuilder: (_, __) => const SizedBox(width: 6),
        itemBuilder: (context, i) => ChoiceChip(
          label: Text(periodLabel(keys[i])),
          selected: keys[i] == selected,
          onSelected: (_) => onSelected(keys[i]),
        ),
      ),
    );
  }
}
