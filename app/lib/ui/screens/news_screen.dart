import 'package:flutter/material.dart';

import '../../data/api_client.dart';
import '../../data/read_store.dart';
import '../../data/repository.dart';
import '../../data/settings_store.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../widgets/common.dart';
import '../widgets/news_widgets.dart';
import 'news_detail_screen.dart';

/// 뉴스 탭 (US-22): Hugging Face 블로그 최신순, 검색, 당겨서 새로고침, 끝까지 내리면 다음 페이지 (BR-A22).
class NewsScreen extends StatefulWidget {
  const NewsScreen({super.key});

  @override
  State<NewsScreen> createState() => _NewsScreenState();
}

class _NewsScreenState extends State<NewsScreen> {
  static const pageSize = 20;
  final _query = TextEditingController();
  final List<NewsBrief> _items = [];
  int _total = 0;
  bool _loading = true;
  bool _offline = false;
  String? _error;
  RadarRepository? _repo;
  SettingsStore? _settings;
  String? _serverUrl;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_repo == null) {
      final services = Services.of(context);
      _repo = services.repository;
      _settings = services.settings;
      _serverUrl = services.settings.serverUrl;
      services.settings.addListener(_onSettings);
      _load();
    }
  }

  void _onSettings() {
    final url = _settings!.serverUrl;
    if (url != _serverUrl) {
      _serverUrl = url;
      _load();
    }
  }

  @override
  void dispose() {
    _settings?.removeListener(_onSettings);
    _query.dispose();
    super.dispose();
  }

  /// 처음 페이지부터 (more = false) 또는 이어서. 빌드 중에 불려도 안전하도록 시작할 때 setState 하지 않는다.
  Future<void> _load({bool more = false}) async {
    if (more && _loading) return;
    _loading = true;
    _error = null;
    if (more && mounted) setState(() {});
    try {
      final result = await _repo!.news(query: _query.text, offset: more ? _items.length : 0, limit: pageSize);
      if (!mounted) return;
      setState(() {
        if (!more) _items.clear();
        _items.addAll(result.data.items);
        _total = result.data.total;
        _offline = result.offline;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.notFound ? '아직 뉴스가 없습니다' : e.message);
    } catch (_) {
      if (mounted) setState(() => _error = '뉴스를 불러오지 못했습니다');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  bool _onScroll(ScrollNotification n) {
    if (n.metrics.extentAfter < 600 && !_loading && _items.length < _total) _load(more: true);
    return false;
  }

  void _open(NewsBrief n) =>
      Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => NewsDetailScreen(newsId: n.id)));

  @override
  Widget build(BuildContext context) {
    final reads = Services.of(context).reads;
    return ListenableBuilder(
      listenable: reads,
      builder: (context, _) => RefreshIndicator(
        onRefresh: _load,
        child: NotificationListener<ScrollNotification>(
          onNotification: _onScroll,
          child: ListView(
            physics: const AlwaysScrollableScrollPhysics(),
            padding: const EdgeInsets.only(bottom: 24),
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
                child: TextField(
                  key: const Key('news-search'),
                  controller: _query,
                  maxLength: 300,
                  textInputAction: TextInputAction.search,
                  onSubmitted: (_) => _load(),
                  decoration: InputDecoration(
                    hintText: '뉴스 검색 (제목 · 요약 · 본문)',
                    prefixIcon: const Icon(Icons.search),
                    counterText: '',
                    border: const OutlineInputBorder(),
                    suffixIcon: IconButton(tooltip: '뉴스 검색', icon: const Icon(Icons.arrow_forward), onPressed: _load),
                  ),
                ),
              ),
              if (_offline) const SourceBanner(offline: true),
              SectionTitle('Hugging Face 소식', subtitle: _total > 0 ? '블로그 글 $_total건 · 최신순' : '블로그 글 · 최신순'),
              if (_error != null && _items.isEmpty) ...[
                EmptyNote(_error!),
                Center(child: FilledButton.tonal(onPressed: _load, child: const Text('다시 시도'))),
              ],
              if (_error == null && !_loading && _items.isEmpty) const EmptyNote('조건에 맞는 뉴스가 없습니다'),
              for (final n in _items)
                NewsTile(news: n, read: reads.isRead(ReadStore.news(n.id)), onTap: () => _open(n)),
              if (_loading)
                const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
              if (!_loading && _items.length < _total)
                Center(child: TextButton(onPressed: () => _load(more: true), child: const Text('더 보기'))),
            ],
          ),
        ),
      ),
    );
  }
}
