import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:redclaw_file_tools/i18n.dart';

void main() {
  testWidgets('Portuguese installation button copy is present', (tester) async {
    await tester.pumpWidget(MaterialApp(home: Scaffold(body: Text(tr('install', 'pt')))));
    expect(find.text('Instalar'), findsOneWidget);
  });
}
