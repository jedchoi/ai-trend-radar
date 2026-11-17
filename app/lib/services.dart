import 'package:flutter/widgets.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

import 'data/cache_store.dart';
import 'data/library_store.dart';
import 'data/repository.dart';
import 'data/settings_store.dart';

/// 앱 전체가 쓰는 서비스 묶음 (의존성 주입, NFR-A06).
class AppServices {
  AppServices({required this.settings, required this.library, required this.repository});

  final SettingsStore settings;
  final LibraryStore library;
  final RadarRepository repository;

  /// [serverUrl] 기본값은 빌드 시 `--dart-define=RADAR_SERVER_URL=https://...` 로 줄 수 있다.
  static Future<AppServices> create({http.Client? client}) async {
    final prefs = await SharedPreferences.getInstance();
    const defaultUrl = String.fromEnvironment('RADAR_SERVER_URL');
    final settings = SettingsStore(prefs, defaultServerUrl: defaultUrl);
    return AppServices(
      settings: settings,
      library: LibraryStore(prefs),
      repository: RadarRepository(
        settings: settings,
        cache: CacheStore(prefs),
        client: client ?? http.Client(),
      ),
    );
  }
}

class Services extends InheritedWidget {
  const Services({super.key, required this.services, required super.child});

  final AppServices services;

  static AppServices of(BuildContext context) {
    final widget = context.dependOnInheritedWidgetOfExactType<Services>();
    assert(widget != null, 'Services 가 위젯 트리에 없습니다');
    return widget!.services;
  }

  @override
  bool updateShouldNotify(Services oldWidget) => services != oldWidget.services;
}
