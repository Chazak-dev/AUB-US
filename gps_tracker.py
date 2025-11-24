import socket
import json
import threading
import time
from config import Server_IP

class GPSTracker:
    def __init__(self, map_widget=None):
        self.udp_socket = None
        self.sharing_socket = None
        self.listener_socket = None
        self.tracking = False
        self.listening = False
        self.map_widget = map_widget  # Reference to the map widget
        self.current_location = (33.9000, 35.4800)  # Default fallback
        
    def start_sharing_location(self, port=8001):
        """Start sharing location as driver"""
        try:
            # Close existing socket if any
            if hasattr(self, 'sharing_socket') and self.sharing_socket:
                self.sharing_socket.close()
                
            self.sharing_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.sharing_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.tracking = True
            self.gps_port = port
            
            print(f"📍 Started sharing location on port {port}")
            
            thread = threading.Thread(target=self._location_update_loop, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print(f"❌ Failed to start GPS sharing: {e}")
            # Try alternative port
            if port == 8001:
                return self.start_sharing_location(8002)
            return False
    
    def _location_update_loop(self):
        """Driver location sharing loop"""
        while self.tracking:
            try:
                lat, lon = self._get_current_location()
                
                gps_data = {
                    "type": "gps_update",
                    "latitude": lat,
                    "longitude": lon
                }
                
                json_message = json.dumps(gps_data)
                
                self.sharing_socket.sendto(
                    json_message.encode('utf-8'),
                    ('127.0.0.1', self.gps_port)  # Send to localhost for passenger
                )
                
                print(f"📍 Location sent: {lat}, {lon}")
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ GPS send error: {e}")
                if self.tracking:  # Only break if we're still supposed to be tracking
                    time.sleep(1)  # Wait before retry
                    continue
                break
    
    def _get_current_location(self):
        """Get current location - improved with proper error handling"""
        try:
            # If we have a map widget with last known location, use it
            if self.map_widget and hasattr(self.map_widget, 'last_known_location'):
                return self.map_widget.last_known_location
            else:
                return 33.8997, 35.4812  # AUB coordinates as fallback
                
        except Exception as e:
            print(f"❌ GPS location error: {e}")
            return 33.8997, 35.4812  # Fallback to AUB
    
    def start_tracking_driver(self, port=8001):
        """Start listening for driver location updates as passenger"""
        try:
            # Close existing listener if any
            if hasattr(self, 'listener_socket') and self.listener_socket:
                self.listener_socket.close()
                
            self.listener_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.listener_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.listener_socket.bind(('0.0.0.0', port))
            self.listener_socket.settimeout(1.0)  # Add timeout to prevent blocking
            self.listening = True
            
            print(f"📍 Listening for driver location on port {port}")
            
            thread = threading.Thread(target=self._location_listener, daemon=True)
            thread.start()
            return True
            
        except Exception as e:
            print(f"❌ Failed to start GPS listener on port {port}: {e}")
            # Try alternative port
            if port == 8001:
                print("🔄 Trying alternative port 8002...")
                return self.start_tracking_driver(8002)
            return False
    
    def _location_listener(self):
        """Passenger location listening loop"""
        while self.listening:
            try:
                data, addr = self.listener_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                self._handle_gps_update(message)
                
            except socket.timeout:
                continue  # Normal timeout, continue listening
            except Exception as e:
                if self.listening:  # Only log error if we're still listening
                    print(f"❌ GPS receive error: {e}")
                break
    
    def _handle_gps_update(self, gps_data):
        """Handle incoming GPS updates"""
        lat = gps_data.get('latitude')
        lon = gps_data.get('longitude')
        
        if lat and lon:
            self.current_location = (lat, lon)
            print(f"📍 Driver location: {lat}, {lon}")
            
            # Update map if available
            if self.map_widget and hasattr(self.map_widget, 'update_driver_location'):
                self.map_widget.update_driver_location(lat, lon)
    
    def stop_sharing_location(self):
        """Stop sharing location (driver)"""
        self.tracking = False
        if hasattr(self, 'sharing_socket') and self.sharing_socket:
            self.sharing_socket.close()
            self.sharing_socket = None
        print("📍 GPS sharing stopped")
    
    def stop_tracking(self):
        """Stop tracking location (passenger)"""
        self.listening = False
        if hasattr(self, 'listener_socket') and self.listener_socket:
            self.listener_socket.close()
            self.listener_socket = None
        print("📍 GPS tracking stopped")
    
    def stop_all(self):
        """Stop both sharing and tracking"""
        self.stop_sharing_location()
        self.stop_tracking()