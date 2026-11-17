const _weekdays = ['월', '화', '수', '목', '금', '토', '일'];

/// '2026-11-13' → '11월 13일 (금)'
String dayLabel(String isoDate) {
  final d = DateTime.tryParse(isoDate);
  if (d == null) return isoDate;
  return '${d.month}월 ${d.day}일 (${_weekdays[d.weekday - 1]})';
}

/// '2026-11-13' → '11.13'
String shortDay(String isoDate) {
  final d = DateTime.tryParse(isoDate);
  return d == null ? isoDate : '${d.month}.${d.day}';
}

/// '2026-W46' → '46주차', '2026-11' → '2026년 11월'
String periodLabel(String key) {
  final week = RegExp(r'^(\d{4})-W(\d{2})$').firstMatch(key);
  if (week != null) return '${int.parse(week.group(2)!)}주차';
  final month = RegExp(r'^(\d{4})-(\d{2})$').firstMatch(key);
  if (month != null) return '${month.group(1)}년 ${int.parse(month.group(2)!)}월';
  return key;
}

/// 1234 → '1.2천', 158598 → '15.9만'
String compact(int n) {
  if (n >= 100000000) return '${(n / 100000000).toStringAsFixed(1)}억';
  if (n >= 10000) return '${(n / 10000).toStringAsFixed(1)}만';
  if (n >= 1000) return '${(n / 1000).toStringAsFixed(1)}천';
  return '$n';
}
