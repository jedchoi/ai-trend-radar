import 'package:flutter/material.dart';

/// 고정 주제 9개 (services.md). 서버 slug 와 같다.
enum Topic {
  llmReasoning('llm-reasoning', 'LLM · 추론', Color(0xFF5B5BD6)),
  agents('agents', '에이전트', Color(0xFF0E9F8C)),
  multimodalVision('multimodal-vision', '멀티모달 · 비전', Color(0xFFE5793B)),
  imageVideoGen('image-video-gen', '이미지 · 영상 생성', Color(0xFFD6457A)),
  roboticsPhysical('robotics-physical', '로보틱스 · 피지컬 AI', Color(0xFF7A8C1E)),
  speechAudio('speech-audio', '음성 · 오디오', Color(0xFF2F86D6)),
  trainingOptimization('training-optimization', '학습 · 최적화', Color(0xFF9B59B6)),
  evaluationBenchmark('evaluation-benchmark', '평가 · 벤치마크', Color(0xFFB8860B)),
  other('other', '기타', Color(0xFF7D8590));

  const Topic(this.slug, this.label, this.color);

  final String slug;
  final String label;
  final Color color;

  static Topic fromSlug(String? slug) =>
      Topic.values.firstWhere((t) => t.slug == slug, orElse: () => Topic.other);
}
