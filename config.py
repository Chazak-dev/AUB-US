import socket
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

Server_IP = os.getenv('AUBUS_SERVER_IP', 'localhost')
Server_port = int(os.getenv('AUBUS_SERVER_PORT', '8888'))
DATABASE_PATH = os.path.join(BASE_DIR, "aubus.db")

# Use environment variables for API keys
WEATHER_API_KEY = os.getenv('WEATHER_API_KEY', 'b78b25fa20341ca104d0bbb80020235d')
GOOGLE_MAPS_API_KEY = os.getenv('GOOGLE_MAPS_API_KEY', 'AIzaSyBp_oQI9HENN1ikS1sz8qDinI-Q3ucvoX4')


Register = 'Register'
Login = 'Login'
Ride_request = 'Request for a ride'
Accept_ride = 'Accept the ride'

Image_message = 'image_message'
Voice_message = 'voice_message'
Location_message = 'location_message'
Chat_message = 'chat_message'