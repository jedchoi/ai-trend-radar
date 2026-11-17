import 'dart:convert';

import 'package:flutter/foundation.dart';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/models.dart';

/// 보관함 상태 (BR-A11).
enum LibraryStatus {
  toRead('읽을 것'),
  trying('시험 중'),
  applied('적용함'),
  onHold('보류');

  const LibraryStatus(this.label);

  final String label;

  static LibraryStatus fromName(String? name) =>
      LibraryStatus.values.firstWhere((s) => s.name == name, orElse: () => LibraryStatus.toRead);
}

/// 보관 항목 종류 (BR-A26): 논문 · 뉴스. 뉴스도 [PaperBrief] 모양으로 저장한다 (요약 = oneLiner).
enum LibraryKind {
  paper,
  news;

  static LibraryKind fromName(String? name) =>
      LibraryKind.values.firstWhere((k) => k.name == name, orElse: () => LibraryKind.paper);
}

class LibraryEntry {
  const LibraryEntry({
    required this.paper,
    required this.status,
    required this.note,
    required this.savedAt,
    this.kind = LibraryKind.paper,
  });

  final PaperBrief paper;
  final LibraryStatus status;
  final String note;
  final DateTime savedAt;
  final LibraryKind kind;

  /// 저장 키: 논문은 id 그대로 (1주기 저장본과 호환), 뉴스는 'news:' 접두.
  String get key => libraryKey(paper.id, kind);

  LibraryEntry copyWith({LibraryStatus? status, String? note}) => LibraryEntry(
      paper: paper, status: status ?? this.status, note: note ?? this.note, savedAt: savedAt, kind: kind);

  Map<String, dynamic> toJson() => {
        'paper': paper.toJson(),
        'status': status.name,
        'note': note,
        'saved_at': savedAt.toIso8601String(),
        'kind': kind.name,
      };

  static LibraryEntry? fromJson(Map<String, dynamic> j) {
    final paper = j['paper'];
    if (paper is! Map<String, dynamic>) return null;
    return LibraryEntry(
      paper: PaperBrief.fromJson(paper),
      status: LibraryStatus.fromName(j['status'] as String?),
      note: j['note'] is String ? j['note'] as String : '',
      savedAt: DateTime.tryParse(j['saved_at'] as String? ?? '') ?? DateTime.fromMillisecondsSinceEpoch(0),
      kind: LibraryKind.fromName(j['kind'] is String ? j['kind'] as String : null),
    );
  }
}

String libraryKey(String id, LibraryKind kind) => kind == LibraryKind.news ? 'news:$id' : id;

/// 뉴스를 보관함 항목 모양으로.
PaperBrief newsAsBrief(NewsBrief n) => PaperBrief(
      id: n.id,
      title: n.title,
      date: n.day,
      topic: n.topic,
      oneLiner: n.summary,
      upvotes: 0,
      featured: false,
    );

class LibraryStore extends ChangeNotifier {
  LibraryStore(this.prefs, {DateTime Function()? clock}) : _clock = clock ?? DateTime.now {
    _load();
  }

  static const _key = 'library:entries';
  static const maxNote = 1000;

  final SharedPreferences prefs;
  final DateTime Function() _clock;
  final Map<String, LibraryEntry> _entries = {};

  void _load() {
    final raw = prefs.getString(_key);
    if (raw == null) return;
    try {
      final list = jsonDecode(raw);
      if (list is! List) return;
      for (final item in list.whereType<Map<String, dynamic>>()) {
        final entry = LibraryEntry.fromJson(item);
        if (entry != null) _entries[entry.key] = entry;
      }
    } on FormatException {
      // 손상된 저장본은 무시
    }
  }

  Future<void> _save() async {
    await prefs.setString(_key, jsonEncode(_entries.values.map((e) => e.toJson()).toList()));
    notifyListeners();
  }

  bool contains(String id, {LibraryKind kind = LibraryKind.paper}) => _entries.containsKey(libraryKey(id, kind));

  LibraryEntry? entry(String id, {LibraryKind kind = LibraryKind.paper}) => _entries[libraryKey(id, kind)];

  /// 최근 저장 먼저, [status] 가 있으면 그 상태만.
  List<LibraryEntry> items({LibraryStatus? status}) {
    final list = _entries.values.where((e) => status == null || e.status == status).toList()
      ..sort((a, b) => b.savedAt.compareTo(a.savedAt));
    return list;
  }

  /// 저장 상태를 뒤집고, 저장됐으면 true.
  Future<bool> toggle(PaperBrief paper, {LibraryKind kind = LibraryKind.paper}) async {
    final key = libraryKey(paper.id, kind);
    if (_entries.remove(key) == null) {
      _entries[key] =
          LibraryEntry(paper: paper, status: LibraryStatus.toRead, note: '', savedAt: _clock(), kind: kind);
    }
    await _save();
    return _entries.containsKey(key);
  }

  /// [key] = [LibraryEntry.key] (논문은 id).
  Future<void> setStatus(String key, LibraryStatus status) async {
    final e = _entries[key];
    if (e == null) return;
    _entries[key] = e.copyWith(status: status);
    await _save();
  }

  Future<void> setNote(String key, String note) async {
    final e = _entries[key];
    if (e == null) return;
    final trimmed = note.length > maxNote ? note.substring(0, maxNote) : note;
    _entries[key] = e.copyWith(note: trimmed);
    await _save();
  }
}
