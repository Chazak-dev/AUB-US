import requests
from PyQt5.QtCore import QTimer, QObject, pyqtSignal

class WeatherService(QObject):
    weather_updated = pyqtSignal(str)
    
    def __init__(self, api_key):
        super().__init__()
        self.api_key = api_key
    
    def get_weather(self):
        """Get weather for Beirut and return formatted string with emoji"""
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q=Beirut&units=metric&APPID={self.api_key}"
            response = requests.get(url)
            data = response.json()
            
            temp = data['main']['temp']
            description = data['weather'][0]['description']
            icon = data['weather'][0]['icon']
            
           
            emoji = '☀️' if 'clear' in description else '⛅' if 'cloud' in description else '🌧️' if 'rain' in description else '🌤️'
            
            return f"{emoji} Weather: {round(temp)}°C\n{description.title()}"
            
        except:
            return "🌤️ Weather: -- °C"
    
    def start_auto_update(self, interval_minutes=30):
        """Start weather updates"""
        # Get initial weather
        weather_text = self.get_weather()
        self.weather_updated.emit(weather_text)
        
        # Set up timer for updates
        timer = QTimer(self)
        timer.timeout.connect(lambda: self.weather_updated.emit(self.get_weather()))
        timer.start(interval_minutes * 60 * 1000)       