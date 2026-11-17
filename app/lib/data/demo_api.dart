import 'dart:convert';

import 'package:flutter/services.dart';

import '../models/json.dart';
import 'api_client.dart';

/// 서버 주소가 없을 때 쓰는 데모 (BR-A13): 앱에 포함한 예시 응답 (`contract/samples` 복사본).
class DemoRadarApi implements RadarApi {
  DemoRadarApi({AssetBundle? bundle}) : bundle = bundle ?? rootBundle;

  final AssetBundle bundle;

  Future<Json> _asset(String name) async =>
      jsonDecode(await bundle.loadString('assets/demo/$name.json')) as Map<String, dynamic>;

  @override
  Future<Json> getJson(String path) async {
    final uri = Uri.parse(path);
    final p = uri.path;
    if (p == '/api/v1/digests') return _asset('digests');
    if (p.startsWith('/api/v1/digests/')) return _asset('digest_latest');
    if (p.startsWith('/api/v1/papers/')) return _paper(p.substring('/api/v1/papers/'.length));
    if (p == '/api/v1/papers') return _search(uri.queryParameters);
    if (p == '/api/v1/trends/periods') return _asset('trend_periods');
    if (p == '/api/v1/trends/series') return _asset('trend_series');
    if (p.startsWith('/api/v1/trends/weekly/')) return _asset('trend_weekly');
    if (p.startsWith('/api/v1/trends/monthly/')) return _asset('trend_monthly');
    throw const ApiException('데모에 없는 경로', status: 404);
  }

  Future<Json> _paper(String id) async {
    final detail = await _asset('paper_detail');
    if ((detail['paper'] as Map<String, dynamic>)['id'] == id) return detail;
    final digest = await _asset('digest_latest');
    final papers = (digest['papers'] as List).cast<Map<String, dynamic>>();
    final match = papers.where((p) => p['id'] == id);
    if (match.isEmpty) throw const ApiException('없는 논문', status: 404);
    return {'paper': match.first, 'related': <Json>[]};
  }

  Future<Json> _search(Map<String, String> params) async {
    final digest = await _asset('digest_latest');
    final q = (params['q'] ?? '').toLowerCase().trim();
    final topic = params['topic'];
    final featuredOnly = params['featured'] == 'true';
    final papers = (digest['papers'] as List).cast<Map<String, dynamic>>().where((p) {
      final text = '${p['title']} ${p['one_liner']} ${(p['keywords'] as List).join(' ')}'.toLowerCase();
      return (q.isEmpty || q.split(RegExp(r'\s+')).every(text.contains)) &&
          (topic == null || p['topic'] == topic) &&
          (!featuredOnly || p['featured'] == true);
    }).toList();
    return {'items': papers, 'total': papers.length};
  }
}
