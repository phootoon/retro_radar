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
  String? deliveryDay; // Made mutable to update after initial parse
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

  // Helper to parse common elements from the shop's main preview element
  static Shop fromPreviewElement(dom.Element element) {
    String getText(dom.Element? el, String selector, [String defaultValue = 'N/A']) {
      return el?.querySelector(selector)?.text.trim() ?? defaultValue;
    }

    String getAttribute(dom.Element? el, String selector, String attribute, [String defaultValue = '']) {
      return el?.querySelector(selector)?.attributes[attribute] ?? defaultValue;
    }
    
    final name = getText(element, 'h4.listing-preview-title');
    final detailsUrl = getAttribute(element, 'a', 'href');

    String address = 'N/A';
    final contactListItems = element.querySelectorAll('ul.lf-contact > li');
    dom.Element? addressLiElement;
    for (var li in contactListItems) {
      if (li.querySelector('i.icon-location-pin-add-2') != null) {
        addressLiElement = li;
        break;
      }
    }

    if (addressLiElement != null) {
      final iconElement = addressLiElement.querySelector('i.icon-location-pin-add-2');
      if (iconElement != null && iconElement.parentNode != null) {
        final parentNodes = iconElement.parentNode!.nodes;
        final iconIndex = parentNodes.indexOf(iconElement);
        if (iconIndex != -1 && (iconIndex + 1) < parentNodes.length) {
          final nextSiblingNode = parentNodes[iconIndex + 1];
          if (nextSiblingNode is dom.Text) {
            address = nextSiblingNode.text.trim();
          } else {
            address = addressLiElement.text.trim().replaceFirst(iconElement.text.trim(), '').trim();
          }
        } else {
          address = addressLiElement.text.trim().replaceFirst(iconElement.text.trim(), '').trim();
        }
      } else {
        address = addressLiElement.text.trim();
      }
      if (address == getText(addressLiElement, 'i.icon-location-pin-add-2')){
          address = addressLiElement.text.trim().replaceFirst(address, '').trim();
      }
      if (address.isEmpty && addressLiElement.text.trim().isNotEmpty) {
        address = addressLiElement.text.trim();
      }
    }

    double? lat, lng;
    final locationsData = element.attributes['data-locations'];
    if (locationsData != null && locationsData.isNotEmpty && locationsData != "false") {
      try {
        final decodedLocations = json.decode(locationsData);
        if (decodedLocations is List && decodedLocations.isNotEmpty) {
          final firstLocation = decodedLocations.first;
          if (firstLocation is Map) {
            lat = double.tryParse(firstLocation['lat']?.toString() ?? '');
            lng = double.tryParse(firstLocation['lng']?.toString() ?? '');
            if (address == 'N/A' || address.isEmpty) {
                address = firstLocation['address']?.toString() ?? 'N/A';
            }
          }
        }
      } catch (e) {
        print('[Shop.fromPreviewElement] Error parsing location data for $name: $e');
      }
    }
    
    String openingHours = 'N/A';
    dom.Element? openingHoursLiElement;
    for (var li in contactListItems) {
        if (li.querySelector('i.mi.access_time') != null) {
            openingHoursLiElement = li;
            break;
        }
    }

    if (openingHoursLiElement != null) {
        final spanNextToIcon = openingHoursLiElement.querySelector('span');
        if (spanNextToIcon != null) {
            openingHours = spanNextToIcon.text.trim();
        } else {
            final iconText = openingHoursLiElement.querySelector('i.mi.access_time')?.text.trim() ?? '';
            openingHours = openingHoursLiElement.text.trim().replaceFirst(iconText, '').trim();
        }
    }

    if (openingHours == 'N/A') {
        final headButtons = element.querySelectorAll('div.lf-head > div.lf-head-btn');
        for (var btn in headButtons) {
            var btnText = btn.text.trim().toUpperCase();
            if (btnText == 'OTWARTE' || btnText == 'ZAMKNIĘTE' || btnText == 'TYLKO PO UMÓWIENIU' || btnText.contains(':')) {
                openingHours = btn.text.trim();
                break;
            }
        }
    }
    
    // Initial deliveryDay is null, will be fetched from details page
    return Shop(
      name: name,
      address: address,
      latitude: lat,
      longitude: lng,
      openingHours: openingHours,
      deliveryDay: null, // Initially null
      detailsUrl: detailsUrl,
    );
  }

  // Method to parse delivery day specifically from a full HTML document (details page)
  static String? parseDeliveryDayFromDetailHtml(String htmlContent) {
    final document = parse(htmlContent);
    String? deliveryDayValue;

    // Strategy based on 'pojedynczy.txt' structure for ul[data-field="dostawa"]
    final deliveryUlElement = document.querySelector('ul[data-field="dostawa"]');
    if (deliveryUlElement != null) {
      final firstLiSpan = deliveryUlElement.querySelector('li > span');
      if (firstLiSpan != null && firstLiSpan.text.trim().isNotEmpty) {
        deliveryDayValue = firstLiSpan.text.trim();
        print('[Shop.parseDeliveryDayFromDetailHtml] Delivery day from ul[data-field="dostawa"]: $deliveryDayValue');
        return deliveryDayValue; // Found, return
      }
    }
    
    // Fallback: search info fields (copied and adapted from previous logic)
    final infoSections = document.querySelectorAll('ul.lf-meta, div.lf-info, ul.c27-listing-details-list, div.job-details-content, div.content-block');
    for (var section in infoSections) {
      final listItems = section.querySelectorAll('li, div.info-field, div.detail-field'); // More general list item selectors
      for (var li in listItems) {
        final labelElement = li.querySelector('div.info-head, span.field-label, strong.key, dt'); // Common label selectors
        if (labelElement != null) {
          final labelText = labelElement.text.trim().toLowerCase();
          if (labelText.contains('dostawa') || labelText.contains('dzień dostawy') || labelText.contains('delivery day')) {
            final valueElement = li.querySelector('div.info-body, span.field-content, div.value, dd'); // Common value selectors
            if (valueElement != null && valueElement.text.trim().isNotEmpty) {
              deliveryDayValue = valueElement.text.trim();
               print('[Shop.parseDeliveryDayFromDetailHtml] Delivery day from info field: $deliveryDayValue');
              return deliveryDayValue; // Found, return
            }
          }
        }
      }
    }
    
    // Fallback for .e-dostawa-badge
    final deliveryBadgeElement = document.querySelector('.e-dostawa-badge');
     if (deliveryBadgeElement != null && deliveryBadgeElement.text.trim().isNotEmpty) {
      deliveryDayValue = deliveryBadgeElement.text.trim();
      print('[Shop.parseDeliveryDayFromDetailHtml] Delivery day from badge: $deliveryDayValue');
      return deliveryDayValue;
    }

    print('[Shop.parseDeliveryDayFromDetailHtml] Delivery day not found in detail HTML.');
    return null;
  }
}

class ShopService {
  final String _baseUrl = 'secondhandy.com.pl';
  final String _securityNonce = '20a291621f'; // Assuming this is still valid or fetched dynamically

  Future<List<Shop>> fetchShops() async {
    final formData = {
      'page': '0',
      'preserve_page': 'false',
      'search_location': '',
      'lat': 'false',
      'lng': 'false',
      'proximity': '30',
      'region': 'poznan',
      'search_keywords': '',
      'category': '',
      'dostawa': '',
      'tags': '',
      'dodatkowe-informacje': '',
      'open-now': '',
      'sort': 'data-dostawy',
    };

    final encodedFormDataParts = <String>[];
    formData.forEach((key, value) {
      encodedFormDataParts.add('form_data[${Uri.encodeQueryComponent(key)}]=${Uri.encodeQueryComponent(value)}');
    });
    final encodedFormDataStr = encodedFormDataParts.join('&');

    final queryParameters = {
      'mylisting-ajax': '1',
      'action': 'get_listings',
      'security': _securityNonce,
      'listing_type': 'place',
      'listing_wrap': 'col-md-12 grid-item',
      'proximity_units': 'km',
    };
    
    final String initialQuery = Uri(queryParameters: queryParameters).query;
    final String fullQuery = '$initialQuery&$encodedFormDataStr';
    final uri = Uri.https(_baseUrl, '', Uri.splitQueryString(fullQuery));
    
    print('[ShopService] Fetching initial shop list from: $uri');

    try {
      final response = await http.get(uri, headers: {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
      });

      if (response.statusCode == 200) {
        final jsonData = json.decode(response.body);
        final htmlContent = jsonData['html'] as String?;

        if (htmlContent != null) {
          print('[ShopService] Initial HTML content received, parsing preview shops.');
          List<Shop> shops = _parsePreviewShops(htmlContent);
          print('[ShopService] Parsed ${shops.length} preview shops. Now fetching details for delivery days...');

          // Iterate and fetch details for each shop
          for (var shop in shops) {
            if (shop.detailsUrl.isNotEmpty) {
              try {
                print('[ShopService] Fetching details for ${shop.name} from ${shop.detailsUrl}');
                final detailResponse = await http.get(Uri.parse(shop.detailsUrl), headers: {
                   'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'
                });
                if (detailResponse.statusCode == 200) {
                  shop.deliveryDay = Shop.parseDeliveryDayFromDetailHtml(detailResponse.body);
                  print('[ShopService] Updated ${shop.name} with delivery day: ${shop.deliveryDay}');
                } else {
                  print('[ShopService] Error fetching details for ${shop.name}: Status code ${detailResponse.statusCode}');
                }
              } catch (e) {
                print('[ShopService] Error fetching/parsing details for ${shop.name}: $e');
              }
            } else {
              print('[ShopService] Skipping details for ${shop.name} due to empty URL.');
            }
          }
          print('[ShopService] Finished fetching all details.');
          return shops;
        } else {
          print('[ShopService] Error: Initial HTML content is null.');
          throw Exception('Initial HTML content is null');
        }
      } else {
        print('[ShopService] Error: Failed to load initial shop list (status code: ${response.statusCode})');
        throw Exception('Failed to load initial shop list (status code: ${response.statusCode})');
      }
    } catch (e) {
      print('[ShopService] Error in fetchShops: $e');
      rethrow;
    }
  }

  // Renamed to clarify it parses the preview HTML from the list API
  List<Shop> _parsePreviewShops(String htmlContent) {
    final document = parse(htmlContent);
    final shopElements = document.querySelectorAll('div.lf-item-container');
    print('[ShopService] _parsePreviewShops: Found ${shopElements.length} shop elements to parse from preview.');
    
    List<Shop> shops = [];
    for (var element in shopElements) {
      try {
        final shop = Shop.fromPreviewElement(element); // Use the renamed factory
        shops.add(shop);
      } catch (e) {
        print('[ShopService] Error parsing one preview shop element: $e');
      }
    }
    return shops;
  }
}

// Example Usage (for testing - you would integrate this into your BLoC/UI)
/*
void main() async {
  final shopService = ShopService();
  try {
    final shops = await shopService.fetchShops();
    if (shops.isNotEmpty) {
      shops.forEach((shop) => print(shop.toString()));
      print('\nSuccessfully fetched and parsed ${shops.length} shops.');
    } else {
      print('No shops found or an error occurred during fetching/parsing.');
    }
  } catch (e) {
     print('Error in main test: $e');
  }
}
*/ 