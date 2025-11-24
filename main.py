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
from weather_service import WeatherService
from config import WEATHER_API_KEY, GOOGLE_MAPS_API_KEY
from gps_tracker import GPSTracker
import threading

widget = None
BASE_DIR = os.path.dirname(__file__)

class GeolocationBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
    
    @pyqtSlot(str)
    def postMessage(self, message):
        try:
            data = json.loads(message)
            if data.get('type') == 'gps_coordinates':
                lat = data['latitude']
                lng = data['longitude']
                print(f"📍 GPS: {lat}, {lng}")
                if self.parent:
                    self.parent.last_known_location = (lat, lng)
        except Exception as e:
            print(f"GPS error: {e}")

class MapWidget(QWebEngineView):
    def __init__(self):
        super().__init__()
        self.last_known_location = (33.8997, 35.4812)
        self.setup_geolocation_bridge()  
        self.load_map()
    
    def setup_geolocation_bridge(self):
        self.channel = QWebChannel(self.page())
        self.page().setWebChannel(self.channel)
        self.bridge = GeolocationBridge(self)
        self.channel.registerObject("pyWebView", self.bridge)
    
    def load_map(self):
        html_path = os.path.join(BASE_DIR, "google_map.html")
        if os.path.exists(html_path):
            with open(html_path, 'r', encoding='utf-8') as file:
                html_content = file.read()
            html_content = html_content.replace('YOUR_API_KEY', GOOGLE_MAPS_API_KEY)
            self.setHtml(html_content)
            print("Map loaded with API key")
        else:
            print(f"Map file not found: {html_path}")
    
    def update_driver_location(self, lat, lng):
        js_code = f"if (typeof updateDriverLocation === 'function') updateDriverLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)
    
    def set_student_location(self, lat, lng):
        js_code = f"if (typeof setStudentLocation === 'function') setStudentLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)
    
    def set_destination_location(self, lat, lng):
        js_code = f"if (typeof setDestinationLocation === 'function') setDestinationLocation({lat}, {lng});"
        self.page().runJavaScript(js_code)

class WelcomeScreen(QDialog): 
    def __init__(self): 
        super(WelcomeScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "welcomescreen.ui")
        loadUi(ui_path, self)
        self.login.clicked.connect(self.gotologin)
        self.createacc.clicked.connect(self.gotocreate)

    def gotologin(self): 
        login = LoginScreen()
        widget.addWidget(login)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def gotocreate(self): 
        create = CreateAccScreen()
        widget.addWidget(create)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class LoginScreen(QDialog):
    def __init__(self):
        super(LoginScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "loginnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login.clicked.connect(self.loginfunction)
        self.backButtonLogin.clicked.connect(self.go_back)
        self.signupLink.mousePressEvent = self.goto_signup

    def loginfunction(self): 
        user = self.emailfield.text()
        password = self.passwordfield.text()

        if len(user)==0 or len(password)==0: 
            self.error.setText("Please input all fields.")
        else: 
            if not server.connect():
                self.error.setText("❌ Cannot connect to server")
                return

            result = server.login(user, password)

            if result['success']:
                self.error.setText("")
                self.error.setStyleSheet("color: green;")
                self.error.setText("✅ Login successful!")
                server.current_user_data = {'username': user, 'email': user}
                self.navigate_to_dashboard()
            else:
                self.error.setText(f"❌ {result['message']}")

    def navigate_to_dashboard(self):
        main_dashboard = MainDashboard()
        widget.addWidget(main_dashboard)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def goto_signup(self, event):
        create = CreateAccScreen()
        widget.addWidget(create)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class CreateAccScreen(QDialog):
    def __init__(self):
        super(CreateAccScreen,self).__init__()
        ui_path = os.path.join(BASE_DIR, "createaccnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirmpasswordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.signup.clicked.connect(self.signupfunction)
        self.backButtonSignup.clicked.connect(self.go_back)
        self.loginLink.mousePressEvent = self.goto_login

    def signupfunction(self): 
        username = self.emailfield.text()
        password = self.passwordfield.text()
        confirmpassword = self.confirmpasswordfield.text()

        if len(username)==0 or len(password)== 0 or len(confirmpassword)==0: 
            self.error.setText("Please input all fields.")
            return
        elif password!=confirmpassword: 
            self.error.setText("Passwords do not match.")
            return
        else:
            if not server.connect():
                self.error.setText("❌ Cannot connect to server")
                return
            
            result = server.register(
                username=username,
                password=password,
                first_name="Temp",
                last_name="User", 
                address="AUB Campus",
                is_driver=False
            )
            
            if result['success']:
                self.error.setText("✅ Account created! Setting up profile...")
                server.current_user_id = result['message'].split("|")[-1]
                QtCore.QTimer.singleShot(1500, self.goto_profile_setup)

    def goto_profile_setup(self):
        fillprofile = FillProfileScreen()  
        widget.addWidget(fillprofile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def goto_login(self, event):
        login = LoginScreen()
        widget.addWidget(login)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class FillProfileScreen(QDialog): 
    def __init__(self):  
        super(FillProfileScreen,self).__init__()
        ui_path = os.path.join(BASE_DIR, "trialprofilenew.ui")
        loadUi(ui_path, self)
        self.profile_photo_path = None
        self.create.clicked.connect(self.create_profile)
        self.profilePhoto.mousePressEvent = self.upload_photo
        self.update_profile_photo_display()

    def upload_photo(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Profile Photo", "", 
            "Image Files (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if file_path:
            self.profile_photo_path = file_path
            self.update_profile_photo_display()
        QtWidgets.QLabel.mousePressEvent(self.profilePhoto, event)

    def update_profile_photo_display(self):
        if self.profile_photo_path:
            try:
                pixmap = QPixmap(self.profile_photo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
                    self.profilePhoto.setPixmap(scaled_pixmap)
                    self.profilePhoto.setText("")
            except:
                self.show_default_photo()
        else:
            self.show_default_photo()

    def show_default_photo(self):
        self.profilePhoto.clear()
        self.profilePhoto.setText("+")

    def create_profile(self):
        first_name = self.firstfield.text().strip()
        last_name = self.lastfield.text().strip()
        address = self.addressfield.text().strip()
        is_driver = self.driverCheckbox.isChecked()
        
        if not first_name or not last_name or not address:
            self.error.setText("Please fill all fields.")
            return
        
        if not server.current_user_id:
            server.current_user_id = "1"
        
        command = f"PROFILE_CREATE|{server.current_user_id}|{first_name}|{last_name}|+961 70 000 000|{address}|{1 if is_driver else 0}|{self.profile_photo_path or 'default.jpg'}"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
        
        if result['success']:
            self.error.setStyleSheet("color: green;")
            self.error.setText("✅ Profile created!")
            QtCore.QTimer.singleShot(1000, self.goto_main_dashboard)
        else:
            self.error.setText(f"❌ {result['message']}")

    def goto_main_dashboard(self):
        main_dashboard = MainDashboard()
        widget.addWidget(main_dashboard)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class MainDashboard(QDialog):
    def __init__(self):
        super(MainDashboard, self).__init__()
        ui_path = os.path.join(BASE_DIR, "main2.ui")
        loadUi(ui_path, self)
        self.is_driver = False
        
        try:
            self.weather_service = WeatherService(WEATHER_API_KEY)
            self.weather_service.weather_updated.connect(self.update_weather_display)
            self.weather_service.start_auto_update(30)
        except:
            self.weather_service = None
        
        self.pushButton.clicked.connect(self.request_ride)
        self.pushButton_2.clicked.connect(self.edit_schedule)
        self.pushButton_3.clicked.connect(self.show_profile)
        self.emergencyContactsButton.clicked.connect(self.show_emergency_contacts)
        
        if hasattr(self, 'checkBox'):
            self.checkBox.stateChanged.connect(self.toggle_driver_mode)
        
        self.update_ui_based_on_role()
        self.update_weather_display()

    def show_emergency_contacts(self):
        emergency_contacts = EmergencyContactsScreen()
        widget.addWidget(emergency_contacts)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def toggle_driver_mode(self, state):
        self.is_driver = (state == Qt.Checked)
        self.update_ui_based_on_role()

    def update_ui_based_on_role(self):
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
        if self.is_driver:
            if self.pushButton.text() == "Go Online":
                command = f"DRIVER_ONLINE|{server.current_user_id}"
                response = server.network.send_protocol_command(command)
                result = server._parse_pipe_response(response)
                
                if result['success']:
                    self.pushButton.setText("Go Offline")
                    driver_online = DriverOnlineScreen()
                    widget.addWidget(driver_online)
                    widget.setCurrentIndex(widget.currentIndex() + 1)
            else:
                command = f"DRIVER_OFFLINE|{server.current_user_id}"
                server.network.send_protocol_command(command)
                self.pushButton.setText("Go Online")
        else:
            active_ride = ActiveRideScreen()
            widget.addWidget(active_ride)
            widget.setCurrentIndex(widget.currentIndex() + 1)

    def edit_schedule(self):
        if not self.is_driver:
            return
        driver_schedule = DriverScheduleScreen()
        widget.addWidget(driver_schedule)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def show_profile(self):
        my_profile = MyProfileScreen()
        widget.addWidget(my_profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def update_weather_display(self, weather_text=None):
        if hasattr(self, 'weatherLabel'):
            if weather_text:
                self.weatherLabel.setText(weather_text)
            elif self.weather_service:
                weather = self.weather_service.get_weather()
                self.weatherLabel.setText(weather)

class EmergencyContactsScreen(QDialog):
    def __init__(self):
        super(EmergencyContactsScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "emergency_contacts.ui")
        loadUi(ui_path, self)
        self.backButton.clicked.connect(self.go_back)
        self.addContactButton.clicked.connect(self.add_contact)
        self.load_contacts()
        self.contactsList.itemClicked.connect(self.on_contact_clicked)

    def load_contacts(self):
        self.contactsList.clear()
        if not server.current_user_id:
            return
        
        command = f"EMERGENCY_CONTACT_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) > 1 and parts[1] != "No contacts":
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
        contact_type = self.contactTypeCombo.currentText()
        contact_value = self.contactValueField.text().strip()
        is_primary = self.primaryContactCheck.isChecked()
        
        if not contact_value:
            QtWidgets.QMessageBox.warning(self, "Error", "Please enter contact value.")
            return
        
        command = f"EMERGENCY_CONTACT_ADD|{server.current_user_id}|{contact_type}|{contact_value}|{is_primary}"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
        
        if result['success']:
            QtWidgets.QMessageBox.information(self, "Success", "Contact added!")
            self.contactValueField.clear()
            self.primaryContactCheck.setChecked(False)
            self.load_contacts()
        else:
            QtWidgets.QMessageBox.critical(self, "Error", result['message'])

    def on_contact_clicked(self, item):
        contact_id = item.data(Qt.UserRole)
        reply = QtWidgets.QMessageBox.question(self, "Remove Contact", 
                                             "Remove this contact?",
                                             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        
        if reply == QtWidgets.QMessageBox.Yes:
            command = f"EMERGENCY_CONTACT_REMOVE|{contact_id}|{server.current_user_id}"
            response = server.network.send_protocol_command(command)
            result = server._parse_pipe_response(response)
            if result['success']:
                self.load_contacts()

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

# CRITICAL FIXES - ADD TO main.py

class DriverScheduleScreen(QDialog):
    def __init__(self):
        super(DriverScheduleScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "driver_schedule.ui")
        loadUi(ui_path, self)
        self.backButton.clicked.connect(self.go_back)
        self.saveButton.clicked.connect(self.save_schedule)
        self.setup_initial_data()

    def setup_initial_data(self):
        if not server.current_user_id:
            return
        # Load existing data...
        print("Initial schedule data loaded")

    def save_schedule(self):
        try:
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
            
            start_location = self.startLocation.text().strip()
            end_location = self.endLocation.text().strip()
            car_model = self.carModel.text().strip()
            car_color = self.carColor.text().strip()
            license_plate = self.licensePlate.text().strip()
            
            if not start_location or not end_location or not car_model:
                QtWidgets.QMessageBox.warning(self, "Error", "Please fill all fields.")
                return
            
            import json
            schedule_json = json.dumps(schedule_data)
            command = f"DRIVER_SCHEDULE|{server.current_user_id}|{schedule_json}"
            server.network.send_protocol_command(command)
            
            command = f"DRIVER_ROUTE_SAVE|{server.current_user_id}|{start_location}|{end_location}"
            server.network.send_protocol_command(command)
            
            command = f"DRIVER_CAR_INFO|{server.current_user_id}|{car_model}|{car_color}|{license_plate}"
            response = server.network.send_protocol_command(command)
            result = server._parse_pipe_response(response)
            
            if result['success']:
                QtWidgets.QMessageBox.information(self, "Success", "Saved!")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class MyProfileScreen(QDialog):
    def __init__(self):
        super(MyProfileScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "profile_view.ui")
        loadUi(ui_path, self)
        self.backButton.clicked.connect(self.go_back)
        self.logoutButton.clicked.connect(self.logout)
        self.rideHistoryButton.clicked.connect(self.show_ride_history)
        self.updateProfileButton.clicked.connect(self.update_profile)
        self.load_user_data()

    def load_user_data(self):
        if not server.current_user_id:
            return
        
        command = f"PROFILE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        first_name = "User"
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) >= 3:
                first_name = parts[1]
                last_name = parts[2]
                self.userNameLabel.setText(f"👤 {first_name} {last_name}")

    def update_profile(self):
        update_profile = UpdateProfileScreen()
        widget.addWidget(update_profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def logout(self):
        reply = QtWidgets.QMessageBox.question(self, "Log Out", 
                                             "Are you sure?",
                                             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        if reply == QtWidgets.QMessageBox.Yes:
            while widget.count() > 1:
                widget.removeWidget(widget.widget(1))
            welcome = WelcomeScreen()
            widget.addWidget(welcome)
            widget.setCurrentIndex(widget.currentIndex() + 1)

    def show_ride_history(self):
        ride_history = RideHistoryScreen()
        widget.addWidget(ride_history)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class UpdateProfileScreen(QDialog):
    def __init__(self):
        super(UpdateProfileScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "update_profile.ui")
        loadUi(ui_path, self)
        self.backButton.clicked.connect(self.go_back)
        self.saveButton.clicked.connect(self.save_profile)
        self.uploadPhotoButton.clicked.connect(self.upload_photo)
        self.profile_photo_path = None
        self.load_current_data()

    def load_current_data(self):
        if not server.current_user_id:
            return
        
        command = f"PROFILE_GET|{server.current_user_id}"
        response = server.network.send_protocol_command(command)
        
        if "SUCCESS" in response:
            parts = response.split("|")
            if len(parts) >= 6:
                self.firstNameField.setText(parts[1])
                self.lastNameField.setText(parts[2])
                self.phoneField.setText(parts[3] if parts[3] else "")
                self.addressField.setText(parts[4] if parts[4] else "")
                self.driverCheckbox.setChecked(parts[5] == "1")
                self.emailField.setText("")  # Optional

    def upload_photo(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Photo", "", "Image Files (*.png *.jpg *.jpeg)"
        )
        if file_path:
            self.profile_photo_path = file_path

    def save_profile(self):
        first_name = self.firstNameField.text().strip()
        last_name = self.lastNameField.text().strip()
        phone = self.phoneField.text().strip()
        address = self.addressField.text().strip()
        is_driver = self.driverCheckbox.isChecked()
        
        if not first_name or not last_name or not address:
            self.errorLabel.setText("❌ Fill required fields.")
            return
        
        command = f"PROFILE_UPDATE|{server.current_user_id}|{first_name}|{last_name}|{phone}|{address}|{1 if is_driver else 0}|"
        response = server.network.send_protocol_command(command)
        result = server._parse_pipe_response(response)
        
        if result['success']:
            self.errorLabel.setStyleSheet("color: green;")
            self.errorLabel.setText("✅ Updated!")
            QtCore.QTimer.singleShot(1500, self.go_back)
        else:
            self.errorLabel.setText(f"❌ {result['message']}")

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class RideHistoryScreen(QDialog):
    def __init__(self):
        super(RideHistoryScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "ridehistory.ui")
        loadUi(ui_path, self)
        self.backButton.clicked.connect(self.go_back)
        self.load_ride_history()

    def load_ride_history(self):
        if not server.current_user_id:
            return
        self.rideList.clear()
        no_rides_item = QtWidgets.QListWidgetItem("No rides yet. Start using AUBus!")
        self.rideList.addItem(no_rides_item)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

# ====================================
# CRITICAL FIXES FOR RIDE FLOW
# ====================================

class DriverOnlineScreen(QDialog):
    def __init__(self):
        super(DriverOnlineScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "driver_online.ui")
        loadUi(ui_path, self)
        
        self.goOfflineButton.clicked.connect(self.go_offline)
        
        # FIXED: Initialize P2P server
        self.p2p_chat = P2PChat()
        started = self.p2p_chat.start_chat_server(port=9000)
        if started:
            print("✅ Driver P2P server on port 9000")
        else:
            print("❌ Failed to start P2P server")
        
        self.setup_online_mode()

    def setup_online_mode(self):
        print("🚗 Driver online - checking for requests...")
        self.check_real_ride_requests()
        
        self.request_check_timer = QtCore.QTimer()
        self.request_check_timer.timeout.connect(self.check_real_ride_requests)
        self.request_check_timer.start(5000)

    def check_real_ride_requests(self):
        try:
            command = "RIDE_REQUESTS_GET_PENDING"
            response = server.network.send_protocol_command(command)
            
            print(f"DEBUG: Pending requests response: {response}")
            
            if "SUCCESS" in response and "No pending" not in response:
                parts = response.split("|")
                
                if len(parts) >= 5:
                    request_id = parts[1]
                    passenger_id = parts[2]
                    pickup_area = parts[3]
                    destination = parts[4]
                    
                    print(f"✅ Found request ID:{request_id} from passenger {passenger_id}")
                    self.show_real_ride_request(request_id, passenger_id, pickup_area, destination)
                    
        except Exception as e:
            print(f"❌ Check error: {e}")

    def show_real_ride_request(self, request_id, passenger_id, pickup_area, destination):
        if hasattr(self, 'request_check_timer'):
            self.request_check_timer.stop()
        
        ride_request = RideRequestScreen()
        
        # CRITICAL FIX: Set data BEFORE adding widget
        ride_request.current_request_id = request_id
        ride_request.real_passenger_id = passenger_id
        ride_request.real_pickup_area = pickup_area
        ride_request.real_destination = destination
        
        # Reload UI
        ride_request.setup_ride_data()
        
        widget.addWidget(ride_request)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_offline(self):
        if hasattr(self, 'request_check_timer'):
            self.request_check_timer.stop()
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)


class RideRequestScreen(QDialog):
    def __init__(self):
        super(RideRequestScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "ride_request.ui")
        loadUi(ui_path, self)
        
        self.current_request_id = None
        self.real_passenger_id = None
        self.real_pickup_area = 'AUB Campus'
        self.real_destination = 'AUB Main Gate'
        
        self.acceptButton.clicked.connect(self.accept_ride)
        self.declineButton.clicked.connect(self.decline_ride)
        
        self.timer_count = 30
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        self.setup_ride_data()

    def setup_ride_data(self):
        try:
            passenger_id = getattr(self, 'real_passenger_id', None)
            
            if passenger_id:
                command = f"PROFILE_GET|{passenger_id}"
                response = server.network.send_protocol_command(command)
                
                if "SUCCESS" in response:
                    parts = response.split("|")
                    if len(parts) >= 3:
                        passenger_name = f"{parts[1]} {parts[2]}"
                        self.passengerInfo.setText(f"👤 {passenger_name}\n⭐ 5.0/5")
                        
                        pickup = getattr(self, 'real_pickup_area', 'AUB Campus')
                        destination = getattr(self, 'real_destination', 'AUB Main Gate')
                        
                        self.rideDetails.setText(
                            f"📍 Pickup: {pickup}\n🎯 Destination: {destination}\n"
                            f"📏 Distance: 1.2 km\n💰 Fare: $5"
                        )
                        return
            
            self.passengerInfo.setText("👤 Passenger\n⭐ 5.0/5")
            self.rideDetails.setText("📍 Pickup: AUB\n🎯 Destination: AUB Gate")
            
        except Exception as e:
            print(f"Error: {e}")

    def update_timer(self):
        self.timer_count -= 1
        self.timerLabel.setText(f"⏰ {self.timer_count} seconds")
        
        if self.timer_count <= 0:
            self.timer.stop()
            self.decline_ride()

    def accept_ride(self):
        print("=== ACCEPT RIDE CALLED ===")
        if hasattr(self, 'timer'):
            self.timer.stop()
        
        try:
            # Send acceptance
            if server.current_user_id and self.current_request_id:
                from datetime import datetime
                acceptance_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                command = f"RIDE_REQUEST_ACCEPT|{server.current_user_id}|{self.current_request_id}|{acceptance_time}"
                response = server.network.send_protocol_command(command)
                print(f"✅ Acceptance response: {response}")
                
                if "ERROR" in response:
                    QtWidgets.QMessageBox.warning(self, "Error", "Ride already taken!")
                    self.return_to_online()
                    return
            
            # ✅ CRITICAL FIX: Get P2P from DriverOnlineScreen at correct index
            # Current stack: [Welcome, MainDashboard, DriverOnline, RideRequest]
            # So DriverOnline is at currentIndex - 1
            driver_online_screen = None
            current_idx = widget.currentIndex()
            
            # Search backwards for DriverOnlineScreen
            for i in range(current_idx - 1, -1, -1):
                screen = widget.widget(i)
                if isinstance(screen, DriverOnlineScreen):
                    driver_online_screen = screen
                    print(f"✅ Found DriverOnlineScreen at index {i}")
                    break
            
            if not driver_online_screen or not hasattr(driver_online_screen, 'p2p_chat'):
                print("❌ ERROR: No P2P instance in driver online screen!")
                QtWidgets.QMessageBox.critical(self, "Error", "P2P chat not initialized!")
                self.return_to_online()
                return
            
            # Create driver active ride screen
            active_ride_driver = ActiveRideDriverScreen()
            
            # ✅ CRITICAL FIX: Pass P2P instance and ride data BEFORE adding widget
            active_ride_driver.p2p_chat = driver_online_screen.p2p_chat
            active_ride_driver.current_ride_id = self.current_request_id
            active_ride_driver.passenger_id = self.real_passenger_id
            active_ride_driver.ride_data = {
                'request_id': self.current_request_id,
                'passenger_id': self.real_passenger_id,
                'pickup_area': self.real_pickup_area,
                'destination': self.real_destination
            }
            
            print(f"✅ Passed P2P and ride data: {active_ride_driver.ride_data}")
            print(f"✅ P2P instance valid: {active_ride_driver.p2p_chat is not None}")
            print(f"✅ P2P connected: {active_ride_driver.p2p_chat.connected_to_peer if active_ride_driver.p2p_chat else False}")
            
            widget.addWidget(active_ride_driver)
            widget.setCurrentIndex(widget.currentIndex() + 1)
        
        except Exception as e:
            print(f"❌ Accept error: {e}")
            import traceback
            traceback.print_exc()
            self.return_to_online()

    def decline_ride(self):
        self.timer.stop()
        self.return_to_online()

    def return_to_online(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)
        
# ADD TO main.py - ACTIVE RIDE SCREENS
class ActiveRideScreen(QDialog):
    """Passenger active ride screen - Polls for driver acceptance"""
    def __init__(self):
        super(ActiveRideScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "activeride3.ui")
        loadUi(ui_path, self)
        
        # Create REAL ride request
        self.current_ride_id = None
        self.driver_accepted = False
        
        if server.current_user_id:
            from datetime import datetime
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            command = f"RIDE_REQUEST_CREATE|{server.current_user_id}|AUB Campus|AUB Main Gate|{timestamp}"
            response = server.network.send_protocol_command(command)
            print(f"✅ Ride request: {response}")
            
            # ✅ Extract actual request_id from response
            if "SUCCESS" in response:
                # Response format: SUCCESS|Ride request created|<request_id>
                parts = response.split("|")
                if len(parts) >= 3:
                    self.current_ride_id = parts[2]
                    print(f"✅ Created ride request ID: {self.current_ride_id}")
                else:
                    # Fallback - shouldn't happen with fixed server
                    self.current_ride_id = "1"
        
        # Map and GPS
        self.map_widget = MapWidget()
        if hasattr(self, 'mapLayout'):
            self.mapLayout.addWidget(self.map_widget)

        self.gps_tracker = GPSTracker()
        self.gps_tracker.start_tracking_driver(8001)

        # Buttons
        self.backButton.clicked.connect(self.go_back)
        self.endRideButton.clicked.connect(self.end_ride)
        self.emergencyButton.clicked.connect(self.handle_emergency)
        self.sendButton.clicked.connect(self.send_p2p_message)

        self.messageDisplay.setHtml("<html><body><div>Waiting for driver to accept...</div></body></html>")

        # P2P - Will connect after driver accepts
        self.p2p_chat = P2PChat()
        self.p2p_chat.set_message_received_callback(self._on_p2p_message_received)
        
        # ✅ CRITICAL FIX: Poll server for ride acceptance
        self.status_check_timer = QtCore.QTimer()
        self.status_check_timer.timeout.connect(self.check_ride_status)
        self.status_check_timer.start(2000)  # Check every 2 seconds
        
        self.load_ride_data()

    def check_ride_status(self):
        """Poll server to check if driver accepted"""
        try:
            if self.driver_accepted:
                self.status_check_timer.stop()
                return
            
            # Check if ride was accepted
            if not self.current_ride_id:
                return
            
            command = f"RIDE_REQUEST_STATUS|{self.current_ride_id}"
            response = server.network.send_protocol_command(command)
            print(f"📊 Status check: {response}")
            
            # Parse response: SUCCESS|status|driver_id|acceptance_time|locked
            if "SUCCESS" in response:
                parts = response.split("|")
                if len(parts) >= 2:
                    status = parts[1]
                    
                    if status == "accepted":
                        # Driver accepted!
                        print("🎉 Driver accepted the ride!")
                        self.driver_accepted = True
                        self.status_check_timer.stop()
                        
                        # Update UI
                        self.statusLabel.setText("✅ Driver accepted! Connecting...")
                        
                        # Get driver info if available
                        driver_id = parts[2] if len(parts) > 2 and parts[2] != "None" else None
                        if driver_id:
                            self.load_driver_info(driver_id)
                        
                        # Now connect to driver via P2P
                        self.connect_to_driver()
                        
        except Exception as e:
            print(f"Status check error: {e}")

    def load_driver_info(self, driver_id):
        """Load driver information"""
        try:
            command = f"PROFILE_GET|{driver_id}"
            response = server.network.send_protocol_command(command)
            
            if "SUCCESS" in response:
                parts = response.split("|")
                if len(parts) >= 3:
                    driver_name = f"{parts[1]} {parts[2]}"
                    self.statusLabel.setText(f"🚗 {driver_name} is on the way!")
                    
                    # Update ride info
                    if hasattr(self, 'rideInfo'):
                        self.rideInfo.setText(
                            f"👤 Driver: {driver_name}\n"
                            f"⭐ Rating: 4.8/5\n"
                            f"🚗 On the way to pickup"
                        )
        except Exception as e:
            print(f"Driver info error: {e}")

    def connect_to_driver(self):
        """Connect to driver's P2P chat after acceptance"""
        def try_connect():
            import time
            for attempt in range(10):
                try:
                    print(f"🔗 Attempt {attempt + 1} to connect to driver on port 9000...")
                    connected = self.p2p_chat.connect_to_peer("localhost", 9000)
                    if connected:
                        print("✅ Connected to driver!")
                        QtCore.QTimer.singleShot(0, lambda: self.messageDisplay.setHtml(
                            "<html><body><div style='color: green; font-weight: bold; padding: 10px;'>"
                            "✅ Connected to driver! You can chat now.</div></body></html>"
                        ))
                        QtCore.QTimer.singleShot(0, lambda: self.onlineStatus.setText("🟢 Connected"))
                        return
                except Exception as e:
                    print(f"Connection attempt {attempt + 1} failed: {e}")
                time.sleep(2)
            
            print("❌ Could not connect to driver")
            QtCore.QTimer.singleShot(0, lambda: self.messageDisplay.setHtml(
                "<html><body><div style='color: orange; padding: 10px;'>"
                "⚠️ Chat unavailable. Driver may not have chat enabled.</div></body></html>"
            ))
            QtCore.QTimer.singleShot(0, lambda: self.onlineStatus.setText("🟡 Chat Unavailable"))
        
        # Start connection in background
        t = threading.Thread(target=try_connect, daemon=True)
        t.start()

    def _on_p2p_message_received(self, sender, text, timestamp):
        QtCore.QTimer.singleShot(0, lambda: self.display_incoming_message(sender, text, timestamp))

    def send_p2p_message(self):
        message_text = self.messageInput.text().strip()
        if not message_text:
            return

        if not self.driver_accepted:
            QtWidgets.QMessageBox.warning(self, "Not Ready", "Please wait for driver to accept your ride.")
            return

        passenger_name = server.current_user_data.get('username', 'Passenger') if server.current_user_data else 'Passenger'

        if not self.p2p_chat.connected_to_peer:
            QtWidgets.QMessageBox.warning(self, "Not Connected", "Chat is not connected. Driver may not have chat enabled.")
            return

        ok = self.p2p_chat.send_chat_message(message_text, passenger_name)
        if ok:
            self.display_own_message(message_text)
            self.messageInput.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Send Failed", "Message could not be sent.")

    def display_own_message(self, message_text):
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            timestamp = datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: right; margin: 10px;'>
                <div style='background-color: #DCF8C6; padding: 10px; border-radius: 15px; 
                            display: inline-block; max-width: 70%;'>
                    <strong>You:</strong> {message_text}<br>
                    <small style='color: #666;'>{timestamp}</small>
                </div>
            </div>
            """
            
            # Clear initial message if present
            if "Waiting for driver" in current_html or "Connected to driver" in current_html:
                self.messageDisplay.setHtml(f"<html><body>{new_message}</body></html>")
            else:
                self.messageDisplay.setHtml(current_html + new_message)
            
            self.messageDisplay.verticalScrollBar().setValue(
                self.messageDisplay.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Display error: {e}")

    def display_incoming_message(self, sender, message_text, timestamp=None):
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            ts = timestamp if timestamp else datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: left; margin: 10px;'>
                <div style='background-color: #FFFFFF; padding: 10px; border-radius: 15px; 
                            display: inline-block; max-width: 70%; border: 2px solid #e6e6e6;'>
                    <strong style='color: #2196F3;'>{sender}:</strong> {message_text}<br>
                    <small style='color: #666;'>{ts}</small>
                </div>
            </div>
            """
            
            # Clear initial message if present
            if "Waiting for driver" in current_html or "Connected to driver" in current_html:
                self.messageDisplay.setHtml(f"<html><body>{new_message}</body></html>")
            else:
                self.messageDisplay.setHtml(current_html + new_message)
            
            self.messageDisplay.verticalScrollBar().setValue(
                self.messageDisplay.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Display error: {e}")

    def load_ride_data(self):
        if not server.current_user_id:
            return
        self.statusLabel.setText("🚗 Looking for driver...")

    def handle_emergency(self):
        try:
            lat, lon = self.map_widget.last_known_location
            ride_id = getattr(self, 'current_ride_id', '')
            
            result = server.trigger_emergency(
                emergency_type="Ride Emergency", 
                ride_id=ride_id,
                latitude=str(lat),
                longitude=str(lon)
            )
            
            if result['success']:
                maps_link = f"https://www.google.com/maps?q={lat},{lon}"
                QtWidgets.QMessageBox.information(
                    self, "Emergency Alert", 
                    f"🚨 EMERGENCY TRIGGERED!\n📍 Location: {lat:.6f}, {lon:.6f}\n🗺️ Map: {maps_link}"
                )
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", str(e))

    def end_ride(self):
        try:
            self.gps_tracker.stop_tracking()
        except:
            pass
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        if hasattr(self, 'status_check_timer'):
            self.status_check_timer.stop()
        QtWidgets.QMessageBox.information(self, "Ride Ended", "Thank you for using AUBus!")
        self.go_back()

    def go_back(self):
        try:
            self.gps_tracker.stop_tracking()
        except:
            pass
        if hasattr(self, 'p2p_chat'):
            self.p2p_chat.end_chat()
        if hasattr(self, 'status_check_timer'):
            self.status_check_timer.stop()
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class ActiveRideDriverScreen(QDialog):
    """Driver active ride screen"""
    def __init__(self):
        super(ActiveRideDriverScreen, self).__init__()
        ui_path = os.path.join(BASE_DIR, "activeride_driver.ui")
        loadUi(ui_path, self)

        print("=== ActiveRideDriverScreen initialized ===")
        print(f"DEBUG: current_ride_id: {getattr(self, 'current_ride_id', 'NOT SET')}")
        print(f"DEBUG: passenger_id: {getattr(self, 'passenger_id', 'NOT SET')}")
        print(f"DEBUG: p2p_chat: {getattr(self, 'p2p_chat', 'NOT SET')}")

        # Map and GPS
        self.map_widget = MapWidget()
        if hasattr(self, 'mapLayout'):
            self.mapLayout.addWidget(self.map_widget)

        self.gps_tracker = GPSTracker()
        self.gps_tracker.start_sharing_location(8002)

        # Buttons
        self.backButton.clicked.connect(self.go_back)
        self.arrivedButton.clicked.connect(self.arrived_at_pickup)
        self.startRideButton.clicked.connect(self.start_ride_to_aub)
        self.completeRideButton.clicked.connect(self.complete_ride)
        self.sendButton.clicked.connect(self.send_p2p_message)

        self.messageDisplay.setHtml("<html><body><div>No messages yet</div></body></html>")

        # CRITICAL FIX: Check if P2P was passed
        if not hasattr(self, 'p2p_chat') or self.p2p_chat is None:
            print("❌ ERROR: No P2P instance found!")
            self.p2p_chat = None
            self.statusLabel.setText("❌ Chat unavailable")
        else:
            print("✅ Using shared P2P instance")
            self.p2p_chat.set_message_received_callback(self._on_p2p_message_received)
            
            if self.p2p_chat.connected_to_peer:
                print("✅ P2P connection is ACTIVE")
                self.statusLabel.setText("✅ Connected to passenger")
            else:
                print("⚠️ P2P connection not yet active")
                self.statusLabel.setText("⏳ Waiting for passenger connection...")

        self.load_ride_data()

    def load_ride_data(self):
        if not server.current_user_id:
            return
        
        passenger_id = getattr(self, 'passenger_id', None)
        if passenger_id:
            try:
                command = f"PROFILE_GET|{passenger_id}"
                response = server.network.send_protocol_command(command)
                
                if "SUCCESS" in response:
                    parts = response.split("|")
                    if len(parts) >= 3:
                        passenger_name = f"{parts[1]} {parts[2]}"
                        self.passengerInfo.setText(f"{passenger_name}\n⭐ 5.0\n📞 Ready")
                        self.statusLabel.setText(f"Driving to {parts[1]} - ETA: 5 min")
                        return
            except Exception as e:
                print(f"Error loading passenger: {e}")
        
        self.passengerInfo.setText("Passenger\n⭐ 5.0\n📞 N/A")
        self.statusLabel.setText("Driving to pickup")

    def _on_p2p_message_received(self, sender, text, timestamp=None):
        print(f"🎯 Driver received: {sender} said '{text}'")
        QtCore.QTimer.singleShot(0, lambda: self._safe_display_incoming_message(sender, text, timestamp))

    def _safe_display_incoming_message(self, sender, text, timestamp):
        try:
            print(f"Displaying from {sender}: {text}")
            
            current_html = self.messageDisplay.toHtml()
            
            from datetime import datetime
            ts = timestamp if timestamp else datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: left; margin: 10px;'>
                <div style='background-color: #FFFFFF; padding: 10px; border-radius: 15px; 
                            display: inline-block; max-width: 70%; border: 2px solid #e6e6e6;'>
                    <strong style='color: #333;'>{sender}:</strong><br>
                    <span style='font-size: 14px;'>{text}</span><br>
                    <small style='color: #888;'>{ts}</small>
                </div>
            </div>
            """
            
            if "No messages" in current_html:
                self.messageDisplay.setHtml(f"<html><body>{new_message}</body></html>")
            else:
                self.messageDisplay.setHtml(current_html + new_message)
            
            self.messageDisplay.verticalScrollBar().setValue(
                self.messageDisplay.verticalScrollBar().maximum()
            )
            
            print(f"✅ Message displayed")
            
        except Exception as e:
            print(f"❌ Display error: {e}")

    def send_p2p_message(self):
        message_text = self.messageInput.text().strip()
        if not message_text:
            return

        driver_name = server.current_user_data.get('username', 'Driver') if server.current_user_data else 'Driver'
        
        if not self.p2p_chat or not self.p2p_chat.connected_to_peer:
            QtWidgets.QMessageBox.warning(self, "Not connected", "Passenger not connected yet.")
            return

        ok = self.p2p_chat.send_chat_message(message_text, driver_name)
        if ok:
            self.display_own_message(message_text)
            self.messageInput.clear()

    def display_own_message(self, message_text):
        from datetime import datetime
        try:
            current_html = self.messageDisplay.toHtml()
            timestamp = datetime.now().strftime('%H:%M')
            
            new_message = f"""
            <div style='text-align: right; margin: 5px;'>
                <div style='background-color: #DCF8C6; padding: 8px; border-radius: 10px; 
                            display: inline-block; max-width: 70%;'>
                    <strong>You:</strong> {message_text}<br>
                    <small style='color: #666;'>{timestamp}</small>
                </div>
            </div>
            """
            
            if "No messages" in current_html:
                self.messageDisplay.setHtml(f"<html><body>{new_message}</body></html>")
            else:
                self.messageDisplay.setHtml(current_html + new_message)
            
            self.messageDisplay.verticalScrollBar().setValue(
                self.messageDisplay.verticalScrollBar().maximum()
            )
        except Exception as e:
            print(f"Display error: {e}")

    def arrived_at_pickup(self):
        self.statusLabel.setText("Arrived - waiting for passenger")
        self.arrivedButton.setEnabled(False)
        self.startRideButton.setEnabled(True)

    def start_ride_to_aub(self):
        self.statusLabel.setText("Driving to AUB")
        self.startRideButton.setEnabled(False)
        self.completeRideButton.setEnabled(True)

    def complete_ride(self):
        QtWidgets.QMessageBox.information(self, "Ride Complete", "Ride completed!")
        self.go_back()

    def go_back(self):
        try:
            self.gps_tracker.stop_sharing_location()
        except:
            pass
        if hasattr(self, 'p2p_chat') and self.p2p_chat:
            self.p2p_chat.end_chat()
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)


# Main application
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