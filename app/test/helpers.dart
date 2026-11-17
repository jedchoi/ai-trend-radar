import 'dart:convert';
import 'dart:io';

import 'package:ai_trend_radar/app.dart';
import 'package:ai_trend_radar/data/cache_store.dart';
import 'package:ai_trend_radar/data/library_store.dart';
import 'package:ai_trend_radar/data/read_store.dart';
import 'package:ai_trend_radar/data/repository.dart';
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/services.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:http/http.dart' as http;
import 'package:http/testing.dart';
import 'package:shared_preferences/shared_preferences.dart';

const testServer = 'https://radar.test';

/// 예시 응답 (서버가 만든 실제 응답 형식, `server/tools/make_samples.py` → contract/samples).
Map<String, dynamic> sample(String name) =>
    jsonDecode(File('../contract/samples/$name.json').readAsStringSync()) as Map<String, dynamic>;

http.Response jsonResponse(Object body, [int status = 200]) => http.Response.bytes(
      utf8.encode(jsonEncode(body)),
      status,
      headers: {'content-type': 'application/json; charset=utf-8'},
    );

/// 언어별 예시가 있으면 그것 (예: paper_detail_ko), 없으면 기본 예시 (BR-S40 의 번역 없음과 같음).
Map<String, dynamic> localizedSample(String name, String? lang) {
  if (lang != null && File('../contract/samples/${name}_$lang.json').existsSync()) return sample('${name}_$lang');
  return sample(name);
}

/// 경로별로 예시 응답을 돌려주는 가짜 서버. [requests] 에 요청 경로를 남긴다.
MockClient sampleServer({List<String>? requests, int? failWith}) {
  return MockClient((request) async {
    final path = request.url.path;
    final lang = request.url.queryParameters['lang'];
    Map<String, dynamic> sample(String name) => localizedSample(name, lang);
    requests?.add(request.url.toString().replaceFirst(testServer, ''));
    if (failWith != null) return jsonResponse({'error': 'x'}, failWith);
    if (path == '/api/v1/digests') return jsonResponse(sample('digests'));
    if (path.startsWith('/api/v1/digests/')) return jsonResponse(sample('digest_latest'));
    if (path == '/api/v1/papers') return jsonResponse(sample('search'));
    if (path.startsWith('/api/v1/papers/')) {
      final id = path.substring('/api/v1/papers/'.length);
      final detail = sample('paper_detail');
      if ((detail['paper'] as Map)['id'] == id) return jsonResponse(detail);
      final papers = (sample('digest_latest')['papers'] as List).cast<Map<String, dynamic>>();
      final match = papers.where((p) => p['id'] == id).toList();
      if (match.isEmpty) return jsonResponse({'error': 'not_found'}, 404);
      return jsonResponse({'paper': match.first, 'related': []});
    }
    if (path == '/api/v1/news') return jsonResponse(sample('news_list'));
    if (path.startsWith('/api/v1/news/')) {
      final id = Uri.decodeComponent(path.substring('/api/v1/news/'.length));
      final detail = sample('news_detail');
      if (detail['id'] == id) return jsonResponse(detail);
      final items = (sample('news_list')['items'] as List).cast<Map<String, dynamic>>();
      final match = items.where((n) => n['id'] == id).toList();
      if (match.isEmpty) return jsonResponse({'error': 'not_found'}, 404);
      return jsonResponse({
        ...match.first,
        'authors': <String>[],
        'content': '(예시 본문)',
        'key_points': <String>[],
        'summary_source': 'ai',
        'provider': 'anthropic',
      });
    }
    if (path == '/api/v1/trends/periods') return jsonResponse(sample('trend_periods'));
    if (path == '/api/v1/trends/series') return jsonResponse(sample('trend_series'));
    if (path.startsWith('/api/v1/trends/weekly/')) return jsonResponse(sample('trend_weekly'));
    if (path.startsWith('/api/v1/trends/monthly/')) return jsonResponse(sample('trend_monthly'));
    return jsonResponse({'error': 'not_found'}, 404);
  });
}

Future<AppServices> makeServices({
  http.Client? client,
  Map<String, Object> prefs = const {'settings:server_url': testServer},
}) async {
  SharedPreferences.setMockInitialValues(prefs);
  final p = await SharedPreferences.getInstance();
  final settings = SettingsStore(p);
  return AppServices(
    settings: settings,
    library: LibraryStore(p),
    reads: ReadStore(p),
    repository: RadarRepository(settings: settings, cache: CacheStore(p), client: client ?? sampleServer()),
  );
}

/// 큰 화면 (세로로 긴 휴대폰) 에서 앱을 띄운다.
Future<AppServices> pumpApp(WidgetTester tester, {AppServices? services, double textScale = 1.0}) async {
  tester.view.physicalSize = const Size(1080, 3200);
  tester.view.devicePixelRatio = 2.0;
  tester.platformDispatcher.textScaleFactorTestValue = textScale;
  addTearDown(tester.view.reset);
  addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);
  final s = services ?? await makeServices();
  await tester.pumpWidget(RadarApp(services: s));
  await tester.pumpAndSettle();
  return s;
}
