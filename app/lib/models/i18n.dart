import '../l10n/strings.dart';
import 'json.dart';

/// 요약류의 두 언어 값 (4주기 FR-39, BR-A50). 서버 응답의 `i18n: {"ko": {...}, "en": {...}}`.
class I18n {
  const I18n([this.values = const {}]);

  final Map<String, Json> values;

  factory I18n.fromJson(Json j) {
    final raw = j['i18n'];
    if (raw is! Map<String, dynamic>) return const I18n();
    return I18n({
      for (final e in raw.entries)
        if (e.value is Map<String, dynamic>) e.key: e.value as Json,
    });
  }

  Json toJson() => values;

  Json? get _current => values[AppLang.code];
  Json? get _other => values[AppLang.english ? 'ko' : 'en'];

  /// 지금 언어 → 다른 언어 → [fallback] (원래 필드) 순으로 고른다.
  T pick<T>(T? Function(Json) read, T fallback) {
    for (final j in [_current, _other]) {
      if (j == null) continue;
      final value = read(j);
      if (value != null) return value;
    }
    return fallback;
  }

  /// 지금 언어 값이 없고 다른 언어 값만 있음 → "번역 준비 중" (BR-A51).
  bool pending(String field) =>
      !(_current?.containsKey(field) ?? false) && (_other?.containsKey(field) ?? false);

  /// [keys] 필드만 남긴다.
  I18n only(List<String> keys) => I18n({
        for (final e in values.entries)
          if (keys.any(e.value.containsKey)) e.key: {for (final k in keys) if (e.value.containsKey(k)) k: e.value[k]},
      });

  /// 필드 이름 바꾸기 (뉴스 요약 → 보관함 한 줄 요약).
  I18n rename(String from, String to) => I18n({
        for (final e in values.entries)
          if (e.value.containsKey(from)) e.key: {to: e.value[from]},
      });
}

String? i18nString(Json j, String key) => strOrNull(j, key);

List<String>? i18nStrings(Json j, String key) => j[key] is List ? strings(j, key) : null;
