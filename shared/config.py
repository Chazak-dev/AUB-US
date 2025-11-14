import socket

Server_IP = socket.gethostbyname(socket.gethostname())
Server_port = 8888

Register = 'Register'
Login = 'Login'
Ride_request = 'Request for a ride'
Accept_ride = 'Accept the ride'

Image_message = 'image_message'
Voice_message = 'voice_message'
Location_message = 'location_message'
Chat_message = 'chat_message'