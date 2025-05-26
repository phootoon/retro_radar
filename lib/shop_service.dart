import 'dart:convert';
import 'package:http/http.dart' as http;
import 'package:html/parser.dart' show parse;
import 'package:html/dom.dart' as dom;

class Shop {
  final String name;
  final String address;
  final double? latitude;
  final double? longitude;
  final String openingHours;
  final String? deliveryDay; // Could be a specific day, " codziennie", or similar
  final String detailsUrl;

  Shop({
    required this.name,
    required this.address,
    this.latitude,
    this.longitude,
    required this.openingHours,
    this.deliveryDay,
    required this.detailsUrl,
  });

  @override
  String toString() {
    return 'Shop{name: $name, address: $address, lat: $latitude, lng: $longitude, openingHours: $openingHours, deliveryDay: $deliveryDay, detailsUrl: $detailsUrl}';
  }

  factory Shop.fromElement(dom.Element element) {
    // Helper to get text or default
    String getText(dom.Element? el, String selector, [String defaultValue = 'N/A']) {
      return el?.querySelector(selector)?.text.trim() ?? defaultValue;
    }

    // Helper to get attribute or default
    String getAttribute(dom.Element? el, String selector, String attribute, [String defaultValue = '']) {
      return el?.querySelector(selector)?.attributes[attribute] ?? defaultValue;
    }
    
    String? deliveryDayValue;
    final deliveryElement = element.querySelector('.e-dostawa-badge');
    if (deliveryElement != null) {
      deliveryDayValue = deliveryElement.text.trim();
    }


    final name = getText(element, 'h4.listing-preview-title');
    final address = getText(element, 'ul.lf-contact li:first-child', 'Address N/A'); // Assuming first li is address
    final detailsUrl = getAttribute(element, 'a', 'href');

    // Extract lat/lng from data-locations attribute
    double? lat, lng;
    final locationsData = element.attributes['data-locations'];
    if (locationsData != null && locationsData.isNotEmpty) {
      try {
        final decodedLocations = json.decode(locationsData);
        if (decodedLocations is List && decodedLocations.isNotEmpty) {
          final firstLocation = decodedLocations.first;
          if (firstLocation is Map) {
            lat = double.tryParse(firstLocation['lat']?.toString() ?? '');
            lng = double.tryParse(firstLocation['lng']?.toString() ?? '');
          }
        }
      } catch (e) {
        print('Error parsing location data: $e');
      }
    }
    
    // Placeholder for opening hours, as it's not directly in the preview
    // This will likely need to be fetched from the detailsUrl or another source
    final openingHours = getText(element, '.event-time', 'Opening hours N/A');


    return Shop(
      name: name,
      address: address,
      latitude: lat,
      longitude: lng,
      openingHours: openingHours,
      deliveryDay: deliveryDayValue,
      detailsUrl: detailsUrl,
    );
  }
}

class ShopService {
  final String _baseUrl = 'secondhandy.com.pl';
  final String _securityNonce = '20a291621f'; // Hardcoded nonce

  Future<List<Shop>> fetchShops() async {
    // Construct the form_data map
    final formData = {
      'page': '0',
      'preserve_page': 'false',
      'search_location': '',
      'lat': 'false',
      'lng': 'false',
      'proximity': '30',
      'region': 'poznan', // Target region
      'search_keywords': '',
      'category': '',
      'dostawa': '', // Assuming this is for delivery day filter, empty means all
      'tags': '',
      'dodatkowe-informacje': '',
      'open-now': '',
      'sort': 'data-dostawy', // Sort by delivery day
    };

    // Encode the form_data for the URI
    final encodedFormData = Uri(queryParameters: 
      formData.map((key, value) => MapEntry('form_data[$key]', value))
    ).query;

    final queryParameters = {
      'mylisting-ajax': '1',
      'action': 'get_listings',
      'security': _securityNonce, // Use the hardcoded nonce
      'listing_type': 'place',
      'listing_wrap': 'col-md-12 grid-item',
      'proximity_units': 'km',
    };

    // Combine queryParameters with the already encoded formData string
    final uri = Uri.https(
        _baseUrl, '', queryParameters)
        .replace(query: '${Uri(queryParameters: queryParameters).query}&$encodedFormData');


    try {
      final response = await http.get(uri);

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        final htmlContent = jsonData['html'] as String?;

        if (htmlContent != null) {
          return _parseShops(htmlContent);
        } else {
          throw Exception('HTML content is null');
        }
      } else {
        throw Exception('Failed to load shops (status code: ${response.statusCode}) Body: ${response.body}');
      }
    } catch (e) {
      print('Error fetching shops: $e');
      // Consider how to handle this in the UI, e.g., show an error message
      return []; // Return empty list or rethrow
    }
  }

  List<Shop> _parseShops(String htmlContent) {
    final document = parse(htmlContent);
    final shopElements = document.querySelectorAll('.lf-item-container'); // Main container for each shop
    
    return shopElements.map((element) => Shop.fromElement(element)).toList();
  }
}

// Example Usage (for testing - you would integrate this into your BLoC/UI)
void main() async {
  final shopService = ShopService();
  final shops = await shopService.fetchShops();
  if (shops.isNotEmpty) {
    for (var shop in shops) {
      print(shop);
    }
  } else {
    print('No shops found or an error occurred.');
  }
} 