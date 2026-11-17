import 'package:flutter/material.dart';

import '../../data/settings_store.dart';
import '../../services.dart';
import '../widgets/common.dart';

/// 설정 (US-04, US-08, US-15).
class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  TextEditingController? _url;
  final _interest = TextEditingController();
  String? _urlError;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    _url ??= TextEditingController(text: Services.of(context).settings.serverUrl);
  }

  @override
  void dispose() {
    _url?.dispose();
    _interest.dispose();
    super.dispose();
  }

  Future<void> _saveUrl(SettingsStore settings) async {
    final messenger = ScaffoldMessenger.of(context);
    final error = await settings.setServerUrl(_url!.text);
    setState(() => _urlError = error);
    if (error == null) {
      _url!.text = settings.serverUrl;
      messenger.showSnackBar(SnackBar(content: Text(settings.demoMode ? '데모 데이터로 전환했습니다' : '서버 주소를 저장했습니다')));
    }
  }

  Future<void> _addInterest(SettingsStore settings) async {
    final messenger = ScaffoldMessenger.of(context);
    final ok = await settings.addInterest(_interest.text);
    if (ok) {
      _interest.clear();
    } else {
      messenger.showSnackBar(const SnackBar(content: Text('추가할 수 없습니다 (1~30자, 최대 20개, 중복 불가)')));
    }
  }

  @override
  Widget build(BuildContext context) {
    final settings = Services.of(context).settings;
    return Scaffold(
      appBar: AppBar(title: const Text('설정')),
      body: ListenableBuilder(
        listenable: settings,
        builder: (context, _) => ListView(
          padding: const EdgeInsets.only(bottom: 32),
          children: [
            const SectionTitle('서버 주소', subtitle: '비워 두면 앱에 들어 있는 데모 데이터를 보여 줍니다'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(
                  child: TextField(
                    key: const Key('server-url'),
                    controller: _url,
                    keyboardType: TextInputType.url,
                    decoration: InputDecoration(
                      hintText: 'https://radar.example.com',
                      errorText: _urlError,
                      errorMaxLines: 2,
                      border: const OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _saveUrl(settings),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(onPressed: () => _saveUrl(settings), child: const Text('저장')),
              ]),
            ),
            const SectionTitle('관심 키워드', subtitle: '맞는 논문을 목록 위로 올리고 "관심" 표시를 붙입니다'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    key: const Key('interest-input'),
                    controller: _interest,
                    maxLength: SettingsStore.maxInterestLength,
                    decoration: const InputDecoration(
                      hintText: '예: agent, RAG, 음성',
                      counterText: '',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _addInterest(settings),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filledTonal(
                  tooltip: '키워드 추가',
                  icon: const Icon(Icons.add),
                  onPressed: () => _addInterest(settings),
                ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                if (settings.interests.isEmpty) const Text('아직 없습니다'),
                for (final w in settings.interests)
                  InputChip(label: Text(w), onDeleted: () => settings.removeInterest(w)),
              ]),
            ),
            const SectionTitle('"AI 에게 묻기" 에 쓸 AI', subtitle: '질문을 복사한 뒤 이 AI 의 웹 화면을 엽니다'),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(spacing: 6, children: [
                for (final t in AskTarget.values)
                  ChoiceChip(
                    label: Text(t.label),
                    selected: settings.askTarget == t,
                    onSelected: (_) => settings.setAskTarget(t),
                  ),
              ]),
            ),
          ],
        ),
      ),
    );
  }
}
