import 'package:flutter/material.dart';

import '../../data/api_client.dart';
import '../../logic/interest_ranker.dart';
import '../../models/models.dart';
import '../../services.dart';
import '../widgets/common.dart';
import '../widgets/paper_widgets.dart';
import 'paper_screen.dart';
import '../../l10n/strings.dart';

enum SearchPeriod {
  week('최근 7일', 'Last 7 days', 7),
  month('최근 30일', 'Last 30 days', 30),
  all('전체', 'All time', null);

  const SearchPeriod(this.labelKo, this.labelEn, this.days);

  final String labelKo;
  final String labelEn;
  final int? days;

  String get label => tr(labelKo, labelEn);
}

/// 검색 (US-12, BR-A10).
class SearchScreen extends StatefulWidget {
  const SearchScreen({super.key});

  @override
  State<SearchScreen> createState() => _SearchScreenState();
}

class _SearchScreenState extends State<SearchScreen> {
  static const pageSize = 20;
  final _query = TextEditingController();
  Topic? _topic;
  SearchPeriod _period = SearchPeriod.all;
  bool _featuredOnly = false;
  final List<PaperBrief> _items = [];
  int _total = 0;
  bool _loading = false;
  bool _searched = false;
  bool _offline = false;
  String? _error;

  @override
  void dispose() {
    _query.dispose();
    super.dispose();
  }

  Future<void> _search({bool more = false}) async {
    final repo = Services.of(context).repository;
    final days = _period.days;
    setState(() {
      _loading = true;
      _error = null;
      if (!more) _items.clear();
    });
    try {
      final result = await repo.search(
        query: _query.text,
        topic: _topic,
        since: days == null ? null : DateTime.now().subtract(Duration(days: days)),
        featuredOnly: _featuredOnly,
        offset: more ? _items.length : 0,
        limit: pageSize,
      );
      if (!mounted) return;
      setState(() {
        _items.addAll(result.data.items);
        _total = result.data.total;
        _offline = result.offline;
        _searched = true;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } catch (_) {
      if (mounted) setState(() => _error = tr('검색하지 못했습니다', 'Search failed'));
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final interests = Services.of(context).settings.interests;
    final items = rankByInterest(_items, (PaperBrief p) => briefInterests(p, interests).isNotEmpty);
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: TextField(
            controller: _query,
            maxLength: 300,
            textInputAction: TextInputAction.search,
            onSubmitted: (_) => _search(),
            decoration: InputDecoration(
              hintText: tr('논문 제목 · 요약 · 키워드 검색 (예: agent memory)', 'Search titles · summaries · keywords (e.g. agent memory)'),
              prefixIcon: const Icon(Icons.search),
              counterText: '',
              border: const OutlineInputBorder(),
              suffixIcon: IconButton(tooltip: tr('검색', 'Search'), icon: const Icon(Icons.arrow_forward), onPressed: _search),
            ),
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16),
          child: Wrap(spacing: 6, runSpacing: 6, crossAxisAlignment: WrapCrossAlignment.center, children: [
            for (final p in SearchPeriod.values)
              ChoiceChip(
                label: Text(p.label),
                selected: _period == p,
                onSelected: (_) {
                  setState(() => _period = p);
                  if (_searched) _search();
                },
              ),
            FilterChip(
              label: Text(tr('주목만', 'Featured only')),
              selected: _featuredOnly,
              onSelected: (v) {
                setState(() => _featuredOnly = v);
                if (_searched) _search();
              },
            ),
            PopupMenuButton<String>(
              tooltip: tr('주제 고르기', 'Choose a topic'),
              onSelected: (slug) {
                setState(() => _topic = slug.isEmpty ? null : Topic.fromSlug(slug));
                if (_searched) _search();
              },
              itemBuilder: (context) => [
                PopupMenuItem<String>(value: '', child: Text(tr('모든 주제', 'All topics'))),
                for (final t in Topic.values) PopupMenuItem<String>(value: t.slug, child: Text(t.label)),
              ],
              child: Chip(
                avatar: const Icon(Icons.filter_list, size: 16),
                label: Text(_topic?.label ?? tr('모든 주제', 'All topics')),
              ),
            ),
          ]),
        ),
        if (_offline) const SourceBanner(offline: true),
        if (_error != null) EmptyNote(_error!),
        if (_searched && !_loading && _items.isEmpty && _error == null) EmptyNote(tr('결과 없음', 'No results')),
        if (!_searched && !_loading)
          EmptyNote(tr('검색어를 넣거나 필터만 고른 뒤 검색하면 지난 논문을 찾을 수 있습니다.',
              'Enter a query or pick filters, then search to find past papers.')),
        if (_searched && _items.isNotEmpty)
          SectionTitle(tr('검색 결과', 'Results'), subtitle: tr('$_total편', '$_total papers')),
        for (final p in items)
          PaperRow.brief(
            p,
            interests: briefInterests(p, interests),
            onTap: () =>
                Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => PaperScreen(paperId: p.id))),
          ),
        if (_loading) const Padding(padding: EdgeInsets.all(24), child: Center(child: CircularProgressIndicator())),
        if (!_loading && _items.length < _total)
          Center(child: TextButton(onPressed: () => _search(more: true), child: Text(tr('더 보기', 'More')))),
      ],
    );
  }
}
