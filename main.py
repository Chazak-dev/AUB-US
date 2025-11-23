import sqlite3
import sys 
import os
import re  
import requests
from PyQt5.uic import loadUi 
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QApplication, QWidget, QStackedWidget, QFileDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtWebChannel import QWebChannel
from PyQt5.QtCore import QObject, pyqtSlot
import json
from server_integration import server
from p2p_chat import P2PChat
# Import weather service and config
from weather_service import WeatherService
from config import WEATHER_API_KEY, GOOGLE_MAPS_API_KEY
from gps_tracker import GPSTracker
import threading

# Global widget reference
widget = None

# Define the base directory for UI files
BASE_DIR = os.path.dirname(__file__)

class GeolocationBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    @pyqtSlot(str)
    def postMessage(self, message):
        """Receive messages from JavaScript"""
        try:
            data = json.loads(message)
            if data.get('type') == 'gps_coordinates':
                lat = data['latitude']
                lng = data['longitude']
                print(f"📍 Received real GPS: {lat}, {lng}")
                # Store coordinates for emergency system
                if self.parent:
                    self.parent.last_known_location = (lat, lng)
        except Exception as e:
            print(f"Error processing GPS message: {e}")

class MapWidget(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.last_known_location = (33.8997, 35.4812)  # Default fallback
        self.setup_geolocation_bridge()  
        self.load_map()
    
    def setup_geolocation_bridge(self):
        """Set up the JavaScript-Python bridge for GPS coordinates"""
        # Create channel for communication
        self.channel = QWebChannel(self.page())
        self.page().setWebChannel(self.channel)
        
        # Expose Python object to JavaScript
        self.bridge = GeolocationBridge(self)
        self.channel.registerObject("pyWebView", self.bridge)
        
        # Inject WebChannel JavaScript
        self.page().runJavaScript("""
            // Inject QWebChannel script
            if (typeof Qt === 'undefined') {
                var script = document.createElement('script');
                script.src = 'qrc:///qtwebchannel/qwebchannel.js';
                script.onload = function() {
                    new QWebChannel(qt.webChannelTransport, function(channel) {
                        window.pyWebView = channel.objects.pyWebView;
                        // Now we can call attemptGeolocation()
                        attemptGeolocation();
                    });
                };
                document.head.appendChild(script);
            }
        """)
    
    def load_map(self):
        """Load the Google Maps HTML file with API key"""
        html_path = os.path.join(BASE_DIR, "google_map.html")
        if os.path.exists(html_path):
            # Load the HTML content
            with open(html_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            
            html_content = html_content.replace('YOUR_API_KEY', GOOGLE_MAPS_API_KEY)
            #api_key_param = f"key={GOOGLE_MAPS_API_KEY}"
            #data_url = f"data:text/html;charset=utf-8,{html_content}"
            
            # Load as data URL to avoid local file restrictions
            self.setHtml(html_content)
            print("Map loaded with API key")
        else:
            print(f"Google Maps HTML file not found at: {html_path}")
            self.setHtml("""
                <html>
                    <body style='font-family: Arial; padding: 20px;'>
                        <h2>Map Configuration Error</h2>
                        <p>Google Maps HTML file not found.</p>
                    </body>
                </html>
            """)
    
    def update_driver_location(self, lat, lng):
        """Update driver location on the map"""
        js_code = f"updateDriverLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)
        print(f"Updating driver location: {lat}, {lng}")
    
    def set_student_location(self, lat, lng):
        """Set student pickup location on the map"""
        js_code = f"setStudentLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)
        print(f"Setting student location: {lat}, {lng}")
    
    def set_destination_location(self, lat, lng):
        """Set destination location on the map"""
        js_code = f"setDestinationLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)
        print(f"Setting destination: {lat}, {lng}")
    
    def draw_route(self, start_lat, start_lng, end_lat, end_lng):
        """Draw route between two points"""
        js_code = f"drawRoute({start_lat}, {start_lng}, {end_lat}, {end_lng});"
        self.page().runJavaScript(js_code)
        print(f"Drawing route from ({start_lat}, {start_lng}) to ({end_lat}, {end_lng})")
    
    def geocode_address(self, address):
        """Convert address to coordinates using Google Geocoding API"""
        try:
            url = "https://maps.googleapis.com/maps/api/geocode/json"
            params = {
                'address': address,
                'key': GOOGLE_MAPS_API_KEY
            }
            response = requests.get(url, params=params)
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                print(f"Geocoded '{address}' to: {location['lat']}, {location['lng']}")
                return location['lat'], location['lng']
            else:
                print(f"Geocoding failed for '{address}': {data['status']}")
                # Return default coordinates (AUB) as fallback
                return 33.8997, 35.4812
        except Exception as e:
            print(f"Geocoding error: {e}")
            # Return default coordinates (AUB) as fallback
            return 33.8997, 35.4812 

class WelcomeScreen(QDialog): 
    def __init__(self): 
        """Initial welcome screen with login/signup options"""
        super(WelcomeScreen, self).__init__()
        
        ui_path = os.path.join(BASE_DIR, "welcomescreen.ui")
        loadUi(ui_path, self)

        self.login.clicked.connect(self.gotologin)
        self.createacc.clicked.connect(self.gotocreate)

    def gotologin(self): 
        """Navigate to login screen"""
        login = LoginScreen()
        widget.addWidget(login)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def gotocreate(self): 
        """Navigate to account creation screen"""
        create = CreateAccScreen()
        widget.addWidget(create)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class LoginScreen(QDialog):
    def __init__(self):
        """Login screen for user authentication"""
        super(LoginScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "loginnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login.clicked.connect(self.loginfunction)
        
        # Connect new buttons
        self.backButtonLogin.clicked.connect(self.go_back)
        self.signupLink.mousePressEvent = self.goto_signup

    def loginfunction(self): 
        """Handle user login with validation"""
        user = self.emailfield.text()
        password = self.passwordfield.text()

        if len(user)==0 or len(password)==0: 
            self.error.setText("Please input all fields.")
        else: 
            # Connect to server and authenticate
            if not server.connect():
                self.error.setText("❌ Cannot connect to server")
                return

            # Send login request to server
            result = server.login(user, password)

            if result['success']:
                self.error.setText("")
                self.error.setStyleSheet("color: green;")
                self.error.setText("✅ Login successful!")
                
                # Store user session data
                server.current_user_data = {'username': user, 'email': user}
                
                # Navigate after brief delay
                self.navigate_to_dashboard()
                self.error.setText(f"❌ {result['message']}")

    def navigate_to_dashboard(self):
        main_dashboard = MainDashboard()
        widget.addWidget(main_dashboard)
        widget.setCurrentIndex(widget.currentIndex() + 1)
           

    def go_back(self):
        """Navigate back to welcome screen"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def goto_signup(self, event):
        """Navigate to signup screen"""
        create = CreateAccScreen()
        widget.addWidget(create)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class CreateAccScreen(QDialog):
    def __init__(self):
        """Screen for creating new user account"""
        super(CreateAccScreen,self).__init__()
        ui_path = os.path.join(BASE_DIR, "createaccnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirmpasswordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.signup.clicked.connect(self.signupfunction)

        # Connecting new buttons
        self.backButtonSignup.clicked.connect(self.go_back)
        self.loginLink.mousePressEvent = self.goto_login

    def signupfunction(self): 
        """Handle new user registration with validation"""
        username = self.emailfield.text()
        password = self.passwordfield.text()
        confirmpassword = self.confirmpasswordfield.text()

        print(f"DEBUG: Attempting registration for user: {username}")  # ADD THIS

        if len(username)==0 or len(password)== 0 or len(confirmpassword)==0: 
            self.error.setText("Please input all fields.")
            return
        elif password!=confirmpassword: 
            self.error.setText("Passwords do not match.")
            return
        else:
            # Connect to server
            if not server.connect():
                self.error.setText("❌ Cannot connect to server")
                return
            
            print("DEBUG: Connected to server, sending REGISTER command")  # ADD THIS
            
            # Register user
            result = server.register(
                username=username,
                password=password,
                first_name="Temp",
                last_name="User", 
                address="AUB Campus",
                is_driver=False
            )
            
            print(f"DEBUG: Server response: {result}")  # ADD THIS
            
            if result['success']:
                print("DEBUG: Registration successful, navigating to profile setup...")
                self.error.setText("✅ Account created! Setting up profile...")
                
                server.current_user_id = result['message'].split("|")[-1]
                print(f"DEBUG: Stored user_id: {server.current_user_id}")
    
                # Navigate to profile setup
                QtCore.QTimer.singleShot(1500, self.goto_profile_setup)

    def goto_profile_setup(self):
        print("DEBUG: Navigating to profile setup...")  # ADD THIS
        fillprofile = FillProfileScreen()  
        widget.addWidget(fillprofile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        """Navigate back to welcome screen"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def goto_login(self, event):
        """Navigate to login screen"""
        login = LoginScreen()
        widget.addWidget(login)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class FillProfileScreen(QDialog): 
    def __init__(self):  
        """Screen for completing user profile after registration"""
        super(FillProfileScreen,self).__init__()
        ui_path = os.path.join(BASE_DIR, "trialprofilenew.ui")
        loadUi(ui_path, self)
        
        # Store profile photo path
        self.profile_photo_path = None
        
        # Connect the create button
        self.create.clicked.connect(self.create_profile)
        
        # Connect profile photo click
        self.profilePhoto.mousePressEvent = self.upload_photo
        
        # Set initial profile photo as placeholder
        self.update_profile_photo_display()

    def upload_photo(self, event):
        """Handle profile photo upload via file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Profile Photo", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.profile_photo_path = file_path
            self.update_profile_photo_display()
            print(f"Profile photo selected: {file_path}")
        
        # Call the original mouse press event to maintain normal behavior
        QtWidgets.QLabel.mousePressEvent(self.profilePhoto, event)

    def update_profile_photo_display(self):
        """Update profile photo display with selected image"""
        if self.profile_photo_path:
            try:
                # Load and scale the image to fit the circular label
                pixmap = QPixmap(self.profile_photo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                    )
                    self.profilePhoto.setPixmap(scaled_pixmap)
                    self.profilePhoto.setText("")  # Remove the '+' text
                else:
                    self.show_default_photo()
            except Exception as e:
                print(f"Error loading image: {e}")
                self.show_default_photo()
        else:
            self.show_default_photo()

    def show_default_photo(self):
        """Show default photo placeholder with '+' symbol"""
        self.profilePhoto.clear()
        self.profilePhoto.setText("+")
        self.profilePhoto.setStyleSheet("""
            background-color: white;
            border-radius: 80px;
            border: 2px solid #cccccc;
            font-size: 48px;
            color: #cccccc;
        """)

    def create_profile(self):
        """Validate and save profile information"""
        first_name = self.firstfield.text().strip()
        last_name = self.lastfield.text().strip()
        address = self.addressfield.text().strip()
        is_driver = self.driverCheckbox.isChecked()
        
        phone = "+961 70 000 000" 
        
        # Validation
        if not first_name:
            self.error.setText("Please enter your first name.")
            return
        if not last_name:
            self.error.setText("Please enter your last name.")
            return
        if not address:
            self.error.setText("Please enter your address.")
            return
        
        self.error.setText("")
        
        # Get current user info from server session
        if not server.current_user_id:
            # If no user_id, we need to get it from the server after login/register
            # For now, use a temporary ID (in production, this should be handled properly)
            server.current_user_id = "1"  # TEMPORARY
        
        # Send profile creation request to server
        # Format: PROFILE_CREATE|user_id|first_name|last_name|phone|area|is_driver|photo_path
        command = f"PROFILE_CREATE|{server.current_user_id}|{first_name}|{last_name}||{address}|{1 if is_driver else 0}|{self.profile_photo_path or 'default.jpg'}"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
        
        if result['success']:
            # Update user's is_driver status in main users table too
            print("Profile created successfully!")
            
            # Show success message
            self.error.setStyleSheet("color: green;")
            self.error.setText("Profile created successfully!")
            
            # Navigate to main dashboard after a brief delay
            QtCore.QTimer.singleShot(1000, self.goto_main_dashboard)
        else:
            self.error.setText(f"❌ {result['message']}")


    def goto_main_dashboard(self):
        try:
            print("Navigating to main dashboard...")
            # Use the global widget reference instead of importing
            main_dashboard = MainDashboard()
            widget.addWidget(main_dashboard)
            widget.setCurrentIndex(widget.currentIndex() + 1)
            print("Navigation successful!")
        except Exception as e:
            print(f"Navigation failed: {e}")
class MainDashboard(QDialog):
    def __init__(self):
        """Main application dashboard with ride options and weather"""
        super(MainDashboard, self).__init__()
        
        ui_path = os.path.join(BASE_DIR, "main2.ui")
        loadUi(ui_path, self)
        print("Main dashboard loaded successfully!")
      
        # Store user role (driver/passenger)
        self.is_driver = False
        
        # Initialize Weather Service
        try:
            self.weather_service = WeatherService(WEATHER_API_KEY)
            self.weather_service.weather_updated.connect(self.update_weather_display)
            self.weather_service.start_auto_update(30)
        except Exception as e:
            print(f"Weather service error: {e}")
            self.weather_service = None
        
        # Connect buttons
        self.pushButton.clicked.connect(self.request_ride)
        self.pushButton_2.clicked.connect(self.edit_schedule)
        self.pushButton_3.clicked.connect(self.show_profile)
        self.emergencyContactsButton.clicked.connect(self.show_emergency_contacts)
        
        # Connect driver mode checkbox
        if hasattr(self, 'checkBox'):
            self.checkBox.stateChanged.connect(self.toggle_driver_mode)
        
        self.update_ui_based_on_role()
        self.update_weather_display()

    def show_emergency_contacts(self):
        """Navigate to emergency contacts management screen"""
        print("Opening emergency contacts...")
        emergency_contacts = EmergencyContactsScreen()
        widget.addWidget(emergency_contacts)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def toggle_driver_mode(self, state):
        """Toggle between driver and passenger mode based on checkbox"""
        self.is_driver = (state == Qt.Checked)
        self.update_ui_based_on_role()
        print(f"Driver mode: {self.is_driver}")

    def update_ui_based_on_role(self):
        """Update UI elements based on user role (driver/passenger)"""
        if self.is_driver:
            self.pushButton.setText("Go Online")
            if hasattr(self, 'pushButton_2'):
                self.pushButton_2.setText("Manage Schedule")
                self.pushButton_2.setEnabled(True)
        else:
            self.pushButton.setText("Request Ride")
            if hasattr(self, 'pushButton_2'):
                self.pushButton_2.setText("Edit Schedule")
                self.pushButton_2.setEnabled(False)

    def request_ride(self):
        """Handle ride request or driver going online based on mode"""
        if self.is_driver:
            print("Driver going online...")
            if self.pushButton.text() == "Go Online":
                # Send driver online status to server
                command = f"DRIVER_ONLINE|{server.current_user_id}"
                response = server.network.send_protocol_command(command)
                result = server._parse_pipe_response(response)
                
                if result['success']:
                    self.pushButton.setText("Go Offline")
                    self.pushButton.setStyleSheet("""
                        background-color: rgb(144, 238, 144);
                        border-radius: 40px;
                        font: 63 12pt "Sitka Heading Semibold";
                        padding: 10px;
                    """)
                    driver_online = DriverOnlineScreen()
                    widget.addWidget(driver_online)
                    widget.setCurrentIndex(widget.currentIndex() + 1)
                else:
                    QtWidgets.QMessageBox.warning(self, "Error", 
                        f"Failed to go online: {result['message']}")
            else:
                # Send driver offline status to server
                command = f"DRIVER_OFFLINE|{server.current_user_id}"
                response = server.network.send_protocol_command(command)
                
                self.pushButton.setText("Go Online")
                self.pushButton.setStyleSheet("""
                    background-color: rgb(251, 201, 255);
                    border-radius: 40px;
                    font: 63 12pt "Sitka Heading Semibold";
                    padding: 10px;
                """)
        else:
            print("Requesting ride...")
            active_ride = ActiveRideScreen()
            widget.addWidget(active_ride)
            widget.setCurrentIndex(widget.currentIndex() + 1)

    def edit_schedule(self):
        """Navigate to driver schedule screen"""
        if not self.is_driver:
            QtWidgets.QMessageBox.information(self, "Info", 
                "Driver mode must be enabled to manage schedule.")
            return
            
        print("Opening driver schedule...")
        driver_schedule = DriverScheduleScreen()
        widget.addWidget(driver_schedule)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def show_profile(self):
        """Navigate to user profile screen"""
        print("Showing profile...")
        my_profile = MyProfileScreen()
        widget.addWidget(my_profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def update_weather_display(self, weather_text=None):
        """Update weather display with live data from weather service"""
        if hasattr(self, 'weatherLabel'):
            if weather_text:
                self.weatherLabel.setText(weather_text)
            else:
                if self.weather_service:
                    weather = self.weather_service.get_weather()
                    self.weatherLabel.setText(weather)
                else:
                    self.weatherLabel.setText("🌤️ Weather: -- °C\nCheck connection")
                    
class EmergencyContactsScreen(QDialog):
    def __init__(self):
        """Screen for managing emergency contacts"""
        super(EmergencyContactsScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "emergency_contacts.ui")
        loadUi(ui_path, self)
        
        # Connect buttons
        self.backButton.clicked.connect(self.go_back)
        self.addContactButton.clicked.connect(self.add_contact)
        
        # Load existing contacts
        self.load_contacts()
        
        # Connect list click events
        self.contactsList.itemClicked.connect(self.on_contact_clicked)

    def load_contacts(self):
        """"Load emergency contacts from database"""
        self.contactsList.clear()
        
        if not server.current_user_id:
            return
        
        # Send request to get emergency contacts
        command = f"EMERGENCY_CONTACT_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) > 1 and parts[1] != "No contacts":
                # Parse contacts: type|value|is_primary|id
                for i in range(1, len(parts), 4):
                    if i+3 < len(parts):
                        contact_type = parts[i]
                        contact_value = parts[i+1]
                        is_primary = parts[i+2] == "1"
                        contact_id = parts[i+3]
                        
                        primary_indicator = "⭐ PRIMARY" if is_primary else ""
                        item_text = f"{contact_type}: {contact_value} {primary_indicator}"
                        item = QtWidgets.QListWidgetItem(item_text)
                        item.setData(Qt.UserRole, contact_id)
                        self.contactsList.addItem(item)

    def add_contact(self):
        """Add new emergency contact"""
        contact_type = self.contactTypeCombo.currentText()
        contact_value = self.contactValueField.text().strip()
        is_primary = self.primaryContactCheck.isChecked()
        
        # Validation
        if not contact_value:
            QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                        "Please enter a contact value.")
            return
            
        # Validate contact format based on type
        if contact_type == "WhatsApp" and not self.validate_phone(contact_value):
            QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                        "Please enter a valid phone number for WhatsApp.")
            return
        elif contact_type == "Email" and not self.validate_email(contact_value):
            QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                        "Please enter a valid email address.")
            return
        command = f"EMERGENCY_CONTACT_ADD|{server.current_user_id}|{contact_type}|{contact_value}|{is_primary}"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
            
        if result['success']:
        
            print(f"Emergency contact added: {contact_type} - {contact_value})")
            
            # Show success message
            QtWidgets.QMessageBox.information(self, "Success", 
                                            "Emergency contact added successfully!")
            
            # Clear form and reload contacts
            self.contactValueField.clear()
            self.primaryContactCheck.setChecked(False)
            self.load_contacts()

        else:
            QtWidgets.QMessageBox.critical(self, "Error", result['message'])
            
    def validate_email(self, email):
        """Basic email validation"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_phone(self, phone):
        """Basic phone number validation"""
        import re
        # Remove spaces and special characters for validation
        clean_phone = re.sub(r'[^\d+]', '', phone)
        return len(clean_phone) >= 10

    def on_contact_clicked(self, item):
        """Handle contact item click for removal"""
        contact_id = item.data(Qt.UserRole)
        reply = QtWidgets.QMessageBox.question(self, "Remove Contact", 
                                             "Remove this emergency contact?",
                                             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        
        if reply == QtWidgets.QMessageBox.Yes:
            command = f"EMERGENCY_CONTACT_REMOVE|{contact_id}|{server.current_user_id}"
            response = server.network.send_protocol_command(command)
            result = server._parse_pipe_response(response)
            if result['success']:
                print(f"Emergency contact removed: {contact_id}")
                self.load_contacts()
            else:
                QtWidgets.QMessageBox.critical(self, "Error", result['message'])
    
                
           
    def go_back(self):
        """Navigate back to main dashboard"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class DriverScheduleScreen(QDialog):
    def __init__(self):
        """Screen for drivers to manage their schedule and car info"""
        super(DriverScheduleScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "driver_schedule.ui")
        loadUi(ui_path, self)
        print("Driver Schedule screen loaded successfully!")
        
        # Connect buttons
        self.backButton.clicked.connect(self.go_back)
        self.saveButton.clicked.connect(self.save_schedule)
        
        # Set up initial data
        self.setup_initial_data()

    def setup_initial_data(self):
        """Load existing schedule data from database for current user"""
        if not server.current_user_id:
            print("No user logged in")
            return
        
        # Fetch driver schedule
        command = f"DRIVER_SCHEDULE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            # Parse schedule data if exists
            # Note: You'll need to add DRIVER_SCHEDULE_GET handler to server
            # For now, leave fields empty for new drivers
            print("Schedule data loaded")
        
        # Fetch driver route
        command = f"DRIVER_ROUTE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) >= 3:
                self.startLocation.setText(parts[1])
                self.endLocation.setText(parts[2])
        
        # Fetch driver car info
        command = f"DRIVER_CAR_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) >= 4:
                self.carModel.setText(parts[1])
                self.carColor.setText(parts[2])
                self.licensePlate.setText(parts[3])
        
    print("Initial schedule data loaded")
    def save_schedule(self):
        """Save driver schedule and car information to database"""
        try:
            # Get schedule data
            schedule_data = {}
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
            for day in days:
                check_widget = getattr(self, f'{day}Check')
                start_widget = getattr(self, f'{day}Start')
                end_widget = getattr(self, f'{day}End')
                
                if check_widget.isChecked():
                    schedule_data[day] = {
                        'enabled': True,
                        'start_time': start_widget.time().toString('hh:mm'),
                        'end_time': end_widget.time().toString('hh:mm')
                    }
            
            # Get route information
            start_location = self.startLocation.text().strip()
            end_location = self.endLocation.text().strip()
            
            # Get car information
            car_model = self.carModel.text().strip()
            car_color = self.carColor.text().strip()
            license_plate = self.licensePlate.text().strip()
            
            # Validation
            if not start_location or not end_location:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter route locations.")
                return
            
            if not car_model or not car_color or not license_plate:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter complete car information.")
                return
            
            # Save schedule to server
            import json
            schedule_json = json.dumps(schedule_data)
            command = f"DRIVER_SCHEDULE|{server.current_user_id}|{schedule_json}"
            response = server.network.send_protocol_command(command)
            
            # Save route to server
            command = f"DRIVER_ROUTE_SAVE|{server.current_user_id}|{start_location}|{end_location}"
            response = server.network.send_protocol_command(command)
            
            # Save car info to server
            command = f"DRIVER_CAR_INFO|{server.current_user_id}|{car_model}|{car_color}|{license_plate}"
            response = server.network.send_protocol_command(command)
            result = server._parse_pipe_response(response)
            
            if result['success']:
                print("Schedule, route, and car info saved successfully")
                self.statusLabel.setText("✅ Schedule saved successfully!")
                self.statusLabel.setStyleSheet("color: green;")
                QtWidgets.QMessageBox.information(self, "Success", 
                                                "Your schedule and car information have been saved!")
                QtCore.QTimer.singleShot(3000, lambda: self.statusLabel.setText(""))
            else:
                QtWidgets.QMessageBox.critical(self, "Error", result['message'])
                
        except Exception as e:
            print(f"Error saving schedule: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save: {str(e)}")
    def go_back(self):
        """Navigate back to main dashboard"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)
class MyProfileScreen(QDialog):
    def __init__(self):
        """Screen to display and manage user profile information"""
        super(MyProfileScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "profile_view.ui")
        loadUi(ui_path, self)
        
        # Connect buttons
        self.backButton.clicked.connect(self.go_back)
        self.logoutButton.clicked.connect(self.logout)
        self.rideHistoryButton.clicked.connect(self.show_ride_history)
        self.updateProfileButton.clicked.connect(self.update_profile)  # NEW CONNECTION
        
        # Load user data
        self.load_user_data()

    def load_user_data(self):
        """Load user data from database for display"""
        if not server.current_user_id:
            print("No user logged in")
            return
        
        # Fetch user profile
        command = f"PROFILE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        # Initialize default values
        first_name = "User"
        last_name = ""
        email = server.current_user_data.get('email', '') if server.current_user_data else ''
        phone = ""
        address = ""
        is_driver = False
        profile_photo = None
        
        if "SUCCESS" in response:
            parts = response.split("|")
            # Format: SUCCESS|first_name|last_name|phone|area|is_driver|photo_path
            if len(parts) >= 6:
                first_name = parts[1]
                last_name = parts[2]
                phone = parts[3]
                address = parts[4]
                is_driver = parts[5] == "1" or parts[5].lower() == "true"
                if len(parts) > 6:
                    profile_photo = parts[6]
        
        # Fetch ride statistics
        command = f"PASSENGER_STATS_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        rides_completed = 0
        average_rating = 0.0
        
        if "SUCCESS" in response:
            # Parse stats: SUCCESS|(total_rides, avg_fare, total_spent)
            parts = response.split("|")
            if len(parts) >= 2:
                try:
                    # Extract tuple from response
                    stats_str = parts[1].strip("()")
                    stats_parts = stats_str.split(",")
                    if len(stats_parts) >= 1:
                        rides_completed = int(stats_parts[0]) if stats_parts[0] else 0
                except:
                    rides_completed = 0
        
        # Fetch average rating
        command = f"RATING_GET|{server.current_user_id}|passenger"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response and "Average=" in response:
            try:
                avg_part = response.split("Average=")[1].split("|")[0]
                average_rating = float(avg_part)
            except:
                average_rating = 0.0
        
        # Update UI with user data
        self.userNameLabel.setText(f"👤 {first_name} {last_name}")
        self.emailLabel.setText(f"📧 Email: {email}")
        self.phoneLabel.setText(f"📞 Phone: {phone if phone else 'Not set'}")
        self.addressLabel.setText(f"🏠 Address: {address if address else 'Not set'}")
        
        user_type = "Driver & Passenger" if is_driver else "Passenger"
        self.userTypeLabel.setText(f"🚗 User Type: {user_type}")
        
        self.ridesCompletedLabel.setText(f"✅ {rides_completed} Rides Completed")
        self.ratingLabel.setText(f"⭐ {average_rating:.1f}/5 Average Rating")
        
        if profile_photo and profile_photo != "default.jpg":
            self.load_profile_photo(profile_photo)
            

    def load_profile_photo(self, photo_path):
        """Load and display profile photo from file path"""
        pixmap = QPixmap(photo_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.profilePhoto.setPixmap(scaled_pixmap)
            self.profilePhoto.setText("")

    def update_profile(self):
        """Navigate to update profile screen"""
        print("Navigating to update profile...")
        update_profile = UpdateProfileScreen()
        widget.addWidget(update_profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def logout(self):
        """Handle user logout with confirmation dialog"""
        reply = QtWidgets.QMessageBox.question(self, "Log Out", 
                                             "Are you sure you want to log out?",
                                             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        
        if reply == QtWidgets.QMessageBox.Yes:
            print("User logged out. Returning to welcome screen...")
            
            # Clear all widgets and go back to welcome screen
            while widget.count() > 1:
                widget.removeWidget(widget.widget(1))
            
            welcome = WelcomeScreen()
            widget.addWidget(welcome)
            widget.setCurrentIndex(widget.currentIndex() + 1)

    def show_ride_history(self):
        """Navigate to ride history screen"""
        print("Navigating to ride history...")
        ride_history = RideHistoryScreen()
        widget.addWidget(ride_history)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        """Navigate back to main dashboard"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)


class UpdateProfileScreen(QDialog):
    def __init__(self):
        """Screen for updating user profile information"""
        super(UpdateProfileScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "update_profile.ui")
        loadUi(ui_path, self)
        
        # Connect buttons
        self.backButton.clicked.connect(self.go_back)
        self.saveButton.clicked.connect(self.save_profile)
        self.uploadPhotoButton.clicked.connect(self.upload_photo)
        
        # Store profile photo path
        self.profile_photo_path = None
        
        # Load current user data
        self.load_current_data()

    def load_current_data(self):
        """Load current user data into form fields"""
        if not server.current_user_id:
            print("No user logged in")
            return
        
        # Fetch user profile
        command = f"PROFILE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        # Initialize with defaults
        first_name = ""
        last_name = ""
        email = ""
        phone = ""
        address = ""
        is_driver = False
        profile_photo = None
        
        if "SUCCESS" in response:
            parts = response.split("|")
            # Format: SUCCESS|first_name|last_name|phone|area|is_driver|photo_path
            if len(parts) >= 6:
                first_name = parts[1]
                last_name = parts[2]
                phone = parts[3]
                address = parts[4]
                is_driver = parts[5] == "1" or parts[5].lower() == "true"
                if len(parts) > 6:
                    profile_photo = parts[6]
        
        # Populate form fields with current data
        self.firstNameField.setText(first_name)
        self.lastNameField.setText(last_name)
        self.emailField.setText(email)
        self.phoneField.setText(phone)
        self.addressField.setText(address)
        self.driverCheckbox.setChecked(is_driver)
        
        # Load profile photo if exists
        if profile_photo and profile_photo != "default.jpg":
            self.profile_photo_path = profile_photo
            self.update_profile_photo_display()


    def upload_photo(self):
        """Handle profile photo upload via file dialog"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Select Profile Photo", 
            "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            self.profile_photo_path = file_path
            self.update_profile_photo_display()
            print(f"Profile photo selected: {file_path}")

    def update_profile_photo_display(self):
        """Update profile photo display with selected image"""
        if self.profile_photo_path:
            try:
                # Load and scale the image to fit the circular label
                pixmap = QPixmap(self.profile_photo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                    )
                    self.profilePhoto.setPixmap(scaled_pixmap)
                    self.profilePhoto.setText("")  # Remove any placeholder text
                else:
                    self.show_default_photo()
            except Exception as e:
                print(f"Error loading image: {e}")
                self.show_default_photo()
        else:
            self.show_default_photo()

    def show_default_photo(self):
        """Show default photo placeholder"""
        self.profilePhoto.clear()
        self.profilePhoto.setText("👤")
        self.profilePhoto.setStyleSheet("""
            background-color: #f0f0f0;
            border-radius: 75px;
            border: 3px solid #cccccc;
            font-size: 48px;
        """)

    def save_profile(self):
        """Save updated profile information to database"""
        first_name = self.firstNameField.text().strip()
        last_name = self.lastNameField.text().strip()
        email = self.emailField.text().strip()
        phone = self.phoneField.text().strip()
        address = self.addressField.text().strip()
        is_driver = self.driverCheckbox.isChecked()
        
        # Validation (keep existing validation)
        if not first_name or not last_name or not email or not phone or not address:
            self.errorLabel.setText("Please fill all fields.")
            return
        
        if not self.validate_email(email):
            self.errorLabel.setText("Please enter a valid email address.")
            return
        
        if not self.validate_phone(phone):
            self.errorLabel.setText("Please enter a valid phone number.")
            return
        
        self.errorLabel.setText("")
        
        # Send profile update request to server
        # Format: PROFILE_UPDATE|user_id|first_name|last_name|phone|area|is_driver|photo_path
        command = f"PROFILE_UPDATE|{server.current_user_id}|{first_name}|{last_name}|{phone}|{address}|{1 if is_driver else 0}|{self.profile_photo_path or ''}"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
        
        if result['success']:
            print("Profile updated successfully!")
            self.errorLabel.setStyleSheet("color: green;")
            self.errorLabel.setText("Profile updated successfully!")
            QtCore.QTimer.singleShot(1500, self.go_back)
        else:
            self.errorLabel.setText(f"❌ {result['message']}")
   

    def validate_email(self, email):
        """Basic email validation"""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def validate_phone(self, phone):
        """Basic phone number validation"""
        # Remove spaces and special characters for validation
        clean_phone = re.sub(r'[^\d+]', '', phone)
        return len(clean_phone) >= 10

    def go_back(self):
        """Navigate back to profile screen"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class RideHistoryScreen(QDialog):
    def __init__(self):
        """Screen to display user's ride history"""
        super(RideHistoryScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "ridehistory.ui")
        loadUi(ui_path, self)
        print("Ride History screen loaded successfully!")
        
        # Connect back button
        self.backButton.clicked.connect(self.go_back)
        
        # Load ride history data
        self.load_ride_history()

    def load_ride_history(self):
        """Load ride history data from database for current user"""
        if not server.current_user_id:
            print("No user logged in")
            return
        
        # Send ride history request to server
        command = f"RIDE_HISTORY_GET|{server.current_user_id}|50|0"
        response = server.network.send_protocol_command(command)
        
        ride_history = []
        
        if "SUCCESS" in response:
            # Parse response format from server
            # The server returns rides data in a specific format
            parts = response.split("|")
            if len(parts) > 1:
                # Parse the rides data
                # Format may be: SUCCESS|[(ride1_data), (ride2_data), ...]
                rides_str = "|".join(parts[1:])
                
                # For now, if no rides found, show empty list
                if "No rides" not in rides_str and rides_str.strip():
                    # Try to parse rides (this depends on your server's exact format)
                    # Since server returns database rows, you may need to adjust parsing
                    try:
                        # Assuming server returns stringified list of tuples
                        import ast
                        rides_data = ast.literal_eval(rides_str)
                        
                        for ride in rides_data:
                            # ride format: (id, driver_id, passenger_id, start_time, end_time, fare, status)
                            if len(ride) >= 6:
                                ride_history.append({
                                    'date': ride[3][:10] if ride[3] else 'Unknown',  # Extract date from timestamp
                                    'time': ride[3][11:16] if len(ride[3]) > 11 else 'Unknown',  # Extract time
                                    'driver': 'Driver',  # You'd need to fetch driver name separately
                                    'from': 'Pickup Location',  # Need to fetch from ride_requests table
                                    'to': 'Destination',  # Need to fetch from ride_requests table
                                    'fare': f"${ride[5]}" if ride[5] else '$0',
                                    'rating': '5.0',  # Need to fetch from ratings table
                                    'type': 'driver' if str(ride[1]) == server.current_user_id else 'passenger'
                                })
                    except:
                        pass
        
        # If no rides found or parsing failed, show empty list
        if not ride_history:
            self.rideList.clear()
            no_rides_item = QtWidgets.QListWidgetItem("No rides found. Start using AUBus to see your ride history!")
            self.rideList.addItem(no_rides_item)
        else:
            self.display_rides(ride_history)

    def display_rides(self, rides):
        """Display rides in the list widget with formatted information"""
        self.rideList.clear()
        
        for ride in rides:
            item_text = f"📅 {ride['date']} ⏰ {ride['time']}\n"
            item_text += f"👤 {ride['driver']} • {'🚗 Driver' if ride['type'] == 'driver' else '👥 Passenger'}\n"
            item_text += f"📍 {ride['from']} → {ride['to']}\n"
            item_text += f"💰 {ride['fare']} • ⭐ {ride['rating']}/5"
            
            item = QtWidgets.QListWidgetItem(item_text)
            self.rideList.addItem(item)

    def go_back(self):
        """Navigate back to profile screen"""
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class DriverOnlineScreen(QDialog):
    def __init__(self):
        """Screen for drivers when they go online to accept rides"""
        super(DriverOnlineScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "driver_online.ui")
        loadUi(ui_path, self)
        print("Driver Online screen loaded successfully!")
        
        self.goOfflineButton.clicked.connect(self.go_offline)
        
        self.p2p_chat = P2PChat()
        started = self.p2p_chat.start_chat_server(port=9000)
        if started:
            print("✅ Driver P2P server started on port 9000")
        else:
            print("❌ Failed to start driver P2P server")
        
        self.setup_online_mode()

    def setup_online_mode(self):
        """Fixed: Check for REAL ride requests from server"""
        print("Driver is now online - checking for REAL ride requests...")
        
        # Check for real pending ride requests immediately
        self.check_real_ride_requests()
        
        # Set up timer to check every 5 seconds
        self.request_check_timer = QtCore.QTimer()
        self.request_check_timer.timeout.connect(self.check_real_ride_requests)
        self.request_check_timer.start(5000)  # Check every 5 seconds

    def check_real_ride_requests(self):
        """Check server for REAL pending ride requests"""
        try:
            # Command to get pending ride requests
            command = "RIDE_REQUESTS_GET_PENDING"
            response = server.network.send_protocol_command(command)
            
            print(f"Server response for pending requests: {response}")
            
            if "SUCCESS" in response and "No pending requests" not in response:
                # Parse the real ride requests from server
                # Format: SUCCESS|request_id1|passenger_id1|pickup1|dest1|...|request_id2|...
                parts = response.split("|")
                
                if len(parts) > 1:
                    # Get the first pending request
                    request_id = parts[1]
                    passenger_id = parts[2]
                    pickup_area = parts[3]
                    destination = parts[4]
                    
                    print(f"Found REAL ride request from passenger {passenger_id}")
                    
                    # Show the REAL ride request
                    self.show_real_ride_request(request_id, passenger_id, pickup_area, destination)
                    
            else:
                print("No real pending ride requests found")
                
        except Exception as e:
            print(f"Error checking for ride requests: {e}")

    def show_real_ride_request(self, request_id, passenger_id, pickup_area, destination):
        """Show the real ride request from server"""
        # Stop the checking timer since we found a request
        if hasattr(self, 'request_check_timer'):
            self.request_check_timer.stop()
        
        # Create ride request screen with REAL data
        ride_request = RideRequestScreen()
        
        # Pass the REAL request data
        ride_request.current_request_id = request_id
        ride_request.real_passenger_id = passenger_id
        ride_request.real_pickup_area = pickup_area
        ride_request.real_destination = destination
        
        widget.addWidget(ride_request)
        widget.setCurrentIndex(widget.currentIndex() + 1)
    def update_available_rides(self, count):
        """Update available rides display with current count"""
        current_text = self.statusCard.text()
        new_text = current_text.replace("Available rides in your area: 3", 
                                      f"Available rides in your area: {count}")
        self.statusCard.setText(new_text)

    def go_offline(self):
        """Handle driver going offline and return to dashboard"""
        print("Driver going offline...")
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def simulate_ride_request(self):
        """Simulate receiving a ride request (for demo purposes)"""
        print("Simulating ride request...")
        ride_request = RideRequestScreen()
        widget.addWidget(ride_request)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class RideRequestScreen(QDialog):
    def __init__(self):
        """Screen showing incoming ride request for drivers"""
        super(RideRequestScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "ride_request.ui")
        loadUi(ui_path, self)
        print("Ride Request screen loaded successfully!")
        
        
        self.current_request_id = getattr(self, 'current_request_id', None)
        self.real_passenger_id = getattr(self, 'real_passenger_id', None) 
        self.real_pickup_area = getattr(self, 'real_pickup_area', 'AUB Campus')
        self.real_destination = getattr(self, 'real_destination', 'AUB Main Gate')
        
        print(f"DEBUG: RideRequestScreen initialized with request_id: {self.current_request_id}")
        
        self.acceptButton.clicked.connect(self.accept_ride)
        self.declineButton.clicked.connect(self.decline_ride)
        
        self.timer_count = 30
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        self.setup_ride_data()

    def setup_ride_data(self):
        """Dynamically get passenger data from server for ANY passenger"""
        try:
            # Get the REAL passenger ID from the ride request
            passenger_id = getattr(self, 'real_passenger_id', None)
            
            if passenger_id:
                # Fetch REAL passenger profile from server
                command = f"PROFILE_GET|{passenger_id}"
                response = server.network.send_protocol_command(command)
                
                if "SUCCESS" in response:
                    parts = response.split("|")
                    if len(parts) >= 3:
                        # Dynamic passenger name - works for ANY user
                        passenger_first_name = parts[1]
                        passenger_last_name = parts[2]
                        passenger_name = f"{passenger_first_name} {passenger_last_name}"
                        
                        # Get passenger rating dynamically
                        rating_command = f"RATING_GET|{passenger_id}|passenger"
                        rating_response = server.network.send_protocol_command(rating_command)
                        
                        passenger_rating = "4.9/5"  # Default
                        if "SUCCESS" in rating_response and "Average=" in rating_response:
                            try:
                                avg_part = rating_response.split("Average=")[1].split("|")[0]
                                passenger_rating = f"{avg_part}/5"
                            except:
                                pass
                        
                        # Use real ride data
                        pickup = getattr(self, 'real_pickup_area', 'AUB Campus')
                        destination = getattr(self, 'real_destination', 'AUB Main Gate')
                        
                        self.passengerInfo.setText(f"👤 {passenger_name}\n⭐ {passenger_rating} Rating")
                        self.rideDetails.setText(f"📍 Pickup: {pickup}\n🎯 Destination: {destination}\n📏 Distance: 1.2 km\n💰 Estimated Fare: $5")
                        return
            
            # FALLBACK: Generic display (no hardcoded names)
            self.passengerInfo.setText(f"👤 Passenger\n⭐ 5.0/5 Rating")
            self.rideDetails.setText(f"📍 Pickup: AUB Campus\n🎯 Destination: AUB Main Gate\n📏 Distance: 1.2 km\n💰 Estimated Fare: $5")
            
        except Exception as e:
            print(f"Error setting up ride data: {e}")
            # Generic fallback - NO HARDCODED NAMES
            self.passengerInfo.setText(f"👤 Passenger\n⭐ 5.0/5 Rating")
            self.rideDetails.setText(f"📍 Pickup: AUB Campus\n🎯 Destination: AUB Main Gate\n📏 Distance: 1.2 km\n💰 Estimated Fare: $5")

    def update_timer(self):
        """Update countdown timer for ride request response"""
        self.timer_count -= 1
        self.timerLabel.setText(f"⏰ {self.timer_count} seconds to respond")
        
        if self.timer_count <= 0:
            self.timer.stop()
            self.auto_decline()

    
    def accept_ride(self):
        """✅ FIXED: Handle ride acceptance with proper data passing"""
        if hasattr(self, 'timer'):
            self.timer.stop()
            print("✅ Timer stopped to prevent auto-decline")
            
            
        print("=== DEBUG: accept_ride() called ===")
        
        try:
           # ✅ UPDATE: Get the P2P instance from DriverOnlineScreen
            driver_online_screen = widget.widget(widget.currentIndex() - 1)
            
            # ✅ USE THE INSTANCE VARIABLES that were initialized in __init__
            current_request_id = self.current_request_id
            passenger_id = self.real_passenger_id
            
            print(f"DEBUG: Accepting ride {current_request_id} for passenger {passenger_id}")
            # Send acceptance to server
            if server.current_user_id and hasattr(self, 'current_request_id'):
                from datetime import datetime
                acceptance_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                command = f"RIDE_REQUEST_ACCEPT|{server.current_user_id}|{self.current_request_id}|{acceptance_time}"
                response = server.network.send_protocol_command(command)
                print(f"DEBUG: Ride acceptance response: {response}")
            
            # ✅ UPDATE: Create ActiveRideDriverScreen and PASS the P2P instance
            active_ride_driver = ActiveRideDriverScreen()
            
            # ✅ CRITICAL: Pass the existing P2P instance
            active_ride_driver.p2p_chat = driver_online_screen.p2p_chat
            
            # Pass the ride data
            active_ride_driver.current_ride_id = self.current_ride_id
            active_ride_driver.passenger_id = self.passenger_id
            active_ride_driver.ride_data = {
                'request_id': self.current_ride_id,
                'passenger_id': self.passenger_id,
                'pickup_area': getattr(self, 'real_pickup_area', 'AUB Campus'),
                'destination': getattr(self, 'real_destination', 'AUB Main Gate')
            }
            
            print(f"DEBUG: Successfully passed ride data and P2P instance to driver screen")
            
            # Now navigate
            widget.addWidget(active_ride_driver)
            widget.setCurrentIndex(widget.currentIndex() + 1)
        
        except Exception as e:
            print(f"❌ DEBUG: Error in accept_ride: {e}")
            import traceback
            traceback.print_exc()
            self.return_to_online()
            
    def auto_decline(self):
        """Auto-decline ride when timer runs out"""
        print("Ride auto-declined (timeout). Returning to online mode...")
        self.return_to_online()
        
    def decline_ride(self):
        """Handle ride decline"""
        print("Ride declined!")
        self.timer.stop()
        self.return_to_online()

    def return_to_online(self):
        """Return to driver online screen after ride decision"""
       
        widget.removeWidget(self)
        # Don't create a new DriverOnlineScreen - just go back to the existing one
        widget.setCurrentIndex(widget.currentIndex() - 1)


# -------------------------
# ActiveRideScreen (Passenger)
# -------------------------
class ActiveRideScreen(QDialog):
    def __init__(self):
        """Passenger active ride screen using P2P chat."""
        super(ActiveRideScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "activeride3.ui")
        loadUi(ui_path, self)
        
        
        if server.current_user_id:
            from datetime import datetime
            command = f"RIDE_REQUEST_CREATE|{server.current_user_id}|AUB Campus|AUB Main Gate|{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            response = server.network.send_protocol_command(command)
            print(f"Ride request created: {response}")
        
        
        self.passenger_name = self.get_passenger_name()

        # Map and GPS setup
        self.map_widget = MapWidget()
        if hasattr(self, 'mapLayout'):
            self.mapLayout.addWidget(self.map_widget)
        else:
            print("Warning: mapLayout not found in UI file")

        self.gps_tracker = GPSTracker()
        original_handler = self.gps_tracker._handle_gps_update
        self.gps_tracker._handle_gps_update = lambda data: self.combined_gps_handler(data, original_handler)
        self.gps_tracker.start_tracking_driver(8001)

        # UI buttons
        self.backButton.clicked.connect(self.go_back)
        self.endRideButton.clicked.connect(self.end_ride)
        self.emergencyButton.clicked.connect(self.handle_emergency)
        # use send_p2p_message for P2P
        self.sendButton.clicked.connect(self.send_p2p_message)

        # Chat UI: clear sample placeholder messages
        try:
            # messageDisplay is a QTextEdit or QWebView used in your UI
            self.messageDisplay.setHtml("<html><body><div>No messages yet</div></body></html>")
        except Exception:
            pass

        # Initialize P2P
        self.p2p_chat = P2PChat()
        self.setup_p2p_chat()

        # Load ride data
        self.load_ride_data()

    def load_ride_data(self):
        """Load active ride info for passenger (placeholder behaviour)."""
        if not server.current_user_id:
            print("No user logged in")
            return
        # This can be improved to parse actual ride info from server
        self.statusLabel.setText("🚗 Driver is on the way - ETA: calculating")

    def setup_p2p_chat(self):
        """Passenger: start P2P server and connect to driver"""
        # Set callback first
        self.p2p_chat.set_message_received_callback(self._on_p2p_message_received)

        # Start passenger server on random port
        started = self.p2p_chat.start_chat_server(port=0)
        if not started:
            print("❌ Failed to start passenger P2P server")
            self.statusLabel.setText("❌ Chat unavailable")
            return

        # Try to connect to driver (driver should be on port 9000)
        def try_connect():
            import time
            max_attempts = 8
            for attempt in range(max_attempts):
                if not self.p2p_chat.connected_to_peer:
                    try:
                        print(f"🔗 Attempting to connect to driver... ({attempt + 1}/{max_attempts})")
                        connected = self.p2p_chat.connect_to_peer("localhost", 9000)
                        if connected:
                            print("✅ Connected to driver via P2P")
                            # Update UI to show connected status
                            QtCore.QTimer.singleShot(0, self.update_chat_status_connected)
                            break
                        else:
                            print(f"❌ Connection attempt {attempt + 1} failed")
                    except Exception as e:
                        print(f"❌ Connection error: {e}")
                    
                    time.sleep(2)  # Wait 2 seconds between attempts
            
            if not self.p2p_chat.connected_to_peer:
                print("❌ Could not connect to driver after all attempts")
                QtCore.QTimer.singleShot(0, self.update_chat_status_failed)
                # But we might still receive incoming connection from driver

        # Start connection attempts in background thread
        t = threading.Thread(target=try_connect, daemon=True)
        t.start()

    def _on_p2p_message_received(self, sender, text, timestamp):
        """
        Called from P2PChat listener thread. Move update to Qt main thread.
        """
        QtCore.QTimer.singleShot(0, lambda: self.display_incoming_message(sender, text, timestamp))

    def send_p2p_message(self):
        """Send a chat message via P2P and display it immediately."""
        message_text = self.messageInput.text().strip()
        if not message_text:
            QtWidgets.QMessageBox.warning(self, "Empty Message", "Please enter a message.")
            return

        # Use current user's name if available
        student_name = self.get_passenger_name()

        if not self.p2p_chat.connected_to_peer:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Not connected to peer yet.")
            return

        ok = self.p2p_chat.send_chat_message(message_text, student_name)
        if ok:
            self.display_own_message(message_text)
            self.messageInput.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Send Failed", "Failed to send message. Check connection.")

    def display_own_message(self, message_text):
        """Passenger: Show outgoing messages on the RIGHT (green)"""
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            timestamp = datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: right; margin: 5px;'>
                <div style='background-color: #DCF8C6; padding: 8px; border-radius: 10px; display: inline-block; max-width: 70%;'>
                    <strong>You (Passenger):</strong> {message_text}<br>
                    <small style='color: #666;'>{timestamp}</small>
                </div>
            </div>
            """
            
            self._update_message_display(current_html, new_message)
            
        except Exception as e:
            print(f"❌ Passenger display error: {e}")

    def display_incoming_message(self, sender, message_text, timestamp=None):
        """Passenger: Show incoming driver messages on the LEFT (white)"""
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            ts = timestamp if timestamp else datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: left; margin: 5px;'>
                <div style='background-color: #FFFFFF; padding: 8px; border-radius: 10px; display: inline-block; max-width: 70%; border: 1px solid #e6e6e6;'>
                    <strong>{sender} (Driver):</strong> {message_text}<br>
                    <small style='color: #666;'>{ts}</small>
                </div>
            </div>
            """
            
            self._update_message_display(current_html, new_message)
            
        except Exception as e:
            print(f"❌ Passenger incoming message error: {e}")

    def _update_message_display(self, current_html, new_message):
        """Helper method to update the message display (common for both screens)"""
        if "No messages yet" in current_html:
            self.messageDisplay.setHtml(f"<html><body style='font-family: Arial;'>{new_message}</body></html>")
        else:
            self.messageDisplay.setHtml(current_html + new_message)
        
        # Scroll to bottom
        self.messageDisplay.verticalScrollBar().setValue(
            self.messageDisplay.verticalScrollBar().maximum()
        )


    def get_passenger_name(self):
        if server.current_user_data:
            return server.current_user_data.get('username', 'Passenger')
        return "Passenger"
    
    def handle_emergency(self):
        """Handle emergency with REAL GPS coordinates from Google Maps"""
        try:
            print("🚨 Emergency button clicked - getting real GPS coordinates...")
            
            # Get REAL GPS coordinates from Google Maps
            lat, lon = self.get_real_gps_coordinates()
            
            # Get current ride ID
            ride_id = getattr(self, 'current_ride_id', '')
            
            # Trigger emergency alert with REAL coordinates
            result = server.trigger_emergency(
                emergency_type="Ride Emergency", 
                ride_id=ride_id,
                latitude=str(lat),
                longitude=str(lon)
            )
            
            if result['success']:
                # Create Google Maps link for emergency contacts
                maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                
                QtWidgets.QMessageBox.information(
                    self, 
                    "Emergency Alert Sent", 
                    f"🚨 EMERGENCY ALERT SENT!\n\n"
                    f"📍 Your Location: {lat:.6f}, {lon:.6f}\n"
                    f"📱 Notifications sent to your emergency contacts\n"
                    f"🗺️ Map: {maps_link}"
                )
                print(f"✅ Emergency alert sent with REAL coordinates: {lat}, {lon}")
            else:
                QtWidgets.QMessageBox.critical(
                    self, 
                    "Emergency Failed", 
                    f"Failed to send emergency alert:\n{result['message']}"
                )
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self, 
                "Emergency System Error", 
                f"Could not get GPS location:\n{str(e)}"
            )
            print(f"💥 Emergency GPS error: {e}")
            
    def get_real_gps_coordinates(self):
        """Get real GPS coordinates from the bridge"""
        try:
            # Try to get coordinates from the MapWidget bridge
            if hasattr(self, 'map_widget') and self.map_widget:
                if hasattr(self.map_widget, 'last_known_location'):
                    lat, lon = self.map_widget.last_known_location
                    print(f"📍 Using bridge GPS: {lat}, {lon}")
                    return lat, lon
            
            # Fallback to GPS tracker
            if hasattr(self, 'gps_tracker') and self.gps_tracker:
                return self.gps_tracker._get_current_location()
            
            # Final fallback
            print("⚠️ Using AUB coordinates as fallback")
            return 33.8997, 35.4812
            
        except Exception as e:
            print(f"Real GPS coordinate error: {e}")
            return 33.8997, 35.4812
        
    def update_chat_status_connected(self):
        """Update UI when chat connects successfully"""
        if hasattr(self, 'statusLabel'):
            self.statusLabel.setText("✅ Chat connected with driver")

    def update_chat_status_failed(self):
        """Update UI when chat fails to connect"""  
        if hasattr(self, 'statusLabel'):
            self.statusLabel.setText("❌ Chat unavailable - driver not connected")

    def end_ride(self):
        """End ride flow for passenger"""
        self.gps_tracker.stop_tracking()
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        # complete ride command omitted (use your server logic)
        QtWidgets.QMessageBox.information(self, "Ride Ended", "Thank you for using AUBus!")
        self.go_back()

    def go_back(self):
        """Cleanup and navigate back."""
        try:
            self.gps_tracker.stop_tracking()
        except:
            pass
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)
   


# -------------------------
# ActiveRideDriverScreen (Driver)
# -------------------------
class ActiveRideDriverScreen(QDialog):
    def __init__(self):
        """Driver active ride screen using SHARED P2P chat instance"""
        super(ActiveRideDriverScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "activeride_driver.ui")
        loadUi(ui_path, self)

        # DEBUG: Print what data we received
        print("=== DEBUG: ActiveRideDriverScreen initialized ===")
        print(f"DEBUG: current_ride_id: {getattr(self, 'current_ride_id', 'NOT SET')}")
        print(f"DEBUG: passenger_id: {getattr(self, 'passenger_id', 'NOT SET')}")
        print(f"DEBUG: ride_data: {getattr(self, 'ride_data', 'NOT SET')}")

        # Map and GPS
        self.map_widget = MapWidget()
        if hasattr(self, 'mapLayout'):
            self.mapLayout.addWidget(self.map_widget)
        else:
            print("Warning: mapLayout not found in UI file")

        self.gps_tracker = GPSTracker()
        self.gps_tracker.start_sharing_location(8002)

        # UI buttons
        self.backButton.clicked.connect(self.go_back)
        self.arrivedButton.clicked.connect(self.arrived_at_pickup)
        self.startRideButton.clicked.connect(self.start_ride_to_aub)
        self.completeRideButton.clicked.connect(self.complete_ride)
        self.sendButton.clicked.connect(self.send_p2p_message)
        self.driver_name = self.get_driver_name()

        # Clear sample messages
        try:
            self.messageDisplay.setHtml("<html><body><div>No messages yet</div></body></html>")
        except Exception:
            pass

        # ✅ UPDATE: P2P instance is passed from previous screen - NO NEW SERVER!
        # Just update the callback to point to THIS screen
        if hasattr(self, 'p2p_chat') and self.p2p_chat:
            print("✅ Using shared P2P instance from previous screen")
            self.p2p_chat.set_message_received_callback(self._on_p2p_message_received)
            
            # Check connection status
            if self.p2p_chat.connected_to_peer:
                print("✅ P2P connection is ACTIVE")
                self.statusLabel.setText("✅ Connected to passenger")
            else:
                print("❌ P2P connection is NOT active")
                self.statusLabel.setText("❌ Not connected to passenger")
        else:
            print("❌ ERROR: No P2P instance found!")
            self.p2p_chat = None
            self.statusLabel.setText("❌ Chat unavailable")

        # Load ride info
        self.load_ride_data()

    def load_ride_data(self):
        """Load active ride data with REAL passenger info."""
        if not server.current_user_id:
            print("No user logged in")
            return
        
        # Try to load real passenger data if available
        passenger_id = getattr(self, 'passenger_id', None)
        if passenger_id:
            try:
                # Fetch real passenger profile
                command = f"PROFILE_GET|{passenger_id}"
                response = server.network.send_protocol_command(command)
                
                if "SUCCESS" in response:
                    parts = response.split("|")
                    if len(parts) >= 3:
                        passenger_name = f"{parts[1]} {parts[2]}"
                        self.passengerInfo.setText(f"{passenger_name}\n⭐ 5.0 Rating\n📞 Ready for pickup")
                        self.statusLabel.setText(f"Driving to {parts[1]} - ETA: 5 minutes")
                        return
            except Exception as e:
                print(f"Error loading passenger data: {e}")
        
        # Fallback
        self.passengerInfo.setText("Passenger\n⭐ 5.0 Rating\n📞 N/A")
        self.statusLabel.setText("Driving to pickup - ETA: calculating")
   
    def _on_p2p_message_received(self, sender, text, timestamp=None):
        """Ensure UI updates happen in main thread"""
        print(f"🎯 Driver P2P received: {sender} said '{text}'")
        # Use singleShot to ensure we're in the main Qt thread
        QtCore.QTimer.singleShot(0, lambda: self._safe_display_incoming_message(sender, text, timestamp))  
        
    def update_p2p_callback(self):
        """Update P2P callback to point to this screen"""
        if hasattr(self, 'p2p_chat') and self.p2p_chat:
            self.p2p_chat.set_message_received_callback(self._on_p2p_message_received)
            print("✅ P2P callback updated to current screen")

    def _safe_display_incoming_message(self, sender, text, timestamp):  # ✅ RENAME THIS METHOD
        """Thread-safe message display for INCOMING messages"""
        try:
            print(f"🎯 Displaying message from {sender}: {text}")
            
            current_html = self.messageDisplay.toHtml()
            
            from datetime import datetime
            ts = timestamp if timestamp else datetime.now().strftime('%H:%M')
            
            # ✅ INCOMING messages on LEFT (white background)
            new_message = f"""
            <div style='text-align: left; margin: 10px;'>
                <div style='background-color: #FFFFFF; padding: 10px; border-radius: 15px; display: inline-block; max-width: 70%; border: 2px solid #e6e6e6;'>
                    <strong style='color: #333;'>{sender}:</strong><br>
                    <span style='font-size: 14px;'>{text}</span><br>
                    <small style='color: #888; font-size: 11px;'>{ts}</small>
                </div>
            </div>
            """
            
            if "No messages yet" in current_html or "No messages" in current_html:
                self.messageDisplay.setHtml(f"""
                <html>
                    <body style='font-family: Arial, sans-serif; margin: 0; padding: 10px; background-color: #f5f5f5;'>
                        {new_message}
                    </body>
                </html>
                """)
            else:
                self.messageDisplay.setHtml(current_html + new_message)
            
            # ✅ Force scroll to bottom
            self.messageDisplay.verticalScrollBar().setValue(
                self.messageDisplay.verticalScrollBar().maximum()
            )
            
            print(f"✅ Message from {sender} displayed successfully")
            
        except Exception as e:
            print(f"❌ Driver message display error: {e}")

    def send_p2p_message(self):
        """Send chat message via P2P and display it."""
        message_text = self.messageInput.text().strip()
        if not message_text:
            QtWidgets.QMessageBox.warning(self, "Empty Message", "Please enter a message.")
            return

        driver_name = self.get_driver_name()
        if not self.p2p_chat.connected_to_peer:
            QtWidgets.QMessageBox.warning(self, "No passenger", "No passenger connected yet.")
            return

        ok = self.p2p_chat.send_chat_message(message_text, driver_name)
        if ok:
            self.display_own_message(message_text)
            self.messageInput.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Send Failed", "Failed to send message. Check connection.")

    
    def display_own_message(self, message_text):
        """Driver: Show outgoing messages on the RIGHT (green)"""
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            timestamp = datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: right; margin: 5px;'>
                <div style='background-color: #DCF8C6; padding: 8px; border-radius: 10px; display: inline-block; max-width: 70%;'>
                    <strong>You (Driver):</strong> {message_text}<br>
                    <small style='color: #666;'>{timestamp}</small>
                </div>
            </div>
            """
            
            self._update_message_display(current_html, new_message)
            
        except Exception as e:
            print(f"❌ Driver display error: {e}")



    def get_driver_name(self):
        if server.current_user_data:
            return server.current_user_data.get('username', 'Driver')
        return "Driver"

    def arrived_at_pickup(self):
        self.ride_state = "arrived"
        self.statusLabel.setText("Arrived at pickup - waiting for passenger")
        self.arrivedButton.setEnabled(False)
        self.startRideButton.setEnabled(True)

    def start_ride_to_aub(self):
        self.ride_state = "riding_to_aub"
        self.startRideButton.setEnabled(False)
        self.completeRideButton.setEnabled(True)

    def complete_ride(self):
        self.ride_state = "completed"
        QtWidgets.QMessageBox.information(self, "Ride Completed", "Ride completed successfully!")
        self.go_back()

    def go_back(self):
        """Cleanup and return to dashboard."""
        try:
            self.gps_tracker.stop_sharing_location()
        except:
            pass
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)




# Main application (keep this exactly the same)
app = QApplication(sys.argv)

widget = QStackedWidget()
welcome = WelcomeScreen()
widget.addWidget(welcome)
widget.setFixedWidth(1200)  
widget.setFixedHeight(800)
widget.setWindowTitle("AUBus - Carpool App")
widget.show()  

try:
    sys.exit(app.exec_())
except Exception as e: 
    print(f"Exiting: {e}")