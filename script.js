class WeatherApp {
    constructor() {
        this.currentForecast = '2hr';
        this.compactView = true;
        this.mapVisible = false;
        this.map = null;
        this.userMarker = null;
        this.darkMode = false;
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.loadThemePreference();
        // Set initial compact view
        document.getElementById('areas-grid').classList.add('compact');
        this.loadForecast('2hr');
    }

    setupEventListeners() {
        document.getElementById('btn-2hr').addEventListener('click', () => this.switchForecast('2hr'));
        document.getElementById('btn-24hr').addEventListener('click', () => this.switchForecast('24hr'));
        document.getElementById('btn-4day').addEventListener('click', () => this.switchForecast('4day'));
        document.getElementById('toggle-layout').addEventListener('click', () => this.toggleLayout());
        document.getElementById('toggle-map').addEventListener('click', () => this.toggleMap());
        document.getElementById('locate-user').addEventListener('click', () => this.locateUser());
        document.getElementById('theme-toggle').addEventListener('click', () => this.toggleTheme());
    }

    switchForecast(type) {
        // Update active button
        document.querySelectorAll('.forecast-btn').forEach(btn => btn.classList.remove('active'));
        document.getElementById(`btn-${type}`).classList.add('active');

        // Hide all sections
        document.querySelectorAll('.forecast-section').forEach(section => section.classList.add('hidden'));
        
        // Show selected section
        document.getElementById(`forecast-${type}`).classList.remove('hidden');
        
        this.currentForecast = type;
        this.loadForecast(type);
    }

    async loadForecast(type) {
        this.showLoading();
        this.hideError();

        try {
            let data;
            switch(type) {
                case '2hr':
                    data = await this.fetch2HourForecast();
                    this.render2HourForecast(data);
                    break;
                case '24hr':
                    data = await this.fetch24HourForecast();
                    this.render24HourForecast(data);
                    break;
                case '4day':
                    data = await this.fetch4DayOutlook();
                    this.render4DayOutlook(data);
                    break;
            }
        } catch (error) {
            this.showError('Failed to load weather data. Please try again.');
            console.error('Error loading forecast:', error);
        } finally {
            this.hideLoading();
        }
    }

    async fetch2HourForecast() {
        const response = await fetch('https://api-open.data.gov.sg/v2/real-time/api/two-hr-forecast');
        const data = await response.json();
        console.log('Full 2-hour API response:', data); // Debug log to see all available data
        return this.convert2HourData(data);
    }

    async fetch24HourForecast() {
        const response = await fetch('https://api-open.data.gov.sg/v2/real-time/api/twenty-four-hr-forecast');
        const data = await response.json();
        return this.organize24HourData(data);
    }

    async fetch4DayOutlook() {
        const response = await fetch('https://api-open.data.gov.sg/v2/real-time/api/four-day-outlook');
        return await response.json();
    }

    convert2HourData(data) {
        const areaCoords = {};
        data.data.area_metadata.forEach(area => {
            areaCoords[area.name] = {
                latitude: area.label_location.latitude,
                longitude: area.label_location.longitude
            };
        });

        const forecasts = data.data.items[0].forecasts;
        const validPeriod = data.data.items[0].valid_period;
        const updateTimestamp = data.data.items[0].update_timestamp;

        return forecasts.map(forecast => ({
            location_name: forecast.area,
            latitude: areaCoords[forecast.area]?.latitude,
            longitude: areaCoords[forecast.area]?.longitude,
            forecast: forecast.forecast,
            start_time: validPeriod.start,
            end_time: validPeriod.end,
            update_timestamp: updateTimestamp
        })).filter(item => item.latitude && item.longitude);
    }

    organize24HourData(data) {
        if (!data?.data?.records?.[0]) return null;

        const record = data.data.records[0];
        const result = {
            timestamp: record.timestamp,
            date: record.date,
            general: record.general,
            regions: {
                west: { forecasts: [] },
                east: { forecasts: [] },
                central: { forecasts: [] },
                south: { forecasts: [] },
                north: { forecasts: [] }
            }
        };

        record.periods?.forEach(period => {
            ['west', 'east', 'central', 'south', 'north'].forEach(region => {
                if (period.regions?.[region]) {
                    result.regions[region].forecasts.push({
                        timePeriod: period.timePeriod,
                        forecast: period.regions[region]
                    });
                }
            });
        });

        return result;
    }

    toggleMap() {
        this.mapVisible = !this.mapVisible;
        const mapDiv = document.getElementById('weather-map');
        const toggleBtn = document.getElementById('toggle-map');
        
        if (this.mapVisible) {
            mapDiv.classList.remove('hidden');
            toggleBtn.textContent = 'Hide Map';
            setTimeout(() => {
                this.initMap();
                // Re-render current data on map
                if (this.currentForecast === '2hr') {
                    this.loadForecast('2hr');
                }
            }, 100);
        } else {
            mapDiv.classList.add('hidden');
            toggleBtn.textContent = 'Show Map';
        }
    }

    initMap() {
        if (!this.map) {
            this.map = L.map('weather-map').setView([1.3521, 103.8198], 11);
            L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
                attribution: '© OpenStreetMap contributors'
            }).addTo(this.map);
            console.log('Map initialized'); // Debug log
        }
        setTimeout(() => {
            this.map.invalidateSize();
            console.log('Map size invalidated'); // Debug log
        }, 200);
    }

    getWeatherColor(forecast) {
        const text = forecast.toLowerCase();
        if (text.includes('sunny') || text.includes('fair')) return '#FFD700'; // Gold
        if (text.includes('partly cloudy') || text.includes('partly cloud')) return '#87CEEB'; // Sky blue
        if (text.includes('cloudy') || text.includes('overcast')) return '#708090'; // Slate gray
        if (text.includes('thundery') || text.includes('thunder')) return '#4B0082'; // Indigo
        if (text.includes('showers') || text.includes('rain')) return '#4169E1'; // Royal blue
        if (text.includes('hazy') || text.includes('haze')) return '#D3D3D3'; // Light gray
        if (text.includes('windy')) return '#00CED1'; // Dark turquoise
        return '#32CD32'; // Lime green (default)
    }

    updateMapMarkers(data) {
        if (!this.map) return;
        
        console.log('Updating map with data:', data); // Debug log
        
        // Clear existing weather markers (but keep user marker)
        this.map.eachLayer(layer => {
            if ((layer instanceof L.Marker || layer instanceof L.CircleMarker) && layer !== this.userMarker) {
                this.map.removeLayer(layer);
            }
        });
        
        // Add markers for each location
        data.forEach(area => {
            console.log(`Area: ${area.location_name}, Lat: ${area.latitude}, Lng: ${area.longitude}`); // Debug log
            if (area.latitude && area.longitude) {
                const emoji = this.getWeatherEmoji(area.forecast);
                const color = this.getWeatherColor(area.forecast);
                
                // Create custom colored circle marker
                const marker = L.circleMarker([area.latitude, area.longitude], {
                    color: '#ffffff',
                    fillColor: color,
                    fillOpacity: 0.8,
                    radius: 10,
                    weight: 2
                }).addTo(this.map);
                
                marker.bindPopup(`
                    <strong>${area.location_name}</strong><br>
                    ${emoji} ${area.forecast}
                `);
                console.log(`Added marker for ${area.location_name}`); // Debug log
            } else {
                console.log(`No coordinates for ${area.location_name}`); // Debug log
            }
        });
    }

    toggleTheme() {
        this.darkMode = !this.darkMode;
        const body = document.body;
        const themeBtn = document.getElementById('theme-toggle');
        
        if (this.darkMode) {
            body.classList.add('dark-mode');
            themeBtn.textContent = '☀️';
        } else {
            body.classList.remove('dark-mode');
            themeBtn.textContent = '🌙';
        }
        
        // Save preference
        localStorage.setItem('darkMode', this.darkMode);
    }

    loadThemePreference() {
        const savedTheme = localStorage.getItem('darkMode');
        if (savedTheme === 'true') {
            this.darkMode = true;
            document.body.classList.add('dark-mode');
            document.getElementById('theme-toggle').textContent = '☀️';
        }
    }

    locateUser() {
        if (!this.map) {
            // Show map first if not visible
            if (!this.mapVisible) {
                this.toggleMap();
            }
            return;
        }

        const locateBtn = document.getElementById('locate-user');
        locateBtn.textContent = '📍 Locating...';
        locateBtn.disabled = true;

        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    // Remove existing user marker
                    if (this.userMarker) {
                        this.map.removeLayer(this.userMarker);
                    }
                    
                    // Create custom red circle marker for user location
                    this.userMarker = L.circleMarker([lat, lng], {
                        color: '#ff0000',
                        fillColor: '#ff0000',
                        fillOpacity: 0.8,
                        radius: 8,
                        weight: 3
                    }).addTo(this.map);
                    
                    this.userMarker.bindPopup('📍 Your Location');
                    
                    // Center map on user location
                    this.map.setView([lat, lng], 13);
                    
                    locateBtn.textContent = '📍 My Location';
                    locateBtn.disabled = false;
                },
                (error) => {
                    console.error('Geolocation error:', error);
                    alert('Unable to get your location. Please check your browser permissions.');
                    locateBtn.textContent = '📍 My Location';
                    locateBtn.disabled = false;
                },
                {
                    enableHighAccuracy: true,
                    timeout: 10000,
                    maximumAge: 300000
                }
            );
        } else {
            alert('Geolocation is not supported by this browser.');
            locateBtn.textContent = '📍 My Location';
            locateBtn.disabled = false;
        }
    }

    toggleLayout() {
        this.compactView = !this.compactView;
        const grid = document.getElementById('areas-grid');
        const toggleBtn = document.getElementById('toggle-layout');
        
        if (this.compactView) {
            grid.classList.add('compact');
            toggleBtn.textContent = 'Standard View';
        } else {
            grid.classList.remove('compact');
            toggleBtn.textContent = 'Compact View';
        }
    }

    getWeatherEmoji(forecast) {
        if (!forecast || typeof forecast !== 'string') return '🌤️';
        const text = forecast.toLowerCase();
        if (text.includes('sunny') || text.includes('fair')) return '☀️';
        if (text.includes('partly cloudy') || text.includes('partly cloud')) return '⛅';
        if (text.includes('cloudy') || text.includes('overcast')) return '☁️';
        if (text.includes('thundery') || text.includes('thunder')) return '⛈️';
        if (text.includes('showers') || text.includes('rain')) return '🌧️';
        if (text.includes('hazy') || text.includes('haze')) return '🌫️';
        if (text.includes('windy')) return '💨';
        return '🌤️';
    }

    render2HourForecast(data) {
        const grid = document.getElementById('areas-grid');
        const periodDiv = document.getElementById('forecast-period');
        
        // Get time range and additional info from first item
        if (data.length > 0) {
            const start = new Date(data[0].start_time);
            const end = new Date(data[0].end_time);
            const timeRange = `${start.toLocaleTimeString('en-SG', {hour: '2-digit', minute: '2-digit'})} - ${end.toLocaleTimeString('en-SG', {hour: '2-digit', minute: '2-digit'})}`;
            
            // Add update time if available
            const updateTime = data[0].update_timestamp ? 
                `<div style="font-size: 0.8rem; color: #666; margin-top: 5px;">Last updated: ${new Date(data[0].update_timestamp).toLocaleTimeString('en-SG', {hour: '2-digit', minute: '2-digit'})}</div>` : '';
            
            periodDiv.innerHTML = `Forecast Period: ${timeRange}${updateTime}`;
        } else {
            periodDiv.textContent = '';
        }
        
        grid.innerHTML = data.map(area => {
            return `
                <div class="area-card" data-lat="${area.latitude}" data-lng="${area.longitude}" data-name="${area.location_name}">
                    <div class="area-name">${area.location_name}</div>
                    <div class="area-forecast">${this.getWeatherEmoji(area.forecast)} ${area.forecast}</div>
                </div>
            `;
        }).join('');
        
        // Add click listeners to area cards
        document.querySelectorAll('.area-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (this.mapVisible && this.map) {
                    const lat = parseFloat(card.dataset.lat);
                    const lng = parseFloat(card.dataset.lng);
                    const name = card.dataset.name;
                    
                    if (lat && lng) {
                        this.map.setView([lat, lng], 14);
                        
                        // Find and open the popup for this location
                        this.map.eachLayer(layer => {
                            if (layer instanceof L.CircleMarker && layer !== this.userMarker && layer.getPopup()) {
                                const popupContent = layer.getPopup().getContent();
                                if (popupContent.includes(name)) {
                                    layer.openPopup();
                                }
                            }
                        });
                    }
                }
            });
        });
        
        // Update map if visible
        if (this.mapVisible) {
            this.updateMapMarkers(data);
        }
    }

    render24HourForecast(data) {
        if (!data) return;

        const generalInfo = document.getElementById('general-info');
        const generalParts = [];
        
        // Handle general forecast text
        let generalForecast = '';
        if (typeof data.general?.forecast === 'string') {
            generalForecast = data.general.forecast;
        } else if (data.general?.forecast && typeof data.general.forecast === 'object') {
            generalForecast = data.general.forecast.text || '';
        }
        
        // Add valid period and update time
        const validPeriod = data.general?.validPeriod?.text || '';
        const updateTime = data.updatedTimestamp ? 
            `<div style="font-size: 0.8rem; color: rgba(255,255,255,0.8); margin-top: 8px;">Last updated: ${new Date(data.updatedTimestamp).toLocaleTimeString('en-SG', {hour: '2-digit', minute: '2-digit'})}</div>` : '';
        
        if (generalForecast) generalParts.push(`<p><strong>🌍 Forecast:</strong> ${this.getWeatherEmoji(generalForecast)} ${generalForecast}</p>`);
        if (validPeriod) generalParts.push(`<p><strong>📅 Valid Period:</strong> ${validPeriod}</p>`);
        if (data.general?.temperature?.low || data.general?.temperature?.high) {
            generalParts.push(`<p><strong>🌡️ Temperature:</strong> ${data.general.temperature?.low || '?'}°C - ${data.general.temperature?.high || '?'}°C</p>`);
        }
        if (data.general?.relative_humidity?.low || data.general?.relative_humidity?.high) {
            generalParts.push(`<p><strong>💧 Humidity:</strong> ${data.general.relative_humidity?.low || '?'}% - ${data.general.relative_humidity?.high || '?'}%</p>`);
        }
        if (data.general?.wind?.direction || data.general?.wind?.speed) {
            generalParts.push(`<p><strong>💨 Wind:</strong> ${data.general.wind?.direction || '?'} ${data.general.wind?.speed?.low || '?'}-${data.general.wind?.speed?.high || '?'} km/h</p>`);
        }
        
        generalInfo.innerHTML = `<h3>🌍 General Forecast</h3>${generalParts.join('')}${updateTime}`;

        const regionsGrid = document.getElementById('regions-grid');
        
        // Group forecasts by time period
        const timePeriodsMap = new Map();
        Object.entries(data.regions).forEach(([region, regionData]) => {
            regionData.forecasts.forEach(forecast => {
                const timeText = forecast.timePeriod?.text || 'Time not available';
                if (!timePeriodsMap.has(timeText)) {
                    timePeriodsMap.set(timeText, {});
                }
                
                // Handle forecast text
                let forecastText = '';
                if (typeof forecast.forecast === 'string') {
                    forecastText = forecast.forecast;
                } else if (forecast.forecast && typeof forecast.forecast === 'object') {
                    forecastText = forecast.forecast.text || '';
                }
                
                timePeriodsMap.get(timeText)[region] = forecastText;
            });
        });
        
        // Render by time periods
        regionsGrid.innerHTML = Array.from(timePeriodsMap.entries()).map(([timePeriod, regions]) => `
            <div class="time-period-section">
                <h4 class="time-period-header">${timePeriod}</h4>
                <div class="regions-row">
                    ${Object.entries(regions).map(([region, forecast]) => `
                        <div class="region-item">
                            <div class="region-name">${region}</div>
                            <div class="region-forecast">${forecast ? `${this.getWeatherEmoji(forecast)} ${forecast}` : 'N/A'}</div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `).join('');
    }

    render4DayOutlook(data) {
        const grid = document.getElementById('outlook-grid');
        console.log('4-day data:', data); // Debug log
        
        // Handle different possible data structures
        let forecasts = [];
        let updateTimestamp = null;
        
        if (data?.data?.records?.[0]?.forecasts) {
            forecasts = data.data.records[0].forecasts;
            updateTimestamp = data.data.records[0].updatedTimestamp;
        } else if (data?.data?.forecasts) {
            forecasts = data.data.forecasts;
            updateTimestamp = data.data.updatedTimestamp;
        } else if (data?.forecasts) {
            forecasts = data.forecasts;
        }
        
        if (!forecasts || forecasts.length === 0) {
            grid.innerHTML = '<div class="day-card">No 4-day forecast data available</div>';
            return;
        }
        
        // Add update timestamp to dedicated div
        const updateDiv = document.getElementById('outlook-update');
        if (updateTimestamp) {
            updateDiv.textContent = `Last updated: ${new Date(updateTimestamp).toLocaleString('en-SG', {weekday: 'short', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit'})}`;
        } else {
            updateDiv.textContent = '';
        }
        
        grid.innerHTML = forecasts.map(forecast => {
            console.log('Individual forecast:', forecast); // Debug log
            
            // Handle forecast text - it might be a string or object
            let forecastText = '';
            let forecastSummary = '';
            if (typeof forecast.forecast === 'string') {
                forecastText = forecast.forecast;
            } else if (forecast.forecast && typeof forecast.forecast === 'object') {
                forecastText = forecast.forecast.text || '';
                forecastSummary = forecast.forecast.summary || '';
            }
            
            // Handle date - format to human readable
            let formattedDate = 'Date not available';
            const dayOfWeek = forecast.day || '';
            if (forecast.date || forecast.timestamp || forecast.forecastDate) {
                const dateStr = forecast.date || forecast.timestamp || forecast.forecastDate;
                const dateObj = new Date(dateStr);
                const dateText = dateObj.toLocaleDateString('en-SG', { 
                    month: 'short', 
                    day: 'numeric' 
                });
                formattedDate = dayOfWeek ? `${dayOfWeek}, ${dateText}` : dateText;
            } else if (dayOfWeek) {
                formattedDate = dayOfWeek;
            }
            
            // Handle humidity - check different possible structures
            const humidityLow = forecast.relative_humidity?.low || forecast.humidity?.low || forecast.relativeHumidity?.low;
            const humidityHigh = forecast.relative_humidity?.high || forecast.humidity?.high || forecast.relativeHumidity?.high;
            
            return `
                <div class="day-card">
                    <div class="day-date">${formattedDate}</div>
                    ${forecastSummary ? `<div class="day-forecast">${this.getWeatherEmoji(forecastSummary)} ${forecastSummary}</div>` : 
                      (forecastText ? `<div class="day-forecast">${this.getWeatherEmoji(forecastText)} ${forecastText}</div>` : '<div class="day-forecast">Forecast not available</div>')}
                    <div class="day-temp">🌡️ ${forecast.temperature?.low || '?'}°C - ${forecast.temperature?.high || '?'}°C</div>
                    <div>💧 Humidity: ${humidityLow || '?'}% - ${humidityHigh || '?'}%</div>
                    <div>💨 Wind: ${forecast.wind?.direction || '?'} ${forecast.wind?.speed?.low || '?'}-${forecast.wind?.speed?.high || '?'} km/h</div>
                </div>
            `;
        }).join('');
    }

    showLoading() {
        document.getElementById('loading').classList.remove('hidden');
    }

    hideLoading() {
        document.getElementById('loading').classList.add('hidden');
    }

    showError(message) {
        const errorDiv = document.getElementById('error');
        errorDiv.textContent = message;
        errorDiv.classList.remove('hidden');
    }

    hideError() {
        document.getElementById('error').classList.add('hidden');
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new WeatherApp();
});
