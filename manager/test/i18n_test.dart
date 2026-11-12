import 'package:flutter_test/flutter_test.dart';
import 'package:redclaw_file_tools/i18n.dart';

void main() {
  test('all core labels are available in five languages', () {
    const languages = ['pt', 'en', 'es', 'fr', 'de'];
    for (final language in languages) {
      expect(tr('install', language), isNotEmpty);
      expect(tr('remove', language), isNotEmpty);
      expect(tr('dependency_plan', language), isNotEmpty);
      expect(tr('unsupported_desc', language), isNotEmpty);
    }
  });
  test('unknown languages fall back to English', () {
    expect(tr('install', 'zz'), 'Install');
  });
}
