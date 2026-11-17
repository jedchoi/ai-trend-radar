/// 한국어 · 영어 (3주기, BR-A32). 화면 글자는 [tr] 로 두 값을 같이 둔다.
///
/// 언어는 [SettingsStore] 가 정하고, 바뀌면 앱 전체를 다시 그린다 (`app.dart` 의 `LanguageRebuilder`).
library;

class AppLang {
  AppLang._();

  /// true = 영어, false = 한국어 (기본).
  static bool english = false;

  /// 서버 요청에 붙이는 값 (BR-A31).
  static String get code => english ? 'en' : 'ko';
}

/// 지금 언어의 글자.
String tr(String ko, String en) => AppLang.english ? en : ko;
