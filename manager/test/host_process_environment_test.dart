import 'package:flutter_test/flutter_test.dart';
import 'package:redclaw_file_tools/host_process_environment.dart';

void main() {
  test('host Python does not inherit bundled AppImage libraries', () {
    final environment = {
      'PATH': '/usr/bin',
      'HOME': '/home/tester',
      'LD_LIBRARY_PATH': '/tmp/.mount_redclaw/usr/lib',
      'LD_PRELOAD': '/tmp/old-driver.so',
      'REDCLAW_BACKEND': '/tmp/.mount_redclaw/backend/redclaw.py',
    };
    final cleaned = hostProcessEnvironment(environment);
    expect(cleaned['LD_LIBRARY_PATH'], isNull);
    expect(cleaned['LD_PRELOAD'], isNull);
    expect(cleaned['PATH'], '/usr/bin');
    expect(cleaned['HOME'], '/home/tester');
    expect(cleaned['REDCLAW_BACKEND'], isNotNull);
    // Avoid modifying the Flutter process environment shared by all widgets.
    expect(environment['LD_LIBRARY_PATH'], isNotNull);
  });
}
