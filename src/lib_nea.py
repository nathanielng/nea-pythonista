#!/usr/bin/env python

import argparse
import json
import requests


try:
    import console
    console.clear()
    ios_pythonista = True
except:
    ios_pythonista = False


urls = {
    '2hr': 'https://api.data.gov.sg/v1/environment/2-hour-weather-forecast',
    '24hr': 'https://api.data.gov.sg/v1/environment/24-hour-weather-forecast',
    '4d': 'https://api.data.gov.sg/v1/environment/4-day-weather-forecast',
    'temp': 'https://api.data.gov.sg/v1/environment/air-temperature',
    'psi': 'https://api.data.gov.sg/v1/environment/psi',
    'pm25': 'https://api.data.gov.sg/v1/environment/pm25',
    'uv': 'https://api.data.gov.sg/v1/environment/uv-index'
}


# ----- API Query Library -----
def t_query(key):
    """
    Returns the raw text from a query
    """
    resp = requests.get(urls[key])
    return resp.text


def d_query(key):
    """
    Returns a dictionary object from a query
    """
    return json.loads(t_query(key))


def d_pprint(d):
    return json.dumps(d, indent=2, ensure_ascii=False)


# ----- Parsers -----
def parse_areametadata(area_metadata):
    d = {}
    for area in area_metadata: 
        name = area['name']
        x = area['label_location']
        d[name] = [x['latitude'], x['longitude']]
    return d


def parse_forecasts(forecasts):
    d = {}
    for forecast in forecasts:
        name = forecast['area']
        x = forecast['forecast']
        d[name] = x
    return d


def parse_2hr(d):
    area_metadata = d['area_metadata']
    area_metadata = parse_areametadata(area_metadata)

    items = d['items'][0]
    forecasts = items['forecasts']
    forecasts = parse_forecasts(forecasts)


def main(args):
    d = d_query(args.key)
    parse_2hr(d)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--key')
    parser.add_argument('--lat', help='Latitude')
    parser.add_argument('--lon', help='Longitude')
    args = parser.parse_args()
    main(args)

