import '../models/models.dart';

/// BR-A05: 관심 키워드 매칭 (대소문자 무시 부분 일치).
List<String> matchInterests(
  List<String> interests, {
  required String title,
  required String oneLiner,
  required Topic topic,
  List<String> keywords = const [],
}) {
  final haystack = [title, oneLiner, topic.label, ...keywords].join('\n').toLowerCase();
  return interests.where((w) => w.trim().isNotEmpty && haystack.contains(w.trim().toLowerCase())).toList();
}

List<String> paperInterests(Paper p, List<String> interests) =>
    matchInterests(interests, title: p.title, oneLiner: p.oneLiner, topic: p.topic, keywords: p.keywords);

List<String> briefInterests(PaperBrief p, List<String> interests) =>
    matchInterests(interests, title: p.title, oneLiner: p.oneLiner, topic: p.topic);

/// 매칭된 항목을 위로 올리되 각 그룹 안의 원래 순서는 유지한다 (안정 정렬).
List<T> rankByInterest<T>(List<T> items, bool Function(T) matches) {
  final hit = <T>[];
  final rest = <T>[];
  for (final item in items) {
    (matches(item) ? hit : rest).add(item);
  }
  return [...hit, ...rest];
}
