import 'package:flutter/material.dart';
import 'package:retro_radar/services/shop_service.dart'; // Assuming shop_service.dart is in lib/services

class ShopListWidget extends StatefulWidget {
  const ShopListWidget({super.key});

  @override
  State<ShopListWidget> createState() => _ShopListWidgetState();
}

class _ShopListWidgetState extends State<ShopListWidget> {
  final ShopService _shopService = ShopService();
  List<Shop> _shops = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    print('[ShopListWidget] initState called. Fetching shops...'); // DEBUG PRINT
    _fetchShopsData();
  }

  Future<void> _fetchShopsData() async {
    print('[ShopListWidget] _fetchShopsData started.'); // DEBUG PRINT
    setState(() {
      _isLoading = true;
      _error = null;
    });
    try {
      final shops = await _shopService.fetchShops();
      print('[ShopListWidget] Successfully fetched ${shops.length} shops.'); // DEBUG PRINT
      if (mounted) { // Check if the widget is still in the tree
        setState(() {
          _shops = shops;
          _isLoading = false;
        });
      }
    } catch (e) {
      print('[ShopListWidget] Caught error in _fetchShopsData: $e'); // DEBUG PRINT
      if (mounted) { // Check if the widget is still in the tree
        setState(() {
          _error = e.toString();
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    print('[ShopListWidget] build called. isLoading: $_isLoading, error: $_error, shops count: ${_shops.length}'); // DEBUG PRINT
    if (_isLoading) {
      return const Center(child: CircularProgressIndicator());
    }

    if (_error != null) {
      return Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text('Error: $_error', style: const TextStyle(color: Colors.red)),
            const SizedBox(height: 8),
            ElevatedButton(
              onPressed: _fetchShopsData,
              child: const Text('Retry'),
            )
          ],
        ),
      );
    }

    if (_shops.isEmpty) {
      return const Center(child: Text('No shops found.'));
    }

    return ListView.builder(
      itemCount: _shops.length,
      itemBuilder: (context, index) {
        final shop = _shops[index];
        return Card(
          margin: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
          child: ListTile(
            title: Text(shop.name),
            subtitle: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(shop.address),
                if (shop.deliveryDay != null && shop.deliveryDay!.isNotEmpty)
                  Text('Delivery: ${shop.deliveryDay}'),
                Text('Opening: ${shop.openingHours}'), // This might need better formatting
              ],
            ),
            trailing: (shop.latitude != null && shop.longitude != null)
                ? const Icon(Icons.map)
                : null, // Placeholder for map icon
            onTap: () {
              // TODO: Implement navigation to shop details screen or map
              print('Tapped on ${shop.name}, URL: ${shop.detailsUrl}');
            },
          ),
        );
      },
    );
  }
} 