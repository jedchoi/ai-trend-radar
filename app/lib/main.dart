import 'package:flutter/material.dart';

import 'app.dart';
import 'services.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final services = await AppServices.create();
  runApp(RadarApp(services: services));
}
