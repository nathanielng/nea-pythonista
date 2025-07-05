#!/usr/bin/env python3

import json
import math
import requests
import os
import urllib.parse

from strands import tool
from typing import Dict, Any, Optional


collection_ids = {
    '2hr-historical': 2179,
    '24hr-historical': 2213,
    '4day-historical': 2212,
    'weatherforecast': 1456
}
valid_collection_ids = [ id for id in collection_ids.values() ]

url_list = {
    '2hr-realtime': 'https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast',
    '24hr-realtime': 'https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast',
    '4day-realtime': 'https://api-open.data.gov.sg/v2/real-time/api/four-day-outlook'
}

# Approximate center points for each region in Singapore
region_coordinates = {
    'north': {'latitude': 1.41, 'longitude': 103.82},   # Woodlands/Yishun area
    'south': {'latitude': 1.28, 'longitude': 103.85},   # Downtown/Southern Islands
    'east': {'latitude': 1.35, 'longitude': 103.94},    # Tampines/Changi area
    'west': {'latitude': 1.35, 'longitude': 103.70},    # Jurong/Choa Chu Kang area
    'central': {'latitude': 1.35, 'longitude': 103.82}  # Central area
}


def get_collection_metadata(collection_id: int):
    """
    Retrieves metadata for a collection from the data.gov.sg API.
    
    This function makes a GET request to the data.gov.sg API to fetch metadata 
    for a specific collection identified by its ID. The metadata typically includes
    information about the collection's contents, structure, and other relevant details.
    
    Args:
        collection_id (int): The unique identifier of the collection to retrieve metadata for
        
    Returns:
        dict: A dictionary containing the collection metadata in JSON format if the request is successful
        None: If the request fails or returns a non-200 status code
    """

    if collection_id not in valid_collection_ids:
        print(f'Invalid collection id: {collection_id}.')
        return None

    URL_TEMPLATE = "https://api-production.data.gov.sg/v2/public/api/collections/{collection_id}/metadata"
    url = URL_TEMPLATE.format(collection_id)

    response = requests.get(url)
    if response.status_code == 200:
        return response.json()
    else:
        print(f'Error parsing json data from {url}. Status code: {response.status_code}')
        return None


def get_forecast(id: str):
    """
    Get weather forecast data from the data.gov.sg API based on the forecast type ID.
    
    Args:
        id (str): The forecast type ID ('2hr-realtime', '24hr-realtime', or '4day-realtime')
        
    Returns:
        dict: JSON response containing the forecast data if successful, None otherwise
    """
    if id in url_list:
        url = url_list[id]
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        else:
            print(f'Error parsing json data from {url}. Status code: {response.status_code}')
            return None
    else:
        print(f'Error: {id} not found in url_list')
        return None


def save_json(response, filename):
    with open(filename, 'w') as f:
        f.write(json.dumps(response, indent=2))


def convert_weather_data(data):
    """
    Convert the weather data from the input file format to the required output format.
    
    Args:
        input_file (str): Path to the input JSON file
        output_file (str): Path to save the output JSON file
    """
    
    # Create a dictionary to map area names to their coordinates
    area_coords = {}
    for area in data['data']['area_metadata']:
        area_coords[area['name']] = {
            'latitude': area['label_location']['latitude'],
            'longitude': area['label_location']['longitude']
        }
    
    # Extract the forecast data and valid period
    forecasts = data['data']['items'][0]['forecasts']
    valid_period = data['data']['items'][0]['valid_period']
    start_time = valid_period['start']
    end_time = valid_period['end']
    
    # Create the new data structure
    weather_data_2hr = []
    
    for forecast_item in forecasts:
        area_name = forecast_item['area']
        if area_name in area_coords:
            weather_data_2hr.append({
                'location_name': area_name,
                'latitude': area_coords[area_name]['latitude'],
                'longitude': area_coords[area_name]['longitude'],
                'forecast': forecast_item['forecast'],
                'start': start_time,
                'end': end_time
            })
    return weather_data_2hr


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(math.radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    r = 6371  # Radius of earth in kilometers
    return c * r


@tool
def geocode_address(address_or_postal: str):
    """
    Converts a Singapore address or postal code to latitude and longitude coordinates
    using the OneMap API (for Singapore addresses) or Nominatim API (for global addresses).
    
    Args:
        address_or_postal (str): Address or postal code to geocode
        
    Returns:
        tuple[float, float]: (latitude, longitude) coordinates or None if geocoding fails
    """
    # First try OneMap API for Singapore addresses
    try:
        # Check if input is a Singapore postal code (6 digits)
        is_sg_postal = address_or_postal.isdigit() and len(address_or_postal) == 6
        
        # Construct the OneMap API URL
        encoded_address = urllib.parse.quote(address_or_postal)
        onemap_url = f"https://developers.onemap.sg/commonapi/search?searchVal={encoded_address}&returnGeom=Y&getAddrDetails=Y"
        
        response = requests.get(onemap_url)
        if response.status_code == 200:
            data = response.json()
            if data.get('found') > 0:
                # Get the first result
                result = data['results'][0]
                return float(result['LATITUDE']), float(result['LONGITUDE'])
    except Exception as e:
        print(f"OneMap API error: {e}")
    
    # Fall back to Nominatim API for non-Singapore addresses
    try:
        # Use Nominatim API with proper user-agent
        nominatim_url = "https://nominatim.openstreetmap.org/search"
        headers = {
            'User-Agent': 'NEA Weather App/1.0'
        }
        params = {
            'q': address_or_postal,
            'format': 'json',
            'limit': 1
        }
        
        response = requests.get(nominatim_url, headers=headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data and len(data) > 0:
                return float(data[0]['lat']), float(data[0]['lon'])
    except Exception as e:
        print(f"Nominatim API error: {e}")
    
    return None


def get_nearest_location_from_lat_long(lat: float, long: float):
    """
    Find the nearest weather station location, for a location specified by
    latitude and longitude coordinates
    
    Args:
        lat (float): Latitude of the target location
        long (float): Longitude of the target location
        
    Returns:
        dict: Dictionary containing weather information for the nearest location
    """
    # List of dictionaries containing weather data for different locations
    weather_data_2hr = init_or_refresh_2hr_data()

    # Find the nearest location
    nearest_location = None
    min_distance = float('inf')
    
    for location in weather_data_2hr:
        distance = haversine_distance(
            lat, long, 
            location['latitude'], 
            location['longitude'])
        if distance < min_distance:
            min_distance = distance
            nearest_location = location
    return nearest_location



def get_nearest_location_by_address(address_or_postal: str):
    """
    Get nearest weather station location, for a location
    specified by address or postal code.
    
    Args:
        address_or_postal (str): Address or postal code
        
    Returns:
        dict: Dictionary containing weather information for the nearest location or None if geocoding fails
    """
    # First geocode the address to get coordinates
    coords = geocode_address(address_or_postal)
    
    if coords:
        lat, long = coords
        # Then find the nearest weather location
        return get_nearest_location_from_lat_long(lat, long)
    else:
        print(f"Could not geocode address: {address_or_postal}")
        return None


def get_region_from_coordinates(latitude: float, longitude: float) -> str:
    """
    Maps latitude and longitude coordinates to one of the five regions in Singapore
    (north, south, east, west, central).
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        
    Returns:
        str: Region name ('north', 'south', 'east', 'west', or 'central')
    """
    # Find the nearest region based on distance
    min_distance = float('inf')
    nearest_region = None
    
    for region, coords in region_coordinates.items():
        distance = haversine_distance(
            latitude, longitude,
            coords['latitude'], coords['longitude']
        )
        if distance < min_distance:
            min_distance = distance
            nearest_region = region
    
    return nearest_region


def get_region_from_address(address_or_postal: str) -> str:
    """
    Maps an address or postal code to one of the five regions in Singapore
    (north, south, east, west, central).
    
    Args:
        address_or_postal (str): Address or postal code
        
    Returns:
        str: Region name ('north', 'south', 'east', 'west', or 'central') or None if geocoding fails
    """
    # First geocode the address to get coordinates
    coords = geocode_address(address_or_postal)
    
    if coords:
        latitude, longitude = coords
        # Then determine the region
        return get_region_from_coordinates(latitude, longitude)
    else:
        print(f"Could not geocode address: {address_or_postal}")
        return None


def organize_weather_by_region(data):
    """
    Organizes 24hr weather forecast data by regions (west, east, central, south, north).
    
    Args:
        data (dict): Dictionary containing weather data in the format of 24hr-realtime.json
        
    Returns:
        dict: Dictionary organized by regions with all relevant weather forecast information
    """
    if not data or 'data' not in data or 'records' not in data['data'] or not data['data']['records']:
        return None
    
    # Get the first record (most recent forecast)
    record = data['data']['records'][0]
    
    # Extract general weather information
    general_info = record.get('general', {})
    
    # Initialize the result structure
    result = {
        'timestamp': record.get('timestamp'),
        'date': record.get('date'),
        'updatedTimestamp': record.get('updatedTimestamp'),
        'general': general_info,
        'regions': {
            'west': {'forecasts': []},
            'east': {'forecasts': []},
            'central': {'forecasts': []},
            'south': {'forecasts': []},
            'north': {'forecasts': []}
        }
    }
    
    # Process each time period
    for period in record.get('periods', []):
        time_period = period.get('timePeriod', {})
        regions_data = period.get('regions', {})
        
        # For each region, add the forecast for this time period
        for region in ['west', 'east', 'central', 'south', 'north']:
            if region in regions_data:
                forecast_entry = {
                    'timePeriod': time_period,
                    'forecast': regions_data[region]
                }
                result['regions'][region]['forecasts'].append(forecast_entry)
    
    return result


def get_weather_for_singapore_coordinates(latitude: float, longitude: float):
    """
    Returns weather forecast data for the region nearest to the given coordinates.
    
    Args:
        latitude (float): Latitude coordinate
        longitude (float): Longitude coordinate
        
    Returns:
        dict: Weather forecast data for the nearest region or None if organized_data 
              doesn't contain region information
    """
    # [dict] Weather data organized by regions from organize_weather_by_region()
    weather_data_24hr = init_or_refresh_24hr_data()

    # Get the region for the coordinates
    region = get_region_from_coordinates(latitude, longitude)
    
    # Check if weather_data_24hr has the required structure
    if not weather_data_24hr or 'regions' not in weather_data_24hr or region not in weather_data_24hr['regions']:
        return None
    
    # Create a result dictionary with general info and region-specific forecasts
    result = {
        'coordinates': {'latitude': latitude, 'longitude': longitude},
        'region': region,
        'timestamp': weather_data_24hr.get('timestamp'),
        'date': weather_data_24hr.get('date'),
        'updatedTimestamp': weather_data_24hr.get('updatedTimestamp'),
        'general': weather_data_24hr.get('general', {}),
        'forecasts': weather_data_24hr['regions'][region].get('forecasts', [])
    }
    
    return result

@tool
def get_weather_for_singapore_address(address_or_postal: str):
    """
    Returns the Singapore weather forecast data for the region nearest
    to the given address or postal code.
    
    Args:
        address_or_postal (str): Address or postal code
        weather_data_24hr (dict): Weather data organized by regions from organize_weather_by_region()
        
    Returns:
        dict: Weather forecast data for the nearest region or None if geocoding fails
              or if weather_data_24hr doesn't contain region information
    """    
    weather_data_24hr = init_or_refresh_24hr_data()

    # Get the region for the address
    region = get_region_from_address(address_or_postal)
    
    if not region:
        return None
    
    # Check if weather_data_24hr has the required structure
    if not weather_data_24hr or 'regions' not in weather_data_24hr or region not in weather_data_24hr['regions']:
        return None
    
    # Create a result dictionary with general info and region-specific forecasts
    result = {
        'address': address_or_postal,
        'region': region,
        'timestamp': weather_data_24hr.get('timestamp'),
        'date': weather_data_24hr.get('date'),
        'updatedTimestamp': weather_data_24hr.get('updatedTimestamp'),
        'general': weather_data_24hr.get('general', {}),
        'forecasts': weather_data_24hr['regions'][region].get('forecasts', [])
    }
    return result


def init_or_refresh_2hr_data():
    response = get_forecast('2hr-realtime')
    save_json(response, '2hr-realtime.json')

    weather_data_2hr = convert_weather_data(response)
    save_json(weather_data_2hr, 'converted-weather-data.json')

    return weather_data_2hr


def init_or_refresh_24hr_data():
    response_24hr = get_forecast('24hr-realtime')
    save_json(response_24hr, '24hr-realtime.json')
    
    weather_data_24hr = organize_weather_by_region(response_24hr)
    save_json(weather_data_24hr, 'organized-weather-by-region.json')

    return weather_data_24hr

def demo():
    # Example of using the geocoding and weather lookup functions
    address = "Orchard Road, Singapore"
    weather = get_weather_for_singapore_address(address)
    if weather:
        print(f"Weather for {address}: {weather['forecast']}")

    # Example of using the new function to get weather for a specific address region
    address = "Changi Airport, Singapore"
    region_weather = get_weather_for_singapore_address(address)
    if region_weather:
        print(f"Weather for {address} (in {region_weather['region']} region):")
        for forecast in region_weather['forecasts']:
            print(f"  {forecast['timePeriod']['start']} to {forecast['timePeriod']['end']}: {forecast['forecast']}")

    # Example of using the new function to get weather for specific coordinates
    lat, lon = 1.3644, 103.9915  # Example coordinates near Changi
    region_weather = get_weather_for_coordinates_region(lat, lon)
    if region_weather:
        print(f"Weather for coordinates ({lat}, {lon}) in {region_weather['region']} region:")
        for forecast in region_weather['forecasts']:
            print(f"  {forecast['timePeriod']['start']} to {forecast['timePeriod']['end']}: {forecast['forecast']}")


weather_data_2hr = init_or_refresh_2hr_data()
weather_data_24hr = init_or_refresh_24hr_data()


if __name__ == '__main__':
    demo()
