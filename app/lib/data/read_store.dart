import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// 읽음 표시 (BR-A23): 상세를 연 논문 · 뉴스. 최대 [maxItems] 개, 넘으면 오래된 것부터 지운다.
class ReadStore extends ChangeNotifier {
  ReadStore(this.prefs) {
    _ids.addAll(prefs.getStringList(_key) ?? const <String>[]);
  }

  static const _key = 'read:ids';
  static const maxItems = 5000;

  static String paper(String id) => 'p:$id';
  static String news(String id) => 'n:$id';

  final SharedPreferences prefs;
  final Set<String> _ids = <String>{}; // 넣은 순서 유지 (LinkedHashSet)

  int get length => _ids.length;

  bool isRead(String key) => _ids.contains(key);

  Future<void> mark(String key) async {
    if (_ids.contains(key)) return;
    _ids.add(key);
    while (_ids.length > maxItems) {
      _ids.remove(_ids.first);
    }
    notifyListeners();
    await prefs.setStringList(_key, _ids.toList(growable: false));
  }
}
