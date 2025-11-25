import pywhatkit
import requests
import time
import smtplib

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager  # Fixed import

import sys
import os
sys.path.append(os.path.dirname(__file__))
import validator

class FreeEmergencyHandler:
    def __init__(self):
        self.smtp_server = "smtp.gmail.com"
        self.smtp_port = 587
        self.email_sender = "itschazakzm@gmail.com"  
        self.email_password = "HelloWorld1476"  
        self.whatsapp_driver = None
        self.whatsapp_initialized = False
    
    def send_whatsapp_free(self, phone_number, message):
        try:
            clean_number = self.clean_phone_number(phone_number)
            pywhatkit.sendwhatmsg_instantly(clean_number, message, 15, True, 3)
            return True, "WhatsApp message sent"
        except Exception as e:
            return self.send_whatsapp_selenium(phone_number, message)
    
    def send_whatsapp_selenium(self, phone_number, message):
        try:
            if not self.whatsapp_initialized:
                self.init_whatsapp_driver()
            clean_number = self.clean_phone_number(phone_number)
            whatsapp_url = f"https://web.whatsapp.com/send?phone={clean_number}&text={requests.utils.quote(message)}"
            self.whatsapp_driver.get(whatsapp_url)
            wait = WebDriverWait(self.whatsapp_driver, 30)
            send_button = wait.until(EC.element_to_be_clickable((By.XPATH, '//span[@data-icon="send"]')))
            send_button.click()
            time.sleep(5)
            return True, "WhatsApp message sent via Selenium"
        except Exception as e:
            return False, f"WhatsApp failed: {str(e)}"
    
    def init_whatsapp_driver(self):
        try:
            options = webdriver.ChromeOptions()
            options.add_argument("--user-data-dir=./whatsapp_profile")
            options.add_argument("--no-sandbox")
            self.whatsapp_driver = webdriver.Chrome(options=options)
            self.whatsapp_driver.get("https://web.whatsapp.com")
            print("Scan QR code within 30 seconds...")
            time.sleep(30)
            self.whatsapp_initialized = True
        except Exception as e:
            print(f"WhatsApp init failed: {e}")
    
    def send_email_free(self, recipient_email, subject, message):
        try:
            msg =  MIMEMultipart()
            msg['From'] = self.email_sender
            msg['To'] = recipient_email
            msg['Subject'] = subject
            msg.attach(MIMEText(message, 'plain'))
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.email_sender, self.email_password)
            server.send_message(msg)
            server.quit()
            return True, "Email sent"
        except Exception as e:
            return False, f"Email failed: {str(e)}"
    
    def clean_phone_number(self, phone_number):
        clean = ''.join(c for c in phone_number if c.isdigit() or c == '+')
        if not clean.startswith('+'):
            clean = '+1' + clean
        return clean

free_emergency_handler = FreeEmergencyHandler()

def handle_emergency_contact_add(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 5:
            return "ERROR|Invalid format"
        _, user_id, contact_type, contact_value, is_primary = parts
        
        if not validator.validate_user_id(user_id):
            return "ERROR|Invalid user_id"
        if contact_type not in ["WhatsApp", "Email"]:
            return "ERROR|Use 'WhatsApp' or 'Email'"
        
        cursor = conn.cursor()
        if is_primary.lower() in ["true", "1"]:
            cursor.execute("UPDATE emergency_contacts SET is_primary = 0 WHERE user_id = ? AND contact_type = ?", (user_id, contact_type))
        
        cursor.execute("INSERT INTO emergency_contacts (user_id, contact_type, contact_value, is_primary) VALUES (?, ?, ?, ?)", 
                      (user_id, contact_type, contact_value, 1 if is_primary.lower() in ["true", "1"] else 0))
        conn.commit()
        return "SUCCESS|Contact added"
    except Exception as e:
        return f"ERROR|{str(e)}"

def handle_emergency_contact_get(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 2:
            return "ERROR|Invalid format"
        _, user_id = parts
        
        cursor = conn.cursor()
        cursor.execute("SELECT id, contact_type, contact_value, is_primary FROM emergency_contacts WHERE user_id = ? ORDER BY is_primary DESC", (user_id,))
        contacts = cursor.fetchall()
        
        if not contacts:
            return "SUCCESS|No contacts"
        
        contact_list = []
        for contact in contacts:
            contact_id, contact_type, contact_value, is_primary = contact
            contact_list.append(f"{contact_type}|{contact_value}|{is_primary}|{contact_id}")
        
        return f"SUCCESS|{'|'.join(contact_list)}"
    except Exception as e:
        return f"ERROR|{str(e)}"

def handle_emergency_contact_remove(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid format"
        _, contact_id, user_id = parts
        
        cursor = conn.cursor()
        cursor.execute("DELETE FROM emergency_contacts WHERE id = ? AND user_id = ?", (contact_id, user_id))
        conn.commit()
        return "SUCCESS|Contact removed"
    except Exception as e:
        return f"ERROR|{str(e)}"

def handle_emergency_test_contact(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid format"
        _, user_id, contact_id = parts
        
        cursor = conn.cursor()
        cursor.execute("SELECT contact_type, contact_value FROM emergency_contacts WHERE id = ? AND user_id = ?", (contact_id, user_id))
        contact = cursor.fetchone()
        if not contact:
            return "ERROR|Contact not found"
        
        contact_type, contact_value = contact
        test_message = "🔧 TEST: This is a test emergency alert from AU Bus System"
        
        if contact_type == "whatsapp":
            success, detail = free_emergency_handler.send_whatsapp_free(contact_value, test_message)
        elif contact_type == "email":
            success, detail = free_emergency_handler.send_email_free(contact_value, "🔧 Test Emergency Alert", test_message)
        
        if success:
            return f"SUCCESS|Test sent to {contact_type}"
        else:
            return f"ERROR|Test failed: {detail}"
    except Exception as e:
        return f"ERROR|{str(e)}"

def handle_emergency_trigger(data, conn):
    try:
        parts = data.split("|")
        if len(parts) < 3:
            return "ERROR|Invalid format"
        _, user_id, emergency_type = parts[:3]
        ride_id = parts[3] if len(parts) > 3 else None
        latitude = parts[4] if len(parts) > 4 else None
        longitude = parts[5] if len(parts) > 5 else None
        
        cursor = conn.cursor()
        cursor.execute("INSERT INTO emergency_events (user_id, ride_id, emergency_type, location_lat, location_lng) VALUES (?, ?, ?, ?, ?)", 
                      (user_id, ride_id, emergency_type, latitude, longitude))
        emergency_event_id = cursor.lastrowid
        
        cursor.execute("SELECT contact_type, contact_value FROM emergency_contacts WHERE user_id = ? AND is_primary = 1", (user_id,))
        contacts = cursor.fetchall()
        
        if not contacts:
            return "ERROR|No emergency contacts"
        
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user_info = cursor.fetchone()
        user_name = user_info[0] if user_info else "User"
        
        location_info = f"Location: {latitude}, {longitude}" if latitude and longitude else "Unknown location"
        emergency_message = f"🚨 EMERGENCY ALERT 🚨\n\nUser: {user_name}\nType: {emergency_type}\n{location_info}\n\nThis is an automated alert from AU Bus System."
        
        successful_notifications = 0
        for contact in contacts:
            contact_type, contact_value = contact
            if contact_type == "WhatsApp":
                success, detail = free_emergency_handler.send_whatsapp_free(contact_value, emergency_message)
            elif contact_type == "Email":
                success, detail = free_emergency_handler.send_email_free(contact_value, f"🚨 EMERGENCY - {user_name}", emergency_message)
            
            if success:
                successful_notifications += 1
        
        conn.commit()
        return f"SUCCESS|Emergency triggered. Notifications sent: {successful_notifications}"
    except Exception as e:
        return f"ERROR|{str(e)}"

def handle_emergency_resolve(data, conn):
    try:
        parts = data.split("|")
        if len(parts) != 3:
            return "ERROR|Invalid format"
        _, emergency_event_id, user_id = parts
        
        cursor = conn.cursor()
        cursor.execute("UPDATE emergency_events SET status = 'resolved' WHERE id = ? AND user_id = ?", (emergency_event_id, user_id))
        conn.commit()
        return "SUCCESS|Emergency resolved"
    except Exception as e:
        return f"ERROR|{str(e)}"
    
def init_whatsapp_driver(self):
    try:
        options = webdriver.ChromeOptions()
        options.add_argument("--user-data-dir=./whatsapp_profile")
        options.add_argument("--no-sandbox")
        
        # Use webdriver-manager to automatically handle ChromeDriver
        service = Service(ChromeDriverManager().install())
        self.whatsapp_driver = webdriver.Chrome(service=service, options=options)
        
        self.whatsapp_driver.get("https://web.whatsapp.com")
        print("Scan QR code within 30 seconds...")
        time.sleep(30)
        self.whatsapp_initialized = True
    except Exception as e:
        print(f"WhatsApp init failed: {e}")
