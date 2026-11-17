import 'dart:convert';

import 'package:shared_preferences/shared_preferences.dart';

import '../models/json.dart';

/// 경로별 마지막 응답 (BR-A12).
class CacheStore {
  CacheStore(this.prefs);

  static const _prefix = 'cache:';

  /// 원문이 든 큰 응답은 저장하지 않는다 (기기 저장소 보호).
  static const maxChars = 300000;
  final SharedPreferences prefs;

  Json? read(String path) {
    final raw = prefs.getString('$_prefix$path');
    if (raw == null) return null;
    try {
      final decoded = jsonDecode(raw);
      return decoded is Map<String, dynamic> ? decoded : null;
    } on FormatException {
      return null;
    }
  }

  Future<void> write(String path, Json json) async {
    final text = jsonEncode(json);
    if (text.length > maxChars) return;
    await prefs.setString('$_prefix$path', text);
  }
}
