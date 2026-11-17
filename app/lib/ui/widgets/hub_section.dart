import 'package:flutter/material.dart';

import '../../models/models.dart';
import '../format.dart';
import 'common.dart';
import 'links.dart';
import '../../l10n/strings.dart';

/// Hugging Face 트렌드 (BR-A04).
class HubSection extends StatefulWidget {
  const HubSection({super.key, required this.items});

  final List<HubItem> items;

  @override
  State<HubSection> createState() => _HubSectionState();
}

class _HubSectionState extends State<HubSection> {
  HubKind kind = HubKind.model;

  @override
  Widget build(BuildContext context) {
    final items = widget.items.where((i) => i.kind == kind).toList()..sort((a, b) => a.rank.compareTo(b.rank));
    final scheme = Theme.of(context).colorScheme;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(
            spacing: 8,
            children: [
              for (final k in HubKind.values)
                ChoiceChip(
                  label: Text(k.label),
                  selected: kind == k,
                  onSelected: (_) => setState(() => kind = k),
                ),
            ],
          ),
        ),
        if (items.isEmpty) EmptyNote(tr('항목이 없습니다', 'No items')),
        for (final item in items)
          ListTile(
            leading: CircleAvatar(
              radius: 14,
              backgroundColor: scheme.primaryContainer,
              child: Text('${item.rank}', style: TextStyle(fontSize: 12, color: scheme.onPrimaryContainer)),
            ),
            title: Text(item.id, maxLines: 1, overflow: TextOverflow.ellipsis),
            subtitle: Wrap(
              spacing: 8,
              runSpacing: 4,
              crossAxisAlignment: WrapCrossAlignment.center,
              children: [
                Text(tr('좋아요 ${compact(item.likes)}', '${compact(item.likes)} likes')),
                if (item.task != null) Text(item.task!),
                if (item.isNew) Badge2(tr('신규', 'New'), color: scheme.error),
                if (item.streakDays >= 3) Badge2(tr('${item.streakDays}일째', 'Day ${item.streakDays}'), color: scheme.tertiary),
              ],
            ),
            trailing: const Icon(Icons.open_in_new, size: 18),
            onTap: () => openLink(context, item.url),
          ),
      ],
    );
  }
}
