import socket
import json
import threading
import time
from config import Server_IP

class GPSTracker:
    def __init__(self):
        self.udp_socket = None
        self.tracking = False
        self.listening = False
        
    def start_sharing_location(self, port=8000):
        
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.tracking = True
            self.gps_port = port
            
            print("Started sharing location on port " + str(port))
            
            thread = threading.Thread(target=self._location_update_loop, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print("Failed to start GPS sharing: " + str(e))
            return False
    
    def _location_update_loop(self):
       
        while self.tracking:
            try:
                
                lat, lon = self._get_current_location()
                
                
                gps_data = {
                    "type": "gps_update",
                    "latitude": lat,
                    "longitude": lon
                }
                
                json_message = json.dumps(gps_data)
                
                self.udp_socket.sendto(
                    json_message.encode('utf-8'),
                    (Server_IP, self.gps_port)
                )
                
                print("Location sent: " + str(lat) + ", " + str(lon))
                time.sleep(3)
                
            except Exception as e:
                print("GPS send error: " + str(e))
                break
    
    def _get_current_location(self):
        
        return 33.9000, 35.4800
    
    def start_tracking_driver(self, port=8000):
        
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.udp_socket.bind((Server_IP, port))
            self.listening = True
            
            print("Listening for driver location on port " + str(port))
            
            thread = threading.Thread(target=self._location_listener, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print("Failed to start GPS listener: " + str(e))
            return False
    
    def _location_listener(self):
        
        while self.listening:
            try:
                
                data, addr = self.udp_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                self._handle_gps_update(message)
                
            except Exception as e:
                print("GPS receive error: " + str(e))
                break
    
    def _handle_gps_update(self, gps_data):
        
        lat = gps_data.get('latitude')
        lon = gps_data.get('longitude')
        print("Driver location: " + str(lat) + ", " + str(lon))
    
    def stop_tracking(self):
        
        self.tracking = False
        self.listening = False
        if self.udp_socket:
            self.udp_socket.close()
        print("GPS tracking stopped")