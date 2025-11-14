import sqlite3
import sys 
import os
from PyQt5.uic import loadUi 
from PyQt5 import QtWidgets, QtCore
from PyQt5.QtWidgets import QDialog, QApplication, QWidget, QStackedWidget, QFileDialog
from PyQt5.QtGui import QPixmap
from PyQt5.QtCore import Qt

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'shared'))
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'backend'))

from weather_service import WeatherService
from config import WEATHER_API_KEY
from frontend.network.network_manager import NetworkManager
from frontend.network.message_protocols import create_login_message, create_register_message

widget = None

BASE_DIR = os.path.dirname(__file__)
UI_DIR = os.path.join(BASE_DIR, "ui_files")

class WelcomeScreen(QDialog): 
    def __init__(self):
        super(WelcomeScreen, self).__init__()
        
        ui_path = os.path.join(UI_DIR, "welcomescreen.ui")
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
        ui_path = os.path.join(UI_DIR, "loginnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.login.clicked.connect(self.loginfunction)

    def loginfunction(self): 
        user = self.emailfield.text()
        password = self.passwordfield.text()

        if len(user)==0 or len(password)==0: 
            self.error.setText("Please input all fields.")
        else: 
            print("Login successful! Navigating to main dashboard...")
            main_dashboard = MainDashboard()
            widget.addWidget(main_dashboard)
            widget.setCurrentIndex(widget.currentIndex() + 1)

class CreateAccScreen(QDialog):
    def __init__(self):
        super(CreateAccScreen,self).__init__()
        ui_path = os.path.join(UI_DIR, "createaccnew.ui")
        loadUi(ui_path, self)
        self.passwordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.confirmpasswordfield.setEchoMode(QtWidgets.QLineEdit.Password)
        self.signup.clicked.connect(self.signupfunction)

    def signupfunction(self): 
       user = self.emailfield.text()
       password = self.passwordfield.text()
       confirmpassword = self.confirmpasswordfield.text()

       if len(user)==0 or len(password)== 0 or len(confirmpassword)==0: 
           self.error.setText("Please input all fields.")
       elif password!=confirmpassword: 
           self.error.setText("Passwords do not match.")
       else:
           self.error.setText("")
           print("Account created! Navigating to profile setup...")
           fillprofile = FillProfileScreen()  
           widget.addWidget(fillprofile)
           widget.setCurrentIndex(widget.currentIndex() + 1)

class FillProfileScreen(QDialog): 
    def __init__(self):  
        super(FillProfileScreen,self).__init__()
        ui_path = os.path.join(UI_DIR, "trialprofilenew.ui")
        loadUi(ui_path, self)
        
        self.profile_photo_path = None
        
        self.create.clicked.connect(self.create_profile)
        
        self.profilePhoto.mousePressEvent = self.upload_photo
        
        self.update_profile_photo_display()

    def upload_photo(self, event):
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
        
        QtWidgets.QLabel.mousePressEvent(self.profilePhoto, event)

    def update_profile_photo_display(self):
        if self.profile_photo_path:
            try:
                pixmap = QPixmap(self.profile_photo_path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(
                        150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
                    )
                    self.profilePhoto.setPixmap(scaled_pixmap)
                    self.profilePhoto.setText("")
                else:
                    self.show_default_photo()
            except Exception as e:
                print(f"Error loading image: {e}")
                self.show_default_photo()
        else:
            self.show_default_photo()

    def show_default_photo(self):
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
        first_name = self.firstfield.text().strip()
        last_name = self.lastfield.text().strip()
        address = self.addressfield.text().strip()
        is_driver = self.driverCheckbox.isChecked()
        
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
        
        profile_data = {
            'first_name': first_name,
            'last_name': last_name,
            'address': address,
            'is_driver': is_driver,
            'photo_path': self.profile_photo_path
        }
        
        print("Profile created successfully!")
        print(f"Profile data: {profile_data}")
        
        self.error.setStyleSheet("color: green;")
        self.error.setText("Profile created successfully!")
        
        QtCore.QTimer.singleShot(1000, self.goto_main_dashboard)

    def goto_main_dashboard(self):
        print("Navigating to main dashboard from profile setup...")
        main_dashboard = MainDashboard()
        widget.addWidget(main_dashboard)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class MainDashboard(QDialog):
    def __init__(self):
        super(MainDashboard, self).__init__()
        try:
            ui_path = os.path.join(UI_DIR, "main.ui")
            loadUi(ui_path, self)
            print("Main dashboard loaded successfully!")
        except Exception as e:
            print(f"Error loading main.ui: {e}")
            try:
                ui_path = os.path.join(UI_DIR, "main2.ui")
                loadUi(ui_path, self)
                print("Main2 dashboard loaded successfully!")
            except Exception as e2:
                print(f"Error loading main2.ui: {e2}")
                return
        
        self.is_driver = False
        
        try:
            self.weather_service = WeatherService(WEATHER_API_KEY)
            self.weather_service.weather_updated.connect(self.update_weather_display)
            self.weather_service.start_auto_update(30)
        except Exception as e:
            print(f"Weather service error: {e}")
            self.weather_service = None
        
        self.pushButton.clicked.connect(self.request_ride)
        self.pushButton_2.clicked.connect(self.edit_schedule)
        self.pushButton_3.clicked.connect(self.show_profile)
        
        if hasattr(self, 'checkBox'):
            self.checkBox.stateChanged.connect(self.toggle_driver_mode)
        
        self.update_ui_based_on_role()
        self.update_weather_display()

    def toggle_driver_mode(self, state):
        self.is_driver = (state == Qt.Checked)
        self.update_ui_based_on_role()
        print(f"Driver mode: {self.is_driver}")

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
            print("Driver going online...")
            if self.pushButton.text() == "Go Online":
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
        if self.is_driver:
            print("Opening schedule management...")
            schedule_screen = DriverScheduleScreen()
            widget.addWidget(schedule_screen)
            widget.setCurrentIndex(widget.currentIndex() + 1)
        else:
            QtWidgets.QMessageBox.information(self, "Schedule", 
                                            "Schedule editing is only available for drivers.\n\n"
                                            "Please enable driver mode to manage your schedule.")

    def show_profile(self):
        my_profile = MyProfileScreen()
        widget.addWidget(my_profile)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def update_weather_display(self, weather_text=None):
        if hasattr(self, 'weatherLabel'):
            if weather_text:
                self.weatherLabel.setText(weather_text)
            else:
                if self.weather_service:
                    weather = self.weather_service.get_weather()
                    self.weatherLabel.setText(weather)
                else:
                    self.weatherLabel.setText("🌤️ Weather: -- °C\nCheck connection")

class DriverScheduleScreen(QDialog):
    def __init__(self):
        super(DriverScheduleScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "driver_schedule.ui")
        loadUi(ui_path, self)
        print("Driver Schedule screen loaded successfully!")
        
        self.backButton.clicked.connect(self.go_back)
        self.saveButton.clicked.connect(self.save_schedule)
        
        self.setup_initial_data()

    def setup_initial_data(self):
        self.carModel.setText("Toyota Corolla")
        self.carColor.setText("White")
        self.licensePlate.setText("ABC 123")
        
        self.startLocation.setText("Hamra, Beirut")
        self.endLocation.setText("AUB Main Gate")
        
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
                        'start': start_widget.time().toString('hh:mm'),
                        'end': end_widget.time().toString('hh:mm')
                    }
            
            route_data = {
                'start_location': self.startLocation.text().strip(),
                'end_location': self.endLocation.text().strip()
            }
            
            car_data = {
                'model': self.carModel.text().strip(),
                'color': self.carColor.text().strip(),
                'license_plate': self.licensePlate.text().strip()
            }
            
            if not route_data['start_location']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter a starting location.")
                return
                
            if not route_data['end_location']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter a destination.")
                return
                
            if not car_data['model']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter your car model.")
                return
                
            if not car_data['color']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter your car color.")
                return
                
            if not car_data['license_plate']:
                QtWidgets.QMessageBox.warning(self, "Validation Error", 
                                            "Please enter your license plate number.")
                return
            
            print("Saving schedule data...")
            print(f"Schedule: {schedule_data}")
            print(f"Route: {route_data}")
            print(f"Car: {car_data}")
            
            self.statusLabel.setText("✅ Schedule saved successfully!")
            self.statusLabel.setStyleSheet("color: green;")
            
            QtWidgets.QMessageBox.information(self, "Success", 
                                            "Your schedule and car information have been saved successfully!")
            
            QtCore.QTimer.singleShot(3000, lambda: self.statusLabel.setText(""))
            
        except Exception as e:
            print(f"Error saving schedule: {e}")
            QtWidgets.QMessageBox.critical(self, "Error", 
                                         f"Failed to save schedule: {str(e)}")

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class MyProfileScreen(QDialog):
    def __init__(self):
        super(MyProfileScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "profile_view.ui")
        loadUi(ui_path, self)
        
        self.backButton.clicked.connect(self.go_back)
        self.logoutButton.clicked.connect(self.logout)
        self.rideHistoryButton.clicked.connect(self.show_ride_history)
        
        self.load_user_data()

    def load_user_data(self):
        user_data = {
            'first_name': 'Aya',
            'last_name': 'Halawi',
            'email': 'ahh100@mail.aub.edu',
            'phone': '+961 76 123 456',
            'address': 'Hamra, Beirut',
            'is_driver': True,
            'profile_photo': None,
            'rides_completed': 24,
            'average_rating': 4.8,
        }
        
        self.userNameLabel.setText(f"👤 {user_data['first_name']} {user_data['last_name']}")
        self.emailLabel.setText(f"📧 Email: {user_data['email']}")
        self.phoneLabel.setText(f"📞 Phone: {user_data['phone']}")
        self.addressLabel.setText(f"📍 Address: {user_data['address']}")
        
        user_type = "Driver & Passenger" if user_data['is_driver'] else "Passenger"
        self.userTypeLabel.setText(f"🚗 User Type: {user_type}")
        
        self.ridesCompletedLabel.setText(f"✅ {user_data['rides_completed']} Rides Completed")
        self.ratingLabel.setText(f"⭐ {user_data['average_rating']}/5 Average Rating")
        
        if user_data['profile_photo']:
            self.load_profile_photo(user_data['profile_photo'])

    def load_profile_photo(self, photo_path):
        pixmap = QPixmap(photo_path)
        if not pixmap.isNull():
            scaled_pixmap = pixmap.scaled(
                150, 150, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation
            )
            self.profilePhoto.setPixmap(scaled_pixmap)
            self.profilePhoto.setText("")

    def logout(self):
        reply = QtWidgets.QMessageBox.question(self, "Log Out", 
                                             "Are you sure you want to log out?",
                                             QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
        
        if reply == QtWidgets.QMessageBox.Yes:
            print("User logged out. Returning to welcome screen...")
            
            while widget.count() > 1:
                widget.removeWidget(widget.widget(1))
            
            welcome = WelcomeScreen()
            widget.addWidget(welcome)
            widget.setCurrentIndex(widget.currentIndex() + 1)

    def show_ride_history(self):
        print("Navigating to ride history...")
        ride_history = RideHistoryScreen()
        widget.addWidget(ride_history)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class RideHistoryScreen(QDialog):
    def __init__(self):
        super(RideHistoryScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "ridehistory.ui")
        loadUi(ui_path, self)
        print("Ride History screen loaded successfully!")
        
        self.backButton.clicked.connect(self.go_back)
        
        self.load_ride_history()

    def load_ride_history(self):
        ride_history = [
            {
                'date': '2024-01-15',
                'time': '08:30 AM',
                'driver': 'Chaza',
                'from': 'Hamra, Beirut',
                'to': 'AUB Main Gate',
                'fare': '$5',
                'rating': '5.0',
                'type': 'passenger'
            },
            {
                'date': '2024-01-14',
                'time': '04:15 PM',
                'driver': 'Aya Halawi',
                'from': 'AUB Campus',
                'to': 'Verdun, Beirut',
                'fare': '$6',
                'rating': '4.8',
                'type': 'passenger'
            },
            {
                'date': '2024-01-13',
                'time': '09:00 AM',
                'driver': 'You',
                'from': 'Hamra, Beirut',
                'to': 'AUB Main Gate',
                'fare': '$25',
                'rating': '4.9',
                'type': 'driver'
            }
        ]
        
        self.display_rides(ride_history)

    def display_rides(self, rides):
        self.rideList.clear()
        
        for ride in rides:
            item_text = f"📅 {ride['date']} ⏰ {ride['time']}\n"
            item_text += f"👤 {ride['driver']} • {'🚗 Driver' if ride['type'] == 'driver' else '👥 Passenger'}\n"
            item_text += f"📍 {ride['from']} → {ride['to']}\n"
            item_text += f"💰 {ride['fare']} • ⭐ {ride['rating']}/5"
            
            item = QtWidgets.QListWidgetItem(item_text)
            self.rideList.addItem(item)

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class DriverOnlineScreen(QDialog):
    def __init__(self):
        super(DriverOnlineScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "driver_online.ui")
        loadUi(ui_path, self)
        print("Driver Online screen loaded successfully!")
        
        self.goOfflineButton.clicked.connect(self.go_offline)
        self.setup_online_mode()

    def setup_online_mode(self):
        print("Driver Aya is now online - listening for ride requests...")
        QtCore.QTimer.singleShot(5000, self.simulate_ride_request)
        available_rides = 3
        self.update_available_rides(available_rides)

    def update_available_rides(self, count):
        current_text = self.statusCard.text()
        new_text = current_text.replace("Available rides in your area: 3", 
                                      f"Available rides in your area: {count}")
        self.statusCard.setText(new_text)

    def go_offline(self):
        print("Driver going offline...")
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def simulate_ride_request(self):
        print("Simulating ride request...")
        ride_request = RideRequestScreen()
        widget.addWidget(ride_request)
        widget.setCurrentIndex(widget.currentIndex() + 1)

class RideRequestScreen(QDialog):
    def __init__(self):
        super(RideRequestScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "ride_request.ui")
        loadUi(ui_path, self)
        print("Ride Request screen loaded successfully!")
        
        self.acceptButton.clicked.connect(self.accept_ride)
        self.declineButton.clicked.connect(self.decline_ride)
        
        self.timer_count = 30
        self.timer = QtCore.QTimer()
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)
        
        self.setup_ride_data()

    def setup_ride_data(self):
        passenger_name = "Ayat"
        passenger_rating = "4.9/5"
        pickup_location = "AUB Campus"
        distance = "1.2 km"
        estimated_fare = "$5"
        
        self.passengerInfo.setText(f"👤 {passenger_name}\n⭐ {passenger_rating} Rating")
        self.rideDetails.setText(f"📍 Pickup: {pickup_location}\n🎯 Destination: AUB Main Gate\n📏 Distance: {distance}\n💰 Estimated Fare: {estimated_fare}")

    def update_timer(self):
        self.timer_count -= 1
        self.timerLabel.setText(f"⏰ {self.timer_count} seconds to respond")
        
        if self.timer_count <= 0:
            self.timer.stop()
            self.auto_decline()

    def accept_ride(self):
        self.timer.stop()
        print("Ride accepted! Navigating to active ride...")
        active_ride_driver = ActiveRideDriverScreen()
        widget.addWidget(active_ride_driver)
        widget.setCurrentIndex(widget.currentIndex() + 1)

    def decline_ride(self):
        self.timer.stop()
        print("Ride declined. Returning to online mode...")
        self.return_to_online()

    def auto_decline(self):
        print("Ride auto-declined (timeout). Returning to online mode...")
        self.return_to_online()

    def return_to_online(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class ActiveRideDriverScreen(QDialog):
    def __init__(self):
        super(ActiveRideDriverScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "activeride_driver.ui")
        loadUi(ui_path, self)
        print("Active Ride Driver screen loaded successfully!")
        
        self.backButton.clicked.connect(self.go_back)
        self.arrivedButton.clicked.connect(self.arrived_at_pickup)
        self.startRideButton.clicked.connect(self.start_ride_to_aub)
        self.completeRideButton.clicked.connect(self.complete_ride)
        self.sendButton.clicked.connect(self.send_message)
        
        self.setup_ride_data()
        self.ride_state = "driving_to_pickup"

    def setup_ride_data(self):
        passenger_name = "Ayat Ahmad"
        passenger_rating = "4.9/5"
        passenger_phone = "+961 76 789 012"
        estimated_earnings = "$5"
        pickup_eta = "3 minutes"
        
        self.passengerInfo.setText(f"{passenger_name}\n⭐ {passenger_rating} Rating\n📞 {passenger_phone}")
        self.earningsLabel.setText(f"💰 Estimated Earnings: {estimated_earnings}")
        self.statusLabel.setText(f"📍 Driving to pickup - {passenger_name} - ETA: {pickup_eta}")

    def arrived_at_pickup(self):
        self.ride_state = "arrived"
        self.statusLabel.setText("📍 Arrived at pickup - Waiting for passenger")
        self.arrivedButton.setEnabled(False)
        self.startRideButton.setEnabled(True)
        print("Driver arrived at pickup location")

    def start_ride_to_aub(self):
        self.ride_state = "riding_to_aub"
        self.statusLabel.setText("🚀 Riding to AUB - ETA: 8 minutes")
        self.startRideButton.setEnabled(False)
        self.completeRideButton.setEnabled(True)
        print("Ride to AUB started")

    def complete_ride(self):
        self.ride_state = "completed"
        print("Ride completed! Processing payment...")
        
        QtWidgets.QMessageBox.information(self, "Ride Completed", 
                                         "Ride completed successfully!\n\n"
                                         f"Earnings: $5\n"
                                         "Thank you for driving with AUBus!")
        
        self.go_back()

    def send_message(self):
        message = self.messageInput.text().strip()
        if message:
            print(f"Message to passenger: {message}")
            self.messageInput.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Empty Message", "Please enter a message to send.")

    def go_back(self):
        if self.ride_state != "completed":
            reply = QtWidgets.QMessageBox.question(self, "Cancel Ride", 
                                                 "Are you sure you want to cancel this ride?",
                                                 QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No)
            if reply == QtWidgets.QMessageBox.Yes:
                print("Ride cancelled by driver")
        
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

class ActiveRideScreen(QDialog):
    def __init__(self):
        super(ActiveRideScreen, self).__init__()
        ui_path = os.path.join(UI_DIR, "activeride2.ui")
        loadUi(ui_path, self)
        print("Active Ride screen loaded successfully!")
        
        self.backButton.clicked.connect(self.go_back)
        self.endRideButton.clicked.connect(self.end_ride)
        self.emergencyButton.clicked.connect(self.emergency)
        self.sendButton.clicked.connect(self.send_message)
        
        self.setup_placeholder_data()

    def setup_placeholder_data(self):
        driver_name = "Chaza"
        car_model = "Toyota Corolla"
        car_color = "White"
        driver_rating = "4.7/5"
        eta = "4 minutes"
        
        self.chatHeader.setText(f"💬 Chat with {driver_name} (Driver)")
        self.rideInfo.setText(f"🚗 {car_model} ({car_color})\n⭐ {driver_name} - {driver_rating} Rating")
        self.statusLabel.setText(f"🚗 Driver is on the way - ETA: {eta}")

    def go_back(self):
        widget.removeWidget(self)
        widget.setCurrentIndex(widget.currentIndex() - 1)

    def end_ride(self):
        print("Ending ride...")
        QtWidgets.QMessageBox.information(self, "Ride Ended", "Thank you for using AUBus!")
        self.go_back()

    def emergency(self):
        print("Emergency button pressed!")
        QtWidgets.QMessageBox.warning(self, "Emergency", "Emergency services have been notified!")

    def send_message(self):
        message = self.messageInput.text().strip()
        if message:
            print(f"Message sent: {message}")
            self.messageInput.clear()
        else:
            QtWidgets.QMessageBox.warning(self, "Empty Message", "Please enter a message to send.")

app = QApplication(sys.argv)

network_manager = NetworkManager()

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
    