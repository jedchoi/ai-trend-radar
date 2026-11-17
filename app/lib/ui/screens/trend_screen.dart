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
      _serverUrl = _settings!.serverUrl;
      _reload();
    }
  }

  void _onSettings() {
    if (_settings!.serverUrl != _serverUrl) {
      _serverUrl = _settings!.serverUrl;
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
              SourceBanner(offline: r.offline, demo: r.demo),
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
                child: SegmentedButton<String>(
                  segments: const [
                    ButtonSegment(value: 'week', label: Text('주간'), icon: Icon(Icons.view_week_outlined)),
                    ButtonSegment(value: 'month', label: Text('월간'), icon: Icon(Icons.calendar_month_outlined)),
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
      return [SizedBox(height: 360, child: ErrorView(message: r.error ?? '오류', onRetry: _reload))];
    }
    final report = r.data!;
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final span = report.period == 'week' ? '전주' : '전월';
    return [
      Container(
        margin: const EdgeInsets.fromLTRB(16, 4, 16, 0),
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(color: scheme.secondaryContainer, borderRadius: BorderRadius.circular(16)),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text('${periodLabel(report.key)} · ${shortDay(report.start)}~${shortDay(report.end)} · 논문 ${report.paperCount}편',
              style: text.labelMedium?.copyWith(color: scheme.onSecondaryContainer)),
          const SizedBox(height: 8),
          Text(report.narrative ?? '이 기간의 해석 문장은 아직 없습니다. 아래 통계를 참고하세요.',
              style: text.bodyMedium?.copyWith(color: scheme.onSecondaryContainer, height: 1.5)),
        ]),
      ),
      SectionTitle('주제별 논문 수', subtitle: '막대 = 이번 기간, 옅은 막대 = $span'),
      if (report.topics.isEmpty) const EmptyNote('논문이 없습니다') else TopicBars(rows: report.topics),
      const SectionTitle('주제별 추이', subtitle: '최근 주간 논문 수, 상위 5개 주제'),
      if (_series.data != null) TopicLines(series: _series.data!),
      SectionTitle('급상승 키워드', subtitle: '직전 4개 기간 평균 대비'),
      if (!report.baselineReady)
        const EmptyNote('비교할 데이터를 모으는 중입니다 (4주 이상 쌓이면 표시)')
      else if (report.risingKeywords.isEmpty)
        const EmptyNote('두 배 이상 늘어난 키워드가 없습니다')
      else
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            for (final k in report.risingKeywords)
              Chip(
                avatar: Icon(Icons.trending_up, size: 16, color: scheme.primary),
                label: Text('${k.keyword} ×${k.ratio.toStringAsFixed(1)} (${k.count}편)'),
              ),
          ]),
        ),
      const SectionTitle('화제 논문', subtitle: '추천 수 상위'),
      for (final p in report.topPapers)
        PaperRow.brief(
          p,
          onTap: () =>
              Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PaperScreen(paperId: p.id))),
        ),
      const SectionTitle('Hub 신규 진입', subtitle: '이 기간에 처음 트렌딩에 오른 항목'),
      if (report.hubNew.isEmpty) const EmptyNote('없습니다'),
      for (final h in report.hubNew)
        ListTile(
          dense: true,
          leading: const Icon(Icons.fiber_new_outlined),
          title: Text(h.id, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text('${h.kind.label} · ${shortDay(h.firstSeen)} 첫 등장 · ${h.days}일'),
          onTap: () => openLink(context, _hubUrl(h.kind, h.id)),
        ),
      const SectionTitle('Hub 꾸준한 인기', subtitle: '기간 마지막 날 기준 연속 일수'),
      for (final h in report.hubSteady)
        ListTile(
          dense: true,
          leading: const Icon(Icons.whatshot_outlined),
          title: Text(h.id, maxLines: 1, overflow: TextOverflow.ellipsis),
          subtitle: Text('${h.kind.label} · ${h.streakDays}일 연속'),
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
