import 'package:flutter/material.dart';

import 'services.dart';
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
          title: 'AI 트렌드 레이더',
          debugShowCheckedModeBanner: false,
          theme: _theme(Brightness.light),
          darkTheme: _theme(Brightness.dark),
          // BR-A25: 기기 글자 크기 × 앱 설정 배율
          builder: (context, child) {
            final media = MediaQuery.of(context);
            final scale = media.textScaler.scale(1) * services.settings.textScale;
            return MediaQuery(
              data: media.copyWith(textScaler: TextScaler.linear(scale)),
              child: child ?? const SizedBox.shrink(),
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

  static const _titles = ['AI 트렌드 레이더', 'Hugging Face 소식', '트렌드 분석', '논문 검색', '보관함'];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: Text(_titles[_index], style: const TextStyle(fontWeight: FontWeight.w800)),
        actions: [
          IconButton(
            tooltip: '설정',
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
        destinations: const [
          NavigationDestination(icon: Icon(Icons.today_outlined), selectedIcon: Icon(Icons.today), label: '오늘'),
          NavigationDestination(icon: Icon(Icons.newspaper_outlined), selectedIcon: Icon(Icons.newspaper), label: '뉴스'),
          NavigationDestination(icon: Icon(Icons.insights_outlined), selectedIcon: Icon(Icons.insights), label: '트렌드'),
          NavigationDestination(icon: Icon(Icons.search), label: '검색'),
          NavigationDestination(
              icon: Icon(Icons.bookmarks_outlined), selectedIcon: Icon(Icons.bookmarks), label: '보관함'),
        ],
      ),
    );
  }
}
