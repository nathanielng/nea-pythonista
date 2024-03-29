#!/usr/bin/env python

import argparse
import datetime
import json
import math
import requests
import re
import urllib.parse

from pytz import timezone


try:
    import ui
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

LATITUDE = None
LONGITUDE = None


# ----- API Query Library -----
def parse_quote(url):
    return urllib.parse.quote(url)


def t_query(key):
    """
    Returns the raw text from a query
    """
    url = urls[key]
    resp = requests.get(url)
    return resp.text


def d_query(key):
    """
    Returns a dictionary object from a query
    """
    return json.loads(t_query(key))


def d_pprint(d, verbose=True):
    """
    Pretty prints a dictionary
    """
    txt = json.dumps(d, indent=2, ensure_ascii=False)
    if verbose is True:
        print(txt)
    return txt


# ----- Utilities -----
def hours_to_timestr(h):
    if h == 0:
        return "12am"
    elif h < 12:
        return f"{h}am"
    elif h == 12:
        return f"{h}pm"
    else:
        return f"{h-12}pm"


def timediff_to_timestr(t_now, tt):
    h_now = t_now.hour
    hh = tt.hour
    if t_now.day == tt.day:
        # Today
        txt = f"{hours_to_timestr(hh)}"
    else:
        # Tomorrow
        txt = f"{hours_to_timestr(hh)}"
    return txt


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
    
    try:
        forecasts = items['forecasts']
        forecasts = parse_forecasts(forecasts)
        return area_metadata, forecasts
    except:
        print(f'Error: No "forecasts" key in items={items}')
        return area_metadata, 'no forecast'


def parse_readings(d):
    region_metadata = d['region_metadata']    
    items = d['items'][0]
    return region_metadata, items['readings']


def parse_pm25(d):
    region_metadata, readings = \
        parse_readings(d)
    return region_metadata, readings['pm25_one_hourly']


def parse_psi(d):
    region_metadata, readings = \
        parse_readings(d)
    return region_metadata, readings


def parse_general_forecast(g):
    forecast = emojify(g['forecast'])
    t = g['temperature']
    rh = g['relative_humidity']
    wind = g['wind']
    w_speed = wind['speed']

    txt = f"24hr Forecast: {forecast}"
    txt += f", {t['low']}-{t['high']}°C"
    txt += f", {rh['low']}-{rh['high']}%RH"
    txt += f", {w_speed['low']}-{w_speed['high']} {wind['direction']}"
    return txt


def remove_timezone_colon(d):
    if d[-3:-2] == ':':
        return d[:-3] + d[-2:]
    else:
        return d


def emojify(x):
    x = re.sub('Thundery Showers', '⛈', x)
    x = re.sub('Cloudy', '☁️', x)
    x = re.sub('Fair', '🌤', x)
    x = re.sub('Windy', '💨', x)
    return x


def parse_periods(periods, by_period=True):
    now = datetime.datetime.now(timezone('Singapore'))
    fmt = "%Y-%m-%dT%H:%M:%S%z"
    txt = ""
    central_txt, north_txt, south_txt, east_txt, west_txt = '[Central]', '[North]', '[South]', '[East]', '[West]'
    for i, p in enumerate(periods):
        tt = p['time']
        tts = remove_timezone_colon(tt['start'])
        tte = remove_timezone_colon(tt['end'])
        start = datetime.datetime.strptime(tts, fmt)
        end = datetime.datetime.strptime(tte, fmt)
        start_txt = timediff_to_timestr(now, start) + " - " + \
            timediff_to_timestr(now, end)

        regions = p['regions']
        west = emojify(regions['west'])
        east = emojify(regions['east'])
        central = emojify(regions['central'])
        south = emojify(regions['south'])
        north = emojify(regions['north'])
        if by_period:
            txt += f"{start_txt}: Central - {central}, North - {north}, South - {south}, East - {east}, West - {west}\n"
        else:
            central_txt += f' {central} ({start_txt})'
            north_txt += f' {north} ({start_txt})'
            south_txt += f' {south} ({start_txt})'
            east_txt += f' {east} ({start_txt})'
            west_txt += f' {west} ({start_txt})'
    if by_period:
        return txt.strip()
    else:
        return f'{central_txt}\n{north_txt}\n{south_txt}\n{east_txt}\n{west_txt}'


# ----- Location Library -----
def get_location():
    """
    Returns the latitude and longitude of the
    current location
    """
    try:
        import location
        my_location = location.get_location()
        return [ my_location['latitude'],
                 my_location['longitude'] ]
    except:
        return [ LATITUDE, LONGITUDE ]


def get_nearest_location(x, places):
    """
    Given a location `x`, and a list of locations, `places`,
    returns the list index corresponding to the minimum distance,
    and the minimum distance.
    """
    min_dist, min_i = 1e10, 0
    for i, place in enumerate(places):
        name = place['name']
        label_location = place['label_location']
        latitude = float(label_location['latitude'])
        longitude = float(label_location['longitude'])
        r2 = (x[0] - latitude)**2 + (x[1] - longitude)**2
        if r2 < min_dist:
            min_dist = r2
            min_i = i
    return places[min_i], math.sqrt(min_dist)


# ----- Forecasts -----
def now_cast():
    d = d_query('2hr')
    # print(d['items'][0])
    if len(d['items'][0]) == 0:
        print(f'2 hour query returns: {d}')
        return 'Now: no forecast'
    
    area_metadata, forecasts = parse_2hr(d)
    x = [ float(LATITUDE),
          float(LONGITUDE) ]
    
    place, dist = get_nearest_location(x, d['area_metadata'])
    x = place['label_location']
    name = place['name']
    nowcast = emojify(forecasts[name])
    txt = f"Now: {nowcast} at {name}"
    return txt


def forecast_24hr():
    d = d_query('24hr')
    status = d['api_info']['status']
    items = d['items'][0]
    general = items['general']
    periods = items['periods']
    txt = parse_general_forecast(general)
    txt += "\n" + parse_periods(periods, by_period=False)
    return txt


def forecast_pm25():
    d = d_query('pm25')
    region_metadata, pm25 = parse_pm25(d)
    x = get_location()
    place, dist = get_nearest_location(x, region_metadata)
    name = place['name']
    x = place['label_location']
    txt = f"PM2.5: {pm25[name]} (location = {name})"
    return txt


def forecast_psi():
    d = d_query('psi')
    region_metadata, readings = parse_psi(d)
    x = get_location()
    place, dist = get_nearest_location(x, region_metadata)
    name = place['name']
    x = place['label_location']
    
    pm10_twenty_four_hourly = readings['pm10_twenty_four_hourly']
    pm25_twenty_four_hourly = readings['pm25_twenty_four_hourly']
    psi_twenty_four_hourly = readings['psi_twenty_four_hourly']
    txt = f"PSI 24hr: {psi_twenty_four_hourly[name]} (PSI)"
    txt += f", {pm25_twenty_four_hourly[name]} (PM2.5)"
    txt += f", {pm10_twenty_four_hourly[name]} (PM10)"
    return txt


def forecast_psi_all():
    d = d_query('psi')
    region_metadata, readings = parse_psi(d)
    x = get_location()
    place, dist = get_nearest_location(x, region_metadata)
    name = place['name']
    x = place['label_location'] 

    o3_sub_index = readings['o3_sub_index']
    pm10_twenty_four_hourly = readings['pm10_twenty_four_hourly']
    pm10_sub_index = readings['pm10_sub_index']
    co_sub_index = readings['co_sub_index']
    pm25_twenty_four_hourly = readings['pm25_twenty_four_hourly']
    so2_sub_index = readings['so2_sub_index']
    co_eight_hour_max = readings['co_eight_hour_max']
    no2_one_hour_max = readings['no2_one_hour_max']
    so2_twenty_four_hourly = readings['so2_twenty_four_hourly']
    pm25_sub_index = readings['pm25_sub_index']
    psi_twenty_four_hourly = readings['psi_twenty_four_hourly']
    o3_eight_hour_max = readings['o3_eight_hour_max']
    txt = f"PSI: {psi_twenty_four_hourly[name]} (24hr)"
    txt += f", PM2.5: {pm25_twenty_four_hourly[name]} (24hr) {pm25_sub_index[name]} (sub-index)"
    txt += f", PM10: {pm10_twenty_four_hourly[name]} (24hr) {pm10_sub_index[name]} (sub-index)"
    txt += f", SO2: {so2_twenty_four_hourly[name]} (24hr) {so2_sub_index[name]} (sub-index)"
    txt += f", O3: {o3_sub_index[name]} (sub-index) {o3_eight_hour_max[name]} (8hr max)"
    txt += f", NO2: {no2_one_hour_max[name]} (1 hr max)"
    txt += f", CO: {co_sub_index[name]} (sub-index) {co_eight_hour_max[name]} (8 hr max)"
    return txt


# ----- Main -----
def main(args):
    if args.key == '2hr':
        txt = now_cast()
    elif args.key == '24hr':
        txt = forecast_24hr()
    elif args.key == 'pm25':
        txt = forecast_pm25()
    elif args.key == 'psi':
        txt = forecast_psi()
    else:
        d = d_query(args.key)
        d_pprint(d)
    print(txt)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--key')
    parser.add_argument('--lat', default=1.290270, help='Latitude')
    parser.add_argument('--lon', default=103.851959, help='Longitude')
    args = parser.parse_args()

    LATITUDE = float(args.lat)
    LONGITUDE = float(args.lon)

    try:
        x = get_location()
        if x is not NONE:
            LATITUDE = x[0]
            LONGITUDE = x[1]
    except:
        pass

    weather_txt = now_cast()
    weather_txt += '\n' + forecast_24hr()

    try:
        v = ui.load_view()
        v['label1'].text = weather_txt
        v.present('sheet')

        import appex
        appex.set_widget_view(v)
    except:
        print(weather_txt)
