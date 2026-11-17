import 'package:flutter/material.dart';

import '../../models/models.dart';

/// 원문 블록 하나 (BR-A24). 길게 누르면 선택 · 복사할 수 있다.
class OriginalBlock extends StatelessWidget {
  const OriginalBlock(this.block, {super.key});

  final TextBlock block;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return switch (block.kind) {
      TextBlockKind.heading => Padding(
          padding: const EdgeInsets.fromLTRB(16, 18, 16, 6),
          child: SelectableText(block.text, style: text.titleMedium?.copyWith(fontWeight: FontWeight.w700)),
        ),
      TextBlockKind.bullet => Padding(
          padding: const EdgeInsets.fromLTRB(24, 2, 16, 2),
          child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text('•  ', style: text.bodyMedium),
            Expanded(child: SelectableText(block.text, style: text.bodyMedium?.copyWith(height: 1.5))),
          ]),
        ),
      TextBlockKind.paragraph => Padding(
          padding: const EdgeInsets.fromLTRB(16, 6, 16, 6),
          child: SelectableText(block.text, style: text.bodyMedium?.copyWith(height: 1.6)),
        ),
    };
  }
}

/// 긴 원문을 읽는 화면 (논문 본문). 블록 단위로 그때그때 그린다.
class OriginalTextScreen extends StatelessWidget {
  const OriginalTextScreen({super.key, required this.title, required this.content, this.sourceLabel});

  final String title;
  final String content;
  final String? sourceLabel;

  @override
  Widget build(BuildContext context) {
    final blocks = textBlocks(content);
    final scheme = Theme.of(context).colorScheme;
    return Scaffold(
      appBar: AppBar(title: const Text('원문')),
      body: ListView.builder(
        padding: const EdgeInsets.only(bottom: 32),
        itemCount: blocks.length + 1,
        itemBuilder: (context, i) {
          if (i == 0) {
            return Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Text(title, style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w800)),
                if (sourceLabel != null) ...[
                  const SizedBox(height: 4),
                  Text(sourceLabel!,
                      style: Theme.of(context).textTheme.labelSmall?.copyWith(color: scheme.onSurfaceVariant)),
                ],
              ]),
            );
          }
          return OriginalBlock(blocks[i - 1]);
        },
      ),
    );
  }
}
