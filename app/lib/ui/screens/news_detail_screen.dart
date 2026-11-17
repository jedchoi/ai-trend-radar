import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../data/library_store.dart';
import '../../data/read_store.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../../state/load_controller.dart';
import '../format.dart';
import '../widgets/common.dart';
import '../widgets/links.dart';
import '../widgets/original_text.dart';
import '../../l10n/strings.dart';
import '../widgets/language_button.dart';

/// 뉴스 상세 (US-22, AC-22-2): 한국어 요약 · 핵심 · 키워드 → 원문 본문 전체.
class NewsDetailScreen extends StatefulWidget {
  const NewsDetailScreen({super.key, required this.newsId});

  final String newsId;

  @override
  State<NewsDetailScreen> createState() => _NewsDetailScreenState();
}

class _NewsDetailScreenState extends State<NewsDetailScreen> {
  LoadController<News>? _c;
  String? _lang;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_c == null) {
      final services = Services.of(context);
      _c = LoadController(() => services.repository.newsDetail(widget.newsId))..load();
      // 다른 화면의 목록을 다시 그리게 하므로 빌드가 끝난 뒤에 (BR-A23)
      WidgetsBinding.instance.addPostFrameCallback((_) => services.reads.mark(ReadStore.news(widget.newsId)));
    }
  }

  @override
  void dispose() {
    _c?.dispose();
    super.dispose();
  }

  Future<void> _copyLink(News n) async {
    final messenger = ScaffoldMessenger.of(context);
    await Clipboard.setData(ClipboardData(text: '${n.brief.title}\n${n.brief.url}'));
    messenger.showSnackBar(SnackBar(content: Text(tr('제목과 링크를 복사했습니다', 'Copied the title and link'))));
  }

  @override
  Widget build(BuildContext context) {
    final services = Services.of(context);
    final lang = services.settings.language;
    if (_lang != null && _lang != lang) {
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (mounted) _c!.load(); // BR-A30
      });
    }
    _lang = lang;
    return ListenableBuilder(
      listenable: Listenable.merge([_c!, services.library]),
      builder: (context, _) {
        final c = _c!;
        final news = c.data;
        final saved = news != null && services.library.contains(news.id, kind: LibraryKind.news);
        return Scaffold(
          appBar: AppBar(
            title: Text(tr('뉴스', 'News')),
            actions: [
              const LanguageButton(),
              if (news != null) ...[
                IconButton(
                  tooltip: saved ? tr('보관함에서 빼기', 'Remove from library') : tr('보관함에 저장', 'Save to library'),
                  icon: Icon(saved ? Icons.bookmark : Icons.bookmark_border),
                  onPressed: () => services.library.toggle(newsAsBrief(news.brief), kind: LibraryKind.news),
                ),
                IconButton(tooltip: tr('링크 복사', 'Copy link'), icon: const Icon(Icons.link), onPressed: () => _copyLink(news)),
              ],
            ],
          ),
          body: switch (c.status) {
            LoadStatus.loading when c.data == null => const Center(child: CircularProgressIndicator()),
            LoadStatus.error when c.data == null => ErrorView(message: c.error ?? tr('오류', 'Error'), onRetry: c.load),
            _ => _body(context, c.data!, c.offline),
          },
        );
      },
    );
  }

  Widget _body(BuildContext context, News n, bool offline) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final b = n.brief;
    final blocks = textBlocks(n.content);
    return ListView(
      padding: const EdgeInsets.only(bottom: 32),
      children: [
        SourceBanner(offline: offline),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Wrap(spacing: 8, runSpacing: 4, crossAxisAlignment: WrapCrossAlignment.center, children: [
              TopicChip(b.topic),
              if (b.day.isNotEmpty) Text(dayLabel(b.day), style: text.labelSmall),
              if (b.organization != null) Text(b.organization!, style: text.labelSmall),
              if (n.untranslated) const PendingTranslation(),
            ]),
            const SizedBox(height: 10),
            Text(b.title, style: text.titleLarge?.copyWith(fontWeight: FontWeight.w800, height: 1.3)),
            if (n.authors.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text(n.authors.take(5).join(', '), style: text.bodySmall?.copyWith(color: scheme.onSurfaceVariant)),
            ],
          ]),
        ),
        Container(
          margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
          padding: const EdgeInsets.all(14),
          decoration: BoxDecoration(color: scheme.primaryContainer, borderRadius: BorderRadius.circular(12)),
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Row(children: [
              Icon(Icons.auto_awesome_outlined, size: 18, color: scheme.onPrimaryContainer),
              const SizedBox(width: 6),
              Text(tr('요약', 'Summary'), style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700)),
              const Spacer(),
              Text(n.aiSummary ? tr('AI 요약', 'AI summary') : tr('본문 첫 문단', 'First paragraph'),
                  style: text.labelSmall?.copyWith(color: scheme.onPrimaryContainer.withValues(alpha: 0.7))),
            ]),
            const SizedBox(height: 6),
            Text(b.summary, style: text.bodyMedium?.copyWith(height: 1.5)),
          ]),
        ),
        if (n.keyPoints.isNotEmpty) ...[
          SectionTitle(tr('핵심', 'Key points')),
          for (final point in n.keyPoints)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 2, 16, 4),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Icon(Icons.check_circle_outline, size: 18, color: scheme.primary),
                const SizedBox(width: 8),
                Expanded(child: Text(point, style: text.bodyMedium?.copyWith(height: 1.45))),
              ]),
            ),
        ],
        if (b.keywords.isNotEmpty)
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
            child: Wrap(spacing: 6, runSpacing: 6, children: [for (final k in b.keywords) Chip(label: Text(k))]),
          ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
          child: OutlinedButton.icon(
            icon: const Icon(Icons.open_in_new),
            label: Text(tr('Hugging Face 에서 원문 열기', 'Open on Hugging Face')),
            onPressed: () => openLink(context, b.url),
          ),
        ),
        SectionTitle(originalTitle(translated: !n.untranslated && AppLang.english == false),
            subtitle: n.content.isEmpty ? null : originalSubtitle(n.content.length, translated: !n.untranslated)),
        if (blocks.isEmpty) EmptyNote(tr('저장된 본문이 없습니다. 위의 버튼으로 원문을 여세요.', 'No stored body. Open the original with the button above.')),
        for (final block in blocks) OriginalBlock(block),
      ],
    );
  }
}
