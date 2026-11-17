import 'package:flutter/material.dart';

import '../../models/models.dart';
import '../format.dart';
import 'common.dart';

String _source(NewsBrief n) => [if (n.organization != null) n.organization!, if (n.day.isNotEmpty) shortDay(n.day)].join(' · ');

/// 뉴스 목록 한 줄 (US-22, BR-A23: 읽은 글은 흐리게).
class NewsTile extends StatelessWidget {
  const NewsTile({super.key, required this.news, required this.onTap, this.read = false});

  final NewsBrief news;
  final VoidCallback onTap;
  final bool read;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final muted = text.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant);
    return Opacity(
      opacity: read ? 0.55 : 1,
      child: InkWell(
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Container(
                width: 4,
                height: 44,
                margin: const EdgeInsets.only(top: 2, right: 12),
                decoration: BoxDecoration(color: news.topic.color, borderRadius: BorderRadius.circular(2)),
              ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(news.title,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: text.bodyLarge?.copyWith(fontWeight: FontWeight.w700, height: 1.3)),
                    const SizedBox(height: 4),
                    Text(news.summary, maxLines: 3, overflow: TextOverflow.ellipsis, style: text.bodySmall),
                    const SizedBox(height: 6),
                    Wrap(
                      spacing: 8,
                      runSpacing: 4,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        TopicChip(news.topic, dense: true),
                        Text(_source(news), style: muted),
                        if (read) Text('읽음', style: muted),
                      ],
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 오늘 화면 위쪽의 가로 뉴스 카드 (BR-A27).
class NewsCard extends StatelessWidget {
  const NewsCard({super.key, required this.news, required this.onTap, this.read = false});

  final NewsBrief news;
  final VoidCallback onTap;
  final bool read;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    return SizedBox(
      width: 260,
      child: Opacity(
        opacity: read ? 0.55 : 1,
        child: Card(
          margin: EdgeInsets.zero,
          clipBehavior: Clip.antiAlias,
          child: InkWell(
            onTap: onTap,
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Icon(Icons.campaign_outlined, size: 16, color: scheme.primary),
                    const SizedBox(width: 4),
                    Expanded(
                      child: Text(_source(news),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: text.labelSmall?.copyWith(color: scheme.onSurfaceVariant)),
                    ),
                  ]),
                  const SizedBox(height: 6),
                  Text(news.title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700, height: 1.25)),
                  const SizedBox(height: 4),
                  Expanded(
                    child: Text(news.summary,
                        maxLines: 3, overflow: TextOverflow.ellipsis, style: text.bodySmall?.copyWith(height: 1.35)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
