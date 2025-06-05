import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart'; // For LatLng
// Potentially add: import 'package:url_launcher/url_launcher.dart';

LatLng? parseLocation(String locationString) {
  try {
    final parts = locationString.split(',');
    if (parts.length == 2) {
      final lat = double.parse(parts[0].trim());
      final lng = double.parse(parts[1].trim());
      return LatLng(lat, lng);
    }
    return null;
  } catch (e) {
    print("🚨 Błąd parsowania lokalizacji: $e");
    return null;
  }
}

void showShopDetailsBottomSheet(BuildContext context, Map<String, dynamic> shopData) {
  final name = shopData['name'] as String? ?? 'Sklep bez nazwy';
  final address = shopData['address'] as String? ?? 'Brak adresu';
  final deliveryDay = shopData['delivery_day'] as String?;
  final openingHours = shopData['opening_hours'] as String?;
  final ratingRaw = shopData['rating'];
  final rating = (ratingRaw is num) ? ratingRaw.toDouble() : null;
  final detailsUrl = shopData['details_url'] as String?;

  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
    ),
    builder: (BuildContext context) {
      return DraggableScrollableSheet(
          expand: false,
          initialChildSize: 0.4,
          minChildSize: 0.2,
          maxChildSize: 0.8,
          builder: (_, scrollController) {
            return Container(
              padding: const EdgeInsets.all(16.0),
              child: ListView(
                controller: scrollController,
                children: <Widget>[
                  Text(
                    name,
                    style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 8),
                  Text('Adres: $address'),
                  const SizedBox(height: 8),
                  if (openingHours != null && openingHours != 'N/A') ...[
                    Text('Godziny otwarcia: $openingHours'),
                    const SizedBox(height: 8),
                  ],
                  if (deliveryDay != null && deliveryDay != 'N/A') ...[
                    Text('Dzień dostawy: $deliveryDay'),
                    const SizedBox(height: 8),
                  ],
                  if (rating != null) ...[
                    Text('Ocena: $rating ★'),
                    const SizedBox(height: 8),
                  ],
                  if (detailsUrl != null) ...[
                    InkWell(
                      child: Text(
                        'Zobacz więcej (link)',
                        style: TextStyle(color: Theme.of(context).colorScheme.primary, decoration: TextDecoration.underline),
                      ),
                      onTap: () {
                        print("INFO: Tapped details URL: $detailsUrl (implement opening with url_launcher)");
                        // Example with url_launcher (add url_launcher to pubspec.yaml first):
                        // Uri url = Uri.parse(detailsUrl);
                        // if (await canLaunchUrl(url)) {
                        //   await launchUrl(url);
                        // } else {
                        //   ScaffoldMessenger.of(context).showSnackBar(
                        //     SnackBar(content: Text('Nie można otworzyć linku: $detailsUrl')),
                        //   );
                        // }
                      },
                    ),
                    const SizedBox(height: 16),
                  ],
                  Align(
                    alignment: Alignment.centerRight,
                    child: TextButton(
                      child: const Text('Zamknij'),
                      onPressed: () => Navigator.of(context).pop(),
                    ),
                  )
                ],
              ),
            );
          }
      );
    },
  );
}