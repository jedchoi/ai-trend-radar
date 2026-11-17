import 'package:flutter/material.dart';

import '../../models/models.dart';
import '../format.dart';
import 'common.dart';

/// 주목 논문 카드 (BR-A02).
class PaperCard extends StatelessWidget {
  const PaperCard({super.key, required this.paper, required this.onTap, this.interests = const []});

  final Paper paper;
  final VoidCallback onTap;
  final List<String> interests;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    return Card(
      margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      clipBehavior: Clip.antiAlias,
      child: InkWell(
        onTap: onTap,
        child: Container(
          decoration: BoxDecoration(border: Border(left: BorderSide(color: paper.topic.color, width: 4))),
          padding: const EdgeInsets.fromLTRB(14, 12, 14, 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              TopicChip(paper.topic),
              const SizedBox(height: 8),
              Text(paper.title,
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                  style: text.titleSmall?.copyWith(fontWeight: FontWeight.w700, height: 1.3)),
              const SizedBox(height: 6),
              Text(paper.oneLiner, maxLines: 4, overflow: TextOverflow.ellipsis, style: text.bodyMedium),
              const SizedBox(height: 8),
              MetaLine(upvotes: paper.upvotes, hasCode: paper.hasCode, interests: interests),
            ],
          ),
        ),
      ),
    );
  }
}

/// 목록 한 줄 (BR-A03).
class PaperRow extends StatelessWidget {
  const PaperRow({
    super.key,
    required this.title,
    required this.oneLiner,
    required this.topic,
    required this.upvotes,
    required this.onTap,
    this.hasCode = false,
    this.date,
    this.interests = const [],
    this.featured = false,
  });

  final String title;
  final String oneLiner;
  final Topic topic;
  final int upvotes;
  final bool hasCode;
  final String? date;
  final List<String> interests;
  final bool featured;
  final VoidCallback onTap;

  factory PaperRow.paper(Paper p, {required VoidCallback onTap, List<String> interests = const []}) => PaperRow(
        title: p.title,
        oneLiner: p.oneLiner,
        topic: p.topic,
        upvotes: p.upvotes,
        hasCode: p.hasCode,
        interests: interests,
        featured: p.featured,
        onTap: onTap,
      );

  factory PaperRow.brief(PaperBrief p, {required VoidCallback onTap, List<String> interests = const []}) => PaperRow(
        title: p.title,
        oneLiner: p.oneLiner,
        topic: p.topic,
        upvotes: p.upvotes,
        hasCode: p.githubUrl != null,
        date: p.date,
        interests: interests,
        featured: p.featured,
        onTap: onTap,
      );

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final muted = text.labelSmall?.copyWith(color: Theme.of(context).colorScheme.onSurfaceVariant);
    return InkWell(
      onTap: onTap,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              width: 4,
              height: 40,
              margin: const EdgeInsets.only(top: 2, right: 12),
              decoration: BoxDecoration(color: topic.color, borderRadius: BorderRadius.circular(2)),
            ),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title,
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: text.bodyMedium?.copyWith(fontWeight: FontWeight.w600)),
                  const SizedBox(height: 2),
                  Text(oneLiner, maxLines: 2, overflow: TextOverflow.ellipsis, style: text.bodySmall),
                  const SizedBox(height: 6),
                  Wrap(
                    spacing: 8,
                    runSpacing: 4,
                    crossAxisAlignment: WrapCrossAlignment.center,
                    children: [
                      TopicChip(topic, dense: true),
                      if (date != null) Text(shortDay(date!), style: muted),
                      if (featured) Text('주목', style: muted?.copyWith(fontWeight: FontWeight.w700)),
                      MetaLine(upvotes: upvotes, hasCode: hasCode, interests: interests),
                    ],
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
