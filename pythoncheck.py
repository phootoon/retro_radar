import requests
import json
from bs4 import BeautifulSoup
import urllib.parse

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
        response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}) # Added a User-Agent
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        print(f"Response Status Code: {response.status_code}")
        # print(f"Response Headers: {response.headers}")
        # print(f"Response Content (first 500 chars): {response.text[:500]}\\n")


        try:
            data = response.json()
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON: {e}")
            print("Response text was:")
            print(response.text[:1000]) # Print more of the response if JSON decoding fails
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
                elif address_parts: # Fallback to joined stripped_strings if specific structure not found
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
            opening_hours_tag = element.select_one('ul.lf-contact li span') # General span in contact
            opening_hours_specific_icon = element.select_one('ul.lf-contact li i.mi.access_time') # Icon specific
            
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
                    if text.upper() in ["OTWARTE", "ZAMKNIĘTE", "TYLKO PO UMÓWIENIU"] or ":" in text: # Check for time like format
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
            
            print(f"--- Shop {i+1} ---")
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

if __name__ == '__main__':
    print("Starting Python shop fetcher...")
    fetched_shops = fetch_shops_python()
    if fetched_shops:
        print(f"\\nSuccessfully fetched and parsed {len(fetched_shops)} shops.")
    else:
        print("\\nNo shops fetched or an error occurred.") 