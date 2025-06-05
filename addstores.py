import requests
import json
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import aiohttp
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import hashlib # For potentially creating more unique IDs


def fetch_shops_python():
    base_url = "https://secondhandy.com.pl/"
    security_nonce = "20a291621f"

    form_data_params = {
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
    }

    # Encode form_data like PHP's http_build_query for arrays/maps
    encoded_form_data_parts = []
    for key, value in form_data_params.items():
        encoded_form_data_parts.append(f"form_data[{urllib.parse.quote(key)}]={urllib.parse.quote(value)}")
    encoded_form_data_str = "&".join(encoded_form_data_parts)

    query_params = {
        'mylisting-ajax': '1',
        'action': 'get_listings',
        'security': security_nonce,
        'listing_type': 'place',
        'listing_wrap': 'col-md-12 grid-item',
        'proximity_units': 'km',
    }

    # Construct the full URL
    # Starting with base_url and the fixed query part
    url = base_url + "?" + urllib.parse.urlencode(query_params)
    # Append the specially encoded form_data
    url += "&" + encoded_form_data_str

    print(f"Requesting URL: {url}\\n")

    shops_data = []

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'})  # Added a User-Agent
        response.raise_for_status()  # Raise an exception for HTTP errors

        print(f"Response Status Code: {response.status_code}")
        # print(f"Response Headers: {response.headers}")
        # print(f"Response Content (first 500 chars): {response.text[:500]}\\n")

        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Response text was:")
            print(response.text[:1000])  # Print more of the response if JSON decoding fails
            return []

        html_content = data.get('html')

        if not html_content:
            print("No 'html' content found in JSON response.")
            print(f"JSON data: {data}")
            return []

        print(f"Found {data.get('found_posts', 0)} posts according to JSON response.")

        soup = BeautifulSoup(html_content, 'html.parser')
        shop_elements = soup.select('div.lf-item-container')

        print(f"Found {len(shop_elements)} shop elements in the HTML content for parsing.\\n")

        for i, element in enumerate(shop_elements):
            name_tag = element.select_one('h4.listing-preview-title')
            name = name_tag.get_text(strip=True) if name_tag else 'N/A'

            address_tag = element.select_one('ul.lf-contact li:first-child')
            # Attempt to get only the address text, excluding potential nested icon text
            address = ""
            if address_tag:
                # Iterate over string parts, ignoring icon tags if necessary
                address_parts = [part.strip() for part in address_tag.stripped_strings]
                address = " ".join(address_parts)
                # A common pattern is an <i> tag for icon, then text. Let's try to remove icon's effect
                icon_tag = address_tag.select_one('i')
                if icon_tag and icon_tag.next_sibling and isinstance(icon_tag.next_sibling, str):
                    address = icon_tag.next_sibling.strip()
                elif address_parts:  # Fallback to joined stripped_strings if specific structure not found
                    address = " ".join(address_parts)
                else:
                    address = address_tag.get_text(strip=True)

            details_url_tag = element.select_one('a')
            details_url = details_url_tag['href'] if details_url_tag and details_url_tag.has_attr('href') else 'N/A'

            lat, lng = None, None
            locations_data_str = element.get('data-locations')
            if locations_data_str:
                try:
                    locations_json = json.loads(locations_data_str)
                    if isinstance(locations_json, list) and locations_json:
                        first_location = locations_json[0]
                        lat_str = first_location.get('lat')
                        lng_str = first_location.get('lng')
                        if lat_str: lat = float(lat_str)
                        if lng_str: lng = float(lng_str)
                        # If address wasn't found well from text, try from data-locations
                        if address == 'N/A' or not address.strip():
                            address = first_location.get('address', 'N/A')

                except (json.JSONDecodeError, TypeError, ValueError) as e:
                    print(f"Error parsing data-locations for {name}: {e}")

            delivery_day_tag = element.select_one('.e-dostawa-badge')
            delivery_day = delivery_day_tag.get_text(strip=True) if delivery_day_tag else None

            # Opening hours are tricky, might be in different places or need details page
            opening_hours_tag = element.select_one('ul.lf-contact li span')  # General span in contact
            opening_hours_specific_icon = element.select_one('ul.lf-contact li i.mi.access_time')  # Icon specific

            opening_hours = 'N/A'
            if opening_hours_specific_icon and opening_hours_specific_icon.parent:
                span_in_parent = opening_hours_specific_icon.parent.select_one('span')
                if span_in_parent:
                    opening_hours = span_in_parent.get_text(strip=True)

            # Fallback for open/closed status shown in header of listing item
            if opening_hours == 'N/A':
                status_tags = element.select('div.lf-head > div.lf-head-btn')
                for tag in status_tags:
                    text = tag.get_text(strip=True)
                    if text.upper() in ["OTWARTE", "ZAMKNIĘTE",
                                        "TYLKO PO UMÓWIENIU"] or ":" in text:  # Check for time like format
                        opening_hours = text
                        break

            # Rating parsing from preview
            rating = 0.0
            rating_element = element.select_one('div.listing-rating.rating-preview-card')
            if rating_element:
                full_stars = len(rating_element.select('i.mi.star'))
                half_stars = len(rating_element.select('i.mi.star_half'))
                rating = float(full_stars + half_stars * 0.5)
            else:
                rating = None  # Or 0.0, or 'N/A' depending on preference

            shops_data.append({
                'name': name,
                'address': address,
                'delivery_day': delivery_day,
                'opening_hours': opening_hours,
                'rating': rating,
            })

            print(f"--- Shop {i + 1} ---")
            print(f"  Name: {name}")
            print(f"  Address: {address}")
            print(f"  Delivery: {delivery_day}")
            print(f"  Opening: {opening_hours}")
            print(f"  Rating: {rating}")
            print("--------------------\\n")


    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")
        import traceback
        traceback.print_exc()

    return shops_data


# --- Helper function to parse delivery day (similar to Dart's Shop.parseDeliveryDayFromDetailHtml) ---
def parse_delivery_day_from_detail_html(html_content):
    if not html_content:
        print("[parse_delivery_day_from_detail_html] HTML content is None, cannot parse.")
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    delivery_day_value = None

    # Strategy based on 'pojedynczy.txt' structure for ul[data-field="dostawa"]
    delivery_ul_element = soup.find('ul', attrs={'data-field': 'dostawa'})
    if delivery_ul_element:
        first_li_span = delivery_ul_element.find('li').find('span') if delivery_ul_element.find('li') else None
        if first_li_span and first_li_span.text.strip():
            delivery_day_value = first_li_span.text.strip()
            # print(f'[parse_delivery_day_from_detail_html] Delivery day from ul[data-field="dostawa"]: {delivery_day_value}')
            return delivery_day_value

    # Fallback: search info fields
    info_sections_selectors = 'ul.lf-meta, div.lf-info, ul.c27-listing-details-list, div.job-details-content, div.content-block'
    info_sections = soup.select(info_sections_selectors)
    for section in info_sections:
        list_items_selectors = 'li, div.info-field, div.detail-field'
        list_items = section.select(list_items_selectors)
        for li in list_items:
            label_element_selectors = 'div.info-head, span.field-label, strong.key, dt'
            label_element = li.select_one(label_element_selectors)
            if label_element:
                label_text = label_element.text.strip().lower()
                if any(keyword in label_text for keyword in ['dostawa', 'dzień dostawy', 'delivery day']):
                    value_element_selectors = 'div.info-body, span.field-content, div.value, dd'
                    value_element = li.select_one(value_element_selectors)
                    if value_element and value_element.text.strip():
                        delivery_day_value = value_element.text.strip()
                        # print(f'[parse_delivery_day_from_detail_html] Delivery day from info field: {delivery_day_value}')
                        return delivery_day_value

    # Fallback for .e-dostawa-badge
    delivery_badge_element = soup.select_one('.e-dostawa-badge')
    if delivery_badge_element and delivery_badge_element.text.strip():
        delivery_day_value = delivery_badge_element.text.strip()
        # print(f'[parse_delivery_day_from_detail_html] Delivery day from badge: {delivery_day_value}')
        return delivery_day_value

    # print('[parse_delivery_day_from_detail_html] Delivery day not found in detail HTML.')
    return None


# --- Helper function to parse basic shop info from preview HTML (similar to Dart's Shop.fromPreviewElement) ---
def parse_shop_from_preview_element(element_html):
    soup = BeautifulSoup(str(element_html), 'html.parser')  # Ensure it's a soup object

    name_el = soup.select_one('h4.listing-preview-title')
    name = name_el.text.strip() if name_el else 'N/A'

    details_url_el = soup.select_one('a')
    details_url = details_url_el['href'] if details_url_el and 'href' in details_url_el.attrs else None

    address = 'N/A'
    address_li_element = None
    contact_list_items = soup.select('ul.lf-contact > li')
    for li in contact_list_items:
        if li.select_one('i.icon-location-pin-add-2'):
            address_li_element = li
            break

    if address_li_element:
        icon_element = address_li_element.select_one('i.icon-location-pin-add-2')
        if icon_element and icon_element.parent:
            icon_index = -1
            try:
                icon_index = icon_element.parent.contents.index(icon_element)
            except ValueError:
                pass

            if icon_index != -1 and (icon_index + 1) < len(icon_element.parent.contents):
                next_sibling = icon_element.parent.contents[icon_index + 1]
                if isinstance(next_sibling, str):
                    address = next_sibling.strip()
                else:
                    address = address_li_element.text.strip().replace(icon_element.text.strip(), '').strip()
            else:
                address = address_li_element.text.strip().replace(icon_element.text.strip(), '').strip()
        else:
            address = address_li_element.text.strip()

        icon_text_for_check = icon_element.text.strip() if icon_element else ''
        if address == icon_text_for_check:
            address = address_li_element.text.strip().replace(address, '').strip()
        if not address and address_li_element.text.strip():
            address = address_li_element.text.strip()

    # --- RE-ADD LAT/LNG PARSING ---
    lat, lng = None, None
    # The 'data-locations' attribute is on the 'element_html' itself (the div.lf-item-container)
    # So, we need to parse it from the original element passed to this function, not 'soup' if 'soup' is just a sub-part.
    # Assuming 'element_html' is the direct BeautifuSoup object for 'div.lf-item-container'
    locations_data_str = element_html.get('data-locations')
    if locations_data_str:
        try:
            locations_json = json.loads(locations_data_str)
            if isinstance(locations_json, list) and locations_json:
                first_location = locations_json[0]
                lat_str = first_location.get('lat')
                lng_str = first_location.get('lng')
                if lat_str: lat = float(lat_str)
                if lng_str: lng = float(lng_str)
                # Fallback for address if not well parsed and available in location data
                if (address == 'N/A' or not address.strip()) and first_location.get('address'):
                    address = first_location.get('address', 'N/A')
        except (json.JSONDecodeError, TypeError, ValueError) as e:
            print(f"Error parsing data-locations for {name}: {e}")
    # --- END LAT/LNG PARSING ---

    opening_hours = 'N/A'
    opening_hours_li_element = None
    for li in contact_list_items:
        if li.select_one('i.mi.access_time'):
            opening_hours_li_element = li
            break

    if opening_hours_li_element:
        span_next_to_icon = opening_hours_li_element.select_one('span')
        if span_next_to_icon:
            opening_hours = span_next_to_icon.text.strip()
        else:
            icon_text = opening_hours_li_element.select_one(
                'i.mi.access_time').text.strip() if opening_hours_li_element.select_one('i.mi.access_time') else ''
            opening_hours = opening_hours_li_element.text.strip().replace(icon_text, '').strip()

    if opening_hours == 'N/A':
        head_buttons = soup.select('div.lf-head > div.lf-head-btn')
        for btn in head_buttons:
            btn_text = btn.text.strip().upper()
            if btn_text == 'OTWARTE' or btn_text == 'ZAMKNIĘTE' or btn_text == 'TYLKO PO UMÓWIENIU' or ':' in btn_text:
                opening_hours = btn.text.strip()
                break

    # Rating parsing
    rating = 0.0
    rating_element = soup.select_one('div.listing-rating.rating-preview-card')
    if rating_element:
        full_stars = len(rating_element.select('i.mi.star'))
        half_stars = len(rating_element.select('i.mi.star_half'))
        rating = float(full_stars + half_stars * 0.5)
    else:
        rating = None  # Or 0.0, or 'N/A' depending on preference

    # --- COMBINE lat and lng into a location string ---
    location_str = None
    if lat is not None and lng is not None:
        location_str = f"{lat},{lng}"

    shop_dict = {
        'name': name,
        'address': address,
        'location': location_str,
        'opening_hours': opening_hours,
        'delivery_day': None,
        'rating': rating,
        'details_url': details_url
    }
    return shop_dict # Return only the dictionary


# --- Async helper to fetch HTML content ---
async def fetch_detail_html(session, url):
    if not url:
        print(f"[fetch_detail_html] Empty URL received, skipping fetch.")
        return None
    try:
        # print(f"[fetch_detail_html] Fetching: {url}")
        async with session.get(url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'}) as response:
            response.raise_for_status()  # raise an error for bad status codes
            html_content = await response.text()
            # print(f"[fetch_detail_html] Successfully fetched: {url}")
            return html_content
    except aiohttp.ClientError as e:
        print(f"[fetch_detail_html] Error fetching {url}: {e}")
        return None
    except Exception as e:
        print(f"[fetch_detail_html] Generic error fetching {url}: {e}")
        return None


# --- Main async function to fetch and process shops ---
async def fetch_shops_python_async():
    base_url = "https://secondhandy.com.pl/"
    security_nonce = "20a291621f"

    form_data_params = {
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
    }

    encoded_form_data_parts = []
    for key, value in form_data_params.items():
        encoded_form_data_parts.append(f"form_data[{urllib.parse.quote(key)}]={urllib.parse.quote(value)}")
    encoded_form_data_str = "&".join(encoded_form_data_parts)

    query_params = {
        'mylisting-ajax': '1',
        'action': 'get_listings',
        'security': security_nonce,
        'listing_type': 'place',
        'listing_wrap': 'col-md-12 grid-item',
        'proximity_units': 'km',
    }
    initial_query = urllib.parse.urlencode(query_params)
    full_url = f"{base_url}?{initial_query}&{encoded_form_data_str}"

    print(f"[fetch_shops_python_async] Fetching initial shop list from: {full_url}")
    all_shops_data = []

    try:
        # Initial request for the list of shops (still using requests for simplicity here, could also be aiohttp)
        response = requests.get(full_url, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36'})
        response.raise_for_status()
        json_data = response.json()
        html_from_api = json_data.get('html')

        if html_from_api:
            soup = BeautifulSoup(html_from_api, 'html.parser')
            shop_elements = soup.select('div.lf-item-container')
            print(
                f"[fetch_shops_python_async] Parsed {len(shop_elements)} preview shops. Now fetching details concurrently...")

            preview_shops_data_list = []
            for el in shop_elements:
                try:
                    # parse_shop_from_preview_element now expects the element itself
                    # and returns a single dictionary.
                    parsed_shop_dict = parse_shop_from_preview_element(el)
                    preview_shops_data_list.append(parsed_shop_dict)
                except Exception as e:
                    print(f"[fetch_shops_python_async] Error parsing one preview shop element: {e}")

            async with aiohttp.ClientSession() as session:
                tasks = []
                for shop_item_dict in preview_shops_data_list:
                    details_url = shop_item_dict.get('details_url')
                    if details_url:
                        tasks.append(fetch_detail_html(session, details_url))
                    else:
                        # Add a dummy completed future for shops with no URL to maintain order
                        tasks.append(asyncio.sleep(0, result=None))

                detail_htmls = await asyncio.gather(*tasks)
                print(f"[fetch_shops_python_async] Finished fetching all {len(detail_htmls)} detail HTMLs.")

            all_shops_data = []
            for i, shop_item_dict in enumerate(preview_shops_data_list):
                if i < len(detail_htmls) and detail_htmls[i]:
                    delivery_day = parse_delivery_day_from_detail_html(detail_htmls[i])
                    shop_item_dict['delivery_day'] = delivery_day
                all_shops_data.append(shop_item_dict)
                print(
                    f"[fetch_shops_python_async] Final shop data: Name: {shop_item_dict['name']}, Location: {shop_item_dict.get('location', 'N/A')}, Delivery: {shop_item_dict.get('delivery_day', 'N/A')}, Rating: {shop_item_dict.get('rating', 'N/A')}")
        else:
            print("[fetch_shops_python_async] Error: 'html' key not found in JSON response or is null.")

    except requests.exceptions.RequestException as e:
        print(f"[fetch_shops_python_async] Error fetching initial shop list: {e}")
    except json.JSONDecodeError as e:
        print(f"[fetch_shops_python_async] Error decoding JSON from initial response: {e}")
    except Exception as e:
        print(f"[fetch_shops_python_async] An unexpected error occurred: {e}")

    return all_shops_data


# --- NEW: Import Firebase Admin SDK ---
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
import hashlib # For potentially creating more unique IDs

# --- NEW: Initialize Firebase Admin App ---
# Replace 'serviceAccountKey.json' with the actual path to your key if it's different.
FB_CREDENTIALS_PATH = "serviceAccountKey.json"
FB_INITIALIZED = False
db = None # Initialize db to None
try:
    cred = credentials.Certificate(FB_CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client() # Get Firestore client
    FB_INITIALIZED = True
    print("Firebase Admin SDK initialized successfully.")
except FileNotFoundError:
    print(f"ERROR: Firebase service account key not found at {FB_CREDENTIALS_PATH}.")
    print("Please download it from Firebase Console > Project Settings > Service Accounts and place it correctly.")
except Exception as e:
    print(f"Error initializing Firebase Admin SDK: {e}")

# --- NEW: Function to delete all documents in a collection ---
def delete_collection(coll_ref, batch_size):
    """Deletes all documents in a collection in batches."""
    docs = coll_ref.limit(batch_size).stream()
    deleted = 0

    for doc in docs:
        print(f"  Deleting doc {doc.id} => {doc.to_dict()}")
        doc.reference.delete()
        deleted += 1

    if deleted >= batch_size:
        return delete_collection(coll_ref, batch_size) # Recursive call to delete remaining
    
    return deleted # Return number of deleted documents in the last batch run

# --- Main execution block ---
if __name__ == "__main__":
    print("Starting Python script to fetch shop data...")
    # In Python 3.7+ you can use asyncio.run()
    fetched_shops = asyncio.run(fetch_shops_python_async())

    if fetched_shops:
        print(f"\n--- Successfully fetched {len(fetched_shops)} shops from website ---")

        if FB_INITIALIZED and db: # Check if db client is available
            print("\nStarting Firestore upload...")

            # --- NEW: Delete existing documents in 'storelist' collection ---
            print("Attempting to clear existing 'storelist' collection...")
            storelist_coll_ref = db.collection('storelist')
            try:
                num_deleted = delete_collection(storelist_coll_ref, 100) # Using a batch size of 100
                print(f"Successfully deleted {num_deleted} documents from 'storelist' collection.")
            except Exception as e:
                print(f"Error deleting collection 'storelist': {e}")
                print("Continuing with data upload, duplicates might occur or old data might persist.")
            # --- END: Deleting collection ---

            shops_uploaded_count = 0
            shops_skipped_count = 0
            shops_failed_count = 0

            for i, shop_data in enumerate(fetched_shops):
                shop_name = shop_data.get('name')
                details_url = shop_data.get('details_url')
                location = shop_data.get('location')

                print(f"\nProcessing shop {i + 1}/{len(fetched_shops)}: {shop_name or 'N/A'}")

                if not shop_name or shop_name == 'N/A':
                    print(f"  SKIPPING: Shop name is missing or 'N/A'.")
                    shops_skipped_count +=1
                    continue
                
                if location is None or location == 'N/A':
                    print(f"  SKIPPING: Location is missing or 'N/A' for '{shop_name}'. Cannot be shown on map.")
                    shops_skipped_count += 1
                    continue

                # --- MODIFIED: Create a document ID from sanitized shop_name ---
                # Firestore document IDs cannot contain '/', be solely '.' or '..', or be empty.
                # Replace common problematic characters. This is a basic sanitization.
                # Consider a more robust slugify function if names are complex.
                sanitized_name = shop_name.replace('/', '-').replace('.', '') # Replace / with - and remove .
                sanitized_name = "".join(c for c in sanitized_name if c.isalnum() or c in [' ', '-', '_']).strip()
                doc_id = sanitized_name
                if not doc_id: # If name becomes empty after sanitization
                    print(f"  SKIPPING: Shop name '{shop_name}' became empty after sanitization.")
                    shops_skipped_count += 1
                    continue
                # --- END: Modified Document ID ---
                
                print(f"  Using Document ID: {doc_id}")

                # --- MODIFIED: Prepare data for Firestore with combined location string ---
                location_value_for_firestore = shop_data.get('location') # Get the combined string

                firestore_shop_data = {
                    'name': shop_name,
                    'address': shop_data.get('address'),
                    'location': location_value_for_firestore,
                    'opening_hours': shop_data.get('opening_hours'),
                    'delivery_day': shop_data.get('delivery_day'),
                    'rating': shop_data.get('rating'),
                    'details_url': details_url,
                    'scraped_at': firestore.SERVER_TIMESTAMP
                }
                
                # Remove keys with None values if you prefer not to store them as null in Firestore
                # firestore_shop_data = {k: v for k, v in firestore_shop_data.items() if v is not None}


                try:
                    db.collection('storelist').document(doc_id).set(firestore_shop_data, merge=True) # ZMIANA TUTAJ: 'stores' -> 'storelist'
                    print(f"  SUCCESS: '{shop_name}' written to Firestore in collection 'storelist'.")
                    shops_uploaded_count += 1
                except Exception as e:
                    print(f"  ERROR writing '{shop_name}' to Firestore: {e}")
                    shops_failed_count += 1
            
            print(f"\n--- Firestore Upload Summary ---")
            print(f"  Successfully uploaded/updated: {shops_uploaded_count}")
            print(f"  Skipped (missing data):      {shops_skipped_count}")
            print(f"  Failed to upload:            {shops_failed_count}")

        else:
            print("\nFirebase Admin SDK not initialized. Skipping Firestore upload.")
            print("Please check Firebase credential setup (serviceAccountKey.json).")
            print("\n--- Fetched Shop Data Summary (Local Display Only) ---")
            for i_shop, shop_item in enumerate(fetched_shops):
                print(f"\n--- Shop {i_shop + 1} / {len(fetched_shops)} ---")
                print(f"  Name:          {shop_item.get('name', 'N/A')}")
                print(f"  Address:       {shop_item.get('address', 'N/A')}")
                print(f"  Location:      {shop_item.get('location', 'N/A')}")
                print(f"  Opening Hours: {shop_item.get('opening_hours', 'N/A')}")
                print(f"  Delivery Day:  {shop_item.get('delivery_day', 'N/A')}")
                print(f"  Rating:        {shop_item.get('rating', 'N/A')}")
                print(f"  Details URL:   {shop_item.get('details_url', 'N/A')}")

    else:
        print("\nNo shops fetched from website or an error occurred during scraping.") 