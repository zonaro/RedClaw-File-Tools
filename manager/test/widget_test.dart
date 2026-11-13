import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:redclaw_file_tools/main.dart';

Map<String, dynamic> demoInventory() {
  final managers = [
    {'id': 'nautilus', 'binary': 'nautilus', 'name': 'Nautilus', 'detected': true},
    {'id': 'dolphin', 'binary': 'dolphin', 'name': 'Dolphin', 'detected': true},
  ];
  return {
    'product': 'RedClaw File Tools',
    'file_managers': managers,
    'extensions': List.generate(30, (i) => {
      'id': 'tool-$i',
      'name': 'Tool $i',
      'category': 'Files',
      'compatibility': {
        'nautilus': {
          'status': 'not_installed',
          'recommendation': 'recommended',
          'support': 'full',
        },
        'dolphin': {
          'status': 'not_installed',
          'recommendation': 'optional',
          'support': 'partial',
        },
      },
    }),
  };
}

void main() {
  for (final size in [
    const Size(320, 480),
    const Size(440, 650),
    const Size(800, 600),
    const Size(1280, 720),
  ]) {
    testWidgets('Responsive manager at ${size.width}x${size.height}',
        (tester) async {
      tester.view.devicePixelRatio = 1;
      tester.view.physicalSize = size;
      addTearDown(tester.view.resetPhysicalSize);
      addTearDown(tester.view.resetDevicePixelRatio);

      await tester.pumpWidget(MaterialApp(
        home: ManagerHome(
          language: 'pt',
          onLanguageChange: (_) {},
          inventoryLoader: () async => demoInventory(),
        ),
      ));
      await tester.pumpAndSettle();

      expect(find.text('RedClaw File Tools'), findsOneWidget);
      expect(find.byType(CustomScrollView), findsOneWidget);
      expect(find.text('Nautilus'), findsWidgets);
      expect(tester.takeException(), isNull);

      // Verify the catalog is actually scrollable on short and narrow windows.
      final vertical = find.byType(CustomScrollView);
      await tester.scrollUntilVisible(
        find.text('Tool 29'),
        240,
        scrollable: find.descendant(
          of: vertical,
          matching: find.byType(Scrollable),
        ).first,
      );
      await tester.pumpAndSettle();
      expect(find.text('Tool 29'), findsOneWidget);
      expect(tester.takeException(), isNull);
    });
  }

  testWidgets('Each detected manager has its own catalog status', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(920, 720);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(MaterialApp(
      home: ManagerHome(
        language: 'en',
        onLanguageChange: (_) {},
        inventoryLoader: () async => demoInventory(),
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.textContaining('Full support'), findsWidgets);

    await tester.tap(find.text('Dolphin'));
    await tester.pumpAndSettle();
    expect(find.textContaining('Partial support'), findsWidgets);
    expect(tester.takeException(), isNull);
  });
  testWidgets('Enabled state is independent for Nautilus and Dolphin', (tester) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(1080, 700);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final data = demoInventory();
    data['extensions'] = [
      {
        'id': 'file-tools',
        'name': 'File Tools',
        'category': 'Files',
        'compatibility': {
          'nautilus': {
            'status': 'disabled',
            'recommendation': 'recommended',
            'support': 'full',
          },
          'dolphin': {
            'status': 'installed',
            'recommendation': 'optional',
            'support': 'partial',
          },
        },
      },
    ];
    await tester.pumpWidget(MaterialApp(
      home: ManagerHome(
        language: 'en',
        onLanguageChange: (_) {},
        inventoryLoader: () async => data,
      ),
    ));
    await tester.pumpAndSettle();
    expect(find.text('Disabled'), findsOneWidget);
    expect(find.text('Enable'), findsOneWidget);
    expect(find.text('Uninstall'), findsOneWidget);

    await tester.tap(find.text('Dolphin'));
    await tester.pumpAndSettle();
    expect(find.text('Disabled'), findsNothing);
    expect(find.text('Disable'), findsOneWidget);
    expect(find.text('Uninstall'), findsOneWidget);
    expect(tester.takeException(), isNull);
  });

}
