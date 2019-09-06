# NEA APIs from data.gov.sg

## 1. Requirements

- `curl` command (`sudo apt-get install curl` or `yum install curl`)
- `http` command (`pip install httpie`)

## 2. NEA API list

1. https://data.gov.sg/dataset/weather-forecast

```bash
curl -X GET "https://api.data.gov.sg/v1/environment/2-hour-weather-forecast" -H "accept: application/json"
http https://api.data.gov.sg/v1/environment/2-hour-weather-forecast
```

2. https://data.gov.sg/dataset/realtime-weather-readings

```bash
curl -X GET "https://api.data.gov.sg/v1/environment/air-temperature" -H "accept: application/json"
http https://api.data.gov.sg/v1/environment/air-temperature
```

3. https://data.gov.sg/dataset/psi

```bash
curl -X GET "https://api.data.gov.sg/v1/environment/psi" -H "accept: application/json"
http https://api.data.gov.sg/v1/environment/psi
```

4. https://data.gov.sg/dataset/ultraviolet-index-uvi

```bash
curl -X GET "https://api.data.gov.sg/v1/environment/uv-index" -H "accept: application/json"
http https://api.data.gov.sg/v1/environment/uv-index
```

5. https://data.gov.sg/dataset/pm2-5

```bash
curl -X GET "https://api.data.gov.sg/v1/environment/pm25" -H "accept: application/json"
http https://api.data.gov.sg/v1/environment/pm25
```
