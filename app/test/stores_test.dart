import 'package:ai_trend_radar/data/library_store.dart';
import 'package:ai_trend_radar/data/settings_store.dart';
import 'package:ai_trend_radar/models/models.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';

PaperBrief brief(String id) => PaperBrief.fromJson({'id': id, 'title': 'Paper $id', 'date': '2026-11-13', 'topic': 'agents'});

void main() {
  late SharedPreferences prefs;

  setUp(() async {
    SharedPreferences.setMockInitialValues({});
    prefs = await SharedPreferences.getInstance();
  });

  group('서버 주소 (BR-A13 / AC-15)', () {
    test('비어 있으면 미설정', () {
      expect(SettingsStore(prefs).configured, isFalse);
    });

    test('http(s) 주소만 저장, 끝의 / 제거', () async {
      final s = SettingsStore(prefs);
      expect(await s.setServerUrl('ftp://x.example'), isNotNull);
      expect(await s.setServerUrl('radar.example.com'), isNotNull);
      expect(s.configured, isFalse);
      expect(await s.setServerUrl(' https://radar.example.com// '), isNull);
      expect(s.serverUrl, 'https://radar.example.com');
      expect(SettingsStore(prefs).serverUrl, 'https://radar.example.com');
      expect(await s.setServerUrl('http://192.168.0.10:8000'), isNull);
      expect(s.configured, isTrue);
      expect(await s.setServerUrl(''), isNull);
      expect(s.configured, isFalse);
    });

    test('빌드 기본 주소', () {
      expect(SettingsStore(prefs, defaultServerUrl: 'https://d.example').serverUrl, 'https://d.example');
    });
  });

  group('관심 키워드 (BR-A06 / AC-04-1)', () {
    test('추가 · 중복 · 길이 · 개수 · 삭제 · 유지', () async {
      final s = SettingsStore(prefs);
      expect(await s.addInterest(' agent '), isTrue);
      expect(await s.addInterest('AGENT'), isFalse);
      expect(await s.addInterest(''), isFalse);
      expect(await s.addInterest('x' * 31), isFalse);
      for (var i = 0; i < 19; i++) {
        expect(await s.addInterest('k$i'), isTrue);
      }
      expect(await s.addInterest('one-more'), isFalse);
      expect(s.interests.first, 'agent');
      await s.removeInterest('agent');
      expect(SettingsStore(prefs).interests, hasLength(19));
    });

    test('묻기 대상', () async {
      final s = SettingsStore(prefs);
      expect(s.askTarget, AskTarget.claude);
      await s.setAskTarget(AskTarget.gemini);
      expect(SettingsStore(prefs).askTarget, AskTarget.gemini);
    });
  });

  group('보관함 (BR-A11 / AC-13)', () {
    test('저장 · 해제 · 상태 · 메모 · 유지', () async {
      var now = DateTime(2026, 11, 13, 9);
      final lib = LibraryStore(prefs, clock: () => now);
      expect(await lib.toggle(brief('a')), isTrue);
      now = now.add(const Duration(minutes: 1));
      await lib.toggle(brief('b'));
      expect(lib.items().map((e) => e.paper.id), ['b', 'a']);
      expect(lib.entry('a')!.status, LibraryStatus.toRead);
      await lib.setStatus('a', LibraryStatus.applied);
      await lib.setNote('a', '사내 검색에 적용');
      expect(lib.items(status: LibraryStatus.applied).single.note, '사내 검색에 적용');
      final reloaded = LibraryStore(prefs);
      expect(reloaded.entry('a')!.status, LibraryStatus.applied);
      expect(reloaded.entry('a')!.paper.topic, Topic.agents);
      expect(await reloaded.toggle(brief('a')), isFalse);
      expect(reloaded.contains('a'), isFalse);
    });

    test('메모 1000자 제한, 없는 항목 무시', () async {
      final lib = LibraryStore(prefs);
      await lib.toggle(brief('a'));
      await lib.setNote('a', 'x' * 1200);
      expect(lib.entry('a')!.note.length, 1000);
      await lib.setStatus('zzz', LibraryStatus.onHold);
      expect(lib.contains('zzz'), isFalse);
    });

    test('손상된 저장본은 무시', () async {
      SharedPreferences.setMockInitialValues({'library:entries': '{not json'});
      final p = await SharedPreferences.getInstance();
      expect(LibraryStore(p).items(), isEmpty);
    });
  });
}
