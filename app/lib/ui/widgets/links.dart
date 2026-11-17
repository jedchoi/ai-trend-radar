import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';
import '../../l10n/strings.dart';

/// http(s) 링크만 외부 앱으로 연다 (NFR-A04).
Future<void> openLink(BuildContext context, String url) async {
  final uri = Uri.tryParse(url);
  final messenger = ScaffoldMessenger.maybeOf(context);
  if (uri == null || (uri.scheme != 'https' && uri.scheme != 'http')) {
    messenger?.showSnackBar(SnackBar(content: Text(tr('열 수 없는 주소입니다', 'This address cannot be opened'))));
    return;
  }
  var ok = false;
  try {
    ok = await launchUrl(uri, mode: LaunchMode.externalApplication);
  } catch (_) {
    ok = false;
  }
  if (!ok) messenger?.showSnackBar(SnackBar(content: Text(tr('링크를 열지 못했습니다', 'Could not open the link'))));
}
