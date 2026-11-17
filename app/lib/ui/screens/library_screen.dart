import 'package:flutter/material.dart';

import '../../data/library_store.dart';
import '../../services.dart';
import '../format.dart';
import '../widgets/common.dart';
import 'news_detail_screen.dart';
import 'paper_screen.dart';

/// 보관함 (US-13, BR-A11).
class LibraryScreen extends StatefulWidget {
  const LibraryScreen({super.key});

  @override
  State<LibraryScreen> createState() => _LibraryScreenState();
}

class _LibraryScreenState extends State<LibraryScreen> {
  LibraryStatus? _filter;

  @override
  Widget build(BuildContext context) {
    final library = Services.of(context).library;
    return ListenableBuilder(
      listenable: library,
      builder: (context, _) {
        final entries = library.items(status: _filter);
        return ListView(
          padding: const EdgeInsets.only(bottom: 24),
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                ChoiceChip(
                  label: Text('전체 ${library.items().length}'),
                  selected: _filter == null,
                  onSelected: (_) => setState(() => _filter = null),
                ),
                for (final s in LibraryStatus.values)
                  ChoiceChip(
                    label: Text('${s.label} ${library.items(status: s).length}'),
                    selected: _filter == s,
                    onSelected: (_) => setState(() => _filter = s),
                  ),
              ]),
            ),
            if (entries.isEmpty)
              const EmptyNote('저장한 논문이 없습니다. 논문 · 뉴스 화면의 책갈피 버튼으로 저장하세요.'),
            for (final e in entries)
              ListTile(
                leading: Container(width: 4, height: 40, color: e.paper.topic.color),
                title: Text(e.paper.title, maxLines: 2, overflow: TextOverflow.ellipsis),
                subtitle: Text(
                  [
                    if (e.kind == LibraryKind.news) '뉴스',
                    e.status.label,
                    if (e.paper.date.isNotEmpty) shortDay(e.paper.date),
                    if (e.note.isNotEmpty) '메모: ${e.note}',
                  ].join(' · '),
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                ),
                trailing: IconButton(
                  tooltip: '상태 · 메모 편집',
                  icon: const Icon(Icons.edit_note),
                  onPressed: () => _edit(context, library, e),
                ),
                onTap: () => Navigator.of(context).push(MaterialPageRoute<void>(
                    builder: (_) => e.kind == LibraryKind.news
                        ? NewsDetailScreen(newsId: e.paper.id)
                        : PaperScreen(paperId: e.paper.id))),
              ),
          ],
        );
      },
    );
  }

  Future<void> _edit(BuildContext context, LibraryStore library, LibraryEntry entry) {
    return showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      showDragHandle: true,
      builder: (context) => _EditSheet(library: library, entry: entry),
    );
  }
}

class _EditSheet extends StatefulWidget {
  const _EditSheet({required this.library, required this.entry});

  final LibraryStore library;
  final LibraryEntry entry;

  @override
  State<_EditSheet> createState() => _EditSheetState();
}

class _EditSheetState extends State<_EditSheet> {
  late LibraryStatus _status = widget.entry.status;
  late final TextEditingController _note = TextEditingController(text: widget.entry.note);

  @override
  void dispose() {
    _note.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final navigator = Navigator.of(context);
    await widget.library.setStatus(widget.entry.key, _status);
    await widget.library.setNote(widget.entry.key, _note.text);
    navigator.pop();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.fromLTRB(16, 0, 16, 16 + MediaQuery.of(context).viewInsets.bottom),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(widget.entry.paper.title, maxLines: 2, overflow: TextOverflow.ellipsis,
              style: Theme.of(context).textTheme.titleSmall),
          const SizedBox(height: 12),
          Wrap(spacing: 6, runSpacing: 6, children: [
            for (final s in LibraryStatus.values)
              ChoiceChip(label: Text(s.label), selected: _status == s, onSelected: (_) => setState(() => _status = s)),
          ]),
          const SizedBox(height: 12),
          TextField(
            controller: _note,
            maxLength: LibraryStore.maxNote,
            maxLines: 4,
            decoration: const InputDecoration(labelText: '메모 (어디에 쓸지, 시험 결과 등)', border: OutlineInputBorder()),
          ),
          Align(alignment: Alignment.centerRight, child: FilledButton(onPressed: _save, child: const Text('저장'))),
        ],
      ),
    );
  }
}
