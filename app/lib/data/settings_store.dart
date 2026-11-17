import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';
import '../l10n/strings.dart';

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
  /// BR-A20: 사용자가 저장한 주소 > 빌드 시 넣은 주소 ([defaultServerUrl], `--dart-define=RADAR_SERVER_URL`).
  SettingsStore(this.prefs, {String defaultServerUrl = ''})
      : _defaultServerUrl = defaultServerUrl,
        _serverUrl = _orDefault(prefs.getString(_kServer), defaultServerUrl),
        _interests = List.of(prefs.getStringList(_kInterests) ?? const <String>[]),
        _askTarget = AskTarget.fromName(prefs.getString(_kAsk)),
        _textScale = _validScale(prefs.getDouble(_kTextScale)),
        _language = prefs.getString(_kLanguage) == 'en' ? 'en' : 'ko' {
    AppLang.english = _language == 'en';
  }

  static const _kServer = 'settings:server_url';
  static const _kInterests = 'settings:interests';
  static const _kAsk = 'settings:ask_target';
  static const _kTextScale = 'settings:text_scale';
  static const _kLanguage = 'settings:language';

  /// BR-A25: 글자 크기 배율.
  static const textScales = <double>[0.9, 1.0, 1.15, 1.3];

  static String _orDefault(String? saved, String fallback) => (saved == null || saved.isEmpty) ? fallback : saved;

  static double _validScale(double? value) => textScales.contains(value) ? value! : 1.0;
  static const maxInterests = 20;
  static const maxInterestLength = 30;

  final SharedPreferences prefs;
  final String _defaultServerUrl;
  String _serverUrl;
  List<String> _interests;
  AskTarget _askTarget;
  double _textScale;
  String _language;

  String get serverUrl => _serverUrl;

  /// BR-A30: 'ko' (기본) · 'en'.
  String get language => _language;

  /// 내용을 다시 받아야 하는지 판단하는 값. 언어는 포함하지 않는다 (응답에 두 언어가 함께 옴, BR-A51).
  String get sourceKey => _serverUrl;
  String get defaultServerUrl => _defaultServerUrl;
  double get textScale => _textScale;
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
      if (!ok || url.length > 300) {
        return tr('http:// 또는 https:// 로 시작하는 주소를 입력하세요', 'Enter an address starting with http:// or https://');
      }
    }
    _serverUrl = _orDefault(url, _defaultServerUrl);
    await prefs.setString(_kServer, url);
    notifyListeners();
    return null;
  }

  Future<void> setLanguage(String value) async {
    final lang = value == 'en' ? 'en' : 'ko';
    if (lang == _language) return;
    _language = lang;
    AppLang.english = lang == 'en';
    await prefs.setString(_kLanguage, lang);
    notifyListeners();
  }

  Future<void> toggleLanguage() => setLanguage(_language == 'en' ? 'ko' : 'en');

  Future<void> setTextScale(double value) async {
    _textScale = _validScale(value);
    await prefs.setDouble(_kTextScale, _textScale);
    notifyListeners();
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
