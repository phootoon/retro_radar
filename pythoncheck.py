import requests
import json
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import aiohttp
import firebase_admin
from firebase_admin import credentials, storage
import re
import io
import uuid

# --- Firebase Initialization ---
# Global variable to ensure Firebase is initialized only once
_firebase_initialized = False

def initialize_firebase(service_account_key_path=None, storage_bucket=None):
    global _firebase_initialized
    if not _firebase_initialized:
        if not storage_bucket:
            print("Firebase Storage bucket must be provided for initialization.")
            return False
        try:
            if service_account_key_path:
                cred = credentials.Certificate(service_account_key_path)
                firebase_admin.initialize_app(cred, {'storageBucket': storage_bucket})
            else: # Rely on GOOGLE_APPLICATION_CREDENTIALS
                # Check if default app already exists (can happen in some environments)
                if not firebase_admin._apps:
                    firebase_admin.initialize_app(options={'storageBucket': storage_bucket})
                else:
                    # If default app exists, ensure our target bucket is accessible
                    # This part is tricky if multiple initializations are attempted with different buckets.
                    # For this script, assume one init or GOOGLE_APP_CREDS points to the correct project.
                    print("Firebase app already initialized. Using existing app with specified bucket.")
                    # We might need to get a specific bucket instance if the default doesn't match.
                    # However, storage.bucket() without args should use the initialized app's bucket.
                    pass 

            print(f"Firebase Admin SDK initialized (or was already initialized) for bucket: {storage_bucket}")
            _firebase_initialized = True
            return True
        except Exception as e:
            print(f"Error initializing Firebase Admin SDK: {e}")
            print("Please ensure GOOGLE_APPLICATION_CREDENTIALS is set OR a valid service_account_key_path and storage_bucket are provided.")
            _firebase_initialized = False # Explicitly set to false on error
            return False
    return True # Already successfully initialized

# --- Image Upload Function ---
def upload_image_to_firebase(image_url, shop_name):
    if not _firebase_initialized:
        print("Firebase not initialized. Skipping image upload.")
        return None
    if not image_url:
        print(f"No image URL provided for {shop_name}. Skipping upload.")
        return None
    try:
        # Ensure URL is absolute
        if image_url.startswith('//'):
            image_url = 'https:' + image_url
        elif image_url.startswith('/'):
            image_url = 'https://secondhandy.com.pl' + image_url

        response = requests.get(image_url, timeout=15)
        response.raise_for_status()
        image_data = io.BytesIO(response.content)
        content_type = response.headers.get('Content-Type', 'image/jpeg')
        file_extension = content_type.split('/')[-1] if '/' in content_type else 'jpg'

        bucket = storage.bucket() # Uses the initialized app's bucket
        safe_shop_name = re.sub(r'[^a-zA-Z0-9_-]', '_', shop_name)
        filename = f"shop_images/{safe_shop_name}_{uuid.uuid4()}.{file_extension}"
        blob = bucket.blob(filename)

        blob.upload_from_file(image_data, content_type=content_type)
        blob.make_public()
        print(f"Uploaded {image_url} to Firebase Storage as {filename}")
        return blob.public_url
    except requests.exceptions.Timeout:
        print(f"Timeout downloading image {image_url} for {shop_name}.")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error downloading image {image_url} for {shop_name}: {e}")
        return None
    except firebase_admin.exceptions.FirebaseError as e:
        print(f"Error uploading image to Firebase for {shop_name}: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during image processing for {shop_name} ({image_url}): {e}")
        return None

def fetch_shops_python():
    base_url = "https://secondhandy.com.pl/"
    security_nonce = "20a291621f"

    form_data_params = {
        'page': '0', 'preserve_page': 'false', 'search_location': '', 'lat': 'false',
        'lng': 'false', 'proximity': '30', 'region': 'poznan', 'search_keywords': '',
        'category': '', 'dostawa': '', 'tags': '', 'dodatkowe-informacje': '',
        'open-now': '', 'sort': 'data-dostawy',
    }
    encoded_form_data_parts = [f"form_data[{urllib.parse.quote(k)}]={urllib.parse.quote(v)}" for k, v in form_data_params.items()]
    encoded_form_data_str = "&".join(encoded_form_data_parts)

    query_params = {
        'mylisting-ajax': '1', 'action': 'get_listings', 'security': security_nonce,
        'listing_type': 'place', 'listing_wrap': 'col-md-12 grid-item', 'proximity_units': 'km',
    }
    url = f"{base_url}?{urllib.parse.urlencode(query_params)}&{encoded_form_data_str}"
    
    print(f"Requesting URL: {url}\\n")
    initial_shops_data = []

    try:
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20)
        response.raise_for_status()
        
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print(f"Response text was (first 1000 chars): {response.text[:1000]}")
            return []

        html_content = data.get('html')
        if not html_content:
            print(f"No 'html' content found in JSON response. Data: {data}")
            return []

        print(f"Found {data.get('found_posts', 0)} posts according to JSON response.")
        soup = BeautifulSoup(html_content, 'html.parser')
        shop_elements = soup.select('div.lf-item-container')
        print(f"Found {len(shop_elements)} shop elements for parsing.\\n")

        for i, element in enumerate(shop_elements):
            # Using a simplified call to parse_shop_from_preview_element
            # Note: parse_shop_from_preview_element expects a Tag, not a string for 'element_html'
            shop_data_preview, _ = parse_shop_from_preview_element(element) # details_url is not used here

            # Delivery day from preview (if available, otherwise remains None)
            delivery_day_tag = element.select_one('.e-dostawa-badge')
            shop_data_preview['delivery_day'] = delivery_day_tag.get_text(strip=True) if delivery_day_tag else None
            
            initial_shops_data.append(shop_data_preview)
            
            print(f"--- Shop {i+1} (Preview Parsed) ---")
            print(f"  Name: {shop_data_preview.get('name', 'N/A')}")
            print(f"  Address: {shop_data_preview.get('address', 'N/A')}")
            print(f"  Delivery: {shop_data_preview.get('delivery_day', 'N/A')}") # From preview
            print(f"  Opening: {shop_data_preview.get('opening_hours', 'N/A')}")
            print(f"  Rating: {shop_data_preview.get('rating', 'N/A')}")
            print("--------------------\n") # Corrected newline

    except requests.exceptions.RequestException as e:
        print(f"HTTP Request failed: {e}")
        traceback.print_exc()
        return [] # Return empty on request failure
    except Exception as e:
        print(f"An error occurred during initial fetch/parse: {e}")
        traceback.print_exc()
        return [] # Return empty on other critical failure

    processed_shops_data = []
    for shop_item_data in initial_shops_data:
        firebase_url = None
        if shop_item_data.get('original_image_url'):
            firebase_url = upload_image_to_firebase(
                shop_item_data['original_image_url'],
                shop_item_data.get('name', 'unknown_shop')
            )
        shop_item_data['firebase_photo_url'] = firebase_url
        processed_shops_data.append(shop_item_data)

    return processed_shops_data

def parse_delivery_day_from_detail_html(html_content):
    if not html_content:
        return None
    soup = BeautifulSoup(html_content, 'html.parser')
    delivery_day_value = None
    delivery_ul_element = soup.find('ul', attrs={'data-field': 'dostawa'})
    if delivery_ul_element:
        first_li_span = delivery_ul_element.find('li').find('span') if delivery_ul_element.find('li') else None
        if first_li_span and first_li_span.text.strip():
            return first_li_span.text.strip()

    info_sections_selectors = 'ul.lf-meta, div.lf-info, ul.c27-listing-details-list, div.job-details-content, div.content-block'
    info_sections = soup.select(info_sections_selectors)
    for section in info_sections:
        list_items_selectors = 'li, div.info-field, div.detail-field'
        list_items = section.select(list_items_selectors)
        for li_item in list_items: # Renamed to avoid conflict
            label_element_selectors = 'div.info-head, span.field-label, strong.key, dt'
            label_element = li_item.select_one(label_element_selectors)
            if label_element:
                label_text = label_element.text.strip().lower()
                if any(keyword in label_text for keyword in ['dostawa', 'dzień dostawy', 'delivery day']):
                    value_element_selectors = 'div.info-body, span.field-content, div.value, dd'
                    value_element = li_item.select_one(value_element_selectors)
                    if value_element and value_element.text.strip():
                        return value_element.text.strip()

    delivery_badge_element = soup.select_one('.e-dostawa-badge')
    if delivery_badge_element and delivery_badge_element.text.strip():
        return delivery_badge_element.text.strip()
    return None

def parse_shop_from_preview_element(element_html): # element_html is a BeautifulSoup Tag
    name_el = element_html.select_one('h4.listing-preview-title')
    name = name_el.text.strip() if name_el else 'N/A'

    details_url_el = element_html.select_one('a') 
    details_url = details_url_el['href'] if details_url_el and 'href' in details_url_el.attrs else ''

    address = 'N/A'
    address_li_element = None
    contact_list_items = element_html.select('ul.lf-contact > li')
    for li_item in contact_list_items: # Renamed to avoid conflict
        if li_item.select_one('i.icon-location-pin-add-2'):
            address_li_element = li_item
            break
    if address_li_element:
        icon_element = address_li_element.select_one('i.icon-location-pin-add-2')
        address_text_content = [s.strip() for s in address_li_element.stripped_strings if s.strip()]
        if icon_element:
            icon_text = icon_element.text.strip()
            address_text_content = [s for s in address_text_content if s != icon_text]
        address = " ".join(address_text_content) if address_text_content else address_li_element.text.strip()


    opening_hours = 'N/A'
    opening_hours_li_element = None
    for li_item in contact_list_items: # Renamed to avoid conflict
        if li_item.select_one('i.mi.access_time'):
            opening_hours_li_element = li_item
            break
    if opening_hours_li_element:
        span_next_to_icon = opening_hours_li_element.select_one('span')
        if span_next_to_icon:
            opening_hours = span_next_to_icon.text.strip()
        else: # Fallback if span is not directly there
            icon_text = opening_hours_li_element.select_one('i.mi.access_time').text.strip()
            opening_hours = opening_hours_li_element.text.strip().replace(icon_text, '').strip()

    if opening_hours == 'N/A': # Fallback for header status
        head_buttons = element_html.select('div.lf-head > div.lf-head-btn')
        for btn in head_buttons:
            btn_text = btn.text.strip()
            if btn_text.upper() in ["OTWARTE", "ZAMKNIĘTE", "TYLKO PO UMÓWIENIU"] or ':' in btn_text:
                opening_hours = btn_text
                break

    rating = None
    rating_element = element_html.select_one('div.listing-rating.rating-preview-card')
    if rating_element:
        full_stars = len(rating_element.select('i.mi.star'))
        half_stars = len(rating_element.select('i.mi.star_half'))
        rating = float(full_stars + half_stars * 0.5)

    original_image_url = None
    background_div = element_html.select_one('div.lf-background')
    if background_div and background_div.get('style'):
        style_attr = background_div['style']
        match = re.search(r"background-image:\s*url\\((['\"]?)(.*?)\\2\\)", style_attr) # Corrected regex for quotes
        if match:
            original_image_url = match.group(3) # Group 3 is the URL
            if original_image_url.startswith('//'):
                original_image_url = 'https:' + original_image_url
            elif original_image_url.startswith('/'):
                original_image_url = 'https://secondhandy.com.pl' + original_image_url
    
    shop_dict = {
        'name': name, 'address': address, 'opening_hours': opening_hours,
        'delivery_day': None, 'rating': rating,
        'original_image_url': original_image_url, 'firebase_photo_url': None
    }
    return shop_dict, details_url

async def fetch_detail_html(session, url):
    if not url: return None
    try:
        async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=15) as response:
            response.raise_for_status()
            return await response.text()
    except Exception as e: # Catch generic aiohttp client errors and others
        print(f"[fetch_detail_html] Error fetching {url}: {type(e).__name__} - {e}")
        return None

async def fetch_shops_python_async():
    print("Fetching shops asynchronously...")
    base_url = "https://secondhandy.com.pl/wp-admin/admin-ajax.php"
    page = 0
    all_shops_data_accumulated = []
    processed_shop_names = set()

    async with aiohttp.ClientSession() as session:
        while True:
            params = {
                'page': str(page), 'preserve_page': 'false', 'search_location': '', 'lat': 'false',
                'lng': 'false', 'proximity': '30', 'region': 'poznan', 'search_keywords': '',
                'category': '', 'dostawa': '', 'tags': '', 'dodatkowe-informacje': '',
                'open-now': '', 'sort': 'data-dostawy',
            }
            encoded_form_data_parts = [f"form_data[{urllib.parse.quote(k)}]={urllib.parse.quote(v)}" for k, v in params.items()]
            encoded_form_data_str = "&".join(encoded_form_data_parts)
            query_params = {
                'mylisting-ajax': '1', 'action': 'get_listings', 'security': '20a291621f',
                'listing_type': 'place', 'listing_wrap': 'col-md-12 grid-item', 'proximity_units': 'km',
            }
            initial_query = urllib.parse.urlencode(query_params)
            full_url = f"{base_url}?{initial_query}&{encoded_form_data_str}"

            print(f"[fetch_shops_python_async] Fetching page {page} from: {full_url}")

            try:
                async with session.get(full_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=20) as response:
                    response.raise_for_status()
                    json_data = await response.json()
                
                html_from_api = json_data.get('html')
                if not html_from_api:
                    print(f"[fetch_shops_python_async] No HTML content on page {page}. Assuming end of pages.")
                    break

                soup = BeautifulSoup(html_from_api, 'html.parser')
                shop_elements = soup.select('div.lf-item-container')
                if not shop_elements:
                    print(f"[fetch_shops_python_async] No shop elements found on page {page}. Assuming end of pages.")
                    break
                
                print(f"[fetch_shops_python_async] Page {page}: Parsed {len(shop_elements)} shops. Fetching details...")

                preview_shops_parsed = []
                for el in shop_elements:
                    try:
                        shop_data, details_url = parse_shop_from_preview_element(el)
                        if shop_data.get('name') not in processed_shop_names:
                             preview_shops_parsed.append({'data': shop_data, 'url': details_url})
                             processed_shop_names.add(shop_data.get('name')) # Add to set early
                        else:
                            print(f"[fetch_shops_python_async] Skipping duplicate (by name on page): {shop_data.get('name')}")
                    except Exception as e:
                        print(f"[fetch_shops_python_async] Error parsing preview element on page {page}: {e}")
                        traceback.print_exc()
                
                detail_tasks = [fetch_detail_html(session, shop_entry['url']) for shop_entry in preview_shops_parsed if shop_entry['url']]
                detail_htmls = await asyncio.gather(*detail_tasks)
                
                detail_html_idx = 0
                for shop_entry in preview_shops_parsed:
                    current_shop_data = shop_entry['data']
                    if shop_entry['url']: # If we attempted to fetch details
                        if detail_html_idx < len(detail_htmls) and detail_htmls[detail_html_idx]:
                            current_shop_data['delivery_day'] = parse_delivery_day_from_detail_html(detail_htmls[detail_html_idx])
                        detail_html_idx +=1

                    firebase_photo_url = None
                    if current_shop_data.get('original_image_url'):
                        firebase_photo_url = await asyncio.to_thread(
                            upload_image_to_firebase,
                            current_shop_data['original_image_url'],
                            current_shop_data.get('name', 'unknown_shop')
                        )
                    current_shop_data['firebase_photo_url'] = firebase_photo_url
                    
                    all_shops_data_accumulated.append(current_shop_data)
                    print(f"[fetch_shops_python_async] Added shop: {current_shop_data.get('name')} (Total: {len(all_shops_data_accumulated)})")

            except aiohttp.ClientError as e:
                print(f"[fetch_shops_python_async] ClientError on page {page}: {e}")
                break 
            except json.JSONDecodeError as e:
                # Need to get text from response if available, but response might be out of scope
                # For now, just log the error.
                print(f"[fetch_shops_python_async] JSONDecodeError on page {page}: {e}")
                break
            except Exception as e:
                print(f"[fetch_shops_python_async] Unexpected error on page {page}: {e}")
                traceback.print_exc()
                break
            
            page += 1
            # if page > 2: # For debugging: limit pages
            #     print("[fetch_shops_python_async] DEBUG: Stopping after 2 pages.")
            #     break
            await asyncio.sleep(1) # Small delay between page fetches

    return all_shops_data_accumulated

# --- Main execution block ---
if __name__ == "__main__":
    print("Starting Python script to fetch shop data...")

    # IMPORTANT: Configure Firebase Storage Bucket Name Here!
    YOUR_FIREBASE_STORAGE_BUCKET = "your-project-id.appspot.com"  # <--- CHANGE THIS TO YOUR BUCKET NAME
    # Optional: If you are not using GOOGLE_APPLICATION_CREDENTIALS env variable,
    # set the path to your service account key JSON file here.
    # SERVICE_ACCOUNT_KEY_PATH = "path/to/your/serviceAccountKey.json"
    # success = initialize_firebase(SERVICE_ACCOUNT_KEY_PATH, YOUR_FIREBASE_STORAGE_BUCKET)
    
    # Initialize Firebase (relies on GOOGLE_APPLICATION_CREDENTIALS if path is None)
    success = initialize_firebase(storage_bucket=YOUR_FIREBASE_STORAGE_BUCKET)

    if not success:
        print("Firebase initialization failed. Images will not be uploaded.")
        # Depending on requirements, you might want to exit or continue without image uploads.
        # For now, the script will continue, and upload_image_to_firebase will skip uploads.

    print("Running asynchronous version...")
    fetched_shops = asyncio.run(fetch_shops_python_async())
    
    if fetched_shops:
        print(f"\n--- Successfully fetched {len(fetched_shops)} shops ---")
        for i, shop in enumerate(fetched_shops):
            print(f"\n--- Shop {i+1} / {len(fetched_shops)} ---")
            print(f"  Name:          {shop.get('name', 'N/A')}")
            print(f"  Address:       {shop.get('address', 'N/A')}")
            print(f"  Opening Hours: {shop.get('opening_hours', 'N/A')}")
            print(f"  Delivery Day:  {shop.get('delivery_day', 'N/A')}")
            print(f"  Rating:        {shop.get('rating', 'N/A')}")
            print(f"  Original Img:  {shop.get('original_image_url', 'N/A')}") # Added for debugging
            print(f"  Firebase Photo: {shop.get('firebase_photo_url', 'N/A')}") # Added
    else:
        print("\nNo shops fetched or an error occurred.") 