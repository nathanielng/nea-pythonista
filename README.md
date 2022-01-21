# nea-pythonista

This is a library for access to weather information from the NEA (National Environment Agency of Singapore).
While it will work as a standalone library, the intention of this library is primarily aimed towards
use in the [Pythonista](http://www.omz-software.com/pythonista/) iOS app.

## NEA API

The raw data returned from the NEA API can be viewed as follows:

```bash
curl -s https://api.data.gov.sg/v1/environment/2-hour-weather-forecast | jq "."
curl -s https://api.data.gov.sg/v1/environment/24-hour-weather-forecast | jq "."
curl -s https://api.data.gov.sg/v1/environment/4-day-weather-forecast | jq "."
curl -s https://api.data.gov.sg/v1/environment/air-temperature | jq "."
curl -s https://api.data.gov.sg/v1/environment/psi | jq "."
curl -s https://api.data.gov.sg/v1/environment/pm25 | jq "."
curl -s https://api.data.gov.sg/v1/environment/uv-index | jq "."
```
