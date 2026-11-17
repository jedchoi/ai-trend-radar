import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../data/library_store.dart';
import '../../logic/ask_prompt.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../../state/load_controller.dart';
import '../format.dart';
import '../widgets/common.dart';
import '../widgets/links.dart';
import '../widgets/paper_widgets.dart';

/// 뉴스 요약 (US-05 ~ US-08, US-13).
class PaperScreen extends StatefulWidget {
  const PaperScreen({super.key, required this.paperId});

  final String paperId;

  @override
  State<PaperScreen> createState() => _PaperScreenState();
}

class _PaperScreenState extends State<PaperScreen> {
  LoadController<PaperWithRelated>? _c;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_c == null) {
      final repo = Services.of(context).repository;
      _c = LoadController(() => repo.paper(widget.paperId))..load();
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Future<void> _ask(Paper paper) async {
    final target = Services.of(context).settings.askTarget;
    final messenger = ScaffoldMessenger.of(context);
    await Clipboard.setData(ClipboardData(text: buildAskPrompt(paper)));
    messenger.showSnackBar(SnackBar(content: Text('질문을 복사했습니다. ${target.label} 에 붙여넣으세요.')));
    if (mounted) await openLink(context, target.url);
  }

  @override
  Widget build(BuildContext context) {
    final services = Services.of(context);
    return ListenableBuilder(
      listenable: Listenable.merge([_c!, services.library]),
      builder: (context, _) {
        final c = _c!;
        final paper = c.data?.paper;
        final saved = paper != null && services.library.contains(paper.id);
        return Scaffold(
          appBar: AppBar(
            title: const Text('논문 요약'),
            actions: [
              if (paper != null) ...[
                IconButton(
                  tooltip: saved ? '보관함에서 빼기' : '보관함에 저장',
                  icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
                  onPressed: () => services.library.toggle(paper.toBrief()),
                ),
                IconButton(
                  tooltip: 'AI 에게 묻기',
                  icon: const Icon(Icons.forum_outlined),
                  onPressed: () => _ask(paper),
                ),
              ],
            ],
          ),
          body: switch (c.status) {
            LoadStatus.loading when c.data == null => const Center(child: CircularProgressIndicator()),
            LoadStatus.error when c.data == null => ErrorView(message: c.error ?? '오류', onRetry: c.load),
            _ => _body(context, c.data!, c.offline, services.library),
          },
        );
      },
    );
  }

  Widget _body(BuildContext context, PaperWithRelated data, bool offline, LibraryStore library) {
    final p = data.paper;
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final entry = library.entry(p.id);
    return ListView(
      padding: const EdgeInsets.only(bottom: 32),
      children: [
        SourceBanner(offline: offline, demo: false),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                TopicChip(p.topic),
                Text(dayLabel(p.date), style: text.labelSmall),
                if (p.featured) Badge2('주목', color: scheme.primary, icon: Icons.local_fire_department),
              ]),
              const SizedBox(height: 10),
              Text(p.title, style: text.titleLarge?.copyWith(fontWeight: FontWeight.w800, height: 1.3)),
              const SizedBox(height: 6),
              Text(
                [if (p.organization != null) p.organization!, p.authors.take(4).join(', ')]
                    .where((s) => s.isNotEmpty)
                    .join(' · '),
                style: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant),
              ),
              const SizedBox(height: 8),
              MetaLine(upvotes: p.upvotes, hasCode: p.hasCode),
            ],
          ),
        ),
        if (entry != null) _LibraryBar(entry: entry, library: library),
        const SectionTitle('한 줄 요약'),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: Text(p.oneLiner, style: text.bodyLarge)),
        if (p.detail != null) ..._detail(context, p.detail!) else ..._abstract(context, p),
        if (p.glossary.isNotEmpty) ...[
          const SectionTitle('용어'),
          for (final g in p.glossary)
            Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: ListTile(title: Text(g.term), subtitle: Text(g.explanation)),
            ),
        ],
        const SectionTitle('바로 가기'),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
              icon: const Icon(Icons.description_outlined),
              label: const Text('논문 (Hugging Face)'),
              onPressed: () => openLink(context, p.hfUrl),
            ),
            if (p.githubUrl != null)
              OutlinedButton.icon(
                icon: const Icon(Icons.code),
                label: Text(p.githubStars == null ? 'GitHub' : 'GitHub ★${compact(p.githubStars!)}'),
                onPressed: () => openLink(context, p.githubUrl!),
              ),
            if (p.projectUrl != null)
              OutlinedButton.icon(
                icon: const Icon(Icons.public),
                label: const Text('프로젝트 페이지'),
                onPressed: () => openLink(context, p.projectUrl!),
              ),
          ]),
        ),
        if (p.keywords.isNotEmpty) ...[
          const SectionTitle('키워드'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(spacing: 6, runSpacing: 6, children: [for (final k in p.keywords) Chip(label: Text(k))]),
          ),
        ],
        const SectionTitle('이어서 볼 이전 논문', subtitle: '같은 키워드를 다룬 논문'),
        if (data.related.isEmpty) const EmptyNote('아직 관련 논문이 없습니다'),
        for (final r in data.related)
          PaperRow.brief(
            r,
            onTap: () => Navigator.of(context)
                .push(MaterialPageRoute<void>(builder: (_) => PaperScreen(paperId: r.id))),
          ),
      ],
    );
  }

  List<Widget> _detail(BuildContext context, PaperDetail d) => [
        _DetailBlock(icon: Icons.science_outlined, title: '무엇을 했나', body: d.what),
        _DetailBlock(icon: Icons.auto_awesome_outlined, title: '새로운 점', body: d.novelty),
        _DetailBlock(icon: Icons.lightbulb_outline, title: '왜 중요한가', body: d.why),
        _DetailBlock(icon: Icons.build_outlined, title: '실무에 쓰려면', body: d.apply, highlight: true),
      ];

  List<Widget> _abstract(BuildContext context, Paper p) => [
        SectionTitle('초록', trailing: Badge2('초록 기반', color: Theme.of(context).colorScheme.outline)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(p.abstract.isEmpty ? '초록이 없습니다.' : p.abstract,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(height: 1.5)),
        ),
      ];
}

class _DetailBlock extends StatelessWidget {
  const _DetailBlock({required this.icon, required this.title, required this.body, this.highlight = false});

  final IconData icon;
  final String title;
  final String body;
  final bool highlight;

  @override
  Widget build(BuildContext context) {
    final scheme = Theme.of(context).colorScheme;
    final text = Theme.of(context).textTheme;
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: highlight ? scheme.primaryContainer : scheme.surfaceContainerHighest.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(children: [
            Icon(icon, size: 18, color: highlight ? scheme.onPrimaryContainer : scheme.primary),
            const SizedBox(width: 6),
            Expanded(child: Text(title, style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700))),
          ]),
          const SizedBox(height: 6),
          Text(body, style: text.bodyMedium?.copyWith(height: 1.5)),
        ],
      ),
    );
  }
}

/// 저장된 논문의 상태 (BR-A11).
class _LibraryBar extends StatelessWidget {
  const _LibraryBar({required this.entry, required this.library});

  final LibraryEntry entry;
  final LibraryStore library;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
        const Icon(Icons.bookmark, size: 18),
        for (final s in LibraryStatus.values)
          ChoiceChip(
            label: Text(s.label),
            selected: entry.status == s,
            onSelected: (_) => library.setStatus(entry.paper.id, s),
          ),
      ]),
    );
  }
}
