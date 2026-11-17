import 'dart:async';
import 'dart:convert';

import 'package:http/http.dart' as http;

import '../models/json.dart';
import '../l10n/strings.dart';

class ApiException implements Exception {
  const ApiException(this.message, {this.status, this.notConfigured = false});

  final String message;
  final int? status;
  final bool notConfigured;

  bool get notFound => status == 404;

  @override
  String toString() => 'ApiException($status): $message';
}

/// 서버 API 의 읽기 경로 하나를 JSON 으로 돌려준다.
abstract class RadarApi {
  Future<Json> getJson(String path);
}

class HttpRadarApi implements RadarApi {
  HttpRadarApi(this.baseUrl, this.client, {this.timeout = const Duration(seconds: 10)});

  final String baseUrl;
  final http.Client client;
  final Duration timeout;

  @override
  Future<Json> getJson(String path) async {
    final http.Response response;
    try {
      response = await client
          .get(Uri.parse('$baseUrl$path'), headers: const {'accept': 'application/json'})
          .timeout(timeout);
    } on TimeoutException {
      throw ApiException(tr('서버 응답이 늦습니다', 'The server is responding slowly'));
    } catch (_) {
      throw ApiException(tr('서버에 연결할 수 없습니다', 'Cannot reach the server'));
    }
    if (response.statusCode != 200) {
      throw ApiException(tr('서버 오류 (${response.statusCode})', 'Server error (${response.statusCode})'),
          status: response.statusCode);
    }
    try {
      final decoded = jsonDecode(utf8.decode(response.bodyBytes));
      if (decoded is Map<String, dynamic>) return decoded;
    } on FormatException {
      // 아래에서 처리
    }
    throw ApiException(tr('응답 형식이 올바르지 않습니다', 'Unexpected response format'));
  }
}
