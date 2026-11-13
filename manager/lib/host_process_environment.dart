/// System Python and package managers must load host libraries, not the
/// Ubuntu libraries bundled for the Flutter AppImage runtime.
Map<String, String> hostProcessEnvironment(Map<String, String> original) {
  final result = Map<String, String>.from(original);
  result.remove('LD_LIBRARY_PATH');
  result.remove('LD_PRELOAD');
  return result;
}
