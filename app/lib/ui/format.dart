import '../l10n/strings.dart';

const _weekdays = ['월', '화', '수', '목', '금', '토', '일'];
const _weekdaysEn = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const _monthsEn = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

/// '2026-11-13' → '11월 13일 (금)' / 'Fri, Nov 13'
String dayLabel(String isoDate) {
  final d = DateTime.tryParse(isoDate);
  if (d == null) return isoDate;
  return tr('${d.month}월 ${d.day}일 (${_weekdays[d.weekday - 1]})',
      '${_weekdaysEn[d.weekday - 1]}, ${_monthsEn[d.month - 1]} ${d.day}');
}

/// '2026-11-13' → '11.13' / '11/13'
String shortDay(String isoDate) {
  final d = DateTime.tryParse(isoDate);
  return d == null ? isoDate : tr('${d.month}.${d.day}', '${d.month}/${d.day}');
}

/// '2026-W46' → '46주차' / 'Week 46', '2026-11' → '2026년 11월' / 'Nov 2026'
String periodLabel(String key) {
  final week = RegExp(r'^(\d{4})-W(\d{2})$').firstMatch(key);
  if (week != null) return tr('${int.parse(week.group(2)!)}주차', 'Week ${int.parse(week.group(2)!)}');
  final month = RegExp(r'^(\d{4})-(\d{2})$').firstMatch(key);
  if (month != null) {
    final m = int.parse(month.group(2)!);
    return tr('${month.group(1)}년 $m월', '${_monthsEn[m - 1]} ${month.group(1)}');
  }
  return key;
}

/// 1234 → '1.2천' / '1.2K', 158598 → '15.9만' / '158.6K'
String compact(int n) {
  if (AppLang.english) {
    if (n >= 1000000000) return '${(n / 1000000000).toStringAsFixed(1)}B';
    if (n >= 1000000) return '${(n / 1000000).toStringAsFixed(1)}M';
    if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}K';
    return '$n';
  }
  if (n >= 100000000) return '${(n / 100000000).toStringAsFixed(1)}억';
  if (n >= 10000) return '${(n / 10000).toStringAsFixed(1)}만';
  if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}천';
  return '$n';
}
