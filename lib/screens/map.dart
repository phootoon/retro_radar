import 'package:cloud_firestore/cloud_firestore.dart';
import 'package:flutter/material.dart';
import 'package:google_maps_flutter/google_maps_flutter.dart';
import 'package:retro_radar/utils/map_utils.dart'; // Import the utility file

class MapScreen extends StatefulWidget {
  // Add a GlobalKey parameter if you need to call methods from outside
  const MapScreen({super.key});

  @override
  State<MapScreen> createState() => MapScreenState();
}

// Make the State class public by removing the underscore
class MapScreenState extends State<MapScreen> {
  late GoogleMapController mapController;
  final Set<Marker> _markers = {};
  bool _isLoading = true;

  static const CameraPosition _initialCameraPosition = CameraPosition(
    target: LatLng(52.4064, 16.9252), // Centrum Poznania
    zoom: 12,
  );

  @override
  void initState() {
    super.initState();
    loadStores(); // Call the public method
  }

  // Make loadStores public
  Future<void> loadStores() async {
    if (!mounted) return; // Add mounted check at the beginning
    setState(() {
      _isLoading = true;
    });
    try {
      final stores =
          await FirebaseFirestore.instance.collection('storelist').get();
      print("📌 Znaleziono ${stores.docs.length} sklepów w 'storelist' (mapa)");

      final Set<Marker> newMarkers = {};

      for (var doc in stores.docs) {
        final data = doc.data();
        final locationString = data['location'] as String?;
        final name = data['name'] as String? ?? 'Sklep bez nazwy';

        if (locationString != null) {
          // Use parseLocation from map_utils.dart
          final location = parseLocation(locationString);

          if (location != null) {
            print(
              "✅ Dodaję znacznik (mapa): $name (${location.latitude}, ${location.longitude})",
            );

            newMarkers.add(
              Marker(
                  markerId: MarkerId(doc.id),
                  position: location,
                  infoWindow: InfoWindow(
                    title: name,
                  ),
                  icon: BitmapDescriptor.defaultMarkerWithHue(
                    BitmapDescriptor.hueViolet,
                  ),
                  onTap: () {
                    // Use showShopDetailsBottomSheet from map_utils.dart
                    showShopDetailsBottomSheet(context, data);
                  }),
            );
          } else {
            print("⚠️ Nieprawidłowy format lokalizacji (mapa): $locationString dla $name");
          }
        } else {
          print("⚠️ Brak pola 'location' (mapa) w dokumencie ${doc.id} ($name)");
        }
      }
      if (mounted) {
        setState(() {
          _markers.clear();
          _markers.addAll(newMarkers);
          _isLoading = false;
        });
      }
    } catch (e) {
      print("❌ Błąd przy pobieraniu sklepów (mapa): $e");
      if (mounted) {
        setState(() {
          _isLoading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    // The Scaffold and AppBar are removed from here.
    // The MainTabsScreen will provide the Scaffold and AppBar.
    return Stack(
      children: [
        GoogleMap(
          initialCameraPosition: _initialCameraPosition,
          onMapCreated: (controller) => mapController = controller,
          markers: _markers,
          myLocationEnabled: true,
          myLocationButtonEnabled: true,
          mapType: MapType.normal,
        ),
        if (_isLoading)
          const Center(
            child: CircularProgressIndicator(
              valueColor: AlwaysStoppedAnimation<Color>(Colors.purple),
            ),
          ),
      ],
    );
  }
}
