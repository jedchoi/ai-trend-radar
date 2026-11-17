import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../data/library_store.dart';
import '../../data/read_store.dart';
import '../../logic/ask_prompt.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../../state/load_controller.dart';
import '../format.dart';
import '../widgets/common.dart';
import '../widgets/links.dart';
import '../widgets/original_text.dart';
import '../widgets/paper_widgets.dart';
import '../../l10n/strings.dart';
import '../widgets/language_button.dart';

/// 뉴스 요약 (US-05 ~ US-08, US-13).
class PaperScreen extends StatefulWidget {
  const PaperScreen({super.key, required this.paperId});

  final String paperId;

  @override
  State<PaperScreen> createState() => _PaperScreenState();
}

class _PaperScreenState extends State<PaperScreen> {
  LoadController<PaperWithRelated>? _c;
  String? _lang;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_c == null) {
      final services = Services.of(context);
      _c = LoadController(() => services.repository.paper(widget.paperId))..load();
      // 다른 화면의 목록을 다시 그리게 하므로 빌드가 끝난 뒤에 (BR-A23)
      WidgetsBinding.instance.addPostFrameCallback((_) => services.reads.mark(ReadStore.paper(widget.paperId)));
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
    messenger.showSnackBar(SnackBar(
        content: Text(tr('질문을 복사했습니다. ${target.label} 에 붙여넣으세요.', 'Copied the question. Paste it into ${target.label}.'))));
    if (mounted) await openLink(context, target.url);
  }

  /// BR-A30: 언어가 바뀌면 그 언어로 다시 받는다.
  void _reloadOnLanguage(String lang) {
    if (_lang != null && _lang != lang) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _c!.load();
      });
    }
    _lang = lang;
  }

  Future<void> _copyLink(Paper paper) async {
    final messenger = ScaffoldMessenger.of(context);
    await Clipboard.setData(ClipboardData(text: '${paper.title}\n${paper.hfUrl}'));
    messenger.showSnackBar(SnackBar(content: Text(tr('제목과 링크를 복사했습니다', 'Copied the title and link'))));
  }

  @override
  Widget build(BuildContext context) {
    final services = Services.of(context);
    _reloadOnLanguage(services.settings.language);
    return ListenableBuilder(
      listenable: Listenable.merge([_c!, services.library]),
      builder: (context, _) {
        final c = _c!;
        final paper = c.data?.paper;
        final saved = paper != null && services.library.contains(paper.id);
        return Scaffold(
          appBar: AppBar(
            title: Text(tr('논문 요약', 'Paper summary')),
            actions: [
              const LanguageButton(),
              if (paper != null) ...[
                IconButton(
                  tooltip: saved ? tr('보관함에서 빼기', 'Remove from library') : tr('보관함에 저장', 'Save to library'),
                  icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
                  onPressed: () => services.library.toggle(paper.toBrief()),
                ),
                IconButton(
                  tooltip: tr('AI 에게 묻기', 'Ask an AI'),
                  icon: const Icon(Icons.forum_outlined),
                  onPressed: () => _ask(paper),
                ),
                IconButton(tooltip: tr('링크 복사', 'Copy link'), icon: const Icon(Icons.link), onPressed: () => _copyLink(paper)),
              ],
            ],
          ),
          body: switch (c.status) {
            LoadStatus.loading when c.data == null => const Center(child: CircularProgressIndicator()),
            LoadStatus.error when c.data == null => ErrorView(message: c.error ?? tr('오류', 'Error'), onRetry: c.load),
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
        SourceBanner(offline: offline),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
                TopicChip(p.topic),
                Text(dayLabel(p.date), style: text.labelSmall),
                if (p.featured) Badge2(tr('주목', 'Featured'), color: scheme.primary, icon: Icons.local_fire_department),
                if (p.untranslated) const PendingTranslation(),
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
        SectionTitle(tr('한 줄 요약', 'In one line')),
        Padding(padding: const EdgeInsets.symmetric(horizontal: 16), child: Text(p.oneLiner, style: text.bodyLarge)),
        if (p.detail != null) ..._detail(context, p.detail!) else ..._abstract(context, p),
        if (p.glossary.isNotEmpty) ...[
          SectionTitle(tr('용어', 'Glossary')),
          for (final g in p.glossary)
            Card(
              margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              child: ListTile(title: Text(g.term), subtitle: Text(g.explanation)),
            ),
        ],
        ..._original(context, p),
        SectionTitle(tr('바로 가기', 'Links')),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 8, runSpacing: 8, children: [
            OutlinedButton.icon(
              icon: const Icon(Icons.description_outlined),
              label: Text(tr('논문 (Hugging Face)', 'Paper (Hugging Face)')),
              onPressed: () => openLink(context, p.hfUrl),
            ),
            if (p.arxivUrl != null)
              OutlinedButton.icon(
                icon: const Icon(Icons.article_outlined),
                label: const Text('arXiv'),
                onPressed: () => openLink(context, p.arxivUrl!),
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
                label: Text(tr('프로젝트 페이지', 'Project page')),
                onPressed: () => openLink(context, p.projectUrl!),
              ),
          ]),
        ),
        if (p.keywords.isNotEmpty) ...[
          SectionTitle(tr('키워드', 'Keywords')),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(spacing: 6, runSpacing: 6, children: [for (final k in p.keywords) Chip(label: Text(k))]),
          ),
        ],
        SectionTitle(tr('이어서 볼 이전 논문', 'Earlier related papers'),
            subtitle: tr('같은 키워드를 다룬 논문', 'Papers sharing keywords')),
        if (data.related.isEmpty) EmptyNote(tr('아직 관련 논문이 없습니다', 'No related papers yet')),
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
        _DetailBlock(icon: Icons.science_outlined, title: tr('무엇을 했나', 'What they did'), body: d.what),
        _DetailBlock(icon: Icons.auto_awesome_outlined, title: tr('새로운 점', "What's new"), body: d.novelty),
        _DetailBlock(icon: Icons.lightbulb_outline, title: tr('왜 중요한가', 'Why it matters'), body: d.why),
        _DetailBlock(icon: Icons.build_outlined, title: tr('실무에 쓰려면', 'Putting it to use'), body: d.apply, highlight: true),
      ];

  /// 원문 (US-23, BR-A24): 초록 원문 펼치기 + 본문 원문 읽기 화면.
  List<Widget> _original(BuildContext context, Paper p) {
    final text = Theme.of(context).textTheme;
    final fullText = p.fullText;
    return [
      // 논문 원문은 언어와 무관하게 영어 그대로 (FR-34 개정, BR-A35)
      SectionTitle(originalTitle(translated: false),
          subtitle: fullText != null
              ? tr('초록 · 본문 (영어 원문 그대로)', 'Abstract · full text')
              : tr('초록 (영어 원문 그대로)', 'Abstract')),
      if (p.detail != null)
        Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          clipBehavior: Clip.antiAlias,
          child: ExpansionTile(
            leading: const Icon(Icons.notes),
            title: Text(tr('초록 (Abstract)', 'Abstract')),
            childrenPadding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
            children: [
              SelectableText(p.abstract.isEmpty ? tr('초록이 없습니다.', 'No abstract.') : p.abstract,
                  style: text.bodyMedium?.copyWith(height: 1.55)),
            ],
          ),
        ),
      if (fullText != null)
        Card(
          margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          child: ListTile(
            leading: const Icon(Icons.menu_book_outlined),
            title: Text(tr('본문 원문 읽기', 'Read the full text')),
            subtitle: Text(tr('${compact(fullText.length)}자', '${compact(fullText.length)} characters')),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                builder: (_) => OriginalTextScreen(
                    title: p.title, content: fullText, sourceLabel: tr('Hugging Face 논문 페이지 본문 (arXiv 원문)', 'Hugging Face paper page (arXiv original)')))),
          ),
        )
      else
        EmptyNote(tr('본문 원문은 주목 논문만 저장합니다. 아래 arXiv · Hugging Face 링크에서 읽을 수 있습니다.',
            'Full text is stored for featured papers only. Read it via the arXiv · Hugging Face links below.')),
    ];
  }

  List<Widget> _abstract(BuildContext context, Paper p) => [
        SectionTitle(tr('초록', 'Abstract'),
            trailing: Badge2(tr('초록 기반', 'From abstract'), color: Theme.of(context).colorScheme.outline)),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Text(p.abstract.isEmpty ? tr('초록이 없습니다.', 'No abstract.') : p.abstract,
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
            onSelected: (_) => library.setStatus(entry.key, s),
          ),
      ]),
    );
  }
}
