import 'package:http/http.dart' as http;

import '../models/json.dart';
import '../models/models.dart';
import 'api_client.dart';
import 'cache_store.dart';
import 'settings_store.dart';
import '../l10n/strings.dart';

/// 불러온 값과 출처 (오프라인 여부).
class Loaded<T> {
  const Loaded(this.data, {this.offline = false});

  final T data;
  final bool offline;
}

/// 네트워크 우선, 실패하면 저장본 (BR-A12). 서버 주소가 없으면 설정 안내 (BR-A13).
class RadarRepository {
  RadarRepository({required this.settings, required this.cache, required this.client});

  final SettingsStore settings;
  final CacheStore cache;
  final http.Client client;

  /// BR-A31: 내용 요청에는 언어를 붙인다 (오프라인 저장본도 언어별 경로로 남는다).
  String _localized(String path) {
    final uri = Uri.parse(path);
    return uri.replace(queryParameters: {...uri.queryParameters, 'lang': settings.language}).toString();
  }

  Future<Loaded<T>> _get<T>(String path, T Function(Json) parse, {bool localized = true}) async {
    if (localized) path = _localized(path);
    if (!settings.configured) {
      throw ApiException(tr('설정에서 서버 주소를 입력하세요', 'Enter the server address in Settings'),
          notConfigured: true);
    }
    final api = HttpRadarApi(settings.serverUrl, client);
    try {
      final json = await api.getJson(path);
      await cache.write(path, json);
      return Loaded(parse(json));
    } on ApiException catch (e) {
      final cached = e.notFound ? null : cache.read(path);
      if (cached != null) return Loaded(parse(cached), offline: true);
      rethrow;
    }
  }

  Future<Loaded<Digest>> latestDigest() => _get('/api/v1/digests/latest', Digest.fromJson);

  Future<Loaded<Digest>> digest(String date) => _get('/api/v1/digests/$date', Digest.fromJson);

  Future<Loaded<List<DigestSummary>>> digests() => _get('/api/v1/digests?limit=30', DigestSummary.listFromJson);

  Future<Loaded<PaperWithRelated>> paper(String id) =>
      _get('/api/v1/papers/${Uri.encodeComponent(id)}', PaperWithRelated.fromJson);

  Future<Loaded<SearchResult>> search({
    String query = '',
    Topic? topic,
    DateTime? since,
    bool featuredOnly = false,
    int offset = 0,
    int limit = 20,
  }) {
    final params = <String, String>{
      if (query.trim().isNotEmpty) 'q': query.trim(),
      if (topic != null) 'topic': topic.slug,
      if (since != null) 'since': _day(since),
      if (featuredOnly) 'featured': 'true',
      'limit': '$limit',
      'offset': '$offset',
    };
    return _get(Uri(path: '/api/v1/papers', queryParameters: params).toString(), SearchResult.fromJson);
  }

  /// 뉴스 목록 (FR-27, BR-A22).
  Future<Loaded<NewsList>> news({String query = '', Topic? topic, int offset = 0, int limit = 20}) {
    final params = <String, String>{
      if (query.trim().isNotEmpty) 'q': query.trim(),
      if (topic != null) 'topic': topic.slug,
      'limit': '$limit',
      'offset': '$offset',
    };
    return _get(Uri(path: '/api/v1/news', queryParameters: params).toString(), NewsList.fromJson);
  }

  /// 뉴스 상세. id 에 '/' 가 들어 있으므로 조각마다 인코딩한다.
  Future<Loaded<News>> newsDetail(String id) =>
      _get('/api/v1/news/${id.split('/').map(Uri.encodeComponent).join('/')}', News.fromJson);

  Future<Loaded<Periods>> periods() => _get('/api/v1/trends/periods', Periods.fromJson, localized: false);

  Future<Loaded<TrendReport>> trend(String period, String key) =>
      _get('/api/v1/trends/${period == 'month' ? 'monthly' : 'weekly'}/$key', TrendReport.fromJson);

  Future<Loaded<TopicSeries>> series({int weeks = 12}) =>
      _get('/api/v1/trends/series?weeks=$weeks', TopicSeries.fromJson, localized: false);

  static String _day(DateTime d) =>
      '${d.year.toString().padLeft(4, '0')}-${d.month.toString().padLeft(2, '0')}-${d.day.toString().padLeft(2, '0')}';
}
