import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import 'package:firebase_auth/firebase_auth.dart'; // For User type in StreamBuilder
import 'package:retro_radar/blocs/auth_bloc.dart';
import 'package:retro_radar/screens/home.dart';
import 'package:retro_radar/screens/login.dart'; // Import your actual LoginScreen
import 'package:retro_radar/screens/map.dart';
import 'package:retro_radar/screens/shop_list_screen.dart';

class LoginTabContent extends StatelessWidget {
  const LoginTabContent({super.key});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Text("Nie jesteś zalogowany.", style: TextStyle(fontSize: 18)),
          const SizedBox(height: 20),
          ElevatedButton(
            child: const Text("Zaloguj się / Zarejestruj"),
            onPressed: () {
              Navigator.of(context).push(MaterialPageRoute(builder: (_) => const LoginScreen()));
            },
          ),
        ],
      )
    );
  }
}

class MainTabsScreen extends StatefulWidget {
  const MainTabsScreen({super.key});

  @override
  State<MainTabsScreen> createState() => _MainTabsScreenState();
}

class _MainTabsScreenState extends State<MainTabsScreen> with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final GlobalKey<MapScreenState> _mapScreenKey = GlobalKey<MapScreenState>();

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 3, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final authBloc = Provider.of<AuthBloc>(context);
    // Calculate TabBar height - typically kTextTabBarHeight if only text, or a bit more with icons.
    // The TabBar widget itself will have a preferred size.
    // Let's use kToolbarHeight as a reference, which is typically 56.0.
    // Or directly use TabBar.preferredSize.height if accessible here or hardcode a suitable value.
    // For a TabBar with icons and text, preferred height is often around 72.0.
    // If we set toolbarHeight to be small, the AppBar effectively just holds the TabBar.

    return DefaultTabController(
      length: 3,
      child: Scaffold(
        appBar: AppBar(
          title: const Text(''),
          toolbarHeight: 0, // Attempt to make the main toolbar area (above bottom) take no space
          // The TabBar itself will define its own height as the 'bottom' of the AppBar.
          // elevation: 0, // Optional: remove shadow if the color matches the body
          bottom: TabBar(
            controller: _tabController,
            tabs: const [
              Tab(icon: Icon(Icons.map_outlined), text: 'Mapa'),
              Tab(icon: Icon(Icons.list_alt_outlined), text: 'Lista Sklepów'),
              Tab(icon: Icon(Icons.account_circle_outlined), text: 'Konto'),
            ],
            // Removed hardcoded colors to use TabBarTheme from MaterialApp
            // indicatorColor: Theme.of(context).colorScheme.secondary,
            // labelColor: Theme.of(context).colorScheme.secondary,
            // unselectedLabelColor: Theme.of(context).textTheme.bodyLarge?.color?.withOpacity(0.7),
            onTap: (index) {
              if (index == _tabController.index && index == 0) {
                _mapScreenKey.currentState?.loadStores();
              }
            },
          ),
        ),
        body: TabBarView(
          controller: _tabController,
          physics: const NeverScrollableScrollPhysics(),
          children: [
            MapScreen(key: _mapScreenKey),
            const ShopListScreen(),
            StreamBuilder<User?>(
              stream: authBloc.currentUser, // Listening to Firebase User object
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Center(child: CircularProgressIndicator());
                }
                if (snapshot.hasData && snapshot.data != null) {
                  return const HomeScreen();
                } else {
                  return const LoginTabContent();
                }
              }
            ),
          ],
        ),
      ),
    );
  }
} 