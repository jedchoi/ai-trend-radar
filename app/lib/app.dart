import 'package:flutter/material.dart';

import 'data/settings_store.dart';
import 'l10n/strings.dart';
import 'services.dart';
import 'ui/widgets/language_button.dart';
import 'ui/screens/library_screen.dart';
import 'ui/screens/news_screen.dart';
import 'ui/screens/search_screen.dart';
import 'ui/screens/settings_screen.dart';
import 'ui/screens/today_screen.dart';
import 'ui/screens/trend_screen.dart';

const _seed = Color(0xFF4F46E5);

class RadarApp extends StatelessWidget {
  const RadarApp({super.key, required this.services});

  final AppServices services;

  ThemeData _theme(Brightness brightness) => ThemeData(
        colorScheme: ColorScheme.fromSeed(seedColor: _seed, brightness: brightness),
        useMaterial3: true,
        visualDensity: VisualDensity.standard,
      );

  @override
  Widget build(BuildContext context) {
    return Services(
      services: services,
      child: ListenableBuilder(
        listenable: services.settings,
        builder: (context, _) => MaterialApp(
          title: tr('AI 트렌드 레이더', 'AI Trend Radar'),
          debugShowCheckedModeBanner: false,
          theme: _theme(Brightness.light),
          darkTheme: _theme(Brightness.dark),
          // BR-A25: 기기 글자 크기 × 앱 설정 배율
          builder: (context, child) {
            final media = MediaQuery.of(context);
            final scale = media.textScaler.scale(1) * services.settings.textScale;
            return LanguageRebuilder(
              settings: services.settings,
              child: MediaQuery(
                data: media.copyWith(textScaler: TextScaler.linear(scale)),
                child: child ?? const SizedBox.shrink(),
              ),
            );
          },
          home: const HomeShell(),
        ),
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key});

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;

  static List<String> get _titles => [
        tr('AI 트렌드 레이더', 'AI Trend Radar'),
        tr('Hugging Face 소식', 'Hugging Face news'),
        tr('트렌드 분석', 'Trends'),
        tr('논문 검색', 'Search papers'),
        tr('보관함', 'Library'),
      ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_index], style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          const LanguageButton(),
          IconButton(
            tooltip: tr('설정', 'Settings'),
            icon: const Icon(Icons.settings_outlined),
            onPressed: () =>
                Navigator.of(context).push(MaterialPageRoute<void>(builder: (_) => const SettingsScreen())),
          ),
        ],
      ),
      body: IndexedStack(
        index: _index,
        children: [
          TodayScreen(onOpenNews: () => setState(() => _index = 1)),
          const NewsScreen(),
          const TrendScreen(),
          const SearchScreen(),
          const LibraryScreen(),
        ],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: [
          NavigationDestination(
              icon: const Icon(Icons.today_outlined), selectedIcon: const Icon(Icons.today), label: tr('오늘', 'Today')),
          NavigationDestination(
              icon: const Icon(Icons.newspaper_outlined),
              selectedIcon: const Icon(Icons.newspaper),
              label: tr('뉴스', 'News')),
          NavigationDestination(
              icon: const Icon(Icons.insights_outlined),
              selectedIcon: const Icon(Icons.insights),
              label: tr('트렌드', 'Trends')),
          NavigationDestination(icon: const Icon(Icons.search), label: tr('검색', 'Search')),
          NavigationDestination(
              icon: const Icon(Icons.bookmarks_outlined),
              selectedIcon: const Icon(Icons.bookmarks),
              label: tr('보관함', 'Library')),
        ],
      ),
    );
  }
}

/// 언어가 바뀌면 열려 있는 모든 화면을 다시 그린다 (BR-A30). 화면 상태 (탭 · 스크롤 · 열린 화면) 는 그대로.
class LanguageRebuilder extends StatefulWidget {
  const LanguageRebuilder({super.key, required this.settings, required this.child});

  final SettingsStore settings;
  final Widget child;

  @override
  State<LanguageRebuilder> createState() => _LanguageRebuilderState();
}

class _LanguageRebuilderState extends State<LanguageRebuilder> {
  late String _language = widget.settings.language;

  @override
  void initState() {
    super.initState();
    widget.settings.addListener(_onSettings);
  }

  @override
  void didUpdateWidget(LanguageRebuilder oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.settings != widget.settings) {
      oldWidget.settings.removeListener(_onSettings);
      widget.settings.addListener(_onSettings);
    }
  }

  @override
  void dispose() {
    widget.settings.removeListener(_onSettings);
    super.dispose();
  }

  void _onSettings() {
    if (widget.settings.language == _language || !mounted) return;
    _language = widget.settings.language;
    void rebuild(Element element) {
      element.markNeedsBuild();
      element.visitChildren(rebuild);
    }

    (context as Element).visitChildren(rebuild);
  }

  @override
  Widget build(BuildContext context) => widget.child;
}
