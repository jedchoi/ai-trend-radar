import 'package:ai_trend_radar/data/api_client.dart';
import 'package:ai_trend_radar/data/cache_store.dart';
import 'package:ai_trend_radar/data/repository.dart';
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

import 'helpers.dart';

Future<RadarRepository> repo(http.Client client, {String url = testServer}) async {
  SharedPreferences.setMockInitialValues({'settings:server_url': url});
  final prefs = await SharedPreferences.getInstance();
  return RadarRepository(settings: SettingsStore(prefs), cache: CacheStore(prefs), client: client);
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('성공하면 저장하고 오프라인 아님 (BR-A12)', () async {
    final r = await repo(sampleServer());
    final loaded = await r.latestDigest();
    expect(loaded.offline, isFalse);
    expect(loaded.data.date, '2026-11-13');
    expect(r.cache.read('/api/v1/digests/latest'), isNotNull);
  });

  test('실패하면 저장본을 오프라인으로 (AC-14-1)', () async {
    final r = await repo(sampleServer());
    await r.latestDigest();
    final offline = RadarRepository(settings: r.settings, cache: r.cache, client: sampleServer(failWith: 503));
    final loaded = await offline.latestDigest();
    expect(loaded.offline, isTrue);
    expect(loaded.data.papers, isNotEmpty);
  });

  test('저장본도 없으면 오류 (AC-14-2)', () async {
    final r = await repo(sampleServer(failWith: 500));
    expect(r.latestDigest(), throwsA(isA<ApiException>()));
  });

  test('네트워크 예외도 ApiException', () async {
    final r = await repo(MockClient((_) async => throw Exception('down')));
    expect(r.digests(), throwsA(isA<ApiException>()));
  });

  test('404 는 저장본을 쓰지 않는다', () async {
    final r = await repo(sampleServer());
    await r.trend('week', '2026-W46');
    final gone = RadarRepository(settings: r.settings, cache: r.cache, client: sampleServer(failWith: 404));
    expect(gone.trend('week', '2026-W46'), throwsA(isA<ApiException>().having((e) => e.notFound, 'notFound', true)));
  });

  test('검색 질의 구성 (BR-A10)', () async {
    final requests = <String>[];
    final r = await repo(sampleServer(requests: requests));
    await r.search(query: ' agent memory ', topic: Topic.agents, since: DateTime(2026, 11, 1), featuredOnly: true,
        offset: 20);
    final uri = Uri.parse(requests.single);
    expect(uri.path, '/api/v1/papers');
    expect(uri.queryParameters, {
      'q': 'agent memory',
      'topic': 'agents',
      'since': '2026-11-01',
      'featured': 'true',
      'limit': '20',
      'offset': '20',
    });
  });

  test('주소가 없으면 네트워크 없이 설정 안내 (BR-A13)', () async {
    final r = await repo(MockClient((_) async => throw StateError('네트워크를 쓰면 안 됨')), url: '');
    expect(r.latestDigest(), throwsA(isA<ApiException>().having((e) => e.notConfigured, 'notConfigured', true)));
  });
}
