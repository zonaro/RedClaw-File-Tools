import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'i18n.dart';

const appVersion = String.fromEnvironment('APP_VERSION', defaultValue: 'development');
const redClawRed = Color(0xFFBB283E);

void main() {
  WidgetsFlutterBinding.ensureInitialized();
  runApp(const RedClawApp());
}

class RedClawApp extends StatefulWidget {
  const RedClawApp({super.key});

  @override
  State<RedClawApp> createState() => _RedClawAppState();
}

class _RedClawAppState extends State<RedClawApp> {
  late String language = () {
    final locale = Platform.localeName.split(RegExp('[-_.]')).first.toLowerCase();
    return languageNames.containsKey(locale) ? locale : 'en';
  }();

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'RedClaw File Tools',
      debugShowCheckedModeBanner: false,
      locale: Locale(language),
      supportedLocales: const [
        Locale('pt', 'BR'), Locale('en'), Locale('es'), Locale('fr'), Locale('de')
      ],
      localizationsDelegates: const [
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      themeMode: ThemeMode.system,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: redClawRed),
        scaffoldBackgroundColor: const Color(0xFFF8F8FA),
      ),
      darkTheme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: redClawRed, brightness: Brightness.dark,
        ),
      ),
      home: ManagerHome(
        language: language,
        onLanguageChange: (newLanguage) => setState(() => language = newLanguage),
      ),
    );
  }
}

class ManagerHome extends StatefulWidget {
  const ManagerHome({
    super.key, required this.language, required this.onLanguageChange,
  });

  final String language;
  final ValueChanged<String> onLanguageChange;

  @override
  State<ManagerHome> createState() => _ManagerHomeState();
}

class _ManagerHomeState extends State<ManagerHome> {
  Map<String, dynamic>? inventory;
  String? currentManager;
  String? error;
  String? busy;
  bool loading = true;
  String search = '';
  String filter = 'all';

  String t(String key) => tr(key, widget.language);

  String _backendPath() {
    final override = Platform.environment['REDCLAW_BACKEND'];
    if (override != null && File(override).existsSync()) return override;
    final wd = Directory.current.path;
    final candidates = [
      File('$wd/../backend/redclaw.py'),
      File('$wd/backend/redclaw.py'),
    ];
    for (final candidate in candidates) {
      if (candidate.existsSync()) return candidate.absolute.path;
    }
    throw StateError('Backend not found; REDCLAW_BACKEND is not configured.');
  }

  Future<Map<String, dynamic>> _cli(String command, [List<String> args = const []]) async {
    final result = await Process.run('python3', [
      _backendPath(), '--json', command, ...args,
    ], runInShell: false);
    final output = result.stdout.toString().trim();
    Map<String, dynamic> data;
    try {
      data = Map<String, dynamic>.from(jsonDecode(output) as Map);
    } catch (_) {
      throw StateError('Invalid backend response: $output ${result.stderr}');
    }
    if (result.exitCode != 0 || data['ok'] == false) {
      throw StateError('${data['error'] ?? result.stderr}');
    }
    return data;
  }

  @override
  void initState() {
    super.initState();
    _refresh();
  }

  String? _preferredManager(List<dynamic> managers) {
    final desktop = (Platform.environment['XDG_CURRENT_DESKTOP'] ?? '').toLowerCase();
    final choices = <String, String>{
      'kde': 'dolphin', 'plasma': 'dolphin', 'gnome': 'nautilus',
      'cinnamon': 'nemo', 'mate': 'caja', 'xfce': 'thunar',
      'lxqt': 'pcmanfm-qt',
    };
    for (final match in choices.entries) {
      if (desktop.contains(match.key) &&
          managers.any((fm) => fm['id'] == match.value && fm['detected'] == true)) {
        return match.value;
      }
    }
    return managers.isNotEmpty ? managers.first['id'] as String : null;
  }

  Future<void> _refresh() async {
    setState(() {
      loading = true;
      error = null;
    });
    try {
      final data = await _cli('inventory');
      if (!mounted) return;
      final managers = data['file_managers'] as List<dynamic>? ?? [];
      setState(() {
        inventory = data;
        if (!managers.any((fm) => fm['id'] == currentManager)) {
          currentManager = _preferredManager(managers);
        }
        loading = false;
      });
    } catch (exception) {
      if (!mounted) return;
      setState(() {
        error = '$exception';
        loading = false;
      });
    }
  }

  void _message(String text) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(text), behavior: SnackBarBehavior.floating),
    );
  }

  Future<void> _change(Map<String, dynamic> entry, {required bool remove}) async {
    final manager = currentManager;
    if (manager == null || busy != null) return;
    final slug = entry['id'] as String;
    setState(() => busy = '$manager/$slug');
    try {
      var installDependencies = true;
      Map<String, dynamic>? plan;
      if (!remove) {
        plan = await _cli('plan', ['--fm', manager, '--slug', slug]);
      }
      if (!mounted) return;
      final dependencyInfo = plan?['dependencies'] as Map<String, dynamic>? ?? {};
      final missing = List<String>.from(dependencyInfo['missing'] as List? ?? []);
      final packages = List<String>.from(dependencyInfo['packages'] as List? ?? []);
      final unresolved = List<String>.from(dependencyInfo['unresolved'] as List? ?? []);
      final conflicts = List<String>.from(plan?['conflicts'] as List? ?? []);
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (dialogContext) => StatefulBuilder(
          builder: (context, updateDialog) => AlertDialog(
            title: Text(remove ? t('confirm_remove') : t('confirm_install')),
            content: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 470),
              child: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('${entry['name']} · $manager',
                        style: Theme.of(context).textTheme.titleMedium),
                    const SizedBox(height: 12),
                    Text(t('only_this_manager')),
                    if (remove) ...[
                      const SizedBox(height: 10),
                      Text(t('remove_warning')),
                    ] else ...[
                      const SizedBox(height: 14),
                      Text(t('dependency_plan'),
                          style: Theme.of(context).textTheme.titleMedium),
                      const SizedBox(height: 8),
                      Text(missing.isEmpty
                          ? t('no_deps')
                          : '${t('missing')}: ${missing.join(', ')}'),
                      if (packages.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text('${t('packages')}: ${packages.join(', ')}'),
                      ],
                      if (unresolved.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text('${t('missing')}: ${unresolved.join(', ')}',
                            style: TextStyle(color: Theme.of(context).colorScheme.error)),
                      ],
                      if (conflicts.isNotEmpty) ...[
                        const SizedBox(height: 8),
                        Text('${t('conflicts')}: ${conflicts.join(', ')}',
                            style: TextStyle(color: Theme.of(context).colorScheme.error)),
                        Text(t('remove_conflicts')),
                      ],
                      if (missing.isNotEmpty)
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(t('install_deps')),
                          value: installDependencies,
                          onChanged: (value) => updateDialog(
                            () => installDependencies = value ?? true,
                          ),
                        ),
                      if (dependencyInfo['requires_admin'] == true)
                        Text(t('polkit'), style: Theme.of(context).textTheme.bodySmall),
                    ],
                  ],
                ),
              ),
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(dialogContext, false),
                child: Text(t('cancel')),
              ),
              FilledButton(
                onPressed: (!remove && (unresolved.isNotEmpty || conflicts.isNotEmpty ||
                    (missing.isNotEmpty && !installDependencies)))
                    ? null
                    : () => Navigator.pop(dialogContext, true),
                child: Text(remove ? t('remove') : t('confirm')),
              ),
            ],
          ),
        ),
      );
      if (confirmed != true) return;
      final args = ['--fm', manager, '--slug', slug, '--yes'];
      if (!remove && installDependencies) args.add('--install-deps');
      await _cli(remove ? 'uninstall' : 'install', args);
      _message('${t(remove ? 'removed_success' : 'installed_success')} ${t('manual_restart')}');
      await _refresh();
    } catch (exception) {
      _message('${t('error')}: $exception');
    } finally {
      if (mounted) setState(() => busy = null);
    }
  }

  String _recommendation(Map<String, dynamic> fmInfo) {
    final state = fmInfo['recommendation']?.toString() ?? 'incompatible';
    return t(state);
  }

  IconData _managerIcon(String id) {
    if (id == 'dolphin') return Icons.view_column_outlined;
    if (id == 'nautilus') return Icons.folder_open_outlined;
    return Icons.folder_outlined;
  }

  Widget _extensionCard(Map<String, dynamic> entry) {
    final current = currentManager;
    final compatibility = Map<String, dynamic>.from(
      (entry['compatibility'] as Map?)?[current] as Map? ?? {},
    );
    final support = compatibility['support']?.toString() ?? 'unsupported';
    final status = compatibility['status']?.toString() ?? 'not_installed';
    final recommendation = compatibility['recommendation']?.toString() ?? 'incompatible';
    final isInstalled = status == 'installed';
    final canManage = support != 'unsupported' && status != 'external' &&
        status != 'modified' && current != null;
    final busyHere = busy == '$current/${entry['id']}';
    final explanation = switch (status) {
      'external' => t('external_desc'),
      'modified' => t('modified_desc'),
      _ when support == 'unsupported' => t('unsupported_desc'),
      _ when support == 'partial' => t('partial_desc'),
      _ when recommendation == 'redundant' => t('redundant_desc'),
      _ => t('full_desc'),
    };
    return Card(
      elevation: 0,
      margin: const EdgeInsets.only(bottom: 9),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
        child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Wrap(
            spacing: 9,
            runSpacing: 8,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              Text(entry['name'] as String,
                  style: Theme.of(context).textTheme.titleMedium),
              Chip(
                visualDensity: VisualDensity.compact,
                label: Text(_recommendation(compatibility)),
              ),
              if (isInstalled)
                Chip(
                  visualDensity: VisualDensity.compact,
                  avatar: const Icon(Icons.check_circle_outline, size: 16),
                  label: Text(t('installed')),
                ),
              if (status == 'external' || status == 'modified')
                Chip(label: Text(t(status)), visualDensity: VisualDensity.compact),
            ],
          ),
          const SizedBox(height: 5),
          Text('${entry['category']} · ${t(support == 'unsupported' ? 'unsupported' : support)}',
              style: Theme.of(context).textTheme.labelSmall),
          const SizedBox(height: 5),
          Text(explanation, style: Theme.of(context).textTheme.bodySmall),
          if (canManage) ...[
            const SizedBox(height: 12),
            Wrap(spacing: 8, children: [
              FilledButton.tonalIcon(
                onPressed: busy == null ? () => _change(entry, remove: false) : null,
                icon: busyHere
                    ? const SizedBox(width: 16, height: 16, child: CircularProgressIndicator(strokeWidth: 2))
                    : Icon(isInstalled ? Icons.system_update_alt : Icons.add_circle_outline),
                label: Text(isInstalled ? t('update') : t('install')),
              ),
              if (isInstalled)
                OutlinedButton.icon(
                  onPressed: busy == null ? () => _change(entry, remove: true) : null,
                  icon: const Icon(Icons.delete_outline),
                  label: Text(t('remove')),
                ),
            ]),
          ],
        ]),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final fms = List<Map<String, dynamic>>.from(
      (inventory?['file_managers'] as List? ?? []).map((item) => Map<String, dynamic>.from(item)),
    );
    final extensions = List<Map<String, dynamic>>.from(
      (inventory?['extensions'] as List? ?? []).map((item) => Map<String, dynamic>.from(item)),
    );
    final filtered = extensions.where((entry) {
      final label = (entry['name'] as String).toLowerCase();
      final id = (entry['id'] as String).toLowerCase();
      if (!label.contains(search.toLowerCase()) && !id.contains(search.toLowerCase())) {
        return false;
      }
      final info = (entry['compatibility'] as Map?)?[currentManager] as Map?;
      if (filter == 'installed') return info?['status'] == 'installed';
      if (filter == 'recommended') return info?['recommendation'] == 'recommended';
      return true;
    }).toList();
    const ranking = <String, int>{
      'recommended': 0, 'optional': 1, 'conditional': 2,
      'redundant': 3, 'incompatible': 4,
    };
    filtered.sort((a, b) {
      final left = ((a['compatibility'] as Map?)?[currentManager] as Map?)?['recommendation'];
      final right = ((b['compatibility'] as Map?)?[currentManager] as Map?)?['recommendation'];
      final order = (ranking[left] ?? 9).compareTo(ranking[right] ?? 9);
      return order != 0 ? order : (a['name'] as String).compareTo(b['name'] as String);
    });

    return Scaffold(
      appBar: AppBar(
        title: Row(children: [
          const Icon(Icons.folder_copy_outlined, color: redClawRed),
          const SizedBox(width: 10),
          const Flexible(child: Text('RedClaw File Tools',
              maxLines: 1, overflow: TextOverflow.ellipsis)),
        ]),
        actions: [
          IconButton(
            tooltip: t('refresh'),
            onPressed: busy == null ? _refresh : null,
            icon: const Icon(Icons.refresh),
          ),
          Padding(
            padding: const EdgeInsets.only(right: 14),
            child: DropdownButtonHideUnderline(
              child: DropdownButton<String>(
                value: widget.language,
                items: languageNames.entries.map((entry) => DropdownMenuItem(
                  value: entry.key,
                  child: Text(entry.value),
                )).toList(),
                onChanged: (value) {
                  if (value != null) widget.onLanguageChange(value);
                },
              ),
            ),
          ),
        ],
      ),
      body: SafeArea(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 1100),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 12),
              child: Column(crossAxisAlignment: CrossAxisAlignment.stretch, children: [
                Text(t('subtitle'), style: Theme.of(context).textTheme.titleMedium),
                const SizedBox(height: 14),
                if (error != null) Card(
                  child: Padding(
                    padding: const EdgeInsets.all(14),
                    child: SelectableText('${t('error')}: $error'),
                  ),
                ),
                if (loading) const LinearProgressIndicator(),
                if (!loading && fms.isEmpty) Padding(
                  padding: const EdgeInsets.symmetric(vertical: 40),
                  child: Center(child: Text(t('no_managers'))),
                ),
                if (fms.isNotEmpty) ...[
                  Text(t('select_manager'),
                      style: Theme.of(context).textTheme.labelLarge),
                  const SizedBox(height: 8),
                  SingleChildScrollView(
                    scrollDirection: Axis.horizontal,
                    child: Row(children: fms.map((fm) {
                      final id = fm['id'] as String;
                      return Padding(
                        padding: const EdgeInsets.only(right: 8),
                        child: ChoiceChip(
                          selected: currentManager == id,
                          avatar: Icon(_managerIcon(id), size: 18),
                          label: Text('${fm['name']}${fm['detected'] == true ? '' : ' · ${t('not_detected')}'}'),
                          onSelected: (_) => setState(() => currentManager = id),
                        ),
                      );
                    }).toList()),
                  ),
                  const SizedBox(height: 16),
                  Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
                    SizedBox(
                      width: 320,
                      child: TextField(
                        decoration: InputDecoration(
                          hintText: t('search'), prefixIcon: const Icon(Icons.search),
                          isDense: true, border: const OutlineInputBorder(),
                        ),
                        onChanged: (value) => setState(() => search = value),
                      ),
                    ),
                    for (final item in ['all', 'recommended', 'installed'])
                      ChoiceChip(
                        label: Text(t(item == 'all' ? 'all'
                            : item == 'recommended' ? 'only_recommended' : 'only_installed')),
                        selected: filter == item,
                        onSelected: (_) => setState(() => filter = item),
                      ),
                  ]),
                  const SizedBox(height: 12),
                ],
                if (fms.isNotEmpty)
                  Expanded(
                    child: filtered.isEmpty
                        ? Center(child: Text(t('no_results')))
                        : ListView.builder(
                            itemCount: filtered.length,
                            itemBuilder: (context, index) => _extensionCard(filtered[index]),
                          ),
                  ),
                const SizedBox(height: 8),
                Text('${t('version')}: $appVersion  ·  ${t('runtime_note')}',
                    style: Theme.of(context).textTheme.bodySmall,
                    textAlign: TextAlign.center),
              ]),
            ),
          ),
        ),
      ),
    );
  }
}
