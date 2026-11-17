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

class LibraryEntry {
  const LibraryEntry({required this.paper, required this.status, required this.note, required this.savedAt});

  final PaperBrief paper;
  final LibraryStatus status;
  final String note;
  final DateTime savedAt;

  LibraryEntry copyWith({LibraryStatus? status, String? note}) =>
      LibraryEntry(paper: paper, status: status ?? this.status, note: note ?? this.note, savedAt: savedAt);

  Map<String, dynamic> toJson() => {
        'paper': paper.toJson(),
        'status': status.name,
        'note': note,
        'saved_at': savedAt.toIso8601String(),
      };

  static LibraryEntry? fromJson(Map<String, dynamic> j) {
    final paper = j['paper'];
    if (paper is! Map<String, dynamic>) return null;
    return LibraryEntry(
      paper: PaperBrief.fromJson(paper),
      status: LibraryStatus.fromName(j['status'] as String?),
      note: j['note'] is String ? j['note'] as String : '',
      savedAt: DateTime.tryParse(j['saved_at'] as String? ?? '') ?? DateTime.fromMillisecondsSinceEpoch(0),
    );
  }
}

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
        if (entry != null) _entries[entry.paper.id] = entry;
      }
    } on FormatException {
      // 손상된 저장본은 무시
    }
  }

  Future<void> _save() async {
    await prefs.setString(_key, jsonEncode(_entries.values.map((e) => e.toJson()).toList()));
    notifyListeners();
  }

  bool contains(String id) => _entries.containsKey(id);

  LibraryEntry? entry(String id) => _entries[id];

  /// 최근 저장 먼저, [status] 가 있으면 그 상태만.
  List<LibraryEntry> items({LibraryStatus? status}) {
    final list = _entries.values.where((e) => status == null || e.status == status).toList()
      ..sort((a, b) => b.savedAt.compareTo(a.savedAt));
    return list;
  }

  /// 저장 상태를 뒤집고, 저장됐으면 true.
  Future<bool> toggle(PaperBrief paper) async {
    if (_entries.remove(paper.id) == null) {
      _entries[paper.id] = LibraryEntry(paper: paper, status: LibraryStatus.toRead, note: '', savedAt: _clock());
    }
    await _save();
    return _entries.containsKey(paper.id);
  }

  Future<void> setStatus(String id, LibraryStatus status) async {
    final e = _entries[id];
    if (e == null) return;
    _entries[id] = e.copyWith(status: status);
    await _save();
  }

  Future<void> setNote(String id, String note) async {
    final e = _entries[id];
    if (e == null) return;
    final trimmed = note.length > maxNote ? note.substring(0, maxNote) : note;
    _entries[id] = e.copyWith(note: trimmed);
    await _save();
  }
}
