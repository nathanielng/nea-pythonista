#!/bin/bash

# Examples:
#   curl -s https://api.data.gov.sg/v1/environment/2-hour-weather-forecast | jq "."
#   python sg_weather.py --start "2024-01-03" --end "2024-01-08" --get_forecasts
#   python sg_weather.py --start "2024-01-01" --end "2024-01-08" --parse_forecasts

import argparse
import datetime
import json
import os
import pandas as pd
import requests
import time

base_url = 'https://api.data.gov.sg/v1/'



# ----- Setup -----
if not os.path.isdir('data'):
    os.mkdir('data')



# ----- Date Time Functions -----
def get_datetime_array(start_dt=datetime.datetime(2024, 1, 1, 0, 0, 0),
                       end_dt='now',
                       increment=86400):
    """
    Set increment=7200 for 2 hour increments
    Set increment=86400 for 1 day increments
    """
    if end_dt == 'now':
        end_dt = datetime.datetime.now()
    
    dt_array = []
    t = start_dt
    while True:
        dt_array.append(t)
        t = t + datetime.timedelta(seconds=increment)
        if t >= end_dt:
            break
    return dt_array



# ----- Weather -----
def get_forecast_json(date='', date_time=''):
    url = base_url + 'environment/2-hour-weather-forecast'
    if date != '':
        response = requests.get(url + f'?date={date}')
    elif date_time != '':
        response = requests.get(url + f'?date_time={date_time}')
    else:
        response = requests.get(url)
        
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        print(f'Error parsing json data. Status code: {response.status_code}')
        return None


def get_temperature_json(date=''):
    url = base_url + 'environment/air-temperature'
    if date != '':
        response = requests.get(url + f'?date={date}')
    else:
        response = requests.get(url)
        
    if response.status_code == 200:
        return json.loads(response.text)
    else:
        print(f'Error parsing json data. Status code: {response.status_code}')
        return response.content.decode('utf-8')



# ----- Area Metadata -----
def get_area_metadata(data):
    area_metadata = []
    for area in data['area_metadata']:
        location = area['label_location']
        area_metadata.append({
            'name': area['name'],
            'latitude': location['latitude'],
            'longitude': location['longitude']
        })
    return area_metadata


def create_area_metadata_csv():
    data = get_forecast_json()
    area_metadata = get_area_metadata(data)
    df = pd.DataFrame(area_metadata)
    df.to_csv('area_metadata.csv')



# ----- Forecasts -----
def get_timedata(items):
    x = {'timestamp': '-', 'update_timestamp': '-', 'validity_start': '-', 'validity_end': '-'}
    for key in ['update_timestamp', 'timestamp', 'valid_period']:
        if key in items:
            if key == 'valid_period':
                x['validity_start'] = items[key]['start']
                x['validity_end'] = items[key]['end']
            else:
                x[key] = items[key]
    return x


def get_forecasts(data):
    if 'items' not in data:
        return None

    forecast_data = []
    for item in data['items']:
        if 'forecasts' not in item:
            continue

        forecast_item = {'timestamp': '-', 'update_timestamp': '-', 'validity_start': '-', 'validity_end': '-'}
        for key in ['update_timestamp', 'timestamp', 'valid_period']:
            if key in item:
                if key == 'valid_period':
                    forecast_item['validity_start'] = item[key]['start']
                    forecast_item['validity_end'] = item[key]['end']
                else:
                    forecast_item[key] = item[key]

        forecast_item['status'] = data['api_info']['status']
        for forecast in item['forecasts']:
            forecast_item[forecast['area']] = forecast['forecast']
        forecast_data.append(forecast_item)

    return forecast_data


def get_forecasts(start_dt, end_dt, increment=86400):
    datetime_array = get_datetime_array(start_dt, end_dt, increment)
    for x in datetime_array:
        date = x.strftime('%Y-%m-%d')
        data = get_forecast_json(date=date)
        if data is None:
            break

        with open(f'data/forecast-{date}.json', 'w') as f:
            f.write(json.dumps(data, indent=2, default=str))
        time.sleep(1)


def parse_forecasts(csv_file, start_dt, end_dt, increment=86400):
    datetime_array = get_datetime_array(start_dt, end_dt, increment)
    new_df = []
    for x in datetime_array:
        date = x.strftime('%Y-%m-%d')
        with open(f'data/forecast-{date}.json') as f:
            data = json.load(f)
            if 'items' in data:
                td = get_timedata(data['items'][0])
                print(f"----- Timestamp: {td['timestamp']}. Update_timestamp: {td['update_timestamp']}. Valid: {td['validity_start']} to {td['validity_end']} -----")

            forecast_data = get_forecasts(data)
            if forecast_data is None:
                print(f'----- {x} BAD FORMATTING. THIS ENTRY WILL BE SKIPPED -----')
                print(json.dumps(data, indent=2, default=str))
                print(f'----- {x} BAD FORMATTING. THIS ENTRY WILL BE SKIPPED -----')
                continue
            new_df = new_df + forecast_data

    if os.path.isfile(csv_file):
        df = pd.read_csv(csv_file, index_col=0)
    else:
        df = pd.DataFrame()

    new_df = pd.DataFrame.from_dict(new_df, orient='columns')
    concat_df = pd.concat((df, new_df), axis='index', join='outer')
    concat_df.to_csv(csv_file)
    return concat_df



# ----- Air Temperature -----
def temperature_main(start_dt, end_dt, csv_file):
    if os.path.isfile(csv_file):
        df = pd.read_csv(csv_file, index_col=0)
    else:
        df = pd.DataFrame()

    datetime_array = get_datetime_array(start_dt, end_dt)
    new_df = []
    for x in datetime_array:
        date_time = x.isoformat()
        data = get_temperature_json(date_time)
        print(json.dumps(data, indent=2, default=str))
        time.sleep(1)

    new_df = pd.DataFrame(new_df)
    concat_df = pd.concat((df, new_df), axis='index', join='outer')
    concat_df.to_csv(csv_file)
    return concat_df



if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--start', default='2024-01-01')
    parser.add_argument('--end', default='2024-01-07')
    parser.add_argument('--file', default='forecasts.csv')
    parser.add_argument('--get_forecasts', action='store_true')
    parser.add_argument('--parse_forecasts', action='store_true')
    args = parser.parse_args()

    start_dt = datetime.datetime.strptime(args.start, '%Y-%m-%d')
    end_dt = datetime.datetime.strptime(args.end, '%Y-%m-%d')

    if args.get_forecasts:
        get_forecasts(start_dt, end_dt)
    if args.parse_forecasts:
        parse_forecasts(args.file, start_dt, end_dt)
