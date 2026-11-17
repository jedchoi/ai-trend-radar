/// 너그러운 JSON 읽기 (NFR-A02): 타입이 틀리거나 없는 필드는 기본값으로 둔다.
library;

typedef Json = Map<String, dynamic>;

String str(Json j, String key, [String fallback = '']) {
  final v = j[key];
  return v is String ? v : fallback;
}

String? strOrNull(Json j, String key) {
  final v = j[key];
  return v is String && v.isNotEmpty ? v : null;
}

int integer(Json j, String key, [int fallback = 0]) {
  final v = j[key];
  if (v is int) return v;
  if (v is num) return v.toInt();
  return fallback;
}

int? intOrNull(Json j, String key) {
  final v = j[key];
  return v is num ? v.toInt() : null;
}

double dbl(Json j, String key, [double fallback = 0]) {
  final v = j[key];
  return v is num ? v.toDouble() : fallback;
}

bool boolean(Json j, String key, [bool fallback = false]) {
  final v = j[key];
  return v is bool ? v : fallback;
}

List<String> strings(Json j, String key) {
  final v = j[key];
  if (v is! List) return const [];
  return v.whereType<String>().toList(growable: false);
}

Json obj(Json j, String key) {
  final v = j[key];
  return v is Map<String, dynamic> ? v : <String, dynamic>{};
}

Json? objOrNull(Json j, String key) {
  final v = j[key];
  return v is Map<String, dynamic> ? v : null;
}

List<T> list<T>(Json j, String key, T Function(Json) parse) {
  final v = j[key];
  if (v is! List) return const [];
  return v.whereType<Map<String, dynamic>>().map(parse).toList(growable: false);
}

DateTime? date(Json j, String key) {
  final v = j[key];
  return v is String ? DateTime.tryParse(v) : null;
}
