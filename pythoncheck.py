import requests
import json
from bs4 import BeautifulSoup
import urllib.parse
import asyncio
import aiohttp


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

            shops_data.append({
                'name': name,
                'address': address,
                'latitude': lat,
                'longitude': lng,
                'delivery_day': delivery_day,
                'opening_hours': opening_hours,
                'details_url': details_url,
            })

            print(f"--- Shop {i + 1} ---")
            print(f"  Name: {name}")
            print(f"  Address: {address}")
            print(f"  Lat/Lng: {lat}/{lng}")
            print(f"  Delivery: {delivery_day}")
            print(f"  Opening: {opening_hours}")
            print(f"  URL: {details_url}")
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
    details_url = details_url_el['href'] if details_url_el and 'href' in details_url_el.attrs else ''

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
                pass  # Icon not directly in parent.contents, may be nested

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
        if not address and address_li_element.text.strip():  # If address became empty, revert
            address = address_li_element.text.strip()

    lat, lng = None, None
    locations_data_attr = soup.get('data-locations')
    if locations_data_attr and locations_data_attr != "false":
        try:
            locations_data = json.loads(locations_data_attr)
            if locations_data and isinstance(locations_data, list) and locations_data[0]:
                first_loc = locations_data[0]
                lat_str = first_loc.get('lat')
                lng_str = first_loc.get('lng')
                lat = float(lat_str) if lat_str else None
                lng = float(lng_str) if lng_str else None
                if (address == 'N/A' or not address) and first_loc.get('address'):
                    address = first_loc.get('address')
        except (json.JSONDecodeError, TypeError, ValueError, IndexError) as e:
            print(f"[parse_shop_from_preview_element] Error parsing location for {name}: {e}")

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

    return {
        'name': name,
        'address': address,
        'latitude': lat,
        'longitude': lng,
        'opening_hours': opening_hours,
        'delivery_day': None,  # Initially None
        'details_url': details_url
    }


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

            preview_shops = []
            for el in shop_elements:
                try:
                    shop_data = parse_shop_from_preview_element(el)
                    preview_shops.append(shop_data)
                except Exception as e:
                    print(f"[fetch_shops_python_async] Error parsing one preview shop element: {e}")

            async with aiohttp.ClientSession() as session:
                tasks = []
                for shop_data in preview_shops:
                    if shop_data.get('details_url'):
                        tasks.append(fetch_detail_html(session, shop_data['details_url']))
                    else:
                        tasks.append(
                            asyncio.sleep(0, result=None))  # Add a dummy completed future for shops with no URL

                detail_htmls = await asyncio.gather(*tasks)

            print(f"[fetch_shops_python_async] Finished fetching all {len(detail_htmls)} detail HTMLs.")

            for i, shop_data in enumerate(preview_shops):
                if i < len(detail_htmls) and detail_htmls[i]:
                    delivery_day = parse_delivery_day_from_detail_html(detail_htmls[i])
                    shop_data['delivery_day'] = delivery_day
                all_shops_data.append(shop_data)
                print(
                    f"[fetch_shops_python_async] Final shop data: Name: {shop_data['name']}, Delivery: {shop_data['delivery_day']}")
        else:
            print("[fetch_shops_python_async] Error: 'html' key not found in JSON response or is null.")

    except requests.exceptions.RequestException as e:
        print(f"[fetch_shops_python_async] Error fetching initial shop list: {e}")
    except json.JSONDecodeError as e:
        print(f"[fetch_shops_python_async] Error decoding JSON from initial response: {e}")
    except Exception as e:
        print(f"[fetch_shops_python_async] An unexpected error occurred: {e}")

    return all_shops_data


# --- Main execution block ---
if __name__ == "__main__":
    print("Starting Python script to fetch shop data...")
    # In Python 3.7+ you can use asyncio.run()
    fetched_shops = asyncio.run(fetch_shops_python_async())

    if fetched_shops:
        print(f"\n--- Successfully fetched {len(fetched_shops)} shops ---")
        for i, shop in enumerate(fetched_shops):
            print(f"\n--- Shop {i + 1} / {len(fetched_shops)} ---")
            print(f"  Name:          {shop.get('name', 'N/A')}")
            print(f"  Address:       {shop.get('address', 'N/A')}")
            print(f"  Opening Hours: {shop.get('opening_hours', 'N/A')}")
            print(f"  Delivery Day:  {shop.get('delivery_day', 'N/A')}")
            print(f"  Latitude:      {shop.get('latitude', 'N/A')}")
            print(f"  Longitude:     {shop.get('longitude', 'N/A')}")
            print(f"  Details URL:   {shop.get('details_url', 'N/A')}")
    else:
        print("\nNo shops fetched or an error occurred.") 