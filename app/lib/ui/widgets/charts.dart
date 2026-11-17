import 'dart:math' as math;

import 'package:flutter/material.dart';

import '../../models/models.dart';
import '../format.dart';

/// 주제별 편수 막대 + 직전 기간 대비 증감 (BR-A09).
class TopicBars extends StatelessWidget {
  const TopicBars({super.key, required this.rows});

  final List<TopicCount> rows;

  @override
  Widget build(BuildContext context) {
    final text = Theme.of(context).textTheme;
    final scheme = Theme.of(context).colorScheme;
    final maxCount = rows.fold<int>(1, (m, r) => math.max(m, math.max(r.count, r.prevCount)));
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        children: [
          for (final r in rows)
            Padding(
              padding: const EdgeInsets.symmetric(vertical: 5),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(children: [
                    Expanded(child: Text(r.topic.label, style: text.bodySmall, overflow: TextOverflow.ellipsis)),
                    Text('${r.count}편', style: text.bodySmall?.copyWith(fontWeight: FontWeight.w700)),
                    const SizedBox(width: 8),
                    SizedBox(
                      width: 44,
                      child: Text(
                        r.delta == 0 ? '–' : (r.delta > 0 ? '▲${r.delta}' : '▼${-r.delta}'),
                        textAlign: TextAlign.right,
                        style: text.labelSmall?.copyWith(
                          color: r.delta > 0 ? scheme.primary : (r.delta < 0 ? scheme.error : scheme.onSurfaceVariant),
                        ),
                      ),
                    ),
                  ]),
                  const SizedBox(height: 4),
                  LayoutBuilder(builder: (context, c) {
                    return Stack(children: [
                      Container(height: 8, width: c.maxWidth, decoration: _bar(scheme.surfaceContainerHighest)),
                      Container(
                        height: 8,
                        width: c.maxWidth * r.prevCount / maxCount,
                        decoration: _bar(r.topic.color.withValues(alpha: 0.25)),
                      ),
                      Container(
                        height: 8,
                        width: c.maxWidth * r.count / maxCount,
                        decoration: _bar(r.topic.color),
                      ),
                    ]);
                  }),
                ],
              ),
            ),
          const SizedBox(height: 4),
          Row(children: [
            _legend(context, scheme.primary, '이번 기간'),
            const SizedBox(width: 12),
            _legend(context, scheme.primary.withValues(alpha: 0.25), '직전 기간'),
          ]),
        ],
      ),
    );
  }

  static BoxDecoration _bar(Color color) => BoxDecoration(color: color, borderRadius: BorderRadius.circular(4));

  static Widget _legend(BuildContext context, Color color, String label) => Row(mainAxisSize: MainAxisSize.min, children: [
        Container(width: 10, height: 10, decoration: _bar(color)),
        const SizedBox(width: 4),
        Text(label, style: Theme.of(context).textTheme.labelSmall),
      ]);
}

/// 주제별 주간 추이 선 차트 (BR-A09, 상위 5개 주제).
class TopicLines extends StatelessWidget {
  const TopicLines({super.key, required this.series, this.maxTopics = 5});

  final TopicSeries series;
  final int maxTopics;

  @override
  Widget build(BuildContext context) {
    final topics = series.topTopics(maxTopics);
    final scheme = Theme.of(context).colorScheme;
    final label = Theme.of(context).textTheme.labelSmall;
    if (topics.isEmpty || series.weeks.length < 2) {
      return const Padding(padding: EdgeInsets.all(16), child: Text('추이를 그릴 데이터가 아직 부족합니다'));
    }
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            height: 160,
            width: double.infinity,
            child: CustomPaint(
              painter: _LinePainter(
                weeks: series.weeks.length,
                lines: {for (final t in topics) t: series.counts[t]!},
                grid: scheme.outlineVariant,
              ),
            ),
          ),
          const SizedBox(height: 4),
          Row(children: [
            Text(periodLabel(series.weeks.first), style: label),
            const Spacer(),
            Text(periodLabel(series.weeks.last), style: label),
          ]),
          const SizedBox(height: 8),
          Wrap(
            spacing: 12,
            runSpacing: 4,
            children: [
              for (final t in topics)
                Row(mainAxisSize: MainAxisSize.min, children: [
                  Container(width: 12, height: 3, color: t.color),
                  const SizedBox(width: 4),
                  Text(t.label, style: label),
                ]),
            ],
          ),
        ],
      ),
    );
  }
}

class _LinePainter extends CustomPainter {
  _LinePainter({required this.weeks, required this.lines, required this.grid});

  final int weeks;
  final Map<Topic, List<int>> lines;
  final Color grid;

  @override
  void paint(Canvas canvas, Size size) {
    final maxValue = math.max(1, lines.values.expand((v) => v).fold<int>(0, math.max));
    final gridPaint = Paint()
      ..color = grid
      ..strokeWidth = 1;
    for (var i = 0; i <= 4; i++) {
      final y = size.height * i / 4;
      canvas.drawLine(Offset(0, y), Offset(size.width, y), gridPaint);
    }
    double x(int i) => weeks == 1 ? 0 : size.width * i / (weeks - 1);
    double y(int v) => size.height - (size.height - 6) * v / maxValue - 3;
    for (final entry in lines.entries) {
      final paint = Paint()
        ..color = entry.key.color
        ..strokeWidth = 2.2
        ..style = PaintingStyle.stroke
        ..strokeJoin = StrokeJoin.round;
      final path = Path();
      for (var i = 0; i < entry.value.length; i++) {
        final point = Offset(x(i), y(entry.value[i]));
        if (i == 0) {
          path.moveTo(point.dx, point.dy);
        } else {
          path.lineTo(point.dx, point.dy);
        }
      }
      canvas.drawPath(path, paint);
      final last = entry.value.length - 1;
      canvas.drawCircle(Offset(x(last), y(entry.value[last])), 3.5, Paint()..color = entry.key.color);
    }
  }

  @override
  bool shouldRepaint(covariant _LinePainter old) => old.lines != lines || old.weeks != weeks || old.grid != grid;
}
