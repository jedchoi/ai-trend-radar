import 'package:flutter/foundation.dart';

import '../data/api_client.dart';
import '../data/repository.dart';

enum LoadStatus { loading, ready, error }

/// 화면 하나의 불러오기 상태 (C-A10).
class LoadController<T> extends ChangeNotifier {
  LoadController(this._loader);

  Future<Loaded<T>> Function() _loader;
  LoadStatus status = LoadStatus.loading;
  T? data;
  bool offline = false;
  bool demo = false;
  String? error;
  int _generation = 0;
  bool _disposed = false;

  Future<void> load([Future<Loaded<T>> Function()? loader]) async {
    if (loader != null) _loader = loader;
    final generation = ++_generation;
    status = LoadStatus.loading;
    error = null;
    _notify();
    try {
      final result = await _loader();
      if (generation != _generation) return; // 더 최근 요청이 있음
      data = result.data;
      offline = result.offline;
      demo = result.demo;
      status = LoadStatus.ready;
    } on ApiException catch (e) {
      if (generation != _generation) return;
      error = e.notFound ? '아직 데이터가 없습니다' : e.message;
      status = LoadStatus.error;
    } catch (_) {
      if (generation != _generation) return;
      error = '데이터를 불러오지 못했습니다';
      status = LoadStatus.error;
    }
    _notify();
  }

  void _notify() {
    if (!_disposed) notifyListeners();
  }

  @override
  void dispose() {
    _disposed = true;
    super.dispose();
  }
}
