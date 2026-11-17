import 'package:flutter/material.dart';

import '../../l10n/strings.dart';
import '../../services.dart';

/// 언어 버튼 (BR-A33): 한국어일 때 "EN", 영어일 때 "한" 을 보여 주고 누르면 바꾼다.
class LanguageButton extends StatelessWidget {
  const LanguageButton({super.key});

  @override
  Widget build(BuildContext context) {
    final settings = Services.of(context).settings;
    return TextButton(
      key: const Key('language-button'),
      onPressed: settings.toggleLanguage,
      child: Text(AppLang.english ? '한' : 'EN', style: const TextStyle(fontWeight: FontWeight.w800)),
    );
  }
}
