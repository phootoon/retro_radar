import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart'; // For launching URLs

class ShopListScreen extends StatefulWidget {
  const ShopListScreen({super.key});

  @override
  State<ShopListScreen> createState() => ShopListScreenState();
}

class ShopListScreenState extends State<ShopListScreen> {
  List<Map<String, dynamic>> _shops = [];
  bool _isLoading = true;
  String _error = '';

  @override
  void initState() {
    super.initState();
    loadShopList();
  }

  Future<void> loadShopList() async {
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
        onRefresh: loadShopList,
        child: buildBody(),
      ),
    );
  }

  Widget buildBody() {
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
                onPressed: loadShopList,
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
        final openingHours = shop['opening_hours'] as String?;
        final deliveryDay = shop['delivery_day'] as String?;
        final detailsUrl = shop['details_url'] as String?;

        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 8.0, vertical: 4.0),
          child: ExpansionTile(
            title: Text(name),
            subtitle: Text(address),
            childrenPadding: const EdgeInsets.all(16.0),
            expandedCrossAxisAlignment: CrossAxisAlignment.start,
            children: <Widget>[
              if (openingHours != null && openingHours.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text("Godziny otwarcia: $openingHours"),
                ),
              if (deliveryDay != null && deliveryDay.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text("Dzień dostawy: $deliveryDay"),
                ),
              if (rating != null)
                Padding(
                  padding: const EdgeInsets.only(bottom: 8.0),
                  child: Text("Ocena: $rating ★"),
                ),
              if (detailsUrl != null && detailsUrl.isNotEmpty)
                InkWell(
                  onTap: () async {
                    final Uri url = Uri.parse(detailsUrl);
                    if (await canLaunchUrl(url)) {
                      await launchUrl(url);
                    } else {
                      ScaffoldMessenger.of(context).showSnackBar(
                        SnackBar(
                          content: Text('Nie można otworzyć linku: $detailsUrl'),
                        ),
                      );
                    }
                  },
                  child: Padding(
                    padding: const EdgeInsets.only(bottom: 8.0),
                    child: Text(
                      'Zobacz szczegóły online',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.primary,
                        decoration: TextDecoration.underline,
                      ),
                    ),
                  ),
                ),
              if ((openingHours == null || openingHours.isEmpty) &&
                  (deliveryDay == null || deliveryDay.isEmpty) &&
                  rating == null &&
                  (detailsUrl == null || detailsUrl.isEmpty))
                const Padding(
                  padding: EdgeInsets.only(bottom: 8.0),
                  child: Text("Brak dodatkowych informacji."),
                ),
            ],
          ),
        );
      },
    );
  }
} 