import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:retro_radar/utils/map_utils.dart'; // Import the utility file

class ShopListScreen extends StatefulWidget {
  const ShopListScreen({super.key});

  @override
  State<ShopListScreen> createState() => _ShopListScreenState();
}

class _ShopListScreenState extends State<ShopListScreen> {
  List<Map<String, dynamic>> _shops = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    _loadShopList();
  }

  Future<void> _loadShopList() async {
    if (!mounted) return;
    setState(() {
      _isLoading = true;
      _error = '';
    });

    try {
      final snapshot = await FirebaseFirestore.instance
          .collection('storelist')
          .orderBy('name') // Optional: order by name
          .get();

      if (!mounted) return;

      final List<Map<String, dynamic>> loadedShops = [];
      for (var doc in snapshot.docs) {
        loadedShops.add(doc.data());
      }
      setState(() {
        _shops = loadedShops;
        _isLoading = false;
      });
    } catch (e) {
      if (!mounted) return;
      print("❌ Błąd przy pobieraniu listy sklepów: $e");
      setState(() {
        _error = "Nie udało się załadować listy sklepów. Spróbuj ponownie.";
        _isLoading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      // AppBar is handled by MainTabsScreen
      body: RefreshIndicator(
        onRefresh: _loadShopList,
        child: _buildBody(),
      ),
    );
  }

  Widget _buildBody() {
    if (_isLoading) {
      return const Center(
        child: CircularProgressIndicator(
          valueColor: AlwaysStoppedAnimation<Color>(Colors.purple),
        ),
      );
    }

    if (_error.isNotEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(_error, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              ElevatedButton(
                onPressed: _loadShopList,
                child: const Text('Spróbuj ponownie'),
              )
            ],
          ),
        ),
      );
    }

    if (_shops.isEmpty) {
      return const Center(
        child: Text("Nie znaleziono żadnych sklepów."),
      );
    }

    return ListView.builder(
      itemCount: _shops.length,
      itemBuilder: (context, index) {
        final shop = _shops[index];
        final name = shop['name'] as String? ?? 'Sklep bez nazwy';
        final address = shop['address'] as String? ?? 'Brak adresu';
        final ratingRaw = shop['rating'];
        final rating = (ratingRaw is num) ? ratingRaw.toDouble() : null;

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
          child: ListTile(
            title: Text(name),
            subtitle: Text(address + (rating != null ? '\nOcena: $rating ★' : '')),
            isThreeLine: rating != null, // Make list tile taller if rating is present
            onTap: () {
              showShopDetailsBottomSheet(context, shop);
            },
            trailing: const Icon(Icons.arrow_forward_ios, size: 16),
          ),
        );
      },
    );
  }
} 