import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// AI 에게 묻기 대상 (BR-A08).
enum AskTarget {
  claude('Claude', 'https://claude.ai/new'),
  chatgpt('ChatGPT', 'https://chatgpt.com/'),
  gemini('Gemini', 'https://gemini.google.com/app');

  const AskTarget(this.label, this.url);

  final String label;
  final String url;

  static AskTarget fromName(String? name) =>
      AskTarget.values.firstWhere((t) => t.name == name, orElse: () => AskTarget.claude);
}

class SettingsStore extends ChangeNotifier {
  SettingsStore(this.prefs, {String defaultServerUrl = ''})
      : _serverUrl = prefs.getString(_kServer) ?? defaultServerUrl,
        _interests = List.of(prefs.getStringList(_kInterests) ?? const <String>[]),
        _askTarget = AskTarget.fromName(prefs.getString(_kAsk));

  static const _kServer = 'settings:server_url';
  static const _kInterests = 'settings:interests';
  static const _kAsk = 'settings:ask_target';
  static const maxInterests = 20;
  static const maxInterestLength = 30;

  final SharedPreferences prefs;
  String _serverUrl;
  List<String> _interests;
  AskTarget _askTarget;

  String get serverUrl => _serverUrl;
  bool get configured => _serverUrl.isNotEmpty;
  List<String> get interests => List.unmodifiable(_interests);
  AskTarget get askTarget => _askTarget;

  /// BR-A13: 빈 값 = 미설정, 아니면 http(s) 주소만. 저장하면 null, 거부하면 이유를 돌려준다.
  Future<String?> setServerUrl(String value) async {
    var url = value.trim();
    while (url.endsWith('/')) {
      url = url.substring(0, url.length - 1);
    }
    if (url.isNotEmpty) {
      final uri = Uri.tryParse(url);
      final ok = uri != null && (uri.scheme == 'https' || uri.scheme == 'http') && uri.host.isNotEmpty;
      if (!ok || url.length > 300) return 'http:// 또는 https:// 로 시작하는 주소를 입력하세요';
    }
    _serverUrl = url;
    await prefs.setString(_kServer, url);
    notifyListeners();
    return null;
  }

  /// BR-A06: 1~30자, 최대 20개, 대소문자 무시 중복 금지. 추가하면 true.
  Future<bool> addInterest(String value) async {
    final word = value.trim();
    if (word.isEmpty || word.length > maxInterestLength || _interests.length >= maxInterests) return false;
    if (_interests.any((w) => w.toLowerCase() == word.toLowerCase())) return false;
    _interests = [..._interests, word];
    await prefs.setStringList(_kInterests, _interests);
    notifyListeners();
    return true;
  }

  Future<void> removeInterest(String value) async {
    _interests = _interests.where((w) => w != value).toList();
    await prefs.setStringList(_kInterests, _interests);
    notifyListeners();
  }

  Future<void> setAskTarget(AskTarget target) async {
    _askTarget = target;
    await prefs.setString(_kAsk, target.name);
    notifyListeners();
  }
}
