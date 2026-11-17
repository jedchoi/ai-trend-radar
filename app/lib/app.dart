import 'package:flutter/material.dart';

import 'services.dart';
import 'ui/screens/library_screen.dart';
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
      child: MaterialApp(
        title: 'AI 트렌드 레이더',
        debugShowCheckedModeBanner: false,
        theme: _theme(Brightness.light),
        darkTheme: _theme(Brightness.dark),
        home: const HomeShell(),
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

  static const _titles = ['AI 트렌드 레이더', '트렌드 분석', '논문 검색', '보관함'];

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
        children: const [TodayScreen(), TrendScreen(), SearchScreen(), LibraryScreen()],
      ),
      bottomNavigationBar: NavigationBar(
        selectedIndex: _index,
        onDestinationSelected: (i) => setState(() => _index = i),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.newspaper_outlined), selectedIcon: Icon(Icons.newspaper), label: '오늘'),
          NavigationDestination(icon: Icon(Icons.insights_outlined), selectedIcon: Icon(Icons.insights), label: '트렌드'),
          NavigationDestination(icon: Icon(Icons.search), label: '검색'),
          NavigationDestination(
              icon: Icon(Icons.bookmarks_outlined), selectedIcon: Icon(Icons.bookmarks), label: '보관함'),
        ],
      ),
    );
  }
}
