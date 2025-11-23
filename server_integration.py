import json
import sys
import os

# Fix import paths - add current directory to Python path
sys.path.append(os.path.dirname(__file__))

from network_manager import NetworkManager

class ServerIntegration:
    def __init__(self):
        self.network = NetworkManager()
        self.current_user_id = None
        self.current_user_data = None
        self.is_driver = False
        
    def connect(self):
        """Connect to the AUBus server"""
        return self.network.connect_to_server()
    
    # =========================================================================
    # AUTHENTICATION METHODS
    # =========================================================================
    
    def register(self, username, password, first_name, last_name, address, is_driver=False):
        """Register new user using pipe protocol format"""
        # Format: REGISTER|username|email|password|first_name|last_name|address|photo|is_driver
        # Even though we don't use email, the protocol expects the field to be there (empty)
        command = f"REGISTER|{username}||{password}|{first_name}|{last_name}|{address}|default.jpg|{1 if is_driver else 0}"
        response = self.network.send_protocol_command(command)
        result = self._parse_pipe_response(response)
        if result['success']:
            # Parse user_id from response
            parts = response.split("|")
            if len(parts) >= 3:
                self.current_user_id = parts[2]  # Extract user_id
            else:
                self.current_user_id = "1"  # Fallback
            print(f"✅ Registration successful - User ID: {self.current_user_id}")
        
        return result

    def login(self, username, password):
        """Login user using pipe protocol format"""
        command = f"LOGIN|{username}|{password}"
        response = self.network.send_protocol_command(command)
        result = self._parse_pipe_response(response)
        
        if result['success']:
            # Parse user_id from response
            parts = response.split("|")
            if len(parts) >= 4:
                self.current_user_id = parts[3]  # Extract user_id
            else:
                self.current_user_id = "1"  # Fallback
            
            self.current_user_data = {'username': username}
            print(f"✅ Login successful - User ID: {self.current_user_id}")
        return result
        
    def logout(self):
        """Logout current user"""
        if not self.current_user_id:
            return {'success': False, 'message': 'No user logged in'}
        
        # Format: USER_LOGOUT|user_id|session_token
        command = f"USER_LOGOUT|{self.current_user_id}|temp_token"
        response = self.network.send_protocol_command(command)
        result = self._parse_pipe_response(response)
        
        if result['success']:
            self.current_user_id = None
            self.current_user_data = None
            self.is_driver = False
        
        return result
    
    # =========================================================================
    # PROFILE METHODS
    # =========================================================================
    
    def create_profile(self, first_name, last_name, phone, area, is_driver, photo_path='default.jpg'):
        """Create user profile"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: PROFILE_CREATE|user_id|first_name|last_name|phone|area|is_driver|photo_path
        command = f"PROFILE_CREATE|{self.current_user_id}|{first_name}|{last_name}|{phone}|{area}|{1 if is_driver else 0}|{photo_path}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def update_profile(self, first_name, last_name, phone, area, is_driver, photo_path=''):
        """Update user profile"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: PROFILE_UPDATE|user_id|first_name|last_name|phone|area|is_driver|photo_path
        command = f"PROFILE_UPDATE|{self.current_user_id}|{first_name}|{last_name}|{phone}|{area}|{1 if is_driver else 0}|{photo_path}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def get_profile(self, user_id=None):
        """Get user profile"""
        uid = user_id or self.current_user_id
        if not uid:
            return {'success': False, 'message': 'No user ID'}
        
        # Format: PROFILE_GET|user_id
        command = f"PROFILE_GET|{uid}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # EMERGENCY CONTACT METHODS
    # =========================================================================
    
    def add_emergency_contact(self, contact_type, contact_value, is_primary=False):
        """Add emergency contact"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: EMERGENCY_CONTACT_ADD|user_id|contact_type|contact_value|is_primary
        command = f"EMERGENCY_CONTACT_ADD|{self.current_user_id}|{contact_type}|{contact_value}|{is_primary}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def get_emergency_contacts(self):
        """Get all emergency contacts for current user"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: EMERGENCY_CONTACT_GET|user_id
        command = f"EMERGENCY_CONTACT_GET|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def remove_emergency_contact(self, contact_id):
        """Remove emergency contact"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: EMERGENCY_CONTACT_REMOVE|contact_id|user_id
        command = f"EMERGENCY_CONTACT_REMOVE|{contact_id}|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def trigger_emergency(self, emergency_type, ride_id='', latitude='', longitude=''):
        """Trigger emergency alert"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: EMERGENCY_TRIGGER|user_id|emergency_type|ride_id|latitude|longitude
        command = f"EMERGENCY_TRIGGER|{self.current_user_id}|{emergency_type}|{ride_id}|{latitude}|{longitude}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # DRIVER METHODS
    # =========================================================================
    
    def save_driver_schedule(self, schedule_json):
        """Save driver schedule"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: DRIVER_SCHEDULE|user_id|schedule_json
        command = f"DRIVER_SCHEDULE|{self.current_user_id}|{schedule_json}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def save_driver_route(self, start_location, end_location):
        """Save driver route"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: DRIVER_ROUTE_SAVE|user_id|start_location|end_location
        command = f"DRIVER_ROUTE_SAVE|{self.current_user_id}|{start_location}|{end_location}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def save_driver_car_info(self, car_model, car_color, license_plate):
        """Save driver car information"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: DRIVER_CAR_INFO|user_id|car_model|car_color|license_plate
        command = f"DRIVER_CAR_INFO|{self.current_user_id}|{car_model}|{car_color}|{license_plate}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def driver_go_online(self, latitude='', longitude=''):
        """Set driver status to online"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: DRIVER_ONLINE|user_id|latitude|longitude
        command = f"DRIVER_ONLINE|{self.current_user_id}|{latitude}|{longitude}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def driver_go_offline(self):
        """Set driver status to offline"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: DRIVER_OFFLINE|user_id
        command = f"DRIVER_OFFLINE|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def get_driver_schedule(self):
        """Get driver schedule"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        command = f"DRIVER_SCHEDULE_GET|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)

    def get_driver_route(self):
        """Get driver route"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        command = f"DRIVER_ROUTE_GET|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)

    def get_driver_car_info(self):
        """Get driver car info"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        command = f"DRIVER_CAR_GET|{self.current_user_id}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # RIDE METHODS
    # =========================================================================
    
    def create_ride_request(self, pickup_area, destination, request_time):
        """Create a new ride request"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RIDE_REQUEST_CREATE|passenger_id|pickup_area|destination|request_time
        command = f"RIDE_REQUEST_CREATE|{self.current_user_id}|{pickup_area}|{destination}|{request_time}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def accept_ride_request(self, request_id, acceptance_time):
        """Accept a ride request as driver"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RIDE_REQUEST_ACCEPT|driver_id|request_id|acceptance_time
        command = f"RIDE_REQUEST_ACCEPT|{self.current_user_id}|{request_id}|{acceptance_time}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def complete_ride(self, request_id, completion_time, fare_final=''):
        """Complete a ride"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RIDE_REQUEST_COMPLETE|request_id|completion_time|fare_final
        command = f"RIDE_REQUEST_COMPLETE|{request_id}|{completion_time}|{fare_final}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def share_ride_location(self, request_id, latitude, longitude, timestamp):
        """Share current GPS location during ride"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RIDE_LOCATION_SHARE|request_id|user_id|latitude|longitude|timestamp
        command = f"RIDE_LOCATION_SHARE|{request_id}|{self.current_user_id}|{latitude}|{longitude}|{timestamp}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def get_ride_history(self, limit=50, offset=0):
        """Get ride history for current user"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RIDE_HISTORY_GET|user_id|limit|offset
        command = f"RIDE_HISTORY_GET|{self.current_user_id}|{limit}|{offset}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # RATING METHODS
    # =========================================================================
    
    def submit_rating(self, request_id, target_id, target_role, rating, comment=''):
        """Submit rating for driver or passenger"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: RATING_SUBMIT|request_id|rater_id|target_id|target_role|rating|comment
        command = f"RATING_SUBMIT|{request_id}|{self.current_user_id}|{target_id}|{target_role}|{rating}|{comment}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    def get_rating(self, target_id, target_role):
        """Get average rating for a user"""
        # Format: RATING_GET|target_id|target_role
        command = f"RATING_GET|{target_id}|{target_role}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # CHAT METHODS
    # =========================================================================
    
    def send_chat_message(self, request_id, message_text, timestamp):
        """Send chat message during ride"""
        if not self.current_user_id:
            return {'success': False, 'message': 'Not logged in'}
        
        # Format: CHAT_MESSAGE_SEND|request_id|sender_id|message_text|timestamp
        # Need to escape pipes in message
        message_text = message_text.replace('|', '\\|')
        command = f"CHAT_MESSAGE_SEND|{request_id}|{self.current_user_id}|{message_text}|{timestamp}"
        response = self.network.send_protocol_command(command)
        return self._parse_pipe_response(response)
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _parse_pipe_response(self, response):
        """Parse pipe-separated responses from server"""
        if not response:
            return {'success': False, 'message': 'Empty response'}
        
        if response.startswith('SUCCESS'):
            parts = response.split('|', 1)
            message = parts[1] if len(parts) > 1 else 'Success'
            return {'success': True, 'message': message, 'raw': response}
        else:
            parts = response.split('|', 1)
            message = parts[1] if len(parts) > 1 else response
            return {'success': False, 'message': message, 'raw': response}

    def send_protocol_command(self, command):
        """Send a protocol command and get response"""
        try:
            self.network.socket.send(command.encode('utf-8'))
            response = self.network.socket.recv(4096).decode('utf-8')
            return response
        except Exception as e:
            print(f"Protocol command error: {e}")
            return f"ERROR|{str(e)}"
    
# Global instance for easy access
server = ServerIntegration()