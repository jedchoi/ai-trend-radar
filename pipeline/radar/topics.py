"""주제 키워드 규칙 (C-P2, BR-P04).

단어 시작 위치 기준 일치: 'agent' 는 'agents' 와 맞고 'reagent' 와는 안 맞는다.
"""

from __future__ import annotations

import re

from radar.models import Topic

RULES: dict[Topic, list[str]] = {
    Topic.LLM_REASONING: [
        "llm",
        "language model",
        "reasoning",
        "chain-of-thought",
        "mixture of experts",
        "moe",
        "long-context",
        "long context",
        "in-context",
        "decoding",
        "kv cache",
        "kv-cache",
        "test-time",
        "rlhf",
        "alignment",
        "instruction tuning",
        "tokenizer",
        "transformer",
    ],
    Topic.AGENTS: [
        "agent",
        "agentic",
        "tool",
        "function calling",
        "web navigation",
        "computer use",
        "gui",
        "planning",
        "multi-agent",
        "memory",
        "workflow",
        "software engineering",
        "swe-bench",
        "coding assistant",
    ],
    Topic.MULTIMODAL_VISION: [
        "vision",
        "visual",
        "image understanding",
        "vlm",
        "multimodal",
        "multi-modal",
        "vision-language",
        "segmentation",
        "detection",
        "ocr",
        "document understanding",
        "3d",
        "point cloud",
        "depth",
    ],
    Topic.IMAGE_VIDEO_GEN: [
        "diffusion",
        "image generation",
        "video generation",
        "text-to-image",
        "text-to-video",
        "video",
        "image editing",
        "generative",
        "flow matching",
        "autoregressive image",
        "render",
    ],
    Topic.ROBOTICS_PHYSICAL: [
        "robot",
        "robotic",
        "manipulation",
        "embodied",
        "world model",
        "driving",
        "autonomous",
        "vla",
        "vision-language-action",
        "locomotion",
        "physical",
        "simulation",
    ],
    Topic.SPEECH_AUDIO: [
        "speech",
        "audio",
        "text-to-speech",
        "tts",
        "asr",
        "voice",
        "music",
        "sound",
        "spoken",
        "full-duplex",
    ],
    Topic.TRAINING_OPTIMIZATION: [
        "training",
        "pretraining",
        "pre-training",
        "fine-tuning",
        "finetuning",
        "optimizer",
        "quantization",
        "distillation",
        "pruning",
        "efficient",
        "scaling law",
        "reinforcement learning",
        "rl",
        "lora",
        "data curation",
        "synthetic data",
    ],
    Topic.EVALUATION_BENCHMARK: [
        "benchmark",
        "evaluation",
        "leaderboard",
        "arena",
        "eval",
        "dataset",
        "metric",
        "hallucination",
        "reliability",
        "robustness",
        "safety",
        "red teaming",
    ],
}
ORDER = list(Topic)
ABSTRACT_CHARS = 600

_PATTERNS = {topic: [re.compile(r"(?<![a-z0-9])" + re.escape(p)) for p in phrases] for topic, phrases in RULES.items()}


def _hits(patterns: list[re.Pattern[str]], text: str) -> int:
    return sum(1 for p in patterns if p.search(text))


def classify(title: str, keywords: list[str], abstract: str) -> Topic:
    title_l = title.lower()
    keywords_l = " | ".join(k.lower() for k in keywords)
    abstract_l = abstract[:ABSTRACT_CHARS].lower()
    best, best_score = Topic.OTHER, 0
    for topic in ORDER:
        if topic is Topic.OTHER:
            continue
        patterns = _PATTERNS[topic]
        score = 2 * _hits(patterns, title_l) + 2 * _hits(patterns, keywords_l) + _hits(patterns, abstract_l)
        if score > best_score:
            best, best_score = topic, score
    return best
