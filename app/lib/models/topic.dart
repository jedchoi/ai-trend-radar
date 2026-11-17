import 'package:flutter/material.dart';
import '../l10n/strings.dart';

/// 고정 주제 9개 (services.md). 서버 slug 와 같다.
enum Topic {
  llmReasoning('llm-reasoning', 'LLM · 추론', 'LLM · Reasoning', Color(0xFF5B5BD6)),
  agents('agents', '에이전트', 'Agents', Color(0xFF0E9F8C)),
  multimodalVision('multimodal-vision', '멀티모달 · 비전', 'Multimodal · Vision', Color(0xFFE5793B)),
  imageVideoGen('image-video-gen', '이미지 · 영상 생성', 'Image · Video Gen', Color(0xFFD6457A)),
  roboticsPhysical('robotics-physical', '로보틱스 · 피지컬 AI', 'Robotics · Physical AI', Color(0xFF7A8C1E)),
  speechAudio('speech-audio', '음성 · 오디오', 'Speech · Audio', Color(0xFF2F86D6)),
  trainingOptimization('training-optimization', '학습 · 최적화', 'Training · Optimization', Color(0xFF9B59B6)),
  evaluationBenchmark('evaluation-benchmark', '평가 · 벤치마크', 'Evaluation · Benchmarks', Color(0xFFB8860B)),
  other('other', '기타', 'Other', Color(0xFF7D8590));

  const Topic(this.slug, this.labelKo, this.labelEn, this.color);

  final String slug;
  final String labelKo;
  final String labelEn;
  final Color color;

  String get label => tr(labelKo, labelEn);

  static Topic fromSlug(String? slug) =>
      Topic.values.firstWhere((t) => t.slug == slug, orElse: () => Topic.other);
}
