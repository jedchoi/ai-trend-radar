import 'package:flutter/material.dart';

import '../../data/settings_store.dart';
import '../../services.dart';
import '../widgets/common.dart';
import '../../l10n/strings.dart';

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
      messenger.showSnackBar(SnackBar(
          content: Text(settings.configured
              ? tr('서버 주소를 저장했습니다', 'Saved the server address')
              : tr('서버 주소를 지웠습니다', 'Cleared the server address'))));
    }
  }

  Future<void> _addInterest(SettingsStore settings) async {
    final messenger = ScaffoldMessenger.of(context);
    final ok = await settings.addInterest(_interest.text);
    if (ok) {
      _interest.clear();
    } else {
      messenger.showSnackBar(SnackBar(
          content: Text(tr('추가할 수 없습니다 (1~30자, 최대 20개, 중복 불가)', 'Cannot add (1-30 characters, up to 20, no duplicates)'))));
    }
  }

  static String _scaleLabel(double scale) {
    if (scale < 1) return tr('작게', 'Small');
    if (scale == 1) return tr('보통', 'Default');
    if (scale < 1.2) return tr('크게', 'Large');
    return tr('아주 크게', 'Extra large');
  }

  @override
  Widget build(BuildContext context) {
    final settings = Services.of(context).settings;
    return Scaffold(
      appBar: AppBar(title: Text(tr('설정', 'Settings'))),
      body: ListenableBuilder(
        listenable: settings,
        builder: (context, _) => ListView(
          padding: const EdgeInsets.only(bottom: 32),
          children: [
            SectionTitle(tr('언어', 'Language'), subtitle: tr('화면 글자와 내용 (번역) 언어', 'Language for screens and content (translations)')),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(spacing: 6, children: [
                ChoiceChip(
                  label: const Text('한국어'),
                  selected: settings.language == 'ko',
                  onSelected: (_) => settings.setLanguage('ko'),
                ),
                ChoiceChip(
                  label: const Text('English'),
                  selected: settings.language == 'en',
                  onSelected: (_) => settings.setLanguage('en'),
                ),
              ]),
            ),
            SectionTitle(tr('서버 주소', 'Server address'),
                subtitle: tr('같은 Wi-Fi 의 PC 서버는 http://<PC IP>:8000, 배포한 서버는 https:// 주소',
                    'A PC on the same Wi-Fi: http://<PC IP>:8000; a deployed server: https://')),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(crossAxisAlignment: CrossAxisAlignment.start, children: [
                Expanded(
                  child: TextField(
                    key: const Key('server-url'),
                    controller: _url,
                    keyboardType: TextInputType.url,
                    decoration: InputDecoration(
                      hintText: 'http://192.168.0.10:8000',
                      errorText: _urlError,
                      errorMaxLines: 2,
                      border: const OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _saveUrl(settings),
                  ),
                ),
                const SizedBox(width: 8),
                FilledButton(onPressed: () => _saveUrl(settings), child: Text(tr('저장', 'Save'))),
              ]),
            ),
            if (settings.defaultServerUrl.isNotEmpty)
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 6, 16, 0),
                child: Text(
                    tr('설치할 때 넣은 기본 주소: ${settings.defaultServerUrl} (비우고 저장하면 이 주소로 돌아갑니다)',
                        'Built-in address: ${settings.defaultServerUrl} (save an empty value to go back to it)'),
                    style: Theme.of(context).textTheme.bodySmall),
              ),
            SectionTitle(tr('글자 크기', 'Text size'), subtitle: tr('기기 글자 크기에 곱해집니다', 'Multiplies the device text size')),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                for (final scale in SettingsStore.textScales)
                  ChoiceChip(
                    label: Text(_scaleLabel(scale)),
                    selected: settings.textScale == scale,
                    onSelected: (_) => settings.setTextScale(scale),
                  ),
              ]),
            ),
            SectionTitle(tr('관심 키워드', 'Interests'),
                subtitle: tr('맞는 논문을 목록 위로 올리고 "관심" 표시를 붙입니다', 'Matching papers move up and get an "Interest" badge')),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(children: [
                Expanded(
                  child: TextField(
                    key: const Key('interest-input'),
                    controller: _interest,
                    maxLength: SettingsStore.maxInterestLength,
                    decoration: const InputDecoration(
                      hintText: tr('예: agent, RAG, 음성', 'e.g. agent, RAG, speech'),
                      counterText: '',
                      border: OutlineInputBorder(),
                    ),
                    onSubmitted: (_) => _addInterest(settings),
                  ),
                ),
                const SizedBox(width: 8),
                IconButton.filledTonal(
                  tooltip: tr('키워드 추가', 'Add keyword'),
                  icon: const Icon(Icons.add),
                  onPressed: () => _addInterest(settings),
                ),
              ]),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 8, 16, 0),
              child: Wrap(spacing: 6, runSpacing: 6, children: [
                if (settings.interests.isEmpty) Text(tr('아직 없습니다', 'None yet')),
                for (final w in settings.interests)
                  InputChip(label: Text(w), onDeleted: () => settings.removeInterest(w)),
              ]),
            ),
            SectionTitle(tr('"AI 에게 묻기" 에 쓸 AI', 'AI for "Ask an AI"'),
                subtitle: tr('질문을 복사한 뒤 이 AI 의 웹 화면을 엽니다', 'Copies the question, then opens this AI on the web')),
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
