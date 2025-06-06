import 'package:flutter/material.dart';
import 'package:firebase_core/firebase_core.dart';
import 'package:provider/provider.dart';
import 'package:retro_radar/blocs/auth_bloc.dart';
import 'package:retro_radar/screens/main_tabs_screen.dart';
import 'firebase_options.dart';

void main() async {
  //to sugeruje czat
  WidgetsFlutterBinding.ensureInitialized(); // Musi być przed inicjalizacją Firebase

  await Firebase.initializeApp(options: DefaultFirebaseOptions.currentPlatform);

  runApp(const MyApp());
}

class MyApp extends StatelessWidget {
  const MyApp({super.key});

  // This widget is the root of your application.
  @override
  Widget build(BuildContext context) {
    const seedColor = Colors.blue; // You can change this to your app's primary brand color

    final lightTheme = ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.fromSeed(
        seedColor: seedColor,
        brightness: Brightness.light,
      ),
      // You can further customize AppBarTheme, TabBarTheme, etc., for light mode if needed
      // For example, to ensure AppBar icons are black in light mode:
      appBarTheme: const AppBarTheme(
        backgroundColor: Colors.white, // Or from colorScheme.surface
        foregroundColor: Colors.black, // For icons and title text
        iconTheme: IconThemeData(color: Colors.black),
        actionsIconTheme: IconThemeData(color: Colors.black),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: seedColor,
        unselectedLabelColor: Colors.black54,
        indicatorColor: seedColor,
      ),
    );

    final darkTheme = ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.fromSeed(
        seedColor: seedColor,
        brightness: Brightness.dark,
      ),
      // For example, to ensure AppBar icons are white in dark mode:
      appBarTheme: AppBarTheme(
        backgroundColor: Colors.grey[850], // Or from colorScheme.surface
        foregroundColor: Colors.white,    // For icons and title text
        iconTheme: const IconThemeData(color: Colors.white),
        actionsIconTheme: const IconThemeData(color: Colors.white),
      ),
      tabBarTheme: TabBarThemeData(
        labelColor: seedColor,
        unselectedLabelColor: Colors.white70,
        indicatorColor: seedColor,
      ),
    );

    return Provider(
      create: (context) => AuthBloc(),
      child: MaterialApp(
        title: 'Retro Radar', // Changed from Flutter Demo
        theme: lightTheme,
        darkTheme: darkTheme,
        themeMode: ThemeMode.system, // Automatically adapt to system theme
        home: const MainTabsScreen(), // Set MainTabsScreen as the home screen
      ),
    );
  }
}
